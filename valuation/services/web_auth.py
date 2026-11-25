"""Nhận diện người đang dùng web hợp nhất (lát 5a, mục 13 của docs/PLAN_WEB_HOP_NHAT.md).

Đăng nhập chung *.btinvest.vn (D98) chỉ là cổng chặn ở Caddy: nó cho qua hay không, chứ không nói cho
ứng dụng biết AI đang dùng. Ở đây lấy cookie phiên của yêu cầu, hỏi dịch vụ coin `GET /api/v1/auth/me`
và trả về mã người dùng của coin. Không tin bất kỳ header nào do trình duyệt tự gửi.

Đóng khi lỗi: coin không trả lời, cấu hình thiếu hoặc chế độ lạ thì báo 503 và KHÔNG cho vào.
Chế độ `dev` (một người dùng thử, cho máy Mac không có coin) chỉ nhận yêu cầu đến từ chính máy này.
"""

from __future__ import annotations

import hashlib
import threading
import time
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import Request

from valuation.config import load_defaults, settings

MODE_COIN = "coin"
MODE_DEV = "dev"
_LOOPBACK = ("127.0.0.1", "::1")

_lock = threading.Lock()
_cache: dict[str, tuple[float, Identity]] = {}


@dataclass(frozen=True)
class Identity:
    """Người dùng theo dịch vụ coin. `coin_user_id` là khóa; email có thể trống ở coin."""

    coin_user_id: str
    email: str | None
    username: str | None
    name: str | None


class AuthError(Exception):
    """Không nhận diện được người dùng: `status` là mã HTTP, `detail` là câu báo cho giao diện."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


def _cfg() -> dict[str, Any]:
    return load_defaults()["web"]["auth"]


def _client() -> httpx.Client:
    """Client ngắn hạn tới dịch vụ coin; không dùng proxy của môi trường."""
    return httpx.Client(timeout=_cfg()["timeout_seconds"], trust_env=False)


def clear_cache() -> None:
    with _lock:
        _cache.clear()


def _text(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _identity_from_payload(data: Any) -> Identity:
    """`/me` của coin trả `{user: {_id, email?, username, firstName, lastName, ...}, ...}` (đọc mã ngày 25/11/2026)."""
    user = data.get("user") if isinstance(data, dict) else None
    uid = _text((user or {}).get("_id") or (user or {}).get("id"))
    if not isinstance(user, dict) or uid is None:
        raise AuthError(
            503, "Dịch vụ đăng nhập trả về thông tin người dùng không đọc được."
        )
    email, username = _text(user.get("email")), _text(user.get("username"))
    name = " ".join(
        part
        for part in (_text(user.get("firstName")), _text(user.get("lastName")))
        if part
    )
    return Identity(
        coin_user_id=uid,
        email=email.lower() if email else None,
        username=username.lower() if username else None,
        name=name or None,
    )


def identity_from_token(token: str) -> Identity:
    """Hỏi coin `/me` bằng đúng cookie phiên (không gửi cookie nào khác), nhớ kết quả theo mã băm của nó.

    Nhớ `cache_seconds` giây để không vượt giới hạn 600 lượt mỗi phút của coin; đổi lại, người vừa bị
    khóa ở coin còn vào được tối đa chừng đó giây.
    """
    cfg = _cfg()
    key = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = time.monotonic()
    with _lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < cfg["cache_seconds"]:
            return hit[1]
    url = settings.web_auth_me_url
    if not url:
        raise AuthError(
            503, "Chưa cấu hình địa chỉ dịch vụ đăng nhập (WEB_AUTH_ME_URL)."
        )
    try:
        with _client() as client:
            # chỉ gửi đúng cookie phiên, không chuyển tiếp cookie nào khác của trình duyệt
            response = client.get(
                url, headers={"Cookie": f"{cfg['cookie_name']}={token}"}
            )
    except httpx.HTTPError as exc:
        raise AuthError(
            503, f"Chưa kết nối được dịch vụ đăng nhập ({type(exc).__name__})."
        ) from exc
    if response.status_code in (401, 403):
        raise AuthError(401, "Phiên đăng nhập đã hết. Đăng nhập lại.")
    if response.status_code != 200:
        raise AuthError(503, f"Dịch vụ đăng nhập trả lỗi {response.status_code}.")
    try:
        data = response.json()
    except ValueError as exc:
        raise AuthError(
            503, "Dịch vụ đăng nhập trả về nội dung không đọc được."
        ) from exc
    identity = _identity_from_payload(data)
    with _lock:
        if len(_cache) >= cfg["cache_entries"]:
            _cache.pop(min(_cache, key=lambda k: _cache[k][0]))
        _cache[key] = (now, identity)
    return identity


def _dev_identity(request: Request) -> Identity:
    host = request.client.host if request.client else ""
    if host not in _LOOPBACK:
        # sau Caddy trên VPS, địa chỉ gọi tới là của Caddy chứ không phải 127.0.0.1: chế độ dev tự vô hiệu
        raise AuthError(403, "Chế độ thử chỉ dùng trên chính máy đang chạy web.")
    email = _text(settings.web_dev_user)
    if email is None:
        raise AuthError(503, "Chế độ thử chưa đặt người dùng (WEB_DEV_USER).")
    email = email.lower()
    return Identity(
        coin_user_id=f"dev:{email}", email=email, username=None, name="Người dùng thử"
    )


def resolve(request: Request) -> Identity:
    """Người đang gửi yêu cầu. Không đăng nhập: AuthError 401; không xác định được: 503 hoặc 403."""
    mode = settings.web_auth_mode
    if mode == MODE_DEV:
        return _dev_identity(request)
    if mode != MODE_COIN:
        raise AuthError(503, "Cấu hình WEB_AUTH_MODE không hợp lệ.")
    token = request.cookies.get(_cfg()["cookie_name"])
    if not token:
        raise AuthError(401, "Chưa đăng nhập.")
    return identity_from_token(token)
