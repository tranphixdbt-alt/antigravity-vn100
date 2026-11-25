"""Web hợp nhất, lát 5a (docs/PLAN_WEB_HOP_NHAT.md mục 13): tài khoản được duyệt và hai vai.

Dịch vụ coin là giả (httpx.MockTransport), tệp dữ liệu người dùng là SQLite tạm, không mở kết nối mạng.
Kiểm: chưa đăng nhập thì không vào; chưa duyệt thì không xem được số liệu; Quản trị đầu tiên lấy từ
`WEB_ADMIN_EMAILS`; duyệt, khóa, đổi vai có nhật ký và chạy lại không nhân đôi; coin sập thì đóng cửa.
"""

from __future__ import annotations

import json
import re
import socket

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from valuation.api import web_main
from valuation.config import load_defaults, settings
from valuation.db import web_user as wu
from valuation.services import web_auth, web_cw

ORIGIN = {"Origin": "http://testserver"}
SEP = {
    "_id": "u-sep",
    "email": "Sep@Example.com",
    "username": "sep",
    "firstName": "Sếp",
}
AN = {
    "_id": "u-an",
    "email": "an@example.com",
    "username": "an",
    "firstName": "An",
    "lastName": "Lê",
}
BINH = {"_id": "u-binh", "username": "binh"}  # tài khoản coin không có email
TOKENS = {"t-sep": SEP, "t-an": AN, "t-binh": BINH}


