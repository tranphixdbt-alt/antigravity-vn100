"""Ghi lại khối ngoại của các phiên mà nguồn chính trả trống, lấy từ Vietcap (lỗi FHSC 23/11/2026).

Mặc định chỉ xem: in số đang có trong DB cạnh số Vietcap của vài mã, không ghi gì.
Với --apply: sao lưu các dòng khối ngoại hiện có của những phiên đó ra CSV, rồi ghi số Vietcap qua
`upsert_market_flows` (chỉ cột dòng tiền, không đụng giá; chạy lại nhiều lần cho cùng kết quả).

    python scripts/repair_foreign_session.py 2026-11-23            # xem trước
    python scripts/repair_foreign_session.py 2026-11-23 --apply    # sao lưu rồi ghi
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from valuation.config import PROJECT_ROOT
from valuation.ingest import vietcap_flow

FOREIGN = [
    "foreign_buy_vol",
    "foreign_buy_val",
    "foreign_sell_vol",
    "foreign_sell_val",
    "foreign_net_vol",
    "foreign_net_val",
]


def _current(days: list[dt.date]) -> pd.DataFrame:
    from valuation.db.models import PricesDaily, Ticker
    from valuation.db.session import SessionLocalRead

    db = SessionLocalRead()
    try:
        q = (
            db.query(
                PricesDaily.ticker,
                PricesDaily.trade_date,
                *[getattr(PricesDaily, c) for c in FOREIGN],
            )
            .join(Ticker, Ticker.ticker == PricesDaily.ticker)
            .filter(Ticker.is_vn100, PricesDaily.trade_date.in_(days))
        )
        return pd.DataFrame(q.all(), columns=["ticker", "trade_date", *FOREIGN])
    finally:
        db.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("days", nargs="+", type=dt.date.fromisoformat)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--backup-dir", type=Path, default=PROJECT_ROOT / "backups")
    a = ap.parse_args()
    cur = _current(a.days)
    if cur.empty:
        print("Không có dòng VN100 nào ở các phiên này.")
        return 1
    tickers = sorted(cur["ticker"].unique())
    zero = (cur["foreign_buy_val"].eq(0) & cur["foreign_sell_val"].eq(0)).sum()
    print(f"{len(cur)} dòng của {len(tickers)} mã; {zero} dòng đang ghi mua = bán = 0.")
    if not a.apply:
        for t in tickers[:3]:
            v = vietcap_flow.fetch_foreign(t)
            v = v[v["time"].isin(a.days)]
            print(
                f"{t} DB:\n{cur[cur['ticker'] == t][['trade_date', 'foreign_buy_val', 'foreign_sell_val', 'foreign_net_val']].to_string(index=False)}"
            )
            print(
                f"{t} Vietcap:\n{v[['time', 'buy_val', 'sell_val', 'net_val']].to_string(index=False)}"
            )
        print("Chưa ghi gì. Thêm --apply để sao lưu rồi ghi.")
        return 0
    a.backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%Y%m%d-%H%M%S")
    path = (
        a.backup_dir
        / f"khoi-ngoai-{'_'.join(d.isoformat() for d in a.days)}-truoc-sua-{stamp}.csv"
    )
    cur.to_csv(path, index=False)
    print(f"Đã sao lưu {len(cur)} dòng: {path}")
    res = vietcap_flow.fill_sessions(tickers, a.days)
    print(f"Đã ghi {res['written']} mã; thiếu {res['missing']}; lỗi {res['errors']}.")
    after = _current(a.days)
    zero = (after["foreign_buy_val"].eq(0) & after["foreign_sell_val"].eq(0)).sum()
    print(
        f"Sau khi ghi: {zero} dòng còn mua = bán = 0; tổng ròng {after['foreign_net_val'].astype(float).sum() / 1e9:,.1f} tỷ đồng."
    )
    return 0 if not res["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
