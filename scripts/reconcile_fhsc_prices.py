"""S1 (docs/PLAN_VNSTOCK_V6.md): đối chiếu giá ngày FHSC (vnstock 6) với giá VCI đang lưu trong DB. Chỉ đọc DB.
Chạy bằng ~/.venv_6x/bin/python. Ghi chi tiết ra CSV cạnh script."""
import sqlite3
import sys
import time
from pathlib import Path

import pandas as pd
from vnstock import Market

DB = "/Users/macos/antigravity-vn100/vn100_full.db"
START = "2026-08-15"
OUT = Path("/Users/macos/antigravity-vn100/logs/reconcile_fhsc_prices.csv")

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
tickers = [r[0] for r in con.execute("SELECT ticker FROM tickers WHERE is_vn100=1 ORDER BY ticker")]
db = pd.read_sql(
    "SELECT ticker, trade_date, close, volume FROM prices_daily WHERE trade_date >= ? AND close IS NOT NULL",
    con, params=(START,), parse_dates=["trade_date"],
)
rows, errors = [], {}
for i, t in enumerate(tickers):
    try:
        f = Market("fhsc").equity(t).ohlcv(start=START)
    except Exception as e:  # noqa: BLE001 — đo đối chiếu: ghi lỗi từng mã rồi chạy tiếp
        errors[t] = f"{type(e).__name__}: {str(e)[:120]}"
        continue
    f = f.assign(trade_date=pd.to_datetime(f["time"]).dt.tz_localize(None).dt.normalize())
    m = db[db.ticker == t].merge(f[["trade_date", "close", "volume"]], on="trade_date", how="outer",
                                 suffixes=("_db", "_fhsc"), indicator=True)
    m["ticker"] = t
    rows.append(m)
    if i % 20 == 19:
        print(f"{i + 1}/{len(tickers)} mã", file=sys.stderr)
    time.sleep(0.3)

all_ = pd.concat(rows, ignore_index=True)
both = all_[all_["_merge"] == "both"].copy()
both["close_fhsc_vnd"] = both["close_fhsc"] * 1000
both["rel"] = both["close_fhsc_vnd"] / both["close_db"].astype(float) - 1
both["vol_rel"] = both["volume_fhsc"] / both["volume_db"].astype(float) - 1
all_.to_csv(OUT, index=False)

print(f"Mã đối chiếu: {all_.ticker.nunique()}/{len(tickers)} · lỗi: {errors or 'không'}")
print(f"Ô giá trùng ngày: {len(both)} · chỉ DB có: {(all_['_merge'] == 'left_only').sum()} · chỉ FHSC có: {(all_['_merge'] == 'right_only').sum()}")
for thr in (0.0005, 0.005, 0.02):
    print(f"  |lệch close| > {thr:.2%}: {(both.rel.abs() > thr).sum()} ô ở {both.loc[both.rel.abs() > thr, 'ticker'].nunique()} mã")
print(f"  |lệch KL| > 1%: {(both.vol_rel.abs() > 0.01).sum()} ô")
worst = both.assign(a=both.rel.abs()).sort_values("a", ascending=False).head(12)
print("\nLệch close lớn nhất:")
print(worst[["ticker", "trade_date", "close_db", "close_fhsc_vnd", "rel"]].to_string(index=False))
by_t = both.groupby("ticker").rel.agg(lambda s: (s.abs() > 0.005).sum())
print("\nMã có ô lệch > 0,5%:", by_t[by_t > 0].to_dict())
only = all_[all_["_merge"] != "both"].groupby(["_merge", "ticker"]).size()
print("\nNgày thiếu một phía (top):", only.sort_values(ascending=False).head(10).to_dict())
for t, d0 in (("TCB", "2026-10-28"), ("HDB", None), ("PC1", "2026-11-03")):
    s = both[both.ticker == t].sort_values("trade_date").tail(14)
    print(f"\n{t} quanh sự kiện quyền:")
    print(s[["trade_date", "close_db", "close_fhsc_vnd", "rel"]].to_string(index=False))
