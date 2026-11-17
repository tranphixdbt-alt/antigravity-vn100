"""Cầu nối FHSC (vnstock thế hệ 6) cho job hằng ngày (D95).

Thế hệ 6 không cài chung được với dòng 4.x của app (cùng tên gói), nên `scripts/fhsc_fetch.py` chạy bằng
python của `~/.venv_6x`, tải cả rổ trong MỘT tiến trình (khởi động vnstock 6 mất ~5 s) rồi trả JSON. Kết quả
nằm trong bộ đệm có hạn; `vnstock_client`/`market_client` lấy từ đây trước, không có thì gọi VCI như cũ.
Ghi DB vẫn do code hiện tại làm. Chỉ job gọi `prefetch`; nút "Tải mới" trong app vẫn đi VCI (nhanh hơn).
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from valuation.config import PROJECT_ROOT, load_defaults

logger = logging.getLogger(__name__)
SCRIPT = PROJECT_ROOT / "scripts" / "fhsc_fetch.py"
VN = ZoneInfo("Asia/Ho_Chi_Minh")
_CACHE: dict[tuple[str, str], tuple[str, dt.datetime, pd.DataFrame]] = {}


def _cfg() -> dict[str, Any]:
    return load_defaults().get("fhsc") or {}


def _now() -> dt.datetime:
    return dt.datetime.now(VN)


def in_service_hours(now: dt.datetime) -> bool:
    start, end = _cfg()["service_hours"]
    return start <= now.astimezone(VN).strftime("%H:%M") < end


def _frame(item: dict[str, Any]) -> pd.DataFrame:
    """Đưa về đúng dạng VCI: giá có `time` là ngày không múi giờ và đơn vị nghìn đồng; dòng tiền `time` là date."""
    if item["kind"] == "prices" and item.get("profile") != "v5":
        # hồ sơ v6 đổi đơn vị bảng giá; chỉ v5 đã đối chiếu (S1) — không đoán hệ số quy đổi
        raise ValueError(f"hồ sơ cột {item.get('profile')!r} chưa được đối chiếu (chỉ nhận v5)")
    df = pd.DataFrame(item["rows"])
    if not df.empty:
        day = pd.to_datetime(df["time"], utc=True).dt.tz_convert(VN).dt.tz_localize(None).dt.normalize()
        df["time"] = day if item["kind"] == "prices" else day.dt.date
    df.attrs.update(source="fhsc", price_unit="thousand_VND")
    return df


def prefetch(
    starts: dict[str, str],
    kinds: list[str],
    now: dt.datetime | None = None,
    run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> dict[str, Any]:
    """Tải trước cho cả rổ. Trả {"ok": số (mã, loại) dùng được, "errors": {...}, "skipped": lý do hoặc None}.
    Mã lỗi/thiếu sẽ tự đi VCI khi run_ingest gọi client."""
    cfg = _cfg()
    now = now or _now()
    python = Path(cfg.get("python", "")).expanduser()
    skip = None
    if not cfg.get("jobs") or os.environ.get("VN100_FHSC_JOBS") == "0":  # conftest đặt =0: test không gọi mạng
        skip = "tắt trong config (fhsc.jobs)"
    elif not in_service_hours(now):
        skip = "ngoài giờ phục vụ FHSC " + "–".join(cfg["service_hours"])
    elif not python.exists():
        skip = f"chưa có {python} (vnstock thế hệ 6)"
    if skip:
        return {"ok": 0, "errors": {}, "skipped": skip}
    req = {"starts": starts, "kinds": kinds} | {
        k: cfg[k] for k in ("min_interval_sec", "rate_limit_wait_sec", "rate_limit_retries")
    }
    try:
        proc = run(
            [str(python), str(SCRIPT)], input=json.dumps(req), capture_output=True, text=True,
            timeout=cfg["timeout_sec"], cwd=PROJECT_ROOT,
        )
    except subprocess.TimeoutExpired:
        return {"ok": 0, "errors": {}, "skipped": f"quá {cfg['timeout_sec']} s, dùng VCI"}
    ok, errors = 0, {}
    for line in proc.stdout.splitlines():
        item = json.loads(line)
        key = f"{item['ticker']}/{item['kind']}"
        if "error" in item:
            errors[key] = item["error"]
            continue
        try:
            _CACHE[(item["ticker"], item["kind"])] = (starts[item["ticker"]], now, _frame(item))
            ok += 1
        except ValueError as exc:
            errors[key] = str(exc)
    if proc.returncode != 0:
        errors["_tiến_trình"] = f"mã thoát {proc.returncode}: {proc.stderr[-300:]}"
    if errors:
        logger.warning("FHSC: %d lỗi, dùng VCI cho các mã đó: %s", len(errors), list(errors)[:10])
    return {"ok": ok, "errors": errors, "skipped": None}


def cached(ticker: str, kind: str, start: str) -> pd.DataFrame | None:
    """Phần đã tải từ `start` trở đi; None nếu chưa tải, tải từ ngày muộn hơn `start`, hoặc quá hạn bộ đệm."""
    hit = _CACHE.get((ticker, kind))
    if hit is None:
        return None
    fetched_from, at, df = hit
    if fetched_from > start or (_now() - at).total_seconds() > _cfg()["cache_ttl_sec"]:
        return None
    return df[pd.to_datetime(df["time"]) >= pd.Timestamp(start)].copy() if not df.empty else df.copy()


def clear() -> None:
    _CACHE.clear()
