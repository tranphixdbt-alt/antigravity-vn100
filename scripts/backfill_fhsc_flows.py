"""Vá khối ngoại/tự doanh gộp (FHSC) vào prices_daily cho một khoảng phiên (D97). Chạy MỘT lần sau sự cố nguồn;
hằng ngày báo cáo sáng tự làm việc này. Chỉ ghi các cột dòng tiền (upsert_market_flows: coalesce, không đụng OHLCV).

    python scripts/backfill_fhsc_flows.py 2026-11-13          # mặc định: rổ VN100
    python scripts/backfill_fhsc_flows.py 2026-11-13 FPT VCB  # vài mã
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main(start: str, tickers: list[str]) -> int:
    from valuation.db.models import Ticker
    from valuation.db.session import SessionLocalRead
    from valuation.ingest import fhsc_bridge
    from valuation.ingest.pipeline import upsert_market_flows

    if not tickers:
        db = SessionLocalRead()
        try:
            tickers = [
                t
                for (t,) in db.query(Ticker.ticker)
                .filter(Ticker.is_vn100)
                .order_by(Ticker.ticker)
            ]
        finally:
            db.close()
    stats = fhsc_bridge.prefetch(dict.fromkeys(tickers, start), ["foreign", "prop"])
    if stats["skipped"]:
        print(f"Bỏ qua: {stats['skipped']}")
        return 1
    done, missing = 0, []
    for t in tickers:
        fo, pr = fhsc_bridge.cached(t, "foreign", start), fhsc_bridge.cached(
            t, "prop", start
        )
        if fo is None and pr is None:
            missing.append(t)
            continue
        upsert_market_flows(t, fo, pr)
        done += 1
    print(
        f"Ghi dòng tiền FHSC từ {start}: {done}/{len(tickers)} mã · lỗi FHSC: {len(stats['errors'])} · thiếu: {missing}"
    )
    return 0 if done else 1


if __name__ == "__main__":
    import datetime as dt
    import re

    dt.date.fromisoformat(sys.argv[1])  # ngày sai định dạng → lỗi ngay
    args = [t.upper() for t in sys.argv[2:]]
    if bad := [t for t in args if not re.fullmatch(r"[A-Z0-9]{3,10}", t)]:
        raise SystemExit(f"Mã không hợp lệ: {bad}")
    raise SystemExit(main(sys.argv[1], args))
