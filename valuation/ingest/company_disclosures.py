"""Tin công bố doanh nghiệp từ VCI (news, chế độ detail): cache JSON theo mã, chỉ để hiển thị (D89).

Không ghi DB, không đi vào định giá. Nguồn lỗi → giữ bản cache cũ, ghi lỗi để UI báo.
"""

from __future__ import annotations

import datetime as dt
import math
import re
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from valuation.config import load_defaults
from valuation.ingest.flow_client import FlowRateLimited, _muted
from valuation.services.ranking_store import read_json, write_json

STORE = Path(__file__).resolve().parents[2] / ".disclosures"
_TICKER = re.compile(r"[A-Z0-9]{3,5}")
_FIELDS = ("id", "title", "content", "publish_time", "source", "url", "category")
# Import vnstock_data đồng thời từ nhiều luồng nền từng gây _ModuleLock deadlock → tuần tự hóa.
_FETCH_LOCK = threading.Lock()


def _cfg() -> dict[str, Any]:
    return load_defaults().get("corporate_actions") or {}


def _path(ticker: str, store: Path) -> Path:
    if not _TICKER.fullmatch(ticker):
        raise ValueError(f"Mã không hợp lệ: {ticker!r}")
    return store / f"{ticker}.json"


def _text(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return str(value).strip() or None


def fetch_vci_disclosures(
    ticker: str, *, days: int, limit: int
) -> list[dict[str, Any]]:
    with _FETCH_LOCK, _muted():
        from vnstock_data.explorer.vci.company import Company

        frame = Company(ticker).news(length=days, mode="detail", limit=limit)
    if frame is None or frame.empty:
        return []
    return [
        {key: _text(row.get(key)) for key in _FIELDS}
        for row in frame.to_dict("records")
    ]


def load_cached_disclosures(
    ticker: str, *, store: Path = STORE
) -> dict[str, Any] | None:
    result: dict[str, Any] | None = read_json(_path(ticker, store))
    return result


def disclosures_stale(
    ticker: str, *, now: dt.datetime | None = None, store: Path = STORE
) -> bool:
    cfg = _cfg()
    now = now or dt.datetime.now()
    cached = load_cached_disclosures(ticker, store=store)
    if not cached:
        return True
    if cached.get("error_at"):
        failed = dt.datetime.fromisoformat(cached["error_at"])
        if now - failed < dt.timedelta(minutes=int(cfg.get("error_retry_minutes", 30))):
            return False
    checked = (
        dt.datetime.fromisoformat(cached["checked_at"])
        if cached.get("checked_at")
        else None
    )
    return checked is None or now - checked >= dt.timedelta(
        hours=int(cfg.get("refresh_ttl_hours", 24))
    )


def refresh_disclosures(
    ticker: str,
    *,
    force: bool = False,
    now: dt.datetime | None = None,
    fetcher: Callable[..., list[dict[str, Any]]] | None = None,
    store: Path = STORE,
) -> dict[str, Any]:
    """Tải lại khi hết TTL (hoặc force). Không bao giờ raise lỗi nguồn: trả status ERROR."""
    cfg = _cfg()
    now = now or dt.datetime.now()
    ticker = ticker.upper()
    path = _path(ticker, store)
    if not force and not disclosures_stale(ticker, now=now, store=store):
        return {"status": "FRESH", "checked": False}
    fetcher = fetcher or fetch_vci_disclosures
    kwargs = {
        "days": int(cfg.get("disclosures_days", 90)),
        "limit": int(cfg.get("disclosures_max_items", 30)),
    }
    cached = read_json(path) or {}
    try:
        try:
            items = fetcher(ticker, **kwargs)
        except FlowRateLimited:
            raise
        # VCI hay timeout / vnai lỗi lẻ: thử lại 1 lần (như flow-daily, D88).
        except Exception:  # noqa: BLE001
            items = fetcher(ticker, **kwargs)
    # Lỗi nguồn không được làm hỏng tab: UI báo lỗi và hiện bản cũ.
    except Exception as exc:  # noqa: BLE001
        write_json(
            path, {**cached, "error": type(exc).__name__, "error_at": now.isoformat()}
        )
        return {"status": "ERROR", "checked": True, "error": type(exc).__name__}
    items = sorted(
        (item for item in items if item.get("title")),
        key=lambda item: str(item.get("publish_time") or ""),
        reverse=True,
    )
    write_json(path, {"ticker": ticker, "checked_at": now.isoformat(), "items": items})
    return {"status": "OK", "checked": True, "seen": len(items)}
