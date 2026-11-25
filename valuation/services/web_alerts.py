"""Cảnh báo trong web hợp nhất (lát 5c, mục 13 của docs/PLAN_WEB_HOP_NHAT.md).

Ba nguồn, đều do dịch vụ chứng quyền (`cw_scanner`) tính; ở đây KHÔNG tính con số nào:

- Bất thường đang mua được (chứng quyền rẻ bất thường, ETF dưới iNAV, hợp đồng tương lai đắt hoặc rẻ, chứng
  quyền giảm mạnh): chung cho mọi người, cùng số với trang Cảnh báo cũ. Nhớ `web.alerts.cache_seconds` giây
  vì dịch vụ đó chạy một luồng và mỗi lượt phải tải cả bảng giá.
- Mức giá từng người tự đặt: lưu ở `web_price_levels` (tệp `web_user.db`), của ai người đó thấy. Giá bây giờ
  và "đã chạm hay chưa" hỏi dịch vụ chứng quyền (`canh_bao_gia.trang_thai_muc`).
- Tín hiệu của danh mục người đó (lát 5b), gồm ngưỡng lãi, lỗ người đó tự đặt ở lệnh mua.

Chỉ báo trong web khi đang mở (người dùng chốt 25/11/2026): không Discord, không lịch chạy nền, nên một mức
chạm lúc không ai mở web thì không được ghi lại.
"""

from __future__ import annotations

import math
import re
import threading
import time
from typing import Any

from sqlalchemy.orm import Session

from valuation.config import load_defaults
from valuation.db.web_user import WebAudit, WebPriceLevel, WebUser, now_utc
from valuation.services import web_cw, web_portfolio

SHARED_PATH = "/api/canh-bao"
FEED_PATH = "/api/canh-bao/tin"
LEVELS_PATH = "/api/tinh/muc-gia"
SIDES = ("duoi", "tren")  # giá xuống tới mức / lên tới mức
NOTE_MAX = 100  # như ô ghi chú của trang Cảnh báo cũ
# Lọc sơ ở đây; mẫu đúng của từng loại mã do dịch vụ chứng quyền kiểm (canh_bao_gia.MAU_MA_MUC)
_CODE = re.compile(r"[A-Z0-9]{3,12}")

_lock = threading.Lock()
_cache: dict[str, tuple[float, Any]] = {}


