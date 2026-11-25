"""Web hợp nhất, lát 4 (docs/PLAN_WEB_HOP_NHAT.md mục 12): cầu nối sang dịch vụ chứng quyền.

Cầu nối không tính gì nên test kiểm đúng ba việc: JSON đi qua nguyên vẹn, chỉ đường dẫn trong danh sách
cho phép mới được gọi, lỗi của dịch vụ được báo đúng mã và đúng câu. Dịch vụ là giả (httpx.MockTransport),
không mở kết nối mạng nào.
"""

from __future__ import annotations

import socket

import httpx
import pytest
from fastapi.testclient import TestClient

from valuation.api import web_main
from valuation.config import load_defaults, settings
from valuation.services import web_cw

# từ lát 5a route số liệu đòi tài khoản đã duyệt; các test này kiểm số liệu nên đi qua bằng fixture
pytestmark = pytest.mark.usefixtures("web_approved")

# Số của CVRE2609 ở lần quét 17/11/2026, chép tay từ file quét của cw_scanner
CW_ROW = {"ma": "CVRE2609", "gia_mua": 1140, "hop_ly": 1397, "dat_re": -18.4}


@pytest.fixture
def service(monkeypatch):
    """Dịch vụ chứng quyền giả: ghi lại đường dẫn được gọi, trả theo bảng `replies`."""
    called: list[str] = []
    replies: dict[str, tuple[int, object]] = {
        "/api/chung-quyen": (200, {"co": True, "tong": 1, "cw": [CW_ROW]}),
        "/api/chung-quyen/CVRE2609": (200, {"cw": CW_ROW, "tieu_chi": []}),
        "/api/trang-cu/cw/CVRE2609": (200, {"html": "<p>trang cũ</p>"}),
        "/api/trang-cu/etf/E1VFVN30": (200, {"html": "<p>quỹ</p>"}),
        "/api/trang-cu/phai-sinh/VN30F1M": (200, {"html": "<p>hợp đồng</p>"}),
        "/api/etf": (503, {"loi": "Đang quét dữ liệu, thử lại sau ít phút."}),
        "/api/phai-sinh": (500, {"loi": "Không tải được dữ liệu (ConnectionError)"}),
        "/api/chung-quyen/CXXX9999": (404, {"loi": "Không có mã này."}),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        called.append(request.url.path)
        status, body = replies[request.url.path]
        return httpx.Response(status, json=body)

    def no_socket(*_args, **_kwargs):
        raise AssertionError("test không được mở kết nối mạng")

    monkeypatch.setattr(socket, "create_connection", no_socket)
    monkeypatch.setattr(
        web_cw,
        "_client",
        lambda: httpx.Client(
            base_url="http://cw.test", transport=httpx.MockTransport(handler)
        ),
    )
    return called


@pytest.fixture
def client():
    return TestClient(web_main.app)


def test_json_di_qua_nguyen_ven(service, client):
    r = client.get("/api/chung-quyen")
    assert r.status_code == 200
    # ca kiểm tay: 1140 / 1397 − 1 = −18,4% đúng số file quét; cầu nối không được làm tròn hay đổi số
    assert r.json() == {"co": True, "tong": 1, "cw": [CW_ROW]}
    assert round((1140 / 1397 - 1) * 100, 1) == r.json()["cw"][0]["dat_re"]
    assert client.get("/api/chung-quyen/CVRE2609").json()["cw"] == CW_ROW
    assert service == ["/api/chung-quyen", "/api/chung-quyen/CVRE2609"]


def test_trang_cu_theo_tung_loai(service, client):
    assert client.get("/api/chung-quyen/CVRE2609/trang-cu").json() == {
        "html": "<p>trang cũ</p>"
    }
    assert client.get("/api/etf/E1VFVN30/trang-cu").json() == {"html": "<p>quỹ</p>"}
    assert client.get("/api/phai-sinh/VN30F1M/trang-cu").json() == {
        "html": "<p>hợp đồng</p>"
    }
    assert service == [
        "/api/trang-cu/cw/CVRE2609",
        "/api/trang-cu/etf/E1VFVN30",
        "/api/trang-cu/phai-sinh/VN30F1M",
    ]


def test_loi_cua_dich_vu_bao_dung_ma_va_cau(service, client):
    dang_quet = client.get("/api/etf")
    assert dang_quet.status_code == 503
    assert dang_quet.json()["detail"] == "Đang quét dữ liệu, thử lại sau ít phút."
    ma_la = client.get("/api/chung-quyen/CXXX9999")
    assert ma_la.status_code == 404 and ma_la.json()["detail"] == "Không có mã này."
    # lỗi lúc tính ở dịch vụ (500) thành 502 ở đây, giữ nguyên câu báo để biết lỗi gì
    loi = client.get("/api/phai-sinh")
    assert loi.status_code == 502 and "ConnectionError" in loi.json()["detail"]


def test_ma_sai_mau_khong_goi_dich_vu(service, client):
    assert client.get("/api/chung-quyen/cvre2609").status_code == 422
    assert client.get("/api/chung-quyen/CV").status_code == 422
    assert client.get("/api/phai-sinh/VN30F9Z/trang-cu").status_code == 422
    assert client.get("/api/etf/..%2F..%2Fquet/trang-cu").status_code in (404, 422)
    assert service == []


def test_chi_duong_dan_trong_danh_sach(service):
    for path in (
        "/quet",
        "/api/chung-quyen/../quet",
        "/api/trang-cu/cw/cvre2609",
        "/api/trang-cu/phai-sinh/VN30F9Z",
        "/api/chung-quyen?von=1",
        "/danh-muc/them",
        "/canh-bao/tin",  # tin của web cũ có mức giá và danh mục dùng chung: web mới không đọc
        "/api/canh-bao/tin/x",
        "/canh-bao/them",
    ):
        with pytest.raises(web_cw.CwServiceError) as exc:
            web_cw.fetch(path)
        assert exc.value.status == 404
    for path in ("/api/tinh/khac", "/canh-bao/them", "/canh-bao/xoa", "/quet"):
        with pytest.raises(web_cw.CwServiceError) as exc:
            web_cw.compute(path, {})
        assert exc.value.status == 404
    assert service == []


def test_duong_canh_bao_va_muc_gia_di_qua(monkeypatch):
    """Lát 5c: hai đường GET cảnh báo chung và đường POST chỉ tính mức giá; lỗi 422 của dịch vụ giữ nguyên."""
    seen: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path))
        if request.method == "POST":
            return httpx.Response(422, json={"loi": "VPB không có trên bảng giá"})
        return httpx.Response(200, json={"ngoai_gio": True, "tin": []})

    monkeypatch.setattr(
        web_cw,
        "_client",
        lambda: httpx.Client(
            base_url="http://cw.test", transport=httpx.MockTransport(handler)
        ),
    )
    assert web_cw.fetch("/api/canh-bao")["ngoai_gio"] is True
    assert web_cw.fetch("/api/canh-bao/tin")["tin"] == []
    with pytest.raises(web_cw.CwServiceError) as exc:
        web_cw.compute("/api/tinh/muc-gia", {"muc": []})
    assert exc.value.status == 422 and exc.value.detail == "VPB không có trên bảng giá"
    assert seen == [
        ("GET", "/api/canh-bao"),
        ("GET", "/api/canh-bao/tin"),
        ("POST", "/api/tinh/muc-gia"),
    ]


