"""S2 (docs/PLAN_VNSTOCK_V6.md): khối ngoại + tự doanh FHSC vs flow_daily (VCI). Chỉ đọc DB. ~/.venv_6x/bin/python."""
import sqlite3
import sys
import time

import pandas as pd
from vnstock import Market

START, END = "2026-10-13", "2026-11-10"  # 20 phiên đã chốt trong flow_daily
con = sqlite3.connect("file:/Users/macos/antigravity-vn100/vn100_full.db?mode=ro", uri=True)
tickers = [r[0] for r in con.execute("SELECT ticker FROM tickers WHERE is_vn100=1 ORDER BY ticker")]
fd = pd.read_sql(
    "SELECT ticker, trade_date, matched_val, fr_net_match_val, fr_net_deal_val, prop_net_match_val, prop_net_deal_val "
    "FROM flow_daily WHERE trade_date BETWEEN ? AND ?", con, params=(START, END), parse_dates=["trade_date"])


def fetch(fn):
    for attempt in range(4):
        try:
            return fn()
        except Exception as e:  # đo thôi: 429 thì chờ rồi thử lại
            if "429" in str(e) and attempt < 3:
                time.sleep(30)
                continue
            raise


parts, errors = [], {}
for i, t in enumerate(tickers):
    try:
        eq = Market("fhsc").equity(t)
        fo = fetch(lambda e=eq: e.foreign_flow(start=START, end=END))
        time.sleep(1.3)
        pr = fetch(lambda e=eq: e.proprietary_flow(start=START, end=END))
        time.sleep(1.3)
    except Exception as e:  # noqa: BLE001 — đo đối chiếu: ghi lỗi từng mã rồi chạy tiếp
        errors[t] = f"{type(e).__name__}: {str(e)[:100]}"
        continue
    for df, name in ((fo, "fo"), (pr, "pr")):
        df["trade_date"] = pd.to_datetime(df["time"]).dt.tz_localize(None).dt.normalize()
    m = (fd[fd.ticker == t]
         .merge(fo[["trade_date", "net_val"]].rename(columns={"net_val": "fo_net"}), on="trade_date", how="left")
         .merge(pr[["trade_date", "net_val"]].rename(columns={"net_val": "pr_net"}), on="trade_date", how="left"))
    parts.append(m)
    if i % 20 == 19:
        print(f"{i + 1}/{len(tickers)}", file=sys.stderr)

a = pd.concat(parts, ignore_index=True)
a.to_csv("/Users/macos/antigravity-vn100/logs/reconcile_fhsc_flows.csv", index=False)
print(f"Mã: {a.ticker.nunique()}/{len(tickers)} · lỗi: {errors or 'không'} · ô: {len(a)}")
den = a["matched_val"].where(a["matched_val"] > 0)
for label, fhsc, cands in (
    ("Khối ngoại", "fo_net", {"khớp lệnh": a.fr_net_match_val, "khớp + thỏa thuận": a.fr_net_match_val + a.fr_net_deal_val.fillna(0)}),
    ("Tự doanh", "pr_net", {"khớp lệnh": a.prop_net_match_val, "khớp + thỏa thuận": a.prop_net_match_val + a.prop_net_deal_val.fillna(0)}),
):
    have = a[fhsc].notna()
    print(f"\n{label}: FHSC có số {have.sum()}/{len(a)} ô")
    for name, vci in cands.items():
        d = (a[fhsc] - vci).abs() / den
        ok = have & vci.notna()
        print(f"  so với VCI {name:<18}: lệch ≤0,1% GTGD {(d[ok] <= 0.001).mean():.1%} · ≤1% GTGD {(d[ok] <= 0.01).mean():.1%} · trung vị {d[ok].median():.4%}")
