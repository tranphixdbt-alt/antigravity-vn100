"""Tải giá ngày, khối ngoại, tự doanh từ FHSC qua vnstock thế hệ 6 (D95). Chạy bằng ~/.venv_6x/bin/python
do `valuation/ingest/fhsc_bridge.py` gọi; CHỈ tải rồi in JSON — ghi DB vẫn do app (~/.venv) làm, nên môi
trường mới không cần gói của dự án.

Vào (stdin, JSON): {"starts": {"FPT": "2026-11-05", ...}, "kinds": ["prices", "foreign", "prop"],
                     "min_interval_sec": 1.4, "rate_limit_wait_sec": 30, "rate_limit_retries": 2}
Ra (stdout): mỗi dòng {"ticker", "kind", "profile", "rows": [...]} hoặc {"ticker", "kind", "error"}.
"""

from __future__ import annotations

import json
import sys
import time
from collections.abc import Callable, Iterator
from typing import Any

INDEXES = {"VNINDEX", "VN30", "HNXINDEX", "UPCOMINDEX"}
METHODS = {"prices": "ohlcv", "foreign": "foreign_flow", "prop": "proprietary_flow"}


def _with_429_retry(fn: Callable[[], Any], wait: float, retries: int, sleep: Callable[[float], None]) -> Any:
    """FHSC trả 429 khi gọi dồn (~3 lần/giây, 12/11/2026) → chờ rồi thử lại; lỗi khác nổi lên ngay."""
    for attempt in range(retries + 1):
        try:
            return fn()
        except Exception as exc:  # chỉ thử lại 429, còn lại ném tiếp cho fetch_all ghi lỗi
            if "429" not in str(exc) or attempt >= retries:
                raise
            sleep(wait)
    raise AssertionError("không tới được")


def fetch_all(
    req: dict[str, Any],
    market: Callable[[], Any],
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> Iterator[dict[str, Any]]:
    """Từng (mã, loại) một, cách nhau ≥ min_interval_sec; lỗi một mã không dừng cả lượt."""
    last: float | None = None
    for ticker, start in req["starts"].items():
        for kind in req["kinds"]:
            if kind != "prices" and ticker in INDEXES:
                continue  # chỉ số không có khối ngoại/tự doanh
            if last is not None and (gap := req["min_interval_sec"] - (clock() - last)) > 0:
                sleep(gap)
            last = clock()
            try:
                m = market()
                asset = m.index(ticker) if ticker in INDEXES else m.equity(ticker)
                method = getattr(asset, METHODS[kind])
                df = _with_429_retry(
                    lambda m=method, s=start: m(start=s),
                    req["rate_limit_wait_sec"],
                    req["rate_limit_retries"],
                    sleep,
                )
                rows = json.loads(df.to_json(orient="records", date_format="iso"))
                yield {"ticker": ticker, "kind": kind, "profile": df.attrs.get("profile"), "rows": rows}
            except Exception as exc:  # noqa: BLE001 — trả lỗi về app, app dùng VCI cho mã này
                yield {"ticker": ticker, "kind": kind, "error": f"{type(exc).__name__}: {str(exc)[:200]}"}


def main() -> int:
    from vnstock import Market

    req = json.load(sys.stdin)
    for item in fetch_all(req, lambda: Market("fhsc")):
        print(json.dumps(item, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