def test_mat_ket_noi_bao_503(monkeypatch, client):
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("từ chối kết nối", request=request)

    monkeypatch.setattr(
        web_cw,
        "_client",
        lambda: httpx.Client(
            base_url="http://cw.test", transport=httpx.MockTransport(down)
        ),
    )
    r = client.get("/api/chung-quyen")
    assert r.status_code == 503
    assert "Chưa kết nối được dịch vụ chứng quyền" in r.json()["detail"]
    assert "ConnectError" in r.json()["detail"]


def test_noi_dung_khong_phai_json_bao_502(monkeypatch):
    monkeypatch.setattr(
        web_cw,
        "_client",
        lambda: httpx.Client(
            base_url="http://cw.test",
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, text="<html>trang chờ</html>")
            ),
        ),
    )
    with pytest.raises(web_cw.CwServiceError) as exc:
        web_cw.fetch("/api/etf")
    assert exc.value.status == 502


def test_cau_hinh_tro_ve_may_nay():
    """Địa chỉ dịch vụ nằm trong config, mặc định là chính máy này (không gọi ra ngoài)."""
    cfg = load_defaults()["web"]
    assert cfg["cw_base_url"].startswith(("http://127.0.0.1:", "http://localhost:"))
    assert cfg["cw_timeout_seconds"] > 0


def test_dia_chi_dich_vu_doi_duoc_bang_bien_moi_truong(monkeypatch):
    """Lát 6: trên VPS dịch vụ chứng quyền là container khác, địa chỉ lấy từ WEB_CW_BASE_URL."""
    monkeypatch.setattr(settings, "web_cw_base_url", "")
    assert web_cw.base_url() == load_defaults()["web"]["cw_base_url"]
    monkeypatch.setattr(settings, "web_cw_base_url", "  http://chungquyen:8000 ")
    assert web_cw.base_url() == "http://chungquyen:8000"
    with web_cw._client() as c:
        assert str(c.base_url) == "http://chungquyen:8000"
    # địa chỉ lạ: báo lỗi cấu hình, không gọi đi đâu
    monkeypatch.setattr(settings, "web_cw_base_url", "chungquyen:8000")
    with pytest.raises(web_cw.CwServiceError) as exc:
        web_cw.fetch("/api/etf")
    assert exc.value.status == 503
    assert "WEB_CW_BASE_URL" in exc.value.detail
