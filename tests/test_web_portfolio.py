"""Web hợp nhất, lát 5b (docs/PLAN_WEB_HOP_NHAT.md mục 13): danh mục 4 loại của từng người.

Phía này chỉ lưu lệnh và kiểm đầu vào; vị thế và lãi lỗ do dịch vụ chứng quyền tính (đã có test ở
cw_scanner/test_vi_the.py với hai ví dụ tính tay người dùng duyệt). Ở đây dịch vụ đó là giả: kiểm rằng lệnh
gửi sang đúng và đủ, kết quả đi về nguyên vẹn, mỗi người chỉ đụng được lệnh của mình, Quản trị chỉ xem.
"""

from __future__ import annotations

import datetime as dt

import pytest

from tests.test_web_auth import ORIGIN, audit, client, coin_env
from valuation.db import web_user as wu
from valuation.services import web_cw, web_flow, web_portfolio, web_valuation

HOM_NAY = dt.date(2026, 11, 25)
GD_CUOI = "2026-12-17"
# Kết quả dịch vụ chứng quyền cho ví dụ đã duyệt: mua 1.000 VRE giá 23.000, giá chờ mua 24.000
#   giá vốn 23.000 × 1,0015 = 23.034,5; lãi (24.000 × 0,9975 − 23.034,5) × 1.000 = 905.500 đ
VI_THE_VRE = {
    "ma": "VRE",
    "so_luong": 1000,
    "gia_von": 23034.5,
    "gia_ban": 24000,
    "co_nguoi_mua": True,
    "co_gia": True,
    "lai": 905500.0,
    "lai_pct": 0.039310599318,
}


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Coin giả + DB người dùng tạm của lát 5a."""
    yield from coin_env(tmp_path, monkeypatch)


@pytest.fixture
def cw(monkeypatch):
    """Dịch vụ chứng quyền giả: ghi lại thân các lần gọi tính; `state["loi"]` đặt lỗi cho lần gọi kế tiếp."""
    state: dict = {
        "goi": [],
        "loi": None,
        "kq": {"cp": [dict(VI_THE_VRE)], "cw": [], "etf": [], "hd": []},
    }

    def compute(path, body):
        assert path == "/api/tinh/danh-muc"
        state["goi"].append(body)
        if state["loi"]:
            raise web_cw.CwServiceError(*state["loi"])
        return (
            {"hop_le": True}
            if body.get("chi_kiem")
            else {**state["kq"], "luc": "2026-11-25T10:00:00"}
        )

    def fetch(path):
        return {
            "/api/chung-quyen": {"co": True, "cw": [{"ma": "CVRE2609"}]},
            "/api/etf": {"co": True, "quy": {"dong": [{"Mã": "E1VFVN30"}]}},
            "/api/phai-sinh": {
                "nhom": [
                    {
                        "chi_so": "VN30",
                        "hop_dong": [
                            {"ma": "VN30F1M", "gd_cuoi": GD_CUOI},
                            {"ma": "VN30F2M", "thieu_dao_han": True},
                        ],
                    }
                ]
            },
        }[path]

    monkeypatch.setattr(web_cw, "compute", compute)
    monkeypatch.setattr(web_cw, "fetch", fetch)
    monkeypatch.setattr(web_valuation, "known", lambda db, ma: ma in ("VRE", "HPG"))
    monkeypatch.setattr(web_portfolio, "today_vn", lambda: HOM_NAY)
    monkeypatch.setattr(
        web_flow,
        "model_upsides",
        lambda db: {
            "rows": {"VRE": {"upside": 0.358, "note": ""}},
            "source": "đợt 20/11",
        },
    )
    return state


def lenh(
    yc,
    loai="cp",
    ma="VRE",
    chieu="MUA",
    so_luong=1000,
    gia=23000,
    ngay="2026-11-20",
    **them,
):
    return {
        "loai": loai,
        "ma": ma,
        "chieu": chieu,
        "so_luong": so_luong,
        "gia": gia,
        "ngay": ngay,
        "ma_yeu_cau": f"yeu-cau-{yc:04d}",
        **them,
    }


def vao(env, token, duyet=True):
    """Client đã đăng nhập; tài khoản không phải sếp thì nhờ sếp duyệt trước."""
    c = client(token)
    toi = c.get("/api/toi").json()
    if duyet and toi["trang_thai"] != "da_duyet":
        sep = client("t-sep")
        sep.get("/api/toi")
        sep.post(f"/api/tai-khoan/{toi['id']}/duyet", json={}, headers=ORIGIN)
    return c


def don_hang(env):
    with env["db"]() as db:
        return db.query(wu.WebOrder).order_by(wu.WebOrder.id).all()


def test_them_lenh_luu_dung_va_gui_lai_khong_nhan_doi(env, cw):
    an = vao(env, "t-an")
    r = an.post(
        "/api/danh-muc/lenh",
        json=lenh(1, ghi_chu="  thử  ", chot_loi=0.3),
        headers=ORIGIN,
    )
    assert (
        r.status_code == 200 and r.json()["da_co"] is False and r.json()["ma"] == "VRE"
    )
    (o,) = don_hang(env)
    assert (o.loai, o.ma, o.chieu, o.so_luong, o.gia, o.ngay) == (
        "cp",
        "VRE",
        "MUA",
        1000,
        23000.0,
        "2026-11-20",
    )
    assert (
        o.chot_loi == 0.3
        and o.cat_lo is None
        and o.ghi_chu == "thử"
        and o.xoa_luc is None
    )
    # trước khi lưu đã nhờ dịch vụ dựng thử vị thế (chỉ kiểm, không gọi giá) với đúng lệnh sắp thêm
    (goi,) = cw["goi"]
    assert goi["chi_kiem"] is True and [
        (x["loai_ts"], x["ma"], x["loai"]) for x in goi["lenh"]
    ] == [("cp", "VRE", "MUA")]
    # bấm gửi hai lần (cùng mã yêu cầu): vẫn một lệnh, không hỏi dịch vụ lần nữa
    r2 = an.post("/api/danh-muc/lenh", json=lenh(1), headers=ORIGIN)
    assert (
        r2.status_code == 200 and r2.json()["da_co"] is True and r2.json()["id"] == o.id
    )
    assert len(don_hang(env)) == 1 and len(cw["goi"]) == 1
    assert audit(env)[-1] == (o.user_id, "them_lenh", f"web_orders:{o.id}")


def test_lenh_sai_khong_luu(env, cw):
    an = vao(env, "t-an")
    sai = [
        lenh(1, loai="vang"),
        lenh(2, ma="vr3!"),
        lenh(3, chieu="GIU"),
        lenh(4, so_luong=0),
        lenh(5, gia=0),
        lenh(6, ngay="2026-11-26"),  # sau "hôm nay" 25/11
        lenh(7, ngay="25/11/2026"),
        lenh(
            8, loai="cw", ma="CVRE2609", so_luong=150, gia=1140
        ),  # chứng quyền: lô chẵn 100
        lenh(9, loai="cw", ma="CVRE2609", so_luong=100, gia=1145),  # bước giá 10 đồng
        lenh(10, chot_loi=50),  # 0,5 = 50%; 50 là nhập nhầm đơn vị
        {**lenh(11), "ma_yeu_cau": "x"},
        lenh(12, ma="XXX"),  # đúng dạng nhưng không có trong dữ liệu
        lenh(
            13, loai="cw", ma="CHPG2601", so_luong=100, gia=500
        ),  # không có trong lần quét
        lenh(14, loai="etf", ma="FUEXXX"),
        lenh(
            15, loai="hd", ma="VN30F2M", so_luong=1, gia=1790
        ),  # chưa có ngày giao dịch cuối
    ]
    for body in sai:
        r = an.post("/api/danh-muc/lenh", json=body, headers=ORIGIN)
        assert r.status_code == 422, body
    assert (
        an.post(
            "/api/danh-muc/lenh", json={**lenh(16), "so_luong": 1.5}, headers=ORIGIN
        ).status_code
        == 422
    )
    assert (
        don_hang(env) == [] and cw["goi"] == []
    )  # không lưu gì, không nhờ dịch vụ tính gì


def test_ban_qua_so_dang_nam_bi_tu_choi(env, cw):
    an = vao(env, "t-an")
    an.post("/api/danh-muc/lenh", json=lenh(1, so_luong=100), headers=ORIGIN)
    cw["loi"] = (422, "lệnh 2 bán 200 VRE nhưng lúc đó chỉ nắm 100")
    r = an.post(
        "/api/danh-muc/lenh",
        json=lenh(2, chieu="BAN", so_luong=200, gia=24000),
        headers=ORIGIN,
    )
    assert (
        r.status_code == 422
        and r.json()["detail"] == "lệnh 2 bán 200 VRE nhưng lúc đó chỉ nắm 100"
    )
    # dịch vụ đã nhận cả lệnh cũ lẫn lệnh định thêm, số lệnh không trùng
    assert [(x["id"], x["loai"], x["so_luong"]) for x in cw["goi"][-1]["lenh"]] == [
        (1, "MUA", 100),
        (2, "BAN", 200),
    ]
    assert len(don_hang(env)) == 1


def test_hop_dong_luu_theo_ngay_giao_dich_cuoi(env, cw):
    an = vao(env, "t-an")
    r = an.post(
        "/api/danh-muc/lenh",
        json=lenh(1, loai="hd", ma="VN30F1M", chieu="BAN", so_luong=2, gia=1790.5),
        headers=ORIGIN,
    )
    assert (
        r.status_code == 200 and r.json()["gd_cuoi"] == GD_CUOI
    )  # lấy từ dịch vụ, không do người dùng gõ
    assert don_hang(env)[0].hop_dong_gd_cuoi == GD_CUOI
    assert cw["goi"][-1]["lenh"][0]["gd_cuoi"] == GD_CUOI
    an.post(
        "/api/danh-muc/lenh",
        json=lenh(2, loai="cw", ma="CVRE2609", so_luong=1000, gia=1140),
        headers=ORIGIN,
    )
    assert (
        "gd_cuoi" not in cw["goi"][-1]["lenh"][-1]
    )  # chỉ hợp đồng tương lai mới gửi ngày giao dịch cuối


def test_danh_muc_ket_qua_di_ve_nguyen_ven(env, cw):
    an = vao(env, "t-an")
    trong = an.get("/api/danh-muc").json()
    assert (
        trong["trong"] is True and trong["so_lenh"] == 0 and cw["goi"] == []
    )  # chưa có lệnh: không gọi dịch vụ
    an.post("/api/danh-muc/lenh", json=lenh(1), headers=ORIGIN)
    d = an.get("/api/danh-muc").json()
    assert d["trong"] is False and d["cua_toi"] is True and d["so_lenh"] == 1
    # ca tính tay đã duyệt: (24.000 × 0,9975 − 23.034,5) × 1.000 = 905.500 đ; phía này không làm tròn, không tính lại
    (vre,) = d["cp"]
    assert (
        vre["lai"] == 905500.0 and vre["gia_von"] == 23034.5 and vre["gia_ban"] == 24000
    )
    assert round((24000 * 0.9975 - 23000 * 1.0015) * 1000, 6) == vre["lai"]
    # thước của cổ phiếu: upside của đợt định giá, gắn thêm chứ không đổi số nào của dịch vụ
    assert vre["upside"] == 0.358 and d["upside_nguon"] == "đợt 20/11"
    assert "chi_kiem" not in cw["goi"][-1] and len(cw["goi"][-1]["lenh"]) == 1


def test_moi_nguoi_chi_dung_duoc_lenh_cua_minh_quan_tri_chi_xem(env, cw):
    an, binh, sep = vao(env, "t-an"), vao(env, "t-binh"), vao(env, "t-sep")
    id_an = an.get("/api/toi").json()["id"]
    lenh_an = an.post("/api/danh-muc/lenh", json=lenh(1), headers=ORIGIN).json()["id"]
    # người khác không thấy, không xem hộ, không xóa được
    assert binh.get("/api/danh-muc/lenh").json()["lenh"] == []
    assert binh.get("/api/danh-muc").json()["trong"] is True
    assert binh.get(f"/api/danh-muc/lenh?nguoi={id_an}").status_code == 403
    assert binh.get(f"/api/danh-muc?nguoi={id_an}").status_code == 403
    assert (
        binh.post(
            f"/api/danh-muc/lenh/{lenh_an}/xoa", json={}, headers=ORIGIN
        ).status_code
        == 404
    )
    assert binh.get("/api/danh-muc/nguoi").status_code == 403
    # Quản trị xem được danh mục của mọi người...
    xem = sep.get(f"/api/danh-muc/lenh?nguoi={id_an}").json()
    assert xem["cua_toi"] is False and [x["id"] for x in xem["lenh"]] == [lenh_an]
    d = sep.get(f"/api/danh-muc?nguoi={id_an}").json()
    assert (
        d["cua_toi"] is False and d["chu"]["id"] == id_an and d["cp"][0]["ma"] == "VRE"
    )
    nguoi = {
        n["id"]: n["so_lenh"] for n in sep.get("/api/danh-muc/nguoi").json()["nguoi"]
    }
    assert nguoi[id_an] == 1 and sum(nguoi.values()) == 1
    assert sep.get("/api/danh-muc?nguoi=999").status_code == 404
    # ...nhưng không xóa hộ, và lệnh Quản trị tự ghi vào danh mục của chính Quản trị
    assert (
        sep.post(
            f"/api/danh-muc/lenh/{lenh_an}/xoa", json={}, headers=ORIGIN
        ).status_code
        == 404
    )
    sep.post(
        "/api/danh-muc/lenh", json=lenh(1), headers=ORIGIN
    )  # cùng mã yêu cầu với An: vẫn là lệnh riêng
    assert sorted(o.user_id for o in don_hang(env)) == sorted(
        {id_an, sep.get("/api/toi").json()["id"]}
    )
    assert all(o.xoa_luc is None for o in don_hang(env))


def test_xoa_la_xoa_mem_va_co_nhat_ky(env, cw):
    an = vao(env, "t-an")
    mua = an.post("/api/danh-muc/lenh", json=lenh(1), headers=ORIGIN).json()["id"]
    ban = an.post(
        "/api/danh-muc/lenh", json=lenh(2, chieu="BAN", gia=24000), headers=ORIGIN
    ).json()["id"]
    # xóa lệnh mua thì lệnh bán còn lại thành bán khống: dịch vụ báo không khớp, không xóa
    cw["loi"] = (422, "lệnh 2 bán 1.000 VRE nhưng lúc đó chỉ nắm 0")
    r = an.post(f"/api/danh-muc/lenh/{mua}/xoa", json={}, headers=ORIGIN)
    assert (
        r.status_code == 409
        and "Chưa xóa được" in r.json()["detail"]
        and "chỉ nắm 0" in r.json()["detail"]
    )
    assert [x["id"] for x in cw["goi"][-1]["lenh"]] == [ban] and all(
        o.xoa_luc is None for o in don_hang(env)
    )
    cw["loi"] = None
    assert an.post(f"/api/danh-muc/lenh/{ban}/xoa", json={}, headers=ORIGIN).json() == {
        "id": ban,
        "da_xoa": True,
    }
    con, da_xoa = don_hang(env)
    assert (
        con.xoa_luc is None and da_xoa.id == ban and da_xoa.xoa_luc is not None
    )  # dòng vẫn còn trong DB
    assert [x["id"] for x in an.get("/api/danh-muc/lenh").json()["lenh"]] == [mua]
    assert (
        an.post(f"/api/danh-muc/lenh/{ban}/xoa", json={}, headers=ORIGIN).status_code
        == 404
    )  # xóa lần hai
    assert [v for _, v, _ in audit(env)][-3:] == ["them_lenh", "them_lenh", "xoa_lenh"]
    # lệnh đã xóa không còn được gửi đi tính
    an.get("/api/danh-muc")
    assert [x["id"] for x in cw["goi"][-1]["lenh"]] == [mua]


def test_dich_vu_chung_quyen_sap_thi_bao_ro_khong_luu(env, cw):
    an = vao(env, "t-an")
    an.post("/api/danh-muc/lenh", json=lenh(1), headers=ORIGIN)
    cw["loi"] = (
        503,
        "Chưa kết nối được dịch vụ chứng quyền, ETF và phái sinh (ConnectError).",
    )
    r = an.get("/api/danh-muc")
    assert (
        r.status_code == 503
        and "Chưa kết nối được dịch vụ chứng quyền" in r.json()["detail"]
    )
    assert (
        an.post("/api/danh-muc/lenh", json=lenh(2), headers=ORIGIN).status_code == 503
    )
    assert len(don_hang(env)) == 1  # không kiểm được vị thế thì không lưu
    assert len(an.get("/api/danh-muc/lenh").json()["lenh"]) == 1  # sổ lệnh vẫn xem được


def test_chua_duyet_va_yeu_cau_la_khong_ghi_duoc(env, cw):
    cho = vao(env, "t-an", duyet=False)
    assert cho.get("/api/danh-muc").status_code == 403
    assert (
        cho.post("/api/danh-muc/lenh", json=lenh(1), headers=ORIGIN).status_code == 403
    )
    an = vao(env, "t-an")
    assert (
        an.post("/api/danh-muc/lenh", json=lenh(1)).status_code == 403
    )  # không có Origin
    assert (
        an.post(
            "/api/danh-muc/lenh",
            json=lenh(1),
            headers={"Origin": "https://trang-la.example"},
        ).status_code
        == 403
    )
    assert client().get("/api/danh-muc").status_code == 401
    assert don_hang(env) == []
