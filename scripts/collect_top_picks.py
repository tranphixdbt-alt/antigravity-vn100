"""Thu số liệu cho báo cáo 20 mã tích sản (D93) — CHỈ ĐỌC DB, không gọi API, không ghi snapshot.

Chạy: ~/.venv/bin/python scripts/collect_top_picks.py [YYYY-MM-DD]
Ra: reports_pdf/top20/data_<ngày>.json (100 hồ sơ + dòng tiền + đồng thuận + cổ tức + 20 mã chọn).
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from valuation.analysis import money_flow as mf
from valuation.analysis.investment_ranking import (
    load_ranking_config,
    rank_companies,
    score_metrics,
)
from valuation.calibration.consensus_view import get_consensus_view
from valuation.config import PROJECT_ROOT, load_defaults
from valuation.data_access.corporate_actions import (
    load_dividend_track_records,
)
from valuation.data_access.investment_snapshot import build_ranking_row
from valuation.db.session import SessionLocalRead
from valuation.ingest.universe import load_vn100_snapshot
from valuation.report.top_picks import (
    composite_score,
    confidence,
    exclusion_reason,
    select_top,
)
from valuation.services.ranking_store import read_json, write_json
from valuation.views import money_flow as mfv

OUT = ROOT / "reports_pdf" / "top20"
TOP_N, MAX_PER_SECTOR = (
    20,
    4,
)  # người dùng chọn "một bảng chung 20 mã"; giới hạn ngành chống dồn (D93)


def main(as_of: dt.date) -> Path:
    cfg = load_ranking_config()
    evidence = read_json(
        PROJECT_ROOT / "config/investment_evidence.json", {"companies": {}}
    )["companies"]
    symbols = load_vn100_snapshot()["symbols"]
    flow_cfg = load_defaults()["money_flow"]
    with SessionLocalRead() as db:
        panel = mfv.load_flow_panel(db, flow_cfg)
        flows = mf.compute_money_flow(
            panel["prices"],
            panel["exact"],
            panel["actions"],
            mfv.sector_map(),
            flow_cfg,
            mfv._now_vn(),
        )
        rows = []
        for i, t in enumerate(symbols, 1):
            print(f"[{i}/{len(symbols)}] {t}", flush=True)
            try:
                row = build_ranking_row(db, t, as_of, cfg, evidence.get(t, {}))
            # Một mã lỗi không dừng cả rổ; lý do ghi vào hồ sơ và mã bị loại ở bước lọc.
            except Exception as exc:  # noqa: BLE001
                row = {
                    "ticker": t,
                    "name": t,
                    "sector": "Chưa rõ",
                    "flags": [],
                    "error": f"{type(exc).__name__}: {exc}"[:300],
                }
            tk = flows["tickers"].get(t)
            # flow_ratio thiếu (prices_daily không có khối ngoại 20 phiên) → dùng ròng khớp lệnh/GTGD 20 phiên
            # từ flow_daily (VCI), cùng định nghĩa "ngoại ròng ÷ giá trị giao dịch" (ghi rõ trong báo cáo).
            if (
                tk
                and row.get("metrics") is not None
                and row["metrics"].get("flow_ratio") is None
            ):
                r_f = tk["flows"]["20"]["loai"].get("r_f")
                if r_f is not None:
                    row["metrics"]["flow_ratio"] = r_f
                    row["flow_ratio_source"] = "flow_daily khớp lệnh 20 phiên"
            rows.append(row)
        score_metrics(rows, cfg)
        rows = rank_companies(rows, cfg)
        consensus = {}
        for t in symbols:
            v = get_consensus_view(db, t, as_of=as_of, window_days=180)
            consensus[t] = {
                "median": v.median,
                "mean": v.mean,
                "count": v.count,
                "min": v.min,
                "max": v.max,
                "newest_age_days": v.newest_age_days,
                "stale": v.stale,
                "quotes": [
                    {
                        "broker": q.broker,
                        "date": q.report_date.isoformat(),
                        "target": q.target_price,
                        "rating": q.rating,
                    }
                    for q in v.quotes
                ],
            }
        ca = load_defaults()["corporate_actions"]
        dividends = load_dividend_track_records(
            db,
            symbols,
            as_of=as_of,
            history_years=int(ca.get("history_years", 5)),
            post_sessions=int(ca.get("price_impact_long_sessions", 20)),
            consistency_years=int(ca.get("dividend_consistency_years", 3)),
        )
    for row in rows:
        row["composite"] = composite_score(row)
        row["excluded"] = exclusion_reason(row, cfg)
        row["confidence"] = confidence(row, consensus.get(row["ticker"], {}))
    picks = [r["ticker"] for r in select_top(rows, cfg, TOP_N, MAX_PER_SECTOR)]
    flow_view = {
        t: {
            k: tk[k]
            for k in (
                "label",
                "context",
                "ret20",
                "votes",
                "flows",
                "domestic",
                "badges",
            )
            if k in tk
        }
        for t, tk in flows["tickers"].items()
    }
    out = OUT / f"data_{as_of.isoformat()}.json"
    write_json(
        out,
        {
            "as_of": as_of.isoformat(),
            "config_version": cfg["version"],
            "picks": picks,
            "top_n": TOP_N,
            "max_per_sector": MAX_PER_SECTOR,
            "flow_meta": flows["meta"],
            "rows": rows,
            "consensus": consensus,
            "dividends": dividends,
            "flows": flow_view,
        },
    )
    return out


if __name__ == "__main__":
    day = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else dt.date.today()
    print(main(day))
