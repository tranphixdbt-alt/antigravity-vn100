"""
Thu thập khuyến nghị ĐA CÔNG TY CHỨNG KHOÁN từ 24hmoney.vn (nguồn tổng hợp công
khai — SSI, KBSV, BSC, MIRAE, ACBS, VCBS, MBS, VNDS...).

Ưu điểm: dữ liệu nằm trong HTML SSR → lấy bằng httpx (KHÔNG cần Chrome, nhanh,
tự động hoá được cho cả 100 mã). Mỗi mã cho 3–5 báo cáo CTCK gần nhất kèm giá
mục tiêu + khuyến nghị + ngày. Ghi vào consensus_history qua upsert (idempotent,
khoá ticker+broker+report_date).

NGUYÊN TẮC: chỉ lưu số liệu thật đọc được; không bịa. Nguồn ghi kèm để truy vết.
"""
from __future__ import annotations

import datetime
import re
from typing import Any, Dict, List

import httpx
from sqlalchemy.dialects.postgresql import insert

from valuation.db.models import Consensus
from valuation.db.session import SessionLocalWrite

_BASE = "https://24hmoney.vn/stock/"
_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# "Khuyến nghị MUA với giá mục tiêu 103,800 đồng/cổ phiếu Nguồn: KBSV-08/06/2026"
_PATTERN = re.compile(
    r"Khuyến nghị\s+(?P<rating>[^<]{1,30}?)\s+với giá mục tiêu\s+"
    r"(?P<tp>[\d.,]+)\s*đồng.*?Nguồn:\s*(?P<broker>[A-Za-z0-9]+)-"
    r"(?P<date>\d{2}/\d{2}/\d{4})",
    re.IGNORECASE | re.DOTALL,
)


def _parse_tp(s: str) -> float:
    """'103,800' -> 103800.0 (bỏ dấu phân cách nghìn)."""
    return float(s.replace(".", "").replace(",", ""))


def fetch_broker_reports(ticker: str, timeout: float = 20.0) -> List[Dict[str, Any]]:
    """Lấy danh sách khuyến nghị CTCK cho 1 mã từ 24hmoney. KHÔNG ghi DB."""
    url = f"{_BASE}{ticker.upper()}"
    resp = httpx.get(url, headers={"User-Agent": _UA}, timeout=timeout, follow_redirects=True)
    resp.raise_for_status()
    html = resp.text

    seen = set()
    out: List[Dict[str, Any]] = []
    for m in _PATTERN.finditer(html):
        broker = m.group("broker").upper().strip()
        try:
            rep_date = datetime.datetime.strptime(m.group("date"), "%d/%m/%Y").date()
        except ValueError:
            continue
        tp = _parse_tp(m.group("tp"))
        # đơn vị: 24hmoney ghi bằng ĐỒNG (vd 103,800) — giữ nguyên VND
        rating = re.sub(r"\s+", " ", m.group("rating")).strip().upper()
        key = (broker, rep_date)
        if key in seen or tp <= 0:
            continue
        seen.add(key)
        out.append({
            "ticker": ticker.upper(), "broker": broker, "report_date": rep_date,
            "target_price": tp, "rating": rating,
            "source_url": url,
            "raw_quote": f"{broker} {rep_date}: {rating}, giá mục tiêu {tp:,.0f} VND (nguồn 24hmoney)",
        })
    return out


def import_broker_reports(ticker: str) -> List[Dict[str, Any]]:
    """Lấy + ghi khuyến nghị CTCK cho 1 mã vào consensus_history (idempotent)."""
    recs = fetch_broker_reports(ticker)
    if not recs:
        return []
    db = SessionLocalWrite()
    try:
        for rec in recs:
            stmt = insert(Consensus).values(rec)
            stmt = stmt.on_conflict_do_update(
                index_elements=["ticker", "broker", "report_date"],
                set_={
                    "target_price": stmt.excluded.target_price,
                    "rating": stmt.excluded.rating,
                    "source_url": stmt.excluded.source_url,
                    "raw_quote": stmt.excluded.raw_quote,
                },
            )
            db.execute(stmt)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return recs
