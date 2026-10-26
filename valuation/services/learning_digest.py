"""Bản tóm tắt tuần cho vòng học (docs/PLAN_LEARNING_LOOP.md, GĐ 2–4).

Python thuần, KHÔNG gọi AI. Ghi vào knowledge/ (thư mục dự án nằm trên Google Drive → routine Claude cloud đọc):
  weekly/<năm>-W<tuần>.md              bản tóm tắt ≤ ~300 dòng (Claude đọc file này, không đọc DB)
  weekly/<năm>-W<tuần>_valuation.csv   định giá 100 mã tuần này vs trung vị CTCK
  weekly/<năm>-W<tuần>_flow_stats.csv  kiểm chứng nhãn dòng tiền (trong mẫu / ngoài mẫu)
  fv_history.csv                       lịch sử FV hằng tuần (nối thêm, không ghi đè)
  flow_backtest_labels.csv             nhãn dòng tiền tính lùi từng tuần (bộ nhớ đệm, chỉ tính tuần mới)

Chỉ mô tả dữ liệu quá khứ — không phải khuyến nghị đầu tư.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import statistics
from collections import Counter
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from valuation.config import PROJECT_ROOT

KNOWLEDGE = PROJECT_ROOT / "knowledge"
VN = ZoneInfo("Asia/Ho_Chi_Minh")
# Nhãn dòng tiền đo từ tuần này (dữ liệu flow_daily bắt đầu 24/10/2024; cần ~2 tháng chuỗi trước tuần đầu).
FLOW_BACKTEST_START = dt.date(2025, 1, 17)
# Mốc tách mẫu: trước = tìm hiểu, từ mốc = kiểm tra ngoài mẫu (docs/PLAN_LEARNING_LOOP.md GĐ 3).
OOS_START = dt.date(2026, 4, 1)
HORIZONS = (5, 20)


def iso_week(d: dt.date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


# ---------- định giá ----------
def valuation_summary(rows: list[dict]) -> dict[str, Any]:
    """rows: ticker, group, published, synth, fv, price, cons_median, cons_n. Lệch CTCK chỉ đo khi ≥ 2 CTCK."""
    pub = [r for r in rows if r.get("published")]
    devs = [r["fv"] / r["cons_median"] - 1 for r in pub if r.get("cons_median") and (r.get("cons_n") or 0) >= 2]

    def stats(ds: list[float]) -> dict[str, Any]:
        return {
            "n": len(ds),
            "in15": sum(abs(x) <= 0.15 for x in ds),
            "in25": sum(abs(x) <= 0.25 for x in ds),
            "median_abs": statistics.median(abs(x) for x in ds) if ds else None,
            "median_signed": statistics.median(ds) if ds else None,
        }

    groups: dict[str, list[float]] = {}
    for r in pub:
        if r.get("cons_median") and (r.get("cons_n") or 0) >= 2:
            key = "BROKER_SYNTH" if r.get("synth") else ("Ngân hàng" if r.get("group") == "NH" else "Mô hình riêng")
            groups.setdefault(key, []).append(r["fv"] / r["cons_median"] - 1)
    return {
        "total": len(rows),
        "published": len(pub),
        "own_model": sum(1 for r in pub if not r.get("synth")),
        "broker_synth": sum(1 for r in pub if r.get("synth")),
        "all": stats(devs),
        "by_group": {k: stats(v) for k, v in sorted(groups.items())},
    }


# ---------- DeepSeek ----------
def _metric_key(metric: str) -> str:
    """Gom biến thể tên chỉ tiêu (`net_income (2026)`, `quality_metrics.roe / ...`) về khóa ngắn."""
    m = re.sub(r"\(.*?\)", "", str(metric or "")).strip().lower()
    return m[:60] or "?"


def ai_issue_counts(index_rows: list[dict], since: dt.date | None = None) -> Counter:
    """Đếm chỉ tiêu bị DeepSeek nghi vấn: mỗi báo cáo đếm 1 lần/chỉ tiêu."""
    c: Counter = Counter()
    for r in index_rows:
        if since and str(r.get("date", "")) < since.isoformat():
            continue
        for key in {_metric_key(i.get("metric")) for i in r.get("issues") or []}:
            c[key] += 1
    return c


# ---------- dòng tiền ----------
def forward_excess(close: pd.DataFrame, asof: dt.date, n: int) -> pd.Series:
    """close: index ngày giao dịch (date), cột mã. Lợi nhuận n phiên sau phiên cuối ≤ asof, trừ trung vị VN100.
    Thiếu đủ n phiên phía sau → Series rỗng (không dùng dữ liệu chưa có)."""
    close = close[~close.index.duplicated(keep="last")].sort_index()
    i0 = sum(1 for d in close.index if d <= asof) - 1  # vị trí phiên cuối ≤ asof
    if i0 < 0 or i0 + n >= len(close.index):
        return pd.Series(dtype=float)
    ret = close.iloc[i0 + n] / close.iloc[i0] - 1
    ret = ret.dropna()
    return ret - ret.median()


def label_stats(events: pd.DataFrame) -> pd.DataFrame:
    """events: date, ticker, label, excess_5, excess_20. Theo nhãn × giai đoạn: số mẫu, lợi nhuận vượt trung vị
    VN100 bình quân và tỷ lệ > 0. Mẫu tuần chồng nhau (20 phiên) → số mẫu hiệu dụng nhỏ hơn n."""
    if events.empty:
        return pd.DataFrame()
    e = events.copy()
    e["period"] = ["ngoài mẫu" if pd.Timestamp(d).date() >= OOS_START else "trong mẫu" for d in e["date"]]
    out = []
    for (label, period), g in e.groupby(["label", "period"]):
        row: dict[str, Any] = {"label": label, "period": period, "n": len(g), "n_weeks": g["date"].nunique()}
        for h in HORIZONS:
            x = g[f"excess_{h}"].dropna()
            row[f"n_{h}"] = len(x)
            row[f"excess_{h}_mean_pct"] = round(float(x.mean()) * 100, 2) if len(x) else None
            row[f"hit_{h}_pct"] = round(float((x > 0).mean()) * 100, 1) if len(x) else None
        out.append(row)
    return pd.DataFrame(out).sort_values(["period", "label"]).reset_index(drop=True)


def week_ends(prices_dates: list[dt.date], start: dt.date, end: dt.date) -> list[dt.date]:
    """Phiên giao dịch cuối mỗi tuần ISO trong [start, end]."""
    last: dict[str, dt.date] = {}
    for d in sorted(prices_dates):
        if start <= d <= end:
            last[iso_week(d)] = d
    return sorted(last.values())


def compute_flow_labels(panel: dict, sectors: dict, cfg: dict, dates: list[dt.date]) -> pd.DataFrame:
    """Nhãn dòng tiền tính lùi tại từng ngày: chỉ dùng giá/dòng tiền ≤ ngày đó và sự kiện đã công bố ≤ ngày đó."""
    from valuation.analysis import money_flow as mf

    # Khung panel ghép từ nhiều phần có thể trùng chỉ mục dòng → lọc bằng mặt nạ sẽ khớp sai dòng; đặt lại chỉ mục.
    prices, exact, actions = (
        None if x is None else x.reset_index(drop=True)
        for x in (panel["prices"], panel.get("exact"), panel.get("actions"))
    )
    pdates = pd.to_datetime(prices["trade_date"]).dt.date
    edates = pd.to_datetime(exact["trade_date"]).dt.date if exact is not None else None
    if actions is not None and len(actions):
        anchor = actions["announcement_date"].fillna(actions["record_date"]).fillna(actions["ex_right_date"])
        adates = pd.to_datetime(anchor).dt.date
    span = dt.timedelta(days=int(cfg["history_days"]) + 10)
    rows = []
    for d in dates:
        ps = prices[(pdates <= d) & (pdates > d - span)]
        es = exact[(edates <= d) & (edates > d - span)] if exact is not None else None
        acts = actions[adates <= d] if actions is not None and len(actions) else actions
        res = mf.compute_money_flow(ps, es, acts, sectors, cfg, dt.datetime(d.year, d.month, d.day, 18, 0, tzinfo=VN))
        for t, tk in res["tickers"].items():
            v = tk["votes"]
            rows.append({
                "date": d.isoformat(), "ticker": t, "sector": tk["sector"], "label": tk["label"]["code"],
                "vote_foreign": v["foreign"]["vote"], "vote_pv": v["pv"]["vote"], "vote_prop": v["prop"]["vote"],
                "single_session": any(str(b).startswith("⚠ Dồn 1 phiên") for b in tk["badges"]),
            })
    return pd.DataFrame(rows)


def close_matrix(prices: pd.DataFrame) -> pd.DataFrame:
    """Ma trận giá đóng cửa ngày × mã (index = date, dòng sau ghi đè dòng trước cùng ngày-mã).
    Dựng bằng numpy, KHÔNG dùng pivot_table/unstack: pandas 2.3.3 trên Python 3.14 trả nhãn index sai và lặp với
    khung lớn (thử 544 ngày × 100 mã, 26/10/2026) — bảng nhỏ vẫn đúng nên test thường không bắt được."""
    days = pd.to_datetime(prices["trade_date"]).dt.date.to_numpy()
    tickers = prices["ticker"].to_numpy()
    uniq_d, di = np.unique(days, return_inverse=True)
    uniq_t, ti = np.unique(tickers, return_inverse=True)
    arr = np.full((len(uniq_d), len(uniq_t)), np.nan)
    arr[di, ti] = prices["close"].to_numpy(dtype=float)
    return pd.DataFrame(arr, index=list(uniq_d), columns=list(uniq_t))


def attach_forward_returns(labels: pd.DataFrame, close: pd.DataFrame) -> pd.DataFrame:
    if labels.empty:
        return labels
    parts = []
    for d, g in labels.groupby("date"):
        g = g.copy()
        asof = dt.date.fromisoformat(str(d))
        for h in HORIZONS:
            g[f"excess_{h}"] = g["ticker"].map(forward_excess(close, asof, h))
        parts.append(g)
    return pd.concat(parts, ignore_index=True)


# ---------- ghi file ----------
def _pct(x: float | None, signed: bool = False) -> str:
    return "—" if x is None else (f"{x * 100:+.1f}%" if signed else f"{x * 100:.1f}%")


def render_digest(week: str, today: dt.date, val: dict, prev_val: dict | None, top_dev: list[dict],
                  ai: dict, ctck: dict, flow: dict, proposals: list[str]) -> str:
    L = [f"# Bản tóm tắt tuần {week} (tạo {today.isoformat()}, Python — không AI)", "",
         "> Mô tả dữ liệu quá khứ, không phải khuyến nghị đầu tư. Số liệu từ DB; nhận định DeepSeek là giả thuyết.", "",
         "## 1. Chất lượng định giá (so trung vị CTCK, chỉ mã ≥ 2 CTCK)", ""]
    a, p = val["all"], (prev_val or {}).get("all") or {}

    def cmp(key: str, signed: bool = False) -> str:
        return f"{_pct(a.get(key), signed)} (tuần trước {_pct(p.get(key), signed)})" if p else _pct(a.get(key), signed)

    L += [f"- Công bố: {val['published']}/{val['total']} — mô hình riêng {val['own_model']}, BROKER_SYNTH {val['broker_synth']}"
          + (f" (tuần trước {prev_val['published']})" if prev_val else ""),
          f"- Đo được lệch: {a['n']} mã · trong ±15%: {a['in15']} · trong ±25%: {a['in25']}",
          f"- Trung vị |lệch|: {cmp('median_abs')} · trung vị lệch có dấu: {cmp('median_signed', True)}", "",
          "| Nhóm | n | ±15% | ±25% | trung vị \\|lệch\\| | trung vị có dấu |", "|---|---|---|---|---|---|"]
    L += [f"| {k} | {s['n']} | {s['in15']} | {s['in25']} | {_pct(s['median_abs'])} | {_pct(s['median_signed'], True)} |"
          for k, s in val["by_group"].items()]
    L += ["", "## 2. Top lệch nhiều nhất (đã công bố)", "", "| Mã | Nhóm | FV | Trung vị CTCK (n) | Lệch |", "|---|---|---|---|---|"]
    L += [f"| {r['ticker']} | {r['kind']} | {r['fv']:,.0f} | {r['cons_median']:,.0f} ({r['cons_n']}) | {_pct(r['dev'], True)} |"
          for r in top_dev]
    L += ["", f"## 3. DeepSeek — {ai['n_week']} báo cáo trong 7 ngày, {ai['n_total']} tích lũy", "",
          "Chỉ tiêu bị nghi vấn nhiều nhất (tích lũy; số báo cáo nêu):", ""]
    L += [f"- `{k}`: {v}" for k, v in ai["top"]] or ["- (chưa có)"]
    L += ["", f"## 4. CTCK — {ctck['n_new']} báo cáo mới trong 7 ngày", ""]
    L += [f"- {r}" for r in ctck["lines"]] or ["- (không có)"]
    L += ["", "## 5. Dòng tiền", "", f"- Phân bố nhãn tuần này: {flow['dist']}",
          f"- Cảnh báo dồn 1 phiên: {flow['single'] or '(không có)'}", "",
          (f"Kiểm chứng nhãn tính lùi ({flow['n_weeks']} tuần, {flow['range']}); lợi nhuận vượt trung vị VN100 "
           f"(ngoài mẫu từ {OOS_START.isoformat()}; mẫu tuần chồng nhau nên số mẫu hiệu dụng nhỏ hơn n):"), "",
          "| Nhãn | Giai đoạn | n | vượt TB 5p | tỷ lệ >0 5p | vượt TB 20p | tỷ lệ >0 20p |", "|---|---|---|---|---|---|---|"]
    for r in flow["stats"]:
        L.append(f"| {r['label']} | {r['period']} | {r['n']} | {r['excess_5_mean_pct']}% | {r['hit_5_pct']}% | "
                 f"{r['excess_20_mean_pct']}% | {r['hit_20_pct']}% |")
    L += ["", "## 6. Đề xuất các tuần trước", ""]
    L += [f"- {x}" for x in proposals] or ["- (chưa có)"]
    L += ["", "File kèm: `<tuần>_valuation.csv`, `<tuần>_flow_stats.csv`, `../fv_history.csv`, `../flow_backtest_labels.csv`."]
    return "\n".join(L) + "\n"


def read_index(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
