"""Khối ngoại từng mã từ Vietcap IQ, chỉ để vá phiên mà FHSC trả trống (lỗi 23/11/2026).

FHSC (nguồn chính, D97) trả khối ngoại mua = bán = 0 cho cả 100 mã VN100 ở phiên 23/11/2026, trong khi Vietcap và
TCBS có số thật. `fhsc_bridge` nhận ra phiên như vậy và bỏ khỏi bộ đệm; module này lấy lại đúng phiên đó.

Nguồn: `iq.vietcap.com.vn/.../company/{mã}/price-history` (config `vietcap_flow`), cùng API mà flow_ingest gọi qua
vnstock_data trước khi gói bị khóa. Cột dùng là *Total (khớp lệnh + thỏa thuận), cùng định nghĩa cột FHSC đang ghi
vào prices_daily: đối chiếu FPT 18–25/11/2026 khớp từng đồng. Đơn vị: cổ phiếu và đồng.
Ghi qua `pipeline.upsert_market_flows` (chỉ cột dòng tiền, idempotent). Phiên Vietcap cũng trả 0 hoặc không có thì
không ghi, báo trong `missing`.
"""

from __future__ import annotations

import datetime as dt
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterable
from typing import Any

import pandas as pd

from valuation.config import load_defaults

COLUMNS = ["time", "buy_vol", "buy_val", "sell_vol", "sell_val", "net_vol", "net_val"]


class VietcapFlowError(RuntimeError):
    """Vietcap không trả lời hoặc trả dữ liệu không đọc được."""


def _cfg() -> dict[str, Any]:
    return dict(load_defaults()["vietcap_flow"])


def parse(rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Dòng price-history của Vietcap → khung khối ngoại cùng dạng FHSC (time là date)."""
    out = []
    for r in rows:
        try:
            day = dt.date.fromisoformat(str(r["tradingDate"])[:10])
            bv, bval = float(r["foreignBuyVolumeTotal"]), float(
                r["foreignBuyValueTotal"]
            )
            sv, sval = float(r["foreignSellVolumeTotal"]), float(
                r["foreignSellValueTotal"]
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise VietcapFlowError(f"dòng Vietcap thiếu cột khối ngoại: {exc}") from exc
        out.append(
            {
                "time": day,
                "buy_vol": bv,
                "buy_val": bval,
                "sell_vol": sv,
                "sell_val": sval,
                "net_vol": bv - sv,
                "net_val": bval - sval,
            }
        )
    df = pd.DataFrame(out, columns=COLUMNS)
    df.attrs.update(source="vietcap_iq")
    return df


def fetch_foreign(
    ticker: str, opener: Callable[..., Any] = urllib.request.urlopen
) -> pd.DataFrame:
    """`page_size` phiên gần nhất của một mã."""
    cfg = _cfg()
    q = urllib.parse.urlencode(
        {"timeFrame": "ONE_DAY", "page": 0, "size": int(cfg["page_size"])}
    )
    req = urllib.request.Request(
        f"{cfg['url'].format(ticker=ticker)}?{q}", headers=dict(cfg["headers"])
    )
    try:
        with opener(req, timeout=float(cfg["timeout_seconds"])) as r:
            body = json.load(r)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise VietcapFlowError(f"Vietcap không trả lời ({type(exc).__name__})") from exc
    rows = ((body or {}).get("data") or {}).get("content")
    if not isinstance(rows, list):
        raise VietcapFlowError("Vietcap trả dữ liệu không có data.content")
    return parse(rows)


def fill_sessions(
    tickers: Iterable[str],
    days: list[dt.date],
    fetch: Callable[[str], pd.DataFrame] | None = None,
    write: Callable[[str, pd.DataFrame, Any], None] | None = None,
    pause: float | None = None,
) -> dict[str, Any]:
    """Lấy khối ngoại của các phiên `days` từ Vietcap rồi ghi. Trả số mã đã ghi, mã thiếu, mã lỗi."""
    if fetch is None:
        fetch = fetch_foreign
    if write is None:
        from valuation.ingest.pipeline import upsert_market_flows as write
    wait = float(_cfg()["pause_seconds"]) if pause is None else pause
    want = set(days)
    written, missing, errors = 0, [], {}
    for i, t in enumerate(tickers):
        if i and wait:
            time.sleep(wait)
        try:
            df = fetch(t)
        except VietcapFlowError as exc:
            errors[t] = str(exc)
            continue
        df = df[df["time"].isin(want) & ~(df["buy_val"].eq(0) & df["sell_val"].eq(0))]
        if len(df) < len(want):
            missing.append(t)
        if not df.empty:
            write(t, df, None)
            written += 1
    return {
        "days": [d.isoformat() for d in sorted(want)],
        "written": written,
        "missing": missing,
        "errors": errors,
    }
