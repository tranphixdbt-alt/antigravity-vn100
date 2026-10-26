"""Client VCI cho flow_daily (B1, D73).

Gọi thẳng explorer vnstock_data (Trading.price_history get_all=True, prop_trade),
không qua tầng chuẩn hóa vì tầng đó bỏ cột khớp/thỏa thuận. Nguồn trả sẵn VND và
cổ phiếu (đã kiểm MCH 09/10: deal_value 9.641.185.650.000 = 9.641,19 tỷ).
"""

from __future__ import annotations

import contextlib
import datetime as dt
import io
import logging
import os
import re
import time
from collections.abc import Callable, Iterable, Iterator
from typing import Any
from urllib.parse import urlparse

import numpy as np
import pandas as pd

from valuation.config import load_defaults
from valuation.db.flow_models import MEASURE_COLUMNS

logger = logging.getLogger(__name__)

TICKER_RE = re.compile(r"^[A-Z0-9]{3}$")
_UNIT = {"vol": "volume", "val": "value"}
_KIND = {"match": "matched", "deal": "deal"}
_SIDES = ("buy", "sell", "net")

# cột flow_daily ← cột VCI price_history(get_all=True), vd fr_buy_match_val ← fr_buy_value_matched
PRICE_MAP: dict[str, str] = {
    "matched_vol": "matched_volume",
    "matched_val": "matched_value",
    "deal_vol": "deal_volume",
    "deal_val": "deal_value",
    **{
        f"fr_{s}_{k}_{u}": f"fr_{s}_{_UNIT[u]}_{_KIND[k]}"
        for s in _SIDES
        for k in _KIND
        for u in _UNIT
    },
    "fr_total_room": "fr_total_room",
    "fr_current_room": "fr_current_room",
    "fr_owned_pct": "fr_owned_percentage",
}

# cột flow_daily ← cột VCI prop_trade, vd prop_buy_deal_vol ← total_deal_buy_trade_volume
PROP_MAP: dict[str, str] = {
    f"prop_{s}_{k}_{u}": (
        f"total_{k}_trade_net_{_UNIT[u]}"
        if s == "net"
        else f"total_{k}_{s}_trade_{_UNIT[u]}"
    )
    for s in _SIDES
    for k in _KIND
    for u in _UNIT
}

# Đẳng thức total = khớp + thỏa thuận: (cột tổng, cột khớp, cột thỏa thuận)
PRICE_IDENTITIES: list[tuple[str, str, str]] = [
    ("total_volume", "matched_volume", "deal_volume"),
    ("total_value", "matched_value", "deal_value"),
    *[
        (
            f"fr_{s}_{_UNIT[u]}_total",
            PRICE_MAP[f"fr_{s}_match_{u}"],
            PRICE_MAP[f"fr_{s}_deal_{u}"],
        )
        for s in _SIDES
        for u in _UNIT
    ],
]
PROP_IDENTITIES: list[tuple[str, str, str]] = [
    (
        f"total_trade_net_{_UNIT[u]}" if s == "net" else f"total_{s}_trade_{_UNIT[u]}",
        PROP_MAP[f"prop_{s}_match_{u}"],
        PROP_MAP[f"prop_{s}_deal_{u}"],
    )
    for s in _SIDES
    for u in _UNIT
]

PRICE_REQUIRED = sorted(
    {"trading_date", *PRICE_MAP.values(), *(c for t in PRICE_IDENTITIES for c in t)}
)
PROP_REQUIRED = sorted(
    {"trading_date", *PROP_MAP.values(), *(c for t in PROP_IDENTITIES for c in t)}
)


class FlowSchemaError(ValueError):
    """Nguồn đổi schema (thiếu cột / trùng ngày): dừng cả job, không chạy tiếp."""


class FlowRateLimited(RuntimeError):
    """vnai/vnstock gọi sys.exit (thường do vượt hạn mức): dừng cả job; thông điệp gốc bị bỏ vì
    có tier/tài khoản."""


class FlowConfigError(RuntimeError):
    """Cấu hình flow_ingest sai (nguồn chưa hỗ trợ, domain ngoài allowlist): dừng cả job."""


def validate_tickers(tickers: Iterable[str], universe: set[str]) -> list[str]:
    """Chỉ nhận mã đúng regex và thuộc VN100 (chống injection)."""
    out: list[str] = []
    for raw in tickers:
        ticker = str(raw).strip().upper()
        if not TICKER_RE.fullmatch(ticker):
            raise ValueError(f"Mã không hợp lệ: {raw!r}")
        if ticker not in universe:
            raise ValueError(f"Mã ngoài VN100: {ticker}")
        out.append(ticker)
    return out


def _require(df: pd.DataFrame, required: list[str], what: str) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise FlowSchemaError(f"VCI {what} thiếu cột: {', '.join(missing)}")
    if df["trading_date"].isna().any() or df["trading_date"].duplicated().any():
        raise FlowSchemaError(f"VCI {what} có trading_date rỗng/trùng")


