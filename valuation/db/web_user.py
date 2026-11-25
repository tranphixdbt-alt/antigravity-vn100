"""Dữ liệu người dùng của web hợp nhất btinvest.vn (lát 5, mục 13 của docs/PLAN_WEB_HOP_NHAT.md).

Nằm ở tệp SQLite RIÊNG (`WEB_USER_DB_URL`, mặc định `web_user.db`), không chung với DB định giá: DB định
giá có thể bị thay bằng bản đóng gói `vn100_full.db.gz`, khi đó tài khoản và danh mục của cả đội sẽ mất
theo. Web mới chỉ ghi vào tệp này.

Bảng: `web_users` (ai được vào, vai gì), `web_audit` (ai làm gì, lúc nào), `web_meta` (phiên bản schema) từ
lát 5a; `web_orders` (lệnh mua bán của từng người, 4 loại tài sản) từ lát 5b; `web_price_levels` (mức giá
từng người tự đặt để được báo) từ lát 5c.
"""

from __future__ import annotations

import datetime as dt
import threading
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from valuation.config import settings

SCHEMA_VERSION = "3"  # 1: tài khoản + nhật ký (5a); 2: thêm web_orders (5b); 3: thêm web_price_levels (5c)

VAI_QUAN_TRI = "quan_tri"
VAI_NHAN_VIEN = "nhan_vien"
VAI = (VAI_QUAN_TRI, VAI_NHAN_VIEN)

CHO_DUYET = "cho_duyet"
DA_DUYET = "da_duyet"
KHOA = "khoa"


class UserBase(DeclarativeBase):
    """Gốc riêng của các bảng người dùng: không chung metadata với các bảng của DB định giá."""


def now_utc() -> dt.datetime:
    """Giờ UTC không kèm múi (SQLite không giữ múi giờ); khi trả ra API thì thêm "Z"."""
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


class WebUser(UserBase):
    """Một tài khoản coin đã từng mở web. Khóa nhận diện là `coin_user_id` (email ở coin có thể trống)."""

    __tablename__ = "web_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    coin_user_id: Mapped[str] = mapped_column(String(64), unique=True)
    email: Mapped[str | None] = mapped_column(String(255))
    username: Mapped[str | None] = mapped_column(String(255))
    ten_hien_thi: Mapped[str | None] = mapped_column(String(255))
    vai: Mapped[str] = mapped_column(String(16), default=VAI_NHAN_VIEN)
    trang_thai: Mapped[str] = mapped_column(String(16), default=CHO_DUYET)
    tao_luc: Mapped[dt.datetime] = mapped_column(DateTime)
    duyet_luc: Mapped[dt.datetime | None] = mapped_column(DateTime)
    duyet_boi: Mapped[int | None] = mapped_column(ForeignKey("web_users.id"))
    thay_luc: Mapped[dt.datetime | None] = mapped_column(DateTime)


class WebAudit(UserBase):
    """Nhật ký: mỗi lần tạo tài khoản, duyệt, khóa, đổi vai ghi một dòng; không sửa, không xóa."""

    __tablename__ = "web_audit"

    id: Mapped[int] = mapped_column(primary_key=True)
    luc: Mapped[dt.datetime] = mapped_column(DateTime)
    # người làm; None = hệ thống
    user_id: Mapped[int | None] = mapped_column(ForeignKey("web_users.id"))
    viec: Mapped[str] = mapped_column(String(32))
    doi_tuong: Mapped[str] = mapped_column(String(64))
    chi_tiet: Mapped[str | None] = mapped_column(Text)


