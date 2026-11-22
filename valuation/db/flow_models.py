"""Bảng flow_daily (B1, D73): dòng tiền khớp/thỏa thuận chính xác theo nguồn.

MetaData RIÊNG, không dùng Base của models.py: init_db()/create_all của app
không được tự tạo bảng này; chỉ scripts/migrate_flow_daily.py tạo sau khi backup.
Đơn vị: giá trị VND, khối lượng cổ phiếu. NULL = nguồn không có số (không phải 0).
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Engine,
    Float,
    MetaData,
    String,
    Table,
    create_engine,
    make_url,
)

from valuation.config import PROJECT_ROOT

FlowMetaData = MetaData()


def open_flow_engine(url: str) -> Engine:
    """Engine cho script flow; SQLite tương đối tính từ gốc repo và phải có sẵn file."""
    parsed = make_url(url)
    if parsed.get_backend_name() != "sqlite":
        return create_engine(url)
    path = Path(parsed.database or "")
    path = path if path.is_absolute() else PROJECT_ROOT / path
    if not path.is_file():
        # sqlite tự tạo file rỗng khi connect → chặn để không đẻ DB rỗng
        raise FileNotFoundError(f"Không thấy file SQLite: {path}")
    return create_engine(f"sqlite:///{path}")


# Float (double) giữ đúng số nguyên VND tới 2^53 ≈ 9e15, đủ cho mọi mã-phiên.
def _sides(who: str) -> list[str]:
    return [
        f"{who}_{side}_{kind}_{unit}"
        for side in ("buy", "sell", "net")
        for kind in ("match", "deal")
        for unit in ("vol", "val")
    ]


MEASURE_COLUMNS: tuple[str, ...] = (
    "matched_vol",
    "matched_val",
    "deal_vol",
    "deal_val",
    *_sides("fr"),
    "fr_total_room",  # cổ phiếu
    "fr_current_room",  # cổ phiếu
    "fr_owned_pct",  # tỷ lệ 0–1 như VCI trả (0,1605 = 16,05%)
    *_sides("prop"),
)
PK_COLUMNS: tuple[str, ...] = ("ticker", "trade_date", "source")

flow_daily = Table(
    "flow_daily",
    FlowMetaData,
    Column("ticker", String, primary_key=True),
    Column("trade_date", Date, primary_key=True),
    Column("source", String, primary_key=True),
    *(Column(name, Float, nullable=True) for name in MEASURE_COLUMNS),
    Column("fetched_at", DateTime, nullable=False),  # giờ VN, không tz
    Column("is_final", Boolean, nullable=False),
    Column("batch_id", String, nullable=False),
    Column("quality_flags", String, nullable=True),  # mã cờ cách bằng dấu phẩy
)

# W0 Wyckoff (D101, docs/PLAN_WYCKOFF_FLOW.md): KL mua/bán CHỦ ĐỘNG theo phiên (cổ phiếu, danh nghĩa như FHSC
# trả). FHSC chỉ giữ ~61 phiên gần nhất → job lưu hằng ngày. Chỉ phiên đã chốt (cầu nối bỏ phiên hôm nay);
# dòng thiếu số không được ghi (không có NULL), phiên đã lưu không bị ghi đè (số lệch chỉ ghi log).
# Tạo bằng scripts/migrate_active_flow.py sau khi backup, như flow_daily.
ACTIVE_COLUMNS: tuple[str, ...] = ("active_buy_vol", "active_sell_vol")
active_flow_daily = Table(
    "active_flow_daily",
    FlowMetaData,
    Column("ticker", String, primary_key=True),
    Column("trade_date", Date, primary_key=True),
    Column("source", String, primary_key=True),
    *(Column(name, Float, nullable=False) for name in ACTIVE_COLUMNS),
    Column("fetched_at", DateTime, nullable=False),  # giờ VN, không tz
)