class AlertError(Exception):
    """Không lưu được mức giá: `status` là mã HTTP, `detail` là câu báo."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


def _cfg() -> dict[str, Any]:
    return load_defaults()["web"]["alerts"]


def _now() -> float:
    return time.monotonic()


def clear_cache() -> None:
    with _lock:
        _cache.clear()


def _fresh(key: str, now: float, cfg: dict[str, Any]) -> Any:
    """Mục còn hạn trong bộ nhớ (kết quả hoặc lỗi của lần gọi gần nhất), hết hạn thì None."""
    hit = _cache.get(key)
    if hit is None:
        return None
    ttl = (
        cfg["error_cache_seconds"]
        if isinstance(hit[1], web_cw.CwServiceError)
        else cfg["cache_seconds"]
    )
    return hit[1] if now - hit[0] < ttl else None


def _shared(feed_only: bool) -> dict[str, Any]:
    """Cảnh báo chung từ dịch vụ chứng quyền, dùng chung cho mọi người trong `cache_seconds` giây.

    `feed_only`: lượt hỏi mỗi phút của trình duyệt. Ngoài giờ khớp lệnh dịch vụ trả ngay, không tải gì; trong
    giờ nó trả đủ các bảng nên trang Cảnh báo dùng lại được. Giữ khóa trong lúc gọi: nhiều người hỏi cùng lúc
    chỉ thành một lượt gọi. Dịch vụ lỗi: nhớ lỗi `error_cache_seconds` giây rồi báo CwServiceError.
    """
    cfg = _cfg()
    with _lock:
        now = _now()
        full = _fresh("day_du", now, cfg)
        if isinstance(full, dict) and (not feed_only or not full["ngoai_gio"]):
            return full
        key = "tin" if feed_only else "day_du"
        hit = _fresh(key, now, cfg)
        if isinstance(hit, web_cw.CwServiceError):
            raise hit
        if hit is not None:
            return hit
        try:
            data = web_cw.fetch(FEED_PATH if feed_only else SHARED_PATH)
        except web_cw.CwServiceError as exc:
            _cache[key] = (_now(), exc)
            raise
        stamp = _now()
        _cache[key] = (stamp, data)
        if feed_only and data.get("day_du"):
            _cache["day_du"] = (stamp, data)
        elif not feed_only and not data["ngoai_gio"]:
            _cache["tin"] = (stamp, data)
        return data


def _iso(value: Any) -> str | None:
    return f"{value.isoformat(timespec='seconds')}Z" if value else None


def _active(db: Session, user_id: int) -> list[WebPriceLevel]:
    return (
        db.query(WebPriceLevel)
        .filter(WebPriceLevel.user_id == user_id, WebPriceLevel.xoa_luc.is_(None))
        .order_by(WebPriceLevel.id)
        .all()
    )


def _for_service(level: WebPriceLevel) -> dict[str, Any]:
    return {
        "id": level.id,
        "ma": level.ma,
        "chieu": level.chieu,
        "muc": level.muc,
        "ghi_chu": level.ghi_chu or "",
    }


def level_dict(level: WebPriceLevel) -> dict[str, Any]:
    return {**_for_service(level), "tao_luc": _iso(level.tao_luc)}


def _audit(db: Session, user_id: int, viec: str, level: WebPriceLevel) -> None:
    db.add(
        WebAudit(
            luc=now_utc(),
            user_id=user_id,
            viec=viec,
            doi_tuong=f"web_price_levels:{level.id}",
        )
    )


def _validate(data: dict[str, Any]) -> dict[str, Any]:
    """Kiểm kiểu của một mức nhập vào; sai thì AlertError 422, không sửa hộ."""
    ma = str(data.get("ma") or "").strip().upper()
    chieu, muc = data.get("chieu"), data.get("muc")
    if not _CODE.fullmatch(ma):
        raise AlertError(422, "Mã không đúng dạng.")
    if chieu not in SIDES:
        raise AlertError(422, "Chọn báo khi giá xuống tới hoặc lên tới mức.")
    if (
        isinstance(muc, bool)
        or not isinstance(muc, (int, float))
        or not math.isfinite(muc)
        or muc <= 0
    ):
        raise AlertError(422, "Mức giá phải lớn hơn 0.")
    note = str(data.get("ghi_chu") or "").strip()
    return {
        "ma": ma,
        "chieu": chieu,
        "muc": float(muc),
        "ghi_chu": note[:NOTE_MAX] or None,
    }


def levels(db: Session, user: WebUser) -> dict[str, Any]:
    """Các mức giá của `user` kèm giá bây giờ. Chưa đặt mức nào thì không gọi dịch vụ chứng quyền.

    Dịch vụ lỗi: vẫn trả danh sách mức (để còn xóa được), kèm câu báo ở `loi_gia`; không có giá thay thế.
    """
    rows = _active(db, user.id)
    base: dict[str, Any] = {
        "toi_da": _cfg()["max_levels"],
        "luc": None,
        "loi_gia": None,
    }
    if not rows:
        return {**base, "muc": []}
    try:
        data = web_cw.compute(LEVELS_PATH, {"muc": [_for_service(r) for r in rows]})
    except web_cw.CwServiceError as exc:
        return {
            **base,
            "loi_gia": exc.detail,
            "muc": [{**level_dict(r), "gia": None, "cham": None} for r in rows],
        }
    created = {r.id: _iso(r.tao_luc) for r in rows}
    return {
        **base,
        "luc": data["luc"],
        "co_phien": data["co_phien"],
        "muc": [{**m, "tao_luc": created.get(m["id"])} for m in data["muc"]],
    }


def add_level(db: Session, user: WebUser, data: dict[str, Any]) -> dict[str, Any]:
    """Đặt một mức giá cho `user`. Đặt lại đúng mức đang có (cùng mã, chiều, mức) thì trả mức đó, không tạo thêm."""
    row = _validate(data)
    current = _active(db, user.id)
    same = next(
        (
            c
            for c in current
            if (c.ma, c.chieu, c.muc) == (row["ma"], row["chieu"], row["muc"])
        ),
        None,
    )
    if same is not None:
        return {**level_dict(same), "da_co": True}
    limit = _cfg()["max_levels"]
    if len(current) >= limit:
        raise AlertError(422, f"Tối đa {limit} mức, hãy xóa bớt mức cũ trước.")
    probe = {
        "id": 1,
        "ma": row["ma"],
        "chieu": row["chieu"],
        "muc": row["muc"],
        "ghi_chu": row["ghi_chu"] or "",
    }
    try:
        # mã có trên bảng giá và mức không lệch quá 10 lần giá hiện tại (nghi nhập sai đơn vị)
        web_cw.compute(LEVELS_PATH, {"muc": [probe], "chi_kiem": True})
    except web_cw.CwServiceError as exc:
        # dịch vụ đánh số mức trong danh sách gửi sang ("mức thứ 1: …"); ở đây chỉ có một mức nên bỏ phần đó
        detail = exc.detail.removeprefix("mức thứ 1: ")
        raise AlertError(exc.status, detail[:1].upper() + detail[1:]) from exc
    level = WebPriceLevel(user_id=user.id, tao_luc=now_utc(), xoa_luc=None, **row)
    db.add(level)
    db.flush()
    _audit(db, user.id, "them_muc_gia", level)
    db.commit()
    return {**level_dict(level), "da_co": False}


def delete_level(db: Session, user: WebUser, level_id: int) -> dict[str, Any]:
    """Xóa mềm một mức giá CỦA CHÍNH `user`."""
    level = (
        db.query(WebPriceLevel)
        .filter(
            WebPriceLevel.id == level_id,
            WebPriceLevel.user_id == user.id,
            WebPriceLevel.xoa_luc.is_(None),
        )
        .one_or_none()
    )
    if level is None:
        raise AlertError(404, "Không có mức giá này trong danh sách của bạn.")
    level.xoa_luc = now_utc()
    _audit(db, user.id, "xoa_muc_gia", level)
    db.commit()
    return {"id": level.id, "da_xoa": True}


def page(db: Session, user: WebUser) -> dict[str, Any]:
    """Trang Cảnh báo: bất thường chung (xem được cả ngoài giờ) và các mức giá của người đang đăng nhập."""
    try:
        shared, shared_error = _shared(feed_only=False), None
    except web_cw.CwServiceError as exc:
        shared, shared_error = None, exc.detail
    return {
        "chung": shared,
        "loi_chung": shared_error,
        "muc_gia": levels(db, user),
        "hoi_moi_giay": _cfg()["poll_seconds"],
    }


def feed(db: Session, user: WebUser) -> dict[str, Any]:
    """Tin để trình duyệt báo: phần chung + mức giá đang chạm + tín hiệu danh mục của chính `user`.

    Ngoài giờ khớp lệnh hoặc ngày nghỉ: không có tin và không gọi giá cho mức giá, danh mục. Phần nào lỗi thì
    ghi vào `loi`, các phần khác vẫn báo.
    """
    base = {"hoi_moi_giay": _cfg()["poll_seconds"]}
    try:
        shared = _shared(feed_only=True)
    except web_cw.CwServiceError as exc:
        return {**base, "ngoai_gio": False, "tin": [], "loi": [exc.detail]}
    if shared["ngoai_gio"]:
        return {**base, "ngoai_gio": True, "tin": [], "loi": list(shared["loi"])}
    tin, loi = list(shared["tin"]), list(shared["loi"])
    rows = _active(db, user.id)
    if rows:
        try:
            data = web_cw.compute(LEVELS_PATH, {"muc": [_for_service(r) for r in rows]})
            tin += data["tin"]
        except web_cw.CwServiceError as exc:
            loi.append(f"mức giá của bạn: {exc.detail}")
    orders = web_portfolio.service_orders(db, user.id)
    if orders:
        try:
            data = web_cw.compute(web_portfolio.COMPUTE_PATH, {"lenh": orders})
            tin += data["tin"]
            loi += data["loi_gia"]
        except web_cw.CwServiceError as exc:
            loi.append(f"danh mục của bạn: {exc.detail}")
    return {**base, "ngoai_gio": False, "tin": tin, "loi": loi}
