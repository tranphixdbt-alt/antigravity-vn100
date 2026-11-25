"""Tài khoản được duyệt và hai vai của web hợp nhất (lát 5a, mục 13 của docs/PLAN_WEB_HOP_NHAT.md).

Mỗi người đăng nhập bằng tài khoản coin có một dòng `web_users`. Lần đầu thấy: `cho_duyet`, trừ khi email
hoặc tên đăng nhập nằm trong `WEB_ADMIN_EMAILS` (Quản trị đầu tiên). Quản trị duyệt, khóa, đổi vai; mỗi
việc ghi một dòng `web_audit`. Chỉ ghi vào tệp dữ liệu người dùng, không đụng DB định giá.
"""

from __future__ import annotations

import datetime as dt
import json
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from valuation.config import load_defaults, settings
from valuation.db.web_user import (
    CHO_DUYET,
    DA_DUYET,
    KHOA,
    VAI,
    VAI_NHAN_VIEN,
    VAI_QUAN_TRI,
    WebAudit,
    WebUser,
    now_utc,
)
from valuation.services.web_auth import Identity

TEN_VAI = {VAI_QUAN_TRI: "Quản trị", VAI_NHAN_VIEN: "Nhân viên"}
TEN_TRANG_THAI = {CHO_DUYET: "Chờ duyệt", DA_DUYET: "Đã duyệt", KHOA: "Đã khóa"}
_STATUS_ORDER = {CHO_DUYET: 0, DA_DUYET: 1, KHOA: 2}


