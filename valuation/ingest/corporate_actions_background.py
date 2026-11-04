"""Kiểm tra nguồn sự kiện trong nền để không chặn giao diện Streamlit."""
from __future__ import annotations

import threading
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Dict

from valuation.db.session import SessionLocalWrite
from valuation.ingest.company_disclosures import refresh_disclosures
from valuation.ingest.corporate_actions import refresh_corporate_actions

_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="corporate-actions")
_FUTURES: Dict[str, Future] = {}
_LOCK = threading.Lock()


def _refresh(ticker: str) -> Dict[str, Any]:
    with SessionLocalWrite() as db:
        result = refresh_corporate_actions(db, ticker)
    refresh_disclosures(ticker)  # tin công bố (D89): tự kiểm TTL, lỗi nguồn không raise
    return result


def schedule_corporate_actions_refresh(ticker: str) -> Dict[str, Any]:
    """Lập lịch một lượt kiểm tra; nhiều rerun không tạo request trùng."""
    ticker = ticker.upper()
    with _LOCK:
        future = _FUTURES.get(ticker)
        if future is not None and not future.done():
            return {"status": "BACKGROUND", "checked": False, "running": True}
        if future is not None and future.done():
            _FUTURES.pop(ticker, None)
            try:
                return future.result()
            except Exception as exc:
                return {"status": "ERROR", "checked": True, "error": str(exc)}
        _FUTURES[ticker] = _EXECUTOR.submit(_refresh, ticker)
    return {"status": "BACKGROUND", "checked": False, "running": True}
