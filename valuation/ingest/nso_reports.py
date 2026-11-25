"""Nạp CPI, bán lẻ, GDP Việt Nam từ báo cáo kinh tế – xã hội của Cục Thống kê (nso.gov.vn) — D121.

Vì sao nguồn này:
- Là nguồn gốc của số liệu (tradingeconomics chép lại từ đây). Trước đây CPI, bán lẻ, GDP nạp tay qua Chrome
  (`scripts/refresh_macro_chrome.md`), lần cuối 10/10 và 11/07/2026 → web hiện CPI tháng 9, GDP quý 2.
- tradingeconomics chặn mọi lượt tải tự động (403 cả với trình duyệt headless); không lách lớp chặn đó.
- nso.gov.vn trả HTML thường (httpx đủ, không cần trình duyệt), nhưng chỉ mở được từ IP Việt Nam: job chạy trên
  VPS; từ máy Mac ở nước ngoài thì quá giờ chờ.

Cách đọc: trang danh mục "Báo cáo tình hình kinh tế – xã hội hằng tháng" → `reports_to_read` bài mới nhất → mỗi bài
tìm ĐÚNG ba câu theo mẫu cố định của Cục Thống kê (đối chiếu 26/11/2026 với các bài tháng 6–10/2026):
- "Chỉ số giá tiêu dùng (CPI) tháng Mười tăng 0,20% so với tháng trước; … và tăng 5,09% so với cùng kỳ năm trước."
- "Tổng mức bán lẻ hàng hóa và doanh thu dịch vụ tiêu dùng theo giá hiện hành tháng Mười … tăng 14,7% so với cùng
  kỳ năm trước."
- "Tổng sản phẩm trong nước (GDP) quý III/2026 ước tính tăng 9,95% so với cùng kỳ năm trước" (chỉ bài theo quý).
Không thấy câu thì không ghi gì cho chỉ tiêu đó (không đoán). Năm của tháng suy từ ngày đăng (bài tháng 12 đăng
tháng 1 năm sau).

Quy tắc ghi (như TPCP_10Y, D100): chỉ THÊM kỳ chưa có trong DB; kỳ đã có mà số khác (Cục Thống kê sửa số, vd GDP
quý II/2026: ước tính đầu 8,39%, báo cáo quý III ghi 8,81%) thì KHÔNG ghi đè, chỉ báo trong `revisions` để người
dùng quyết. Ngày lưu = ngày cuối kỳ (tháng/quý), giá trị decimal_rate (5,09% → 0,0509). Ghi qua
`upsert_macro_series` (registry + idempotent). Gỡ: xóa dòng `source='nso.gov.vn'` có `created_at` từ ngày chạy.
"""

from __future__ import annotations

import calendar
import datetime as dt
import html as _html
import logging
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.orm import Session

from valuation.config import load_defaults
from valuation.ingest.macro_store import MacroPoint, upsert_macro_series
from valuation.ingest.tpcp_scraper import _assert_allowed_host

logger = logging.getLogger(__name__)

SOURCE = "nso.gov.vn"
Fetcher = Callable[[str], str]

_MONTHS = {
    "mười hai": 12,
    "mười một": 11,
    "mười": 10,
    "chín": 9,
    "tám": 8,
    "bảy": 7,
    "sáu": 6,
    "năm": 5,
    "tư": 4,
    "ba": 3,
    "hai": 2,
    "một": 1,
    "giêng": 1,
}
_MONTH_RE = "|".join(sorted(_MONTHS, key=len, reverse=True))
_QUARTERS = {"I": 1, "II": 2, "III": 3, "IV": 4}
# Phần giữa câu: mọi ký tự trừ dấu chấm kết câu; dấu chấm giữa hai chữ số (1.005,2) vẫn thuộc câu.
_SENT = r"(?:[^.]|(?<=\d)\.(?=\d))*?"
_YOY = r"(tăng|giảm) ([\d.,]+)% so với cùng kỳ năm trước"

