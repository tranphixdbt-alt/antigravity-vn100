"""Mua/bán chủ động theo phiên từ FHSC → bảng active_flow_daily (D101, W0 của docs/PLAN_WYCKOFF_FLOW.md).

FHSC `Market().equity(mã).active_flow()` chỉ trả ~61 phiên gần nhất, nên phải lưu mỗi ngày; phiên quá 61 ngày
không lấy lại được. Tải qua cầu nối `fhsc_bridge` (vnstock thế hệ 6, giãn nhịp, bỏ phiên hôm nay chưa chốt).

Quy tắc dữ liệu (skill vn-finance-data):
- Thiếu số, số âm, hoặc cả mua lẫn bán bằng 0 → bỏ dòng và đếm, không đoán, không ghi 0.
- Phiên đã lưu không bị ghi đè: nguồn đổi số thì giữ bản đã lưu, ghi (mã, ngày) vào `mismatches`
  (như flow_daily với phiên đã chốt).
- Đơn vị: cổ phiếu, danh nghĩa như FHSC trả (chưa điều chỉnh thưởng/cổ tức CP).
"""

from __future__ import annotations

import datetime as dt
import math
from collections.abc import Callable
from typing import Any

import pandas as pd
from sqlalchemy import Engine, select

from valuation.db.flow_models import ACTIVE_COLUMNS, active_flow_daily

SOURCE = "fhsc"
_FHSC_COLS = {
    "active_buy_vol": "active_buy_volume",
    "active_sell_vol": "active_sell_volume",
}


def _ok(x: Any) -> float | None:
    """Số hữu hạn ≥ 0, ngược lại None."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) and v >= 0 else None


def normalize(
    df: pd.DataFrame, ticker: str, fetched_at: dt.datetime
) -> tuple[list[dict[str, Any]], int]:
    """Khung từ `fhsc_bridge.cached(mã, "active", ...)` → (dòng hợp lệ theo ngày tăng dần, số dòng bỏ).

    df có cột `time` (date) và `active_buy_volume`, `active_sell_volume`. Trùng ngày → giữ dòng sau, đếm là bỏ.
    """
    keep: dict[dt.date, dict[str, Any]] = {}
    dropped = 0
    for rec in df.to_dict("records"):
        day = pd.Timestamp(rec["time"]).date()
        vals = {col: _ok(rec.get(src)) for col, src in _FHSC_COLS.items()}
        if any(v is None for v in vals.values()) or all(v == 0 for v in vals.values()):
            dropped += 1
            continue
        if day in keep:
            dropped += 1
        keep[day] = {
            "ticker": ticker,
            "trade_date": day,
            "source": SOURCE,
            **vals,
            "fetched_at": fetched_at,
        }
    return [keep[d] for d in sorted(keep)], dropped


def store(engine: Engine, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Chỉ INSERT phiên chưa có; phiên đã có giữ nguyên (đếm `unchanged`, lệch số → `mismatches`)."""
    stats: dict[str, Any] = {"inserted": 0, "unchanged": 0, "mismatches": []}
    if not rows:
        return stats
    c = active_flow_daily.c
    by_ticker: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_ticker.setdefault(r["ticker"], []).append(r)
    with engine.begin() as conn:
        for ticker, group in by_ticker.items():
            dates = [r["trade_date"] for r in group]
            found = conn.execute(
                select(active_flow_daily).where(
                    c.ticker == ticker,
                    c.source == SOURCE,
                    c.trade_date.between(min(dates), max(dates)),
                )
            ).mappings()
            existing = {row["trade_date"]: row for row in found}
            new = []
            for r in group:
                old = existing.get(r["trade_date"])
                if old is None:
                    new.append(r)
                    continue
                stats["unchanged"] += 1
                if any(float(old[col]) != r[col] for col in ACTIVE_COLUMNS):
                    stats["mismatches"].append((ticker, r["trade_date"].isoformat()))
            if new:
                conn.execute(active_flow_daily.insert(), new)
                stats["inserted"] += len(new)
    return stats


def collect(
    engine: Engine,
    tickers: list[str],
    now: dt.datetime,
    start: str,
    *,
    prefetch: Callable[..., dict[str, Any]],
    cached: Callable[[str, str, str], pd.DataFrame | None],
) -> dict[str, Any]:
    """Tải cả rổ một lượt qua cầu nối FHSC rồi lưu. Trả thống kê để job in và báo lỗi."""
    res = prefetch({t: start for t in tickers}, ["active"], now=now)
    stats: dict[str, Any] = {
        "skipped": res["skipped"],
        "errors": res["errors"],
        "inserted": 0,
        "unchanged": 0,
        "mismatches": [],
        "dropped": 0,
        "missing": [],
        "tickers_ok": 0,
        "latest_date": None,
    }
    if res["skipped"]:
        return stats
    fetched_at = now.replace(tzinfo=None) if now.tzinfo else now
    rows: list[dict[str, Any]] = []
    for t in tickers:
        df = cached(t, "active", start)
        if df is None:
            stats["missing"].append(t)
            continue
        good, bad = normalize(df, t, fetched_at)
        stats["dropped"] += bad
        if good:
            stats["tickers_ok"] += 1
            rows += good
    stats |= store(engine, rows)
    if rows:
        stats["latest_date"] = max(r["trade_date"] for r in rows).isoformat()
    return stats