def coin_env(tmp_path, monkeypatch):
    """Coin giả + DB người dùng tạm. Trả về dict: `calls` (cookie coin nhận được), `db` (mở phiên đọc), `down`."""
    calls: list[str] = []
    state = {"down": False, "status": 200}

    def handler(request: httpx.Request) -> httpx.Response:
        if state["down"]:
            raise httpx.ConnectError("từ chối kết nối", request=request)
        cookie = request.headers.get("cookie", "")
        calls.append(cookie)
        if state["status"] != 200:
            return httpx.Response(state["status"], json={"message": "lỗi"})
        token = cookie.removeprefix("access_token=")
        if token not in TOKENS:
            return httpx.Response(401, json={"message": "Invalid access token"})
        return httpx.Response(200, json={"user": TOKENS[token], "permissions": []})

    def no_socket(*_args, **_kwargs):
        raise AssertionError("test không được mở kết nối mạng")

    engine = create_engine(
        f"sqlite:///{tmp_path / 'web_user.db'}",
        connect_args={"check_same_thread": False},
    )
    wu.init_schema(engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def user_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(socket, "create_connection", no_socket)
    monkeypatch.setattr(
        web_auth,
        "_client",
        lambda: httpx.Client(transport=httpx.MockTransport(handler)),
    )
    monkeypatch.setattr(settings, "web_auth_mode", "coin")
    monkeypatch.setattr(settings, "web_auth_me_url", "http://coin.test/api/v1/auth/me")
    monkeypatch.setattr(settings, "web_admin_emails", " sep@example.com ")
    web_auth.clear_cache()
    web_main.app.dependency_overrides[wu.get_user_db] = user_db
    yield {"calls": calls, "state": state, "db": factory, "engine": engine}
    web_main.app.dependency_overrides.pop(wu.get_user_db, None)
    web_auth.clear_cache()


@pytest.fixture
def env(tmp_path, monkeypatch):
    yield from coin_env(tmp_path, monkeypatch)


def client(token: str | None = None) -> TestClient:
    c = TestClient(web_main.app)
    if token:
        c.cookies.set("access_token", token)
    return c


def api_operations() -> set[tuple[str, str]]:
    """Mọi cặp (phương thức, đường dẫn) dưới `/api/`, lấy từ bản mô tả API do FastAPI tự sinh."""
    paths = web_main.app.openapi()["paths"]
    return {
        (method.upper(), path)
        for path, operations in paths.items()
        for method in operations
        if path.startswith("/api/")
    }


def flat_routes(routes):
    """Route `/api/` thật của ứng dụng, mở cả các nhóm gắn bằng `include_router` (FastAPI giữ chúng trong vỏ riêng)."""
    for route in routes:
        inner = getattr(route, "original_router", None)
        if inner is not None:
            yield from flat_routes(inner.routes)
        elif getattr(route, "methods", None) and route.path.startswith("/api/"):
            yield route


def users(env) -> list[wu.WebUser]:
    with env["db"]() as db:
        return db.query(wu.WebUser).order_by(wu.WebUser.id).all()


def audit(env) -> list[tuple[int | None, str, str]]:
    with env["db"]() as db:
        return [
            (a.user_id, a.viec, a.doi_tuong)
            for a in db.query(wu.WebAudit).order_by(wu.WebAudit.id)
        ]


def test_chua_dang_nhap_thi_khong_vao(env):
    assert client().get("/api/toi").status_code == 401
    # route số liệu của lát 1–4 cũng đóng, và không tạo dòng tài khoản nào
    assert client().get("/api/xep-hang").status_code == 401
    assert client().get("/api/chung-quyen").status_code == 401
    assert (
        client().get("/api/suc-khoe").status_code == 200
    )  # kiểm sống của máy chủ, không có số liệu
    assert (
        client("t-la").get("/api/toi").status_code == 401
    )  # coin không nhận cookie này
    assert users(env) == []


def test_nguoi_moi_cho_duyet_va_khong_xem_duoc_so_lieu(env, monkeypatch):
    monkeypatch.setattr(web_cw, "fetch", lambda path: {"co": True})
    an = client("t-an")
    toi = an.get("/api/toi").json()
    assert toi["trang_thai"] == "cho_duyet" and toi["vai"] == "nhan_vien"
    assert toi["ten"] == "An Lê" and toi["email"] == "an@example.com"
    r = an.get("/api/chung-quyen")
    assert (
        r.status_code == 403
        and r.json()["detail"] == "Tài khoản đang chờ Quản trị duyệt."
    )
    assert an.get("/api/tai-khoan").status_code == 403
    for _ in range(3):  # gọi lại nhiều lần vẫn chỉ một dòng tài khoản, một dòng nhật ký
        an.get("/api/toi")
    assert [u.coin_user_id for u in users(env)] == ["u-an"]
    assert [v for _, v, _ in audit(env)] == ["tao"]


def test_quan_tri_dau_tien_lay_tu_env(env, monkeypatch):
    toi = (
        client("t-sep").get("/api/toi").json()
    )  # email ở coin viết hoa, danh sách viết thường và có dấu cách
    assert (
        toi["vai"] == "quan_tri"
        and toi["trang_thai"] == "da_duyet"
        and toi["email"] == "sep@example.com"
    )
    assert audit(env) == [(None, "quan_tri_dau_tien", "web_users:1")]
    # tài khoản không có email: khớp bằng tên đăng nhập; thêm vào danh sách SAU khi đã mở web thì được nâng lên
    binh = client("t-binh")
    assert binh.get("/api/toi").json()["trang_thai"] == "cho_duyet"
    monkeypatch.setattr(settings, "web_admin_emails", "sep@example.com,BINH")
    toi = binh.get("/api/toi").json()
    assert (
        toi["vai"] == "quan_tri"
        and toi["trang_thai"] == "da_duyet"
        and toi["email"] is None
    )
    assert audit(env)[-1] == (None, "quan_tri_dau_tien", "web_users:2")


def test_duyet_khoa_doi_vai_co_nhat_ky_va_khong_nhan_doi(env, monkeypatch):
    monkeypatch.setattr(web_cw, "fetch", lambda path: {"co": True})
    sep, an = client("t-sep"), client("t-an")
    sep.get("/api/toi")
    an.get("/api/toi")
    ds = sep.get("/api/tai-khoan").json()
    assert ds["toi"] == 1 and [u["id"] for u in ds["tai_khoan"]] == [
        2,
        1,
    ]  # chờ duyệt đứng trước
    r = sep.post("/api/tai-khoan/2/duyet", json={}, headers=ORIGIN)
    assert r.status_code == 200 and r.json()["trang_thai"] == "da_duyet"
    assert (
        sep.post("/api/tai-khoan/2/duyet", json={}, headers=ORIGIN).status_code == 200
    )  # duyệt lần hai
    assert an.get("/api/chung-quyen").json() == {
        "co": True
    }  # đã duyệt thì xem được số liệu
    assert an.get("/api/tai-khoan").status_code == 403  # nhưng không phải Quản trị
    assert an.post("/api/tai-khoan/1/khoa", json={}, headers=ORIGIN).status_code == 403

    assert (
        sep.post(
            "/api/tai-khoan/2/vai", json={"vai": "quan_tri"}, headers=ORIGIN
        ).json()["vai"]
        == "quan_tri"
    )
    assert an.get("/api/tai-khoan").status_code == 200
    assert (
        sep.post(
            "/api/tai-khoan/2/vai", json={"vai": "giam_doc"}, headers=ORIGIN
        ).status_code
        == 422
    )
    assert (
        sep.post("/api/tai-khoan/2/khoa", json={}, headers=ORIGIN).json()["trang_thai"]
        == "khoa"
    )
    r = an.get("/api/chung-quyen")
    assert r.status_code == 403 and r.json()["detail"] == "Tài khoản đã bị khóa."
    assert (
        an.get("/api/toi").json()["trang_thai"] == "khoa"
    )  # người bị khóa vẫn hỏi được trạng thái của mình
    assert (
        sep.post("/api/tai-khoan/99/duyet", json={}, headers=ORIGIN).status_code == 404
    )

    assert len(users(env)) == 2
    # mỗi việc đúng một dòng, ghi rõ ai làm (1 = sếp); duyệt lần hai không thêm dòng
    assert audit(env) == [
        (None, "quan_tri_dau_tien", "web_users:1"),
        (None, "tao", "web_users:2"),
        (1, "duyet", "web_users:2"),
        (1, "doi_vai", "web_users:2"),
        (1, "khoa", "web_users:2"),
    ]
    with env["db"]() as db:
        chi_tiet = db.query(wu.WebAudit).filter_by(viec="doi_vai").one().chi_tiet
        assert json.loads(chi_tiet) == {"truoc": "nhan_vien", "sau": "quan_tri"}
        assert db.get(wu.WebUser, 2).duyet_boi == 1


def test_phai_con_it_nhat_mot_quan_tri(env):
    sep, an = client("t-sep"), client("t-an")
    sep.get("/api/toi")
    an.get("/api/toi")
    r = sep.post("/api/tai-khoan/1/khoa", json={}, headers=ORIGIN)
    assert r.status_code == 409 and "ít nhất một Quản trị" in r.json()["detail"]
    assert (
        sep.post(
            "/api/tai-khoan/1/vai", json={"vai": "nhan_vien"}, headers=ORIGIN
        ).status_code
        == 409
    )
    # có Quản trị thứ hai đang hoạt động thì hạ vai được
    sep.post("/api/tai-khoan/2/duyet", json={}, headers=ORIGIN)
    sep.post("/api/tai-khoan/2/vai", json={"vai": "quan_tri"}, headers=ORIGIN)
    assert (
        an.post(
            "/api/tai-khoan/2/vai", json={"vai": "nhan_vien"}, headers=ORIGIN
        ).json()["vai"]
        == "nhan_vien"
    )


def test_yeu_cau_ghi_phai_gui_tu_chinh_trang_web(env):
    sep = client("t-sep")
    sep.get("/api/toi")
    client("t-an").get("/api/toi")
    assert (
        sep.post("/api/tai-khoan/2/duyet", json={}).status_code == 403
    )  # không có Origin
    la = {"Origin": "https://trang-la.example"}
    assert sep.post("/api/tai-khoan/2/duyet", json={}, headers=la).status_code == 403
    # đúng nguồn nhưng gửi kiểu form (trang lạ dựng được form, không dựng được JSON)
    assert (
        sep.post("/api/tai-khoan/2/duyet", data={"x": "1"}, headers=ORIGIN).status_code
        == 415
    )
    assert users(env)[1].trang_thai == "cho_duyet"  # cả ba lần đều không ghi gì
    ref = {"Referer": "http://testserver/#hom-nay"}  # trình duyệt cũ chỉ gửi Referer
    assert sep.post("/api/tai-khoan/2/duyet", json={}, headers=ref).status_code == 200


def test_coin_sap_thi_dong_cua(env, monkeypatch):
    monkeypatch.setattr(web_cw, "fetch", lambda path: {"co": True})
    sep = client("t-sep")
    assert sep.get("/api/chung-quyen").status_code == 200
    web_auth.clear_cache()
    env["state"]["down"] = True
    r = sep.get("/api/chung-quyen")
    assert r.status_code == 503 and "ConnectError" in r.json()["detail"]
    env["state"]["down"] = False
    env["state"]["status"] = 500  # coin trả lỗi lạ cũng không cho vào
    assert sep.get("/api/toi").status_code == 503
    monkeypatch.setattr(settings, "web_auth_me_url", "")
    env["state"]["status"] = 200
    assert sep.get("/api/toi").status_code == 503  # thiếu cấu hình: đóng
    monkeypatch.setattr(settings, "web_auth_mode", "tat")
    assert sep.get("/api/toi").status_code == 503  # chế độ lạ: đóng


def test_nho_ket_qua_hoi_coin_tinh_tay(env, monkeypatch):
    """Ca tính tay: cache_seconds = 60. Giây 0 hỏi coin; giây 59 còn nhớ; giây 60 hỏi lại."""
    assert load_defaults()["web"]["auth"]["cache_seconds"] == 60
    dong_ho = {"t": 1000.0}
    monkeypatch.setattr(web_auth.time, "monotonic", lambda: dong_ho["t"])
    sep = client("t-sep")
    for _ in range(5):
        assert sep.get("/api/toi").status_code == 200
    assert len(env["calls"]) == 1
    dong_ho["t"] = 1059.0
    sep.get("/api/toi")
    assert len(env["calls"]) == 1
    dong_ho["t"] = 1060.0
    sep.get("/api/toi")
    assert len(env["calls"]) == 2
    client("t-an").get("/api/toi")  # người khác, cookie khác: không dùng chung kết quả
    assert len(env["calls"]) == 3


def test_chi_gui_cookie_phien_cho_coin(env):
    c = client("t-sep")
    c.cookies.set("refresh_token", "bi-mat-khong-duoc-gui")
    c.cookies.set("khac", "x")
    assert c.get("/api/toi").status_code == 200
    assert env["calls"] == ["access_token=t-sep"]


def test_coin_tra_thieu_ma_nguoi_dung(env, monkeypatch):
    monkeypatch.setitem(TOKENS, "t-hong", {"email": "x@example.com"})
    assert client("t-hong").get("/api/toi").status_code == 503
    assert users(env) == []


def test_che_do_dev_chi_tren_chinh_may(env, monkeypatch):
    monkeypatch.setattr(settings, "web_auth_mode", "dev")
    monkeypatch.setattr(settings, "web_dev_user", "Thu@Example.com")
    monkeypatch.setattr(settings, "web_admin_emails", "thu@example.com")
    tai_may = TestClient(web_main.app, client=("127.0.0.1", 50000))
    toi = tai_may.get("/api/toi").json()
    assert (
        toi["email"] == "thu@example.com"
        and toi["vai"] == "quan_tri"
        and toi["che_do"] == "dev"
    )
    assert users(env)[0].coin_user_id == "dev:thu@example.com"
    assert env["calls"] == []  # chế độ dev không hỏi coin
    # yêu cầu đến từ máy khác (trên VPS là Caddy): chế độ dev tự vô hiệu
    tu_xa = TestClient(web_main.app, client=("172.18.0.5", 50000))
    assert tu_xa.get("/api/toi").status_code == 403
    monkeypatch.setattr(settings, "web_dev_user", "")
    assert tai_may.get("/api/toi").status_code == 503


def test_moi_duong_api_deu_dong_khi_chua_dang_nhap(env):
    """Lát 6: ở btinvest.vn Caddy không chặn hộ nữa, nên TỪNG đường `/api/` của ứng dụng phải tự đòi đăng nhập.

    Duyệt bảng route thật của ứng dụng: thêm route mới mà quên gắn điều kiện tài khoản thì test này trượt.
    Yêu cầu ghi được gửi kèm `Origin` và JSON đúng kiểu để chắc lý do bị chặn là chưa đăng nhập (401).
    """
    cong_khai = {("GET", "/api/suc-khoe")}  # kiểm sống của máy chủ, không có số liệu
    tat_ca = api_operations()
    # hai cách đếm phải ra cùng một bảng: route không hiện trong bản mô tả API cũng không lọt
    assert {
        (m, r.path) for r in flat_routes(web_main.app.routes) for m in r.methods
    } == tat_ca
    da_kiem: set[tuple[str, str]] = set()
    khach = client()
    for method, path in sorted(tat_ca - cong_khai):
        url = re.sub(r"\{\w*id\}", "1", path)
        url = re.sub(r"\{\w+\}", "AAA", url)
        r = khach.request(
            method, url, headers=ORIGIN, json={} if method != "GET" else None
        )
        assert r.status_code == 401, (method, path, r.status_code)
        da_kiem.add((method, path))
    # không qua mặt bằng cách kiểm ít: bảng route thật có cả nhóm số liệu lẫn nhóm ghi
    assert ("GET", "/api/co-phieu/{ma}/dinh-gia") in da_kiem
    assert ("GET", "/api/chung-quyen/{ma}/trang-cu") in da_kiem
    assert ("POST", "/api/danh-muc/lenh") in da_kiem
    assert ("POST", "/api/tai-khoan/{user_id}/duyet") in da_kiem
    assert ("POST", "/api/muc-gia/{level_id}/xoa") in da_kiem
    assert len(da_kiem) == len(tat_ca) - 1 >= 35
    assert users(env) == []  # không ai được tạo dòng tài khoản khi chưa đăng nhập


def test_khung_web_va_bieu_tuong_mo_duoc_khi_chua_dang_nhap(env):
    """Khung web tĩnh (không có số liệu) và biểu tượng trang ai cũng tải được; trang chỉ trỏ tới tệp có thật."""
    c = client()
    trang = c.get("/")
    assert trang.status_code == 200 and "text/html" in trang.headers["content-type"]
    bieu_tuong = re.findall(
        r'<link rel="(?:icon|apple-touch-icon)"[^>]*href="([^"]+)"', trang.text
    )
    assert sorted(bieu_tuong) == ["apple-touch-icon.png", "favicon.ico"]
    for ten in (*bieu_tuong, "app.js", "app.css"):
        tep = c.get(f"/{ten}")
        assert tep.status_code == 200 and len(tep.content) > 500, ten
    # đúng là tệp ảnh, không phải trang lỗi trả kèm mã 200
    assert c.get("/favicon.ico").content[:4] == b"\x00\x00\x01\x00"
    assert c.get("/apple-touch-icon.png").content[:8] == b"\x89PNG\r\n\x1a\n"
    assert users(env) == []


def test_khung_web_luon_hoi_lai_may_chu_sau_deploy(env):
    """Tệp giao diện phải kèm `Cache-Control: no-cache`: không có thì trình duyệt tự giữ app.js cũ một thời gian sau
    mỗi lần deploy (thấy thật khi thử bốn ô trang chủ 26/11/2026), giao diện cũ gọi API mới. Có ETag nên hỏi lại chỉ
    tốn một yêu cầu nhỏ trả 304."""
    c = client()
    for duong in ("/", "/app.js", "/app.css", "/favicon.ico"):
        r = c.get(duong)
        assert (
            r.status_code == 200 and r.headers.get("cache-control") == "no-cache"
        ), duong
        assert r.headers.get("etag"), duong
    tag = c.get("/app.js").headers["etag"]
    assert c.get("/app.js", headers={"If-None-Match": tag}).status_code == 304
    # số liệu không bị gắn kiểu lưu đệm này (đường /api/ tự quyết)
    assert c.get("/api/suc-khoe").headers.get("cache-control") != "no-cache"


def test_tu_tao_thu_muc_cha_cua_tep_du_lieu(tmp_path, monkeypatch):
    """Lát 6: trên VPS tệp nằm ở /data/web_user/, thư mục đó chưa có ở lần chạy đầu."""
    path = tmp_path / "web_user" / "web_user.db"
    monkeypatch.setattr(settings, "web_user_db_url", f"sqlite:///{path}")
    monkeypatch.setattr(wu, "_engine", None)
    monkeypatch.setattr(wu, "_factory", None)
    with wu.session_factory()() as db:
        assert db.get(wu.WebMeta, "schema_version").gia_tri == wu.SCHEMA_VERSION
    assert path.is_file()
    wu._engine.dispose()
    assert wu.sqlite_file("sqlite://") is None
    assert wu.sqlite_file("postgresql://may-khac/web") is None


def test_schema_tao_lai_khong_trung(env):
    wu.init_schema(env["engine"])
    wu.init_schema(env["engine"])
    with env["db"]() as db:
        assert [(m.khoa, m.gia_tri) for m in db.query(wu.WebMeta)] == [
            ("schema_version", wu.SCHEMA_VERSION)
        ]