def _part(
    df: pd.DataFrame,
    required: list[str],
    mapping: dict[str, str],
    triples: list[tuple[str, str, str]],
    what: str,
    rel_tol: float,
) -> tuple[pd.DataFrame, dict[dt.date, list[str]]]:
    """Map cột + cờ 'id:<cột tổng>' khi |tổng − (khớp + thỏa thuận)| > tol × max(|·|, 1)."""
    _require(df, required, what)
    dates = pd.to_datetime(df["trading_date"]).dt.date.tolist()
    num = {
        c: pd.to_numeric(df[c]).to_numpy()
        for c in {*mapping.values(), *(c for t in triples for c in t)}
    }
    part = pd.DataFrame(
        {dst: num[src] for dst, src in mapping.items()},
        index=pd.Index(dates, name="trade_date"),
    )
    prefix = "prop:" if what == "prop_trade" else ""
    flags: dict[dt.date, list[str]] = {d: [] for d in dates}
    for total, match, deal in triples:
        t, m, d_ = num[total], num[match], num[deal]
        scale = np.maximum.reduce([np.abs(t), np.abs(m), np.abs(d_), np.ones_like(t)])
        bad = (
            np.abs(t - (m + d_)) > rel_tol * scale
        )  # NaN so sánh ra False: không gắn cờ, giữ NaN
        for date, is_bad in zip(dates, bad):
            if is_bad:
                flags[date].append(f"id:{prefix}{total}")
    return part, flags


def to_flow_frame(
    ticker: str,
    price: pd.DataFrame | None,
    prop: pd.DataFrame | None,
    rel_tol: float,
    source: str = "VCI",
) -> pd.DataFrame:
    """Ghép price_history + prop_trade về cột flow_daily (chưa có fetched_at/is_final/batch_id)."""
    cols = ["ticker", "trade_date", "source", *MEASURE_COLUMNS, "quality_flags"]
    pieces = {
        missing: _part(df, req, mapping, triples, what, rel_tol)
        for df, req, mapping, triples, what, missing in (
            (
                price,
                PRICE_REQUIRED,
                PRICE_MAP,
                PRICE_IDENTITIES,
                "price_history",
                "no_price",
            ),
            (prop, PROP_REQUIRED, PROP_MAP, PROP_IDENTITIES, "prop_trade", "no_prop"),
        )
        if df is not None and not df.empty
    }
    if not pieces:
        return pd.DataFrame(columns=cols)
    merged = (
        pd.concat([part for part, _ in pieces.values()], axis=1)
        .sort_index()
        .rename_axis("trade_date")
    )
    out = merged.reindex(columns=list(MEASURE_COLUMNS)).reset_index()
    flags: list[str | None] = []
    for date in merged.index:
        codes: list[str] = []
        for missing in ("no_price", "no_prop"):
            got = pieces[missing][1] if missing in pieces else {}
            codes += got.get(date, [missing])  # thiếu cả nhóm → NULL, không phải 0
        flags.append(",".join(sorted(codes)) or None)
    out["quality_flags"] = flags
    out["ticker"] = ticker
    out["source"] = source
    return out[cols]


@contextlib.contextmanager
def _muted() -> Iterator[None]:
    """vnai/vnii in/log tên tài khoản, tier, quảng cáo → bỏ hết, chỉ giữ exception.

    SystemExit của thư viện (vnai CleanErrorContext: "Rate limit exceeded … Gói hiện tại: …") đổi
    thành FlowRateLimited KHÔNG mang chuỗi gốc (`from None`), để không lọt tier ra stderr.
    """
    previous = logging.root.manager.disable
    logging.disable(logging.CRITICAL)  # logger thư viện propagate lên root của job
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
            io.StringIO()
        ):
            yield
    except SystemExit:
        raise FlowRateLimited(
            "thư viện vnstock/vnai dừng tiến trình (thường do vượt hạn mức API)"
        ) from None
    finally:
        logging.disable(previous)


class FlowClient:
    """Gọi VCI có throttle theo flow_ingest.max_calls_per_minute; mỗi mã 2 lượt gọi."""

    def __init__(
        self,
        cfg: dict[str, Any] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        defaults = load_defaults()
        self.cfg = cfg or defaults["flow_ingest"]
        # cùng quy ước đẳng thức dòng tiền với tab (money_flow.net_identity_rel_tol)
        self.rel_tol = float(defaults["money_flow"]["net_identity_rel_tol"])
        self._gap = 60.0 / float(self.cfg["max_calls_per_minute"])
        self._sleep, self._clock = sleep, clock
        self._last: float | None = None
        self._trading: Any = None

    def _trading_cls(self) -> Any:
        if self._trading is None:
            if self.cfg["source"] != "VCI":
                raise FlowConfigError(
                    f"flow_ingest.source chưa hỗ trợ: {self.cfg['source']}"
                )
            from valuation.config import settings

            if settings.vnstock_api_key:
                os.environ["VNSTOCK_API_KEY"] = settings.vnstock_api_key
            with _muted():
                from vnstock_data.explorer.vci.const import _VCI_COMPANY_URL
                from vnstock_data.explorer.vci.trading import Trading
            host = urlparse(_VCI_COMPANY_URL).hostname
            if host not in self.cfg["allowed_domains"]:
                raise FlowConfigError(f"Domain VCI ngoài allowlist flow_ingest: {host}")
            self._trading = Trading
        return self._trading

    def _call(self, fn: Callable[..., pd.DataFrame], **kwargs: Any) -> pd.DataFrame:
        if self._last is not None:
            wait = self._gap - (self._clock() - self._last)
            if wait > 0:
                self._sleep(wait)
        try:
            with _muted():
                return fn(**kwargs)
        finally:
            self._last = self._clock()

    def fetch(self, ticker: str, start: dt.date, end: dt.date) -> pd.DataFrame:
        if not TICKER_RE.fullmatch(ticker):
            raise ValueError(f"Mã không hợp lệ: {ticker!r}")
        trading = self._trading_cls()(ticker)
        span = {"resolution": "1D", "start": start.isoformat(), "end": end.isoformat()}
        price = self._call(trading.price_history, get_all=True, **span)
        prop = self._call(trading.prop_trade, **span)
        return to_flow_frame(ticker, price, prop, self.rel_tol, self.cfg["source"])
