"""Cầu nối chỉ đọc sang dịch vụ chứng quyền cho web hợp nhất btinvest.vn (lát 4, mục 12 của kế hoạch).

Chứng quyền, ETF và hợp đồng tương lai do repo `cw_scanner` tính (file quét, Black-Scholes, NAV, basis)
và trả qua `web_api.py` của nó. Ở đây KHÔNG tính gì: chỉ nhận đường dẫn nằm trong danh sách cho phép,
gọi GET tới dịch vụ chạy trên cùng máy (`web.cw_base_url`) và trả nguyên JSON. Lỗi của dịch vụ được
báo nguyên văn, không thay bằng số cũ.
"""

from __future__ import annotations

import re
from typing import Any

import httpx

from valuation.config import load_defaults, settings

# chỉ các đường dẫn GET mà cw_scanner/web_api.py có; mã phải đúng mẫu chữ hoa + số
_ALLOWED = re.compile(
    r"/api/(?:chung-quyen(?:/[A-Z0-9]{4,12})?|etf|phai-sinh|canh-bao(?:/tin)?"
    r"|trang-cu/(?:cw/[A-Z0-9]{4,12}|etf/[A-Z0-9]{3,12}|phai-sinh/VN(?:30|100)F[12][MQ]))"
)
# đường POST chỉ tính của cw_scanner/web_api.py
_ALLOWED_COMPUTE = ("/api/tinh/danh-muc", "/api/tinh/muc-gia")
_PASS_THROUGH = (
    404,
    503,
)  # mã lạ / đang quét: giữ nguyên mã của dịch vụ; lỗi khác quy về 502


class CwServiceError(Exception):
    """Dịch vụ chứng quyền không trả được số: `status` để route trả đúng mã HTTP, `detail` là câu báo."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


def base_url() -> str:
    """Địa chỉ dịch vụ chứng quyền.

    Biến môi trường `WEB_CW_BASE_URL` (trên VPS là tên container trong mạng Docker) được ưu tiên; để trống
    thì dùng `web.cw_base_url` trong config (dịch vụ chạy trên cùng máy). Địa chỉ lạ thì báo lỗi, không gọi.
    """
    url = settings.web_cw_base_url.strip() or load_defaults()["web"]["cw_base_url"]
    if not url.startswith(("http://", "https://")):
        raise CwServiceError(
            503, "Cấu hình địa chỉ dịch vụ chứng quyền (WEB_CW_BASE_URL) không hợp lệ."
        )
    return url


def _client() -> httpx.Client:
    """Client ngắn hạn tới dịch vụ chứng quyền; không dùng proxy của môi trường."""
    return httpx.Client(
        base_url=base_url(),
        timeout=load_defaults()["web"]["cw_timeout_seconds"],
        trust_env=False,
    )


def _reply(response: httpx.Response, pass_through: tuple[int, ...]) -> Any:
    """JSON của dịch vụ; mã lỗi nằm trong `pass_through` giữ nguyên, lỗi khác quy về 502, câu báo giữ nguyên văn."""
    try:
        data = response.json()
    except ValueError as exc:
        raise CwServiceError(
            502, "Dịch vụ chứng quyền trả về nội dung không đọc được."
        ) from exc
    if response.status_code != 200:
        detail = data.get("loi") if isinstance(data, dict) else None
        status = response.status_code if response.status_code in pass_through else 502
        raise CwServiceError(
            status, detail or f"Dịch vụ chứng quyền trả lỗi {response.status_code}."
        )
    return data


def _unreachable(exc: httpx.HTTPError) -> CwServiceError:
    return CwServiceError(
        503,
        "Chưa kết nối được dịch vụ chứng quyền, ETF và phái sinh "
        f"({type(exc).__name__}). Kiểm tra dịch vụ đó đã chạy chưa.",
    )


def fetch(path: str) -> Any:
    """JSON của `path` từ dịch vụ chứng quyền. Sai đường dẫn, mất kết nối, dịch vụ lỗi: CwServiceError."""
    if not _ALLOWED.fullmatch(path):
        raise CwServiceError(404, "Không có đường dẫn này.")
    try:
        with _client() as client:
            response = client.get(path)
    except httpx.HTTPError as exc:
        raise _unreachable(exc) from exc
    return _reply(response, _PASS_THROUGH)


def compute(path: str, body: dict[str, Any]) -> Any:
    """Nhờ dịch vụ chứng quyền TÍNH trên dữ liệu gửi kèm (vị thế, lãi lỗ của một bộ lệnh; giá bây giờ của các
    mức giá tự đặt); dịch vụ đó không lưu gì.

    Lệnh sai, bán quá số đang nắm, mức giá sai đơn vị: dịch vụ trả 422 kèm lý do, giữ nguyên để báo cho người dùng.
    """
    if path not in _ALLOWED_COMPUTE:
        raise CwServiceError(404, "Không có đường dẫn này.")
    try:
        with _client() as client:
            response = client.post(path, json=body)
    except httpx.HTTPError as exc:
        raise _unreachable(exc) from exc
    return _reply(response, (*_PASS_THROUGH, 422))
