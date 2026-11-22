"""Lưu mua/bán chủ động FHSC của rổ VN100 vào active_flow_daily (D101, W0 docs/PLAN_WYCKOFF_FLOW.md).

Lịch: 07:35 thứ Hai–thứ Sáu trong vn100-worker (scheduler.py), trước báo cáo sáng. FHSC chỉ giữ ~61 phiên gần
nhất: lỡ vài ngày vẫn tự bù ở lượt sau, lỡ quá ~61 phiên thì mất hẳn. Cầu nối bỏ phiên hôm nay (chưa chốt).
Thoát mã 1 khi bị bỏ qua (ngoài giờ FHSC, tắt FHSC) hoặc không lưu được mã nào, để log scheduler thấy exit=1.

    python scripts/update_active_flow.py
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect, select

from valuation.config import load_defaults, settings
from valuation.db.flow_models import active_flow_daily, open_flow_engine
from valuation.db.models import Ticker
from valuation.ingest import fhsc_bridge
from valuation.ingest.active_flow import collect


def main() -> int:
    engine = open_flow_engine(settings.database_url_write)
    if not inspect(engine).has_table(active_flow_daily.name):
        print(
            "Chưa có bảng active_flow_daily — chạy scripts/migrate_active_flow.py --apply trước"
        )
        return 2
    with engine.connect() as conn:
        tickers = sorted(
            conn.execute(select(Ticker.ticker).where(Ticker.is_vn100)).scalars()
        )
    now = dt.datetime.now(fhsc_bridge.VN)
    lookback = int(load_defaults()["active_flow"]["lookback_days"])
    start = (now.date() - dt.timedelta(days=lookback)).isoformat()
    stats = collect(
        engine,
        tickers,
        now,
        start,
        prefetch=fhsc_bridge.prefetch,
        cached=fhsc_bridge.cached,
    )
    summary = {
        "tickers": len(tickers),
        **{
            k: stats[k]
            for k in (
                "tickers_ok",
                "inserted",
                "unchanged",
                "dropped",
                "latest_date",
                "skipped",
            )
        },
        "missing": stats["missing"][:20],
        "errors": dict(list(stats["errors"].items())[:10]),
        "mismatches": stats["mismatches"][:20],
    }
    print(json.dumps(summary, ensure_ascii=False))
    if stats["skipped"] or not stats["tickers_ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