CPI_RE = re.compile(
    rf"Chỉ số giá tiêu dùng \(CPI\s*\) tháng ({_MONTH_RE})(?: năm (\d{{4}}))? {_SENT}{_YOY}",
    re.IGNORECASE,
)
RETAIL_RE = re.compile(
    r"Tổng mức bán lẻ hàng hóa và doanh thu dịch vụ tiêu dùng theo giá hiện hành tháng "
    rf"({_MONTH_RE})(?: năm (\d{{4}}))? {_SENT}{_YOY}",
    re.IGNORECASE,
)
GDP_RE = re.compile(
    rf"Tổng sản phẩm trong nước \(GDP\s*\) quý (IV|III|II|I)/(\d{{4}}){_SENT}"
    r"(tăng|giảm)(?: ước đạt| ước tính)? ([\d.,]+)% so với cùng kỳ năm trước"
)
LINK_RE = re.compile(
    r'href="(https://www\.nso\.gov\.vn/[a-z0-9-]+/(\d{4})/(\d{2})/bao-cao-tinh-hinh-kinh-te-xa-hoi-[a-z0-9-]+/)"'
)


@dataclass(frozen=True)
class NsoConfig:
    list_url: str
    reports_to_read: int
    timeout_sec: float
    sane_range_pct: dict[str, tuple[float, float]]


def load_nso_config() -> NsoConfig:
    cfg = load_defaults()["macro_sources"]["nso_reports"]
    return NsoConfig(
        list_url=str(cfg["list_url"]),
        reports_to_read=int(cfg["reports_to_read"]),
        timeout_sec=float(cfg["timeout_sec"]),
        sane_range_pct={
            k: (float(v[0]), float(v[1])) for k, v in cfg["sane_range_pct"].items()
        },
    )


def report_links(list_html: str) -> list[tuple[int, int, str]]:
    """[(năm đăng, tháng đăng, url)] các bài báo cáo kinh tế – xã hội, mới nhất trước, không trùng."""
    seen: dict[str, tuple[int, int, str]] = {}
    for url, y, m in LINK_RE.findall(list_html):
        seen.setdefault(url, (int(y), int(m), url))
    return sorted(seen.values(), reverse=True)


def page_text(page_html: str) -> str:
    text = re.sub(
        r"<(script|style)\b.*?</\1>", " ", page_html, flags=re.DOTALL | re.IGNORECASE
    )
    # Trang của Cục Thống kê không ở dạng NFC (dấu tách rời) → chuẩn hóa để mẫu câu (NFC) khớp
    text = unicodedata.normalize("NFC", _html.unescape(re.sub(r"<[^>]+>", " ", text)))
    return re.sub(r"\s+", " ", text)


def _pct(direction: str, number: str) -> float:
    """'tăng', '5,09' → 5.09; 'giảm' → âm. Số kiểu Việt Nam: chấm hàng nghìn, phẩy thập phân."""
    value = float(number.replace(".", "").replace(",", "."))
    return -value if direction.lower() == "giảm" else value


def _month_end(year: int, month: int) -> dt.date:
    return dt.date(year, month, calendar.monthrange(year, month)[1])


def _period_year(
    month: int, year_in_text: str | None, pub_year: int, pub_month: int
) -> int:
    if year_in_text:
        return int(year_in_text)
    return pub_year if month <= pub_month else pub_year - 1


def parse_report(
    text: str, pub_year: int, pub_month: int
) -> list[tuple[str, dt.date, float]]:
    """[(mã chỉ tiêu, ngày cuối kỳ, %)] tìm được trong một bài. Mỗi chỉ tiêu lấy câu ĐẦU TIÊN khớp mẫu."""
    out: list[tuple[str, dt.date, float]] = []
    for code, rx in (("CPI_YOY", CPI_RE), ("RETAIL_SALES_YOY", RETAIL_RE)):
        m = rx.search(text)
        if m:
            month = _MONTHS[m.group(1).lower()]
            year = _period_year(month, m.group(2), pub_year, pub_month)
            out.append((code, _month_end(year, month), _pct(m.group(3), m.group(4))))
    g = GDP_RE.search(text)
    if g:
        q, year = _QUARTERS[g.group(1)], int(g.group(2))
        out.append(("GDP_YOY", _month_end(year, q * 3), _pct(g.group(3), g.group(4))))
    return out


