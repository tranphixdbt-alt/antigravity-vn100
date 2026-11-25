"""Danh mục 4 loại của từng người trên web hợp nhất (lát 5b, mục 13 của docs/PLAN_WEB_HOP_NHAT.md).

Ở đây chỉ LƯU lệnh (tệp dữ liệu người dùng `web_user.db`) và kiểm đầu vào. Vị thế, giá vốn bình quân và lãi
lỗ do dịch vụ chứng quyền tính (`cw_scanner/vi_the.py`): chứng quyền theo đúng trang Danh mục cũ; cổ phiếu
và ETF cùng công thức đó; hợp đồng tương lai sau phí và thuế. Ba công thức người dùng duyệt ngày 25/11/2026.
Module này không tự tính con số nào; riêng thước của cổ phiếu lấy upside của đợt định giá VN100 gần nhất.

Quyền: mỗi người chỉ thêm, xóa lệnh của mình. Quản trị XEM được danh mục của mọi người (người dùng chốt
25/11/2026), không sửa hộ.
"""

from __future__ import annotations

import datetime as dt
import math
import re
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from valuation.db.web_user import WebAudit, WebOrder, WebUser, now_utc
from valuation.services import web_cw, web_flow, web_valuation

COMPUTE_PATH = "/api/tinh/danh-muc"
ASSETS = {
    "cp": "Cổ phiếu",
    "cw": "Chứng quyền",
    "etf": "ETF",
    "hd": "Hợp đồng tương lai",
}
SIDES = ("MUA", "BAN")
_VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
_CODE = {
    "cp": re.compile(r"[A-Z0-9]{3}"),
    "cw": re.compile(r"C[A-Z]{3}\d{4}"),
    "etf": re.compile(r"[A-Z0-9]{3,12}"),
    "hd": re.compile(r"VN(30|100)F[12][MQ]"),
}
# Quy tắc nhập lệnh chứng quyền của trang Danh mục cũ (danh_muc.kiem_tra_lenh): lô chẵn 100, bước giá 10 đồng
CW_LOT = 100
CW_TICK = 10
MAX_THRESHOLD = 10.0  # chốt lời / cắt lỗ tối đa 1.000%, như trang cũ
NOTE_MAX = 255