class UserActionError(Exception):
    """Việc Quản trị yêu cầu không làm được: `status` là mã HTTP, `detail` là câu báo."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


def admin_keys() -> set[str]:
    """Email hoặc tên đăng nhập của Quản trị đầu tiên, lấy từ `WEB_ADMIN_EMAILS` (không nằm trong repo)."""
    return {
        k.strip().lower() for k in settings.web_admin_emails.split(",") if k.strip()
    }


def _iso(value: dt.datetime | None) -> str | None:
    return f"{value.isoformat(timespec='seconds')}Z" if value else None


def to_dict(user: WebUser) -> dict[str, Any]:
    return {
        "id": user.id,
        "ten": user.ten_hien_thi
        or user.username
        or user.email
        or f"Tài khoản {user.id}",
        "email": user.email,
        "username": user.username,
        "vai": user.vai,
        "ten_vai": TEN_VAI.get(user.vai, user.vai),
        "trang_thai": user.trang_thai,
        "ten_trang_thai": TEN_TRANG_THAI.get(user.trang_thai, user.trang_thai),
        "tao_luc": _iso(user.tao_luc),
        "duyet_luc": _iso(user.duyet_luc),
        "thay_luc": _iso(user.thay_luc),
    }


def _audit(
    db: Session, actor_id: int | None, viec: str, target: WebUser, **chi_tiet: Any
) -> None:
    db.add(
        WebAudit(
            luc=now_utc(),
            user_id=actor_id,
            viec=viec,
            doi_tuong=f"web_users:{target.id}",
            chi_tiet=json.dumps(chi_tiet, ensure_ascii=False) if chi_tiet else None,
        )
    )


def _is_first_admin(identity: Identity) -> bool:
    return bool({identity.email, identity.username} & admin_keys())


def _create(db: Session, identity: Identity) -> WebUser:
    now, first_admin = now_utc(), _is_first_admin(identity)
    user = WebUser(
        coin_user_id=identity.coin_user_id,
        email=identity.email,
        username=identity.username,
        ten_hien_thi=identity.name,
        vai=VAI_QUAN_TRI if first_admin else VAI_NHAN_VIEN,
        trang_thai=DA_DUYET if first_admin else CHO_DUYET,
        tao_luc=now,
        duyet_luc=now if first_admin else None,
        thay_luc=now,
    )
    db.add(user)
    db.flush()
    _audit(db, None, "quan_tri_dau_tien" if first_admin else "tao", user)
    db.commit()
    return user


def ensure_user(db: Session, identity: Identity) -> WebUser:
    """Dòng `web_users` của người này; tạo ở lần đầu thấy. Gọi lại bao nhiêu lần cũng chỉ có một dòng."""
    user = db.query(WebUser).filter_by(coin_user_id=identity.coin_user_id).one_or_none()
    if user is None:
        try:
            return _create(db, identity)
        except IntegrityError:
            # hai yêu cầu đầu tiên của cùng một người tới cùng lúc: yêu cầu kia đã tạo dòng
            db.rollback()
            user = db.query(WebUser).filter_by(coin_user_id=identity.coin_user_id).one()
    changed = False
    for field, value in (
        ("email", identity.email),
        ("username", identity.username),
        ("ten_hien_thi", identity.name),
    ):
        if (
            value is not None and getattr(user, field) != value
        ):  # người dùng đổi thông tin ở coin
            setattr(user, field, value)
            changed = True
    if _is_first_admin(identity) and (
        user.vai != VAI_QUAN_TRI or user.trang_thai != DA_DUYET
    ):
        # WEB_ADMIN_EMAILS được thêm sau khi người này đã mở web: nâng lên Quản trị
        user.vai, user.trang_thai = VAI_QUAN_TRI, DA_DUYET
        user.duyet_luc = user.duyet_luc or now_utc()
        _audit(db, None, "quan_tri_dau_tien", user)
        changed = True
    now = now_utc()
    refresh = load_defaults()["web"]["auth"]["seen_refresh_seconds"]
    if user.thay_luc is None or (now - user.thay_luc).total_seconds() >= refresh:
        user.thay_luc = now
        changed = True
    if changed:
        db.commit()
    return user


def list_users(db: Session) -> list[dict[str, Any]]:
    """Mọi tài khoản đã từng mở web: chờ duyệt đứng trước, rồi đã duyệt, rồi đã khóa; trong nhóm thì mới trước."""
    users = db.query(WebUser).all()
    users.sort(key=lambda u: (_STATUS_ORDER.get(u.trang_thai, 9), -u.id))
    return [to_dict(u) for u in users]


def _target(db: Session, user_id: int) -> WebUser:
    user = db.get(WebUser, user_id)
    if user is None:
        raise UserActionError(404, "Không có tài khoản này.")
    return user


def _keep_one_admin(db: Session, target: WebUser) -> None:
    """Không khóa hoặc hạ vai Quản trị đang hoạt động cuối cùng (kể cả tự làm với chính mình)."""
    if target.vai != VAI_QUAN_TRI or target.trang_thai != DA_DUYET:
        return
    active = db.query(WebUser).filter_by(vai=VAI_QUAN_TRI, trang_thai=DA_DUYET).count()
    if active <= 1:
        raise UserActionError(409, "Phải còn ít nhất một Quản trị đang hoạt động.")


def approve(db: Session, actor: WebUser, user_id: int) -> dict[str, Any]:
    """Duyệt một tài khoản (cũng dùng để mở khóa). Đã duyệt rồi thì không làm gì và không ghi thêm nhật ký."""
    target = _target(db, user_id)
    if target.trang_thai != DA_DUYET:
        truoc = target.trang_thai
        target.trang_thai, target.duyet_luc, target.duyet_boi = (
            DA_DUYET,
            now_utc(),
            actor.id,
        )
        _audit(db, actor.id, "duyet", target, truoc=truoc)
        db.commit()
    return to_dict(target)


def block(db: Session, actor: WebUser, user_id: int) -> dict[str, Any]:
    target = _target(db, user_id)
    if target.trang_thai != KHOA:
        _keep_one_admin(db, target)
        truoc = target.trang_thai
        target.trang_thai = KHOA
        _audit(db, actor.id, "khoa", target, truoc=truoc)
        db.commit()
    return to_dict(target)


def set_role(db: Session, actor: WebUser, user_id: int, vai: str) -> dict[str, Any]:
    if vai not in VAI:
        raise UserActionError(422, "Vai không hợp lệ.")
    target = _target(db, user_id)
    if target.vai != vai:
        if vai != VAI_QUAN_TRI:
            _keep_one_admin(db, target)
        truoc = target.vai
        target.vai = vai
        _audit(db, actor.id, "doi_vai", target, truoc=truoc, sau=vai)
        db.commit()
    return to_dict(target)
