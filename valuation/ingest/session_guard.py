"""Chặn ghi số của phiên đang giao dịch (D121).

Giá, khối ngoại, tự doanh của phiên hôm nay chỉ được ghi DB sau giờ đóng phiên (`market_session.close`).
Trước giờ đó số còn đổi từng phút; ghi vào thì DB có một "phiên mới nhất" sai (lỗi 25/11/2026: MCH đóng cửa
133.000, khối lượng 22.200 ghi giữa phiên; phiên thật đóng 130.000, khối lượng 472.904). Lượt tải sau giờ
đóng phiên (job `gia-cuoi-phien` 15:45) hoặc sáng hôm sau (đệm 5 ngày) sẽ lấy số đã chốt.

Một chỗ dùng chung cho mọi đường ghi: `pipeline.run_ingest` (job giá, Quét VN100, nút "Tải mới"/mở mã ở web cũ)
và `fhsc_bridge.prefetch`.
"""

from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

import pandas as pd

from valuation.config import load_defaults


def _cfg() -> dict:
    return load_defaults()["market_session"]


def now_vn() -> dt.datetime:
    return dt.datetime.now(ZoneInfo(_cfg()["timezone"]))


def unfinished_session_date(now: dt.datetime | None = None) -> dt.date | None:
    """Ngày của phiên CHƯA chốt tại `now` (giờ VN): hôm nay nếu chưa tới giờ đóng phiên, ngược lại None.

    Thứ Bảy, Chủ nhật không có phiên nhưng trả hôm nay cũng vô hại: nguồn không có dòng của ngày đó.
    """
    cfg = _cfg()
    local = (now or now_vn()).astimezone(ZoneInfo(cfg["timezone"]))
    return local.date() if local.strftime("%H:%M") < str(cfg["close"]) else None


def drop_unfinished_session(
    df: pd.DataFrame, now: dt.datetime | None = None, col: str = "time"
) -> pd.DataFrame:
    """Bỏ các dòng thuộc phiên chưa chốt. `col` chứa Timestamp, chuỗi ngày hoặc date đều được."""
    if df.empty or col not in df.columns:
        return df
    day = unfinished_session_date(now)
    if day is None:
        return df
    days = pd.to_datetime(df[col]).dt.date
    return df[days < day].copy() if (days >= day).any() else df