def _existing(db: Session, codes: list[str]) -> dict[tuple[str, dt.date], float]:
    from valuation.db.models import MacroSeries

    rows = db.query(
        MacroSeries.indicator_code, MacroSeries.date, MacroSeries.value
    ).filter(MacroSeries.indicator_code.in_(codes))
    return {(c, d): float(v) for c, d, v in rows if v is not None}


def _httpx_fetch(url: str, timeout_sec: float) -> str:
    import httpx

    ua = load_defaults()["macro_sources"].get(
        "user_agent", "antigravity-vn100-macro/1.0"
    )
    resp = httpx.get(
        url, headers={"User-Agent": ua}, timeout=timeout_sec, follow_redirects=True
    )
    resp.raise_for_status()
    return resp.text


def run_nso_update(
    db: Session,
    fetch: Fetcher | None = None,
    cfg: NsoConfig | None = None,
    dry_run: bool = False,
) -> dict:
    """Đọc các bài mới nhất → thêm kỳ chưa có → báo kỳ đã có mà số khác. Lỗi tải/đọc nằm trong `error`."""
    cfg = cfg or load_nso_config()
    fetch = fetch or (lambda u: _httpx_fetch(u, cfg.timeout_sec))
    found: dict[tuple[str, dt.date], tuple[float, str]] = {}
    read: list[str] = []
    error: str | None = None
    try:
        _assert_allowed_host(cfg.list_url)
        links = report_links(fetch(cfg.list_url))[: cfg.reports_to_read]
        if not links:
            raise ValueError(
                "trang danh mục không có liên kết báo cáo kinh tế – xã hội (cấu trúc trang đổi?)"
            )
        for pub_y, pub_m, url in links:
            _assert_allowed_host(url)
            read.append(url)
            for code, day, pct in parse_report(page_text(fetch(url)), pub_y, pub_m):
                lo, hi = cfg.sane_range_pct[code]
                if not lo <= pct <= hi:
                    raise ValueError(
                        f"{code} {day} = {pct}% ngoài khoảng hợp lý [{lo}; {hi}]% ({url})"
                    )
                prev = found.get((code, day))
                if prev and abs(prev[0] - pct) > 1e-9:
                    raise ValueError(
                        f"{code} {day}: hai bài ghi {prev[0]}% và {pct}% ({prev[1]}, {url})"
                    )
                found[(code, day)] = (pct, url)
    except (
        Exception
    ) as exc:  # trả lỗi để script thoát mã 1 (scheduler báo Discord), không nuốt
        logger.exception("Nạp vĩ mô từ nso.gov.vn lỗi")
        error = f"{type(exc).__name__}: {str(exc)[:300]}"

    have = _existing(db, ["CPI_YOY", "RETAIL_SALES_YOY", "GDP_YOY"])
    points: list[MacroPoint] = []
    revisions: list[dict] = []
    for (code, day), (pct, url) in sorted(found.items()):
        value = round(pct / 100.0, 8)
        old = have.get((code, day))
        if old is None:
            points.append(MacroPoint(code, day, value, SOURCE))
        elif abs(old - value) > 5e-5:
            revisions.append(
                {
                    "code": code,
                    "date": day.isoformat(),
                    "db": old,
                    "nso": value,
                    "url": url,
                }
            )
    written = (
        upsert_macro_series(points, db)
        if points and not dry_run and error is None
        else 0
    )
    return {
        "read": read,
        "found": [(c, d.isoformat(), p) for (c, d), (p, _) in sorted(found.items())],
        "points": [(p.indicator_code, p.date.isoformat(), p.value) for p in points],
        "written": written,
        "revisions": revisions,
        "error": error,
        "dry_run": dry_run,
    }
