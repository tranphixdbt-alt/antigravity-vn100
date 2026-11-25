"""Điều kiện dùng chung cho các route của web hợp nhất (lát 5a): ai đang gọi, đã được duyệt chưa, có phải
Quản trị không, và yêu cầu ghi có gửi từ chính trang web không."""

from __future__ import annotations

from typing import Annotated
from urllib.parse import urlsplit

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from valuation.db.web_user import DA_DUYET, KHOA, VAI_QUAN_TRI, WebUser, get_user_db
from valuation.services import web_auth, web_users

UserDb = Annotated[Session, Depends(get_user_db)]


def current_user(request: Request, udb: UserDb) -> WebUser:
    """Người đang đăng nhập (tạo dòng `web_users` ở lần đầu thấy). Chưa đăng nhập: 401."""
    try:
        identity = web_auth.resolve(request)
    except web_auth.AuthError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.detail) from exc
    return web_users.ensure_user(udb, identity)


CurrentUser = Annotated[WebUser, Depends(current_user)]


def require_approved(user: CurrentUser) -> WebUser:
    """Chỉ tài khoản đã duyệt mới xem được số liệu."""
    if user.trang_thai != DA_DUYET:
        detail = (
            "Tài khoản đã bị khóa."
            if user.trang_thai == KHOA
            else "Tài khoản đang chờ Quản trị duyệt."
        )
        raise HTTPException(status_code=403, detail=detail)
    return user


ApprovedUser = Annotated[WebUser, Depends(require_approved)]


def require_admin(user: ApprovedUser) -> WebUser:
    if user.vai != VAI_QUAN_TRI:
        raise HTTPException(status_code=403, detail="Chỉ Quản trị làm được việc này.")
    return user


AdminUser = Annotated[WebUser, Depends(require_admin)]


def same_origin(request: Request) -> None:
    """Chặn trang web khác tự gửi yêu cầu ghi thay người dùng (CSRF): `Origin` (hoặc `Referer`) phải trùng
    tên miền đang truy cập, và thân yêu cầu phải là JSON (form của trang lạ không gửi được kiểu này).
    """
    source = request.headers.get("origin") or request.headers.get("referer") or ""
    host = request.headers.get("host") or ""
    if not host or urlsplit(source).netloc != host:
        raise HTTPException(status_code=403, detail="Yêu cầu không gửi từ trang này.")
    if not request.headers.get("content-type", "").startswith("application/json"):
        raise HTTPException(status_code=415, detail="Yêu cầu ghi phải gửi dạng JSON.")