class WebOrder(UserBase):
    """Một lệnh mua hoặc bán người dùng tự ghi vào danh mục. Không sửa: ghi sai thì xóa (xóa mềm) rồi ghi lại."""

    __tablename__ = "web_orders"
    __table_args__ = (
        UniqueConstraint("user_id", "ma_yeu_cau", name="uq_web_orders_request"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("web_users.id"), index=True)
    loai: Mapped[str] = mapped_column(String(8))  # cp, cw, etf, hd
    ma: Mapped[str] = mapped_column(String(16))
    chieu: Mapped[str] = mapped_column(
        String(4)
    )  # MUA, BAN (hợp đồng tương lai: Long, Short)
    so_luong: Mapped[int] = mapped_column()
    gia: Mapped[float] = mapped_column()  # đồng; hợp đồng tương lai: điểm
    ngay: Mapped[str] = mapped_column(
        String(10)
    )  # ngày giao dịch người dùng nhập, YYYY-MM-DD
    chot_loi: Mapped[float | None] = mapped_column()  # 0,5 = báo khi lãi từ 50%
    cat_lo: Mapped[float | None] = mapped_column()
    ghi_chu: Mapped[str | None] = mapped_column(String(255))
    # hợp đồng tương lai nhận diện bằng ngày giao dịch cuối: tên VN30F1M mỗi tháng trỏ sang hợp đồng khác
    hop_dong_gd_cuoi: Mapped[str | None] = mapped_column(String(10))
    # mã do trình duyệt sinh cho mỗi lần bấm gửi: gửi lại cùng mã thì không thành hai lệnh
    ma_yeu_cau: Mapped[str] = mapped_column(String(64))
    tao_luc: Mapped[dt.datetime] = mapped_column(DateTime)
    xoa_luc: Mapped[dt.datetime | None] = mapped_column(DateTime)


class WebPriceLevel(UserBase):
    """Một mức giá người dùng tự đặt để được báo khi giá chạm. Không sửa: đặt sai thì xóa (xóa mềm) rồi đặt lại."""

    __tablename__ = "web_price_levels"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("web_users.id"), index=True)
    # chứng quyền, cổ phiếu, ETF hoặc hợp đồng tương lai (tên VN30F1M: tự chuyển sang hợp đồng mới khi đáo hạn)
    ma: Mapped[str] = mapped_column(String(16))
    chieu: Mapped[str] = mapped_column(
        String(4)
    )  # duoi: giá xuống tới mức; tren: lên tới
    muc: Mapped[float] = mapped_column()  # đồng; hợp đồng tương lai: điểm
    ghi_chu: Mapped[str | None] = mapped_column(String(255))
    tao_luc: Mapped[dt.datetime] = mapped_column(DateTime)
    xoa_luc: Mapped[dt.datetime | None] = mapped_column(DateTime)


class WebMeta(UserBase):
    __tablename__ = "web_meta"

    khoa: Mapped[str] = mapped_column(String(32), primary_key=True)
    gia_tri: Mapped[str] = mapped_column(String(255))


_lock = threading.Lock()
_engine: Engine | None = None
_factory: sessionmaker | None = None


def init_schema(engine: Engine) -> None:
    """Tạo bảng còn thiếu và ghi phiên bản schema. Chạy lại bao nhiêu lần cũng không tạo trùng."""
    UserBase.metadata.create_all(bind=engine)
    with Session(engine) as db:
        meta = db.get(WebMeta, "schema_version")
        if meta is None:
            db.add(WebMeta(khoa="schema_version", gia_tri=SCHEMA_VERSION))
            db.commit()
        elif int(meta.gia_tri) < int(SCHEMA_VERSION):
            # bản schema sau chỉ THÊM bảng (create_all ở trên đã tạo); không đổi, không xóa cột của bản trước
            meta.gia_tri = SCHEMA_VERSION
            db.commit()


def sqlite_file(url: str) -> Path | None:
    """Đường dẫn tệp của một địa chỉ SQLite; `None` nếu là DB khác hoặc SQLite trong bộ nhớ."""
    parsed = make_url(url)
    if parsed.get_backend_name() != "sqlite" or parsed.database in (
        None,
        "",
        ":memory:",
    ):
        return None
    return Path(parsed.database)


def session_factory() -> sessionmaker:
    """Tạo engine ở lần gọi đầu (không tạo tệp DB chỉ vì có ai import module này)."""
    global _engine, _factory
    with _lock:
        if _factory is None:
            url = settings.web_user_db_url
            path = sqlite_file(url)
            if path is not None:
                # SQLite không tự tạo thư mục cha; trên VPS tệp nằm ở /data/web_user/ (lát 6)
                path.parent.mkdir(parents=True, exist_ok=True)
            kwargs = (
                {"connect_args": {"check_same_thread": False}}
                if url.startswith("sqlite")
                else {}
            )
            _engine = create_engine(url, pool_pre_ping=True, **kwargs)
            init_schema(_engine)
            _factory = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
        return _factory


def get_user_db() -> Iterator[Session]:
    db = session_factory()()
    try:
        yield db
    finally:
        db.close()