class PortfolioError(Exception):
    """Không lưu được hoặc không tính được danh mục: `status` là mã HTTP, `detail` là câu báo."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


def today_vn() -> dt.date:
    return dt.datetime.now(_VN_TZ).date()


def _iso(value: dt.datetime | None) -> str | None:
    return f"{value.isoformat(timespec='seconds')}Z" if value else None


def _active(db: Session, user_id: int) -> list[WebOrder]:
    return (
        db.query(WebOrder)
        .filter(WebOrder.user_id == user_id, WebOrder.xoa_luc.is_(None))
        .order_by(WebOrder.ngay, WebOrder.id)
        .all()
    )


def _for_service(o: WebOrder) -> dict[str, Any]:
    """Một lệnh ở dạng đường chỉ tính của dịch vụ chứng quyền đọc."""
    row: dict[str, Any] = {
        "id": o.id,
        "loai_ts": o.loai,
        "ma": o.ma,
        "loai": o.chieu,
        "so_luong": o.so_luong,
        "gia": o.gia,
        "ngay": o.ngay,
        "chot_loi": o.chot_loi,
        "cat_lo": o.cat_lo,
    }
    if o.loai == "hd":
        row["gd_cuoi"] = o.hop_dong_gd_cuoi
    return row


def service_orders(db: Session, user_id: int) -> list[dict[str, Any]]:
    """Lệnh còn hiệu lực của một người ở dạng dịch vụ chứng quyền đọc (phần cảnh báo dùng lại)."""
    return [_for_service(o) for o in _active(db, user_id)]


def order_dict(o: WebOrder) -> dict[str, Any]:
    return {
        "id": o.id,
        "loai": o.loai,
        "ten_loai": ASSETS.get(o.loai, o.loai),
        "ma": o.ma,
        "chieu": o.chieu,
        "so_luong": o.so_luong,
        "gia": o.gia,
        "ngay": o.ngay,
        "chot_loi": o.chot_loi,
        "cat_lo": o.cat_lo,
        "ghi_chu": o.ghi_chu,
        "gd_cuoi": o.hop_dong_gd_cuoi,
        "tao_luc": _iso(o.tao_luc),
    }


def list_orders(db: Session, user_id: int) -> list[dict[str, Any]]:
    """Sổ lệnh còn hiệu lực của một người, lệnh mới nhất đứng trước."""
    return [order_dict(o) for o in reversed(_active(db, user_id))]


def _audit(db: Session, user_id: int, viec: str, order: WebOrder) -> None:
    db.add(
        WebAudit(
            luc=now_utc(),
            user_id=user_id,
            viec=viec,
            doi_tuong=f"web_orders:{order.id}",
        )
    )


def _resolve_symbol(read_db: Any, loai: str, ma: str) -> str | None:
    """Mã phải có thật trong dữ liệu của đúng loại tài sản. Hợp đồng tương lai: trả ngày giao dịch cuối."""
    try:
        if loai == "cp":
            if not web_valuation.known(read_db, ma):
                raise PortfolioError(422, f"Không có cổ phiếu {ma} trong dữ liệu.")
        elif loai == "cw":
            data = web_cw.fetch("/api/chung-quyen")
            if not data.get("co") or ma not in {c["ma"] for c in data["cw"]}:
                raise PortfolioError(
                    422, f"{ma} không có trong lần quét chứng quyền gần nhất."
                )
        elif loai == "etf":
            data = web_cw.fetch("/api/etf")
            if not data.get("co") or ma not in {h["Mã"] for h in data["quy"]["dong"]}:
                raise PortfolioError(
                    422, f"Không có quỹ ETF {ma} trong kết quả gần nhất."
                )
        else:
            data = web_cw.fetch("/api/phai-sinh")
            found = [h for n in data["nhom"] for h in n["hop_dong"] if h["ma"] == ma]
            if not found or found[0].get("thieu_dao_han"):
                raise PortfolioError(
                    422, f"Chưa xác định được ngày giao dịch cuối của hợp đồng {ma}."
                )
            return str(found[0]["gd_cuoi"])[:10]
    except web_cw.CwServiceError as exc:
        raise PortfolioError(exc.status, exc.detail) from exc
    return None


def _validate(data: dict[str, Any], today: dt.date) -> dict[str, Any]:
    """Kiểm kiểu và khoảng giá trị của một lệnh nhập vào; sai thì PortfolioError 422, không sửa hộ."""
    loai, chieu = data.get("loai"), data.get("chieu")
    ma = str(data.get("ma") or "").strip().upper()
    if loai not in ASSETS:
        raise PortfolioError(422, "Loại tài sản không hợp lệ.")
    if not _CODE[loai].fullmatch(ma):
        raise PortfolioError(422, f"Mã {ASSETS[loai].lower()} không đúng dạng.")
    if chieu not in SIDES:
        raise PortfolioError(422, "Lệnh phải là mua hoặc bán.")
    so_luong, gia = data.get("so_luong"), data.get("gia")
    if isinstance(so_luong, bool) or not isinstance(so_luong, int) or so_luong <= 0:
        raise PortfolioError(422, "Số lượng phải là số nguyên dương.")
    if (
        isinstance(gia, bool)
        or not isinstance(gia, (int, float))
        or not math.isfinite(gia)
        or gia <= 0
    ):
        raise PortfolioError(422, "Giá phải lớn hơn 0.")
    if loai == "cw":
        if so_luong % CW_LOT:
            raise PortfolioError(
                422, f"Số lượng chứng quyền phải là bội số của {CW_LOT}."
            )
        if gia != round(gia) or round(gia) % CW_TICK:
            raise PortfolioError(
                422, f"Giá chứng quyền phải theo bước giá {CW_TICK} đồng."
            )
    try:
        ngay = dt.date.fromisoformat(str(data.get("ngay") or ""))
    except ValueError as exc:
        raise PortfolioError(422, "Ngày không hợp lệ.") from exc
    if ngay > today:
        raise PortfolioError(422, "Ngày giao dịch không được ở tương lai.")
    row: dict[str, Any] = {
        "loai": loai,
        "ma": ma,
        "chieu": chieu,
        "so_luong": so_luong,
        "gia": float(gia),
        "ngay": ngay.isoformat(),
    }
    for key, ten in (("chot_loi", "chốt lời"), ("cat_lo", "cắt lỗ")):
        x = data.get(key)
        if x is not None and (
            isinstance(x, bool)
            or not isinstance(x, (int, float))
            or not 0 < x <= MAX_THRESHOLD
        ):
            raise PortfolioError(422, f"Ngưỡng {ten} phải từ 1% đến 1.000%.")
        row[key] = float(x) if x is not None else None
    note = str(data.get("ghi_chu") or "").strip()
    row["ghi_chu"] = note[:NOTE_MAX] or None
    request_id = str(data.get("ma_yeu_cau") or "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,64}", request_id):
        raise PortfolioError(422, "Thiếu mã yêu cầu của lần gửi.")
    row["ma_yeu_cau"] = request_id
    return row


def _check_positions(orders: list[dict[str, Any]], status: int, prefix: str) -> None:
    """Nhờ dịch vụ chứng quyền dựng thử vị thế (không gọi giá): bán quá số đang nắm thì báo lỗi, không lưu."""
    if not orders:
        return
    try:
        web_cw.compute(COMPUTE_PATH, {"lenh": orders, "chi_kiem": True})
    except web_cw.CwServiceError as exc:
        if exc.status == 422:
            raise PortfolioError(status, f"{prefix}{exc.detail}") from exc
        raise PortfolioError(exc.status, exc.detail) from exc


def add_order(
    db: Session, read_db: Any, user: WebUser, data: dict[str, Any]
) -> dict[str, Any]:
    """Thêm một lệnh vào danh mục của `user`. Gửi lại cùng `ma_yeu_cau` thì trả lệnh đã lưu, không tạo thêm."""
    row = _validate(data, today_vn())
    existing = (
        db.query(WebOrder)
        .filter_by(user_id=user.id, ma_yeu_cau=row["ma_yeu_cau"])
        .one_or_none()
    )
    if existing is not None:
        return {**order_dict(existing), "da_co": True}
    gd_cuoi = _resolve_symbol(read_db, row["loai"], row["ma"])
    order = WebOrder(
        user_id=user.id,
        hop_dong_gd_cuoi=gd_cuoi,
        tao_luc=now_utc(),
        xoa_luc=None,
        **row,
    )
    current = [_for_service(o) for o in _active(db, user.id)]
    draft = {
        **_for_service(order),
        "id": max((o["id"] for o in current), default=0) + 1,
    }
    _check_positions([*current, draft], 422, "")
    db.add(order)
    try:
        db.flush()
    except IntegrityError:
        # hai lần bấm gửi tới cùng lúc: lần kia đã lưu lệnh này
        db.rollback()
        existing = (
            db.query(WebOrder)
            .filter_by(user_id=user.id, ma_yeu_cau=row["ma_yeu_cau"])
            .one()
        )
        return {**order_dict(existing), "da_co": True}
    _audit(db, user.id, "them_lenh", order)
    db.commit()
    return {**order_dict(order), "da_co": False}


def delete_order(db: Session, user: WebUser, order_id: int) -> dict[str, Any]:
    """Xóa mềm một lệnh CỦA CHÍNH `user`. Xóa mà làm một lệnh bán khác thành bán quá số đang nắm thì từ chối."""
    order = (
        db.query(WebOrder)
        .filter(
            WebOrder.id == order_id,
            WebOrder.user_id == user.id,
            WebOrder.xoa_luc.is_(None),
        )
        .one_or_none()
    )
    if order is None:
        raise PortfolioError(404, "Không có lệnh này trong danh mục của bạn.")
    remaining = [_for_service(o) for o in _active(db, user.id) if o.id != order.id]
    _check_positions(
        remaining, 409, "Chưa xóa được vì các lệnh còn lại sẽ không khớp: "
    )
    order.xoa_luc = now_utc()
    _audit(db, user.id, "xoa_lenh", order)
    db.commit()
    return {"id": order.id, "da_xoa": True}


def portfolio(db: Session, read_db: Any, owner: WebUser) -> dict[str, Any]:
    """Danh mục đã định giá của `owner`. Chưa có lệnh nào thì không gọi dịch vụ chứng quyền."""
    orders = _active(db, owner.id)
    base: dict[str, Any] = {
        "chu": {
            "id": owner.id,
            "ten": owner.ten_hien_thi or owner.username or owner.email,
        },
        "so_lenh": len(orders),
    }
    if not orders:
        return {**base, "trong": True}
    try:
        data = web_cw.compute(COMPUTE_PATH, {"lenh": [_for_service(o) for o in orders]})
    except web_cw.CwServiceError as exc:
        raise PortfolioError(exc.status, exc.detail) from exc
    upside_source = None
    if data.get("cp"):
        # thước của cổ phiếu: upside của đợt định giá VN100 gần nhất (cùng số với tab Cổ phiếu), không tính lại
        ups = web_flow.model_upsides(read_db)
        upside_source = ups.get("source")
        for row in data["cp"]:
            row["upside"] = (ups["rows"].get(row["ma"]) or {}).get("upside")
    return {**base, "trong": False, **data, "upside_nguon": upside_source}


def owners(db: Session) -> list[dict[str, Any]]:
    """Mọi tài khoản kèm số lệnh đang có, để Quản trị chọn danh mục muốn xem."""
    counts: dict[int, int] = {}
    for (user_id,) in db.query(WebOrder.user_id).filter(WebOrder.xoa_luc.is_(None)):
        counts[user_id] = counts.get(user_id, 0) + 1
    users = db.query(WebUser).order_by(WebUser.id).all()
    return [
        {
            "id": u.id,
            "ten": u.ten_hien_thi or u.username or u.email or f"Tài khoản {u.id}",
            "email": u.email or u.username,
            "vai": u.vai,
            "so_lenh": counts.get(u.id, 0),
        }
        for u in users
    ]
