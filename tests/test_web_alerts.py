"""Web hợp nhất, lát 5c (docs/PLAN_WEB_HOP_NHAT.md mục 13): cảnh báo trong web.

Phía này chỉ lưu mức giá của từng người và gộp tin; mọi con số do dịch vụ chứng quyền tính (đã có test ở
cw_scanner/test_web_api.py, test_vi_the.py với ca tính tay). Ở đây dịch vụ đó là giả: kiểm rằng mức giá của
ai người đó thấy, quá số mức bị từ chối, ngoài giờ không gọi giá, phần chung được nhớ và dùng chung, dịch
vụ lỗi thì báo ra chứ không im lặng.
"""

from __future__ import annotations

import pytest

from tests.test_web_auth import ORIGIN, audit, client, coin_env
from tests.test_web_portfolio import vao
from valuation.db import web_user as wu
from valuation.services import web_alerts, web_cw

TIN_CW = {
    "id": "2026-11-25|cw|CVRE2609",
    "tieu_de": "CW rẻ bất thường: CVRE2609",
    "noi_dung": "chào bán 980 đ, lệch -18,4% so với giá lẽ ra theo VRE; mua được 12,3 triệu",
    "link": "/cw/CVRE2609",
}
TIN_DM = {
    "id": "2026-11-25|dm-chot_loi|VRE",
    "tieu_de": "Danh mục: VRE",
    "noi_dung": "lãi nếu bán ngay +3,9% (ngưỡng +3%), giá chờ mua 24.000 đ",
    "link": "/danh-muc",
}
NGOAI_GIO = {
    "day_du": False,
    "luc": "2026-11-25T12:00:00",
    "ngoai_gio": True,
    "tin": [],
    "loi": [],
}
TRONG_GIO = {
    "day_du": True,
    "luc": "2026-11-25T10:00:00",
    "ngoai_gio": False,
    "phien": "2026-11-25",
    "loi": [],
    "cw": [{"ma": "CVRE2609", "lech": -0.184}],
    "etf": [],
    "hd": [],
    "giam_manh": [],
    "tin": [TIN_CW],
}
SAU_GIO = {**TRONG_GIO, "luc": "2026-11-25T15:30:00", "ngoai_gio": True, "tin": []}
CFG = {
    "cache_seconds": 45,
    "error_cache_seconds": 10,
    "poll_seconds": 60,
    "max_levels": 50,
}


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Coin giả + DB người dùng tạm của lát 5a."""
    yield from coin_env(tmp_path, monkeypatch)


@pytest.fixture
def dv(monkeypatch):
    """Dịch vụ chứng quyền giả: ghi lại mọi lượt gọi; `state` đổi câu trả lời, lỗi và giờ của đồng hồ nhớ đệm."""
    state: dict = {
        "fetch": [],
        "compute": [],
        "tra": {web_alerts.FEED_PATH: TRONG_GIO, web_alerts.SHARED_PATH: TRONG_GIO},
        "loi_fetch": None,
        "loi_compute": {},
        "gio": 1000.0,
        "cfg": dict(CFG),
    }

    def fetch(path):
        state["fetch"].append(path)
        if state["loi_fetch"]:
            raise web_cw.CwServiceError(*state["loi_fetch"])
        return state["tra"][path]

    def compute(path, body):
        state["compute"].append((path, body))
        if path in state["loi_compute"]:
            raise web_cw.CwServiceError(*state["loi_compute"][path])
        if path == web_alerts.LEVELS_PATH:
            if body.get("chi_kiem"):
                return {"hop_le": True}
            # giá giả 24.000 đ: mức "xuống tới" từ 24.000 trở lên là đang chạm
            cham = lambda m: m["chieu"] == "duoi" and m["muc"] >= 24000
            return {
                "luc": "2026-11-25T10:00:05",
                "co_phien": True,
                "muc": [
                    {
                        **m,
                        "ma_that": m["ma"],
                        "gia": 24000,
                        "cham": cham(m),
                        "cach": 24000 / m["muc"] - 1,
                        "don_vi": "đ",
                    }
                    for m in body["muc"]
                ],
                "tin": [
                    {
                        "id": f"2026-11-25|muc|{m['id']}",
                        "tieu_de": f"Chạm mức giá: {m['ma']}",
                        "noi_dung": f"giá 24.000 ≤ mức {m['muc']:,.0f}".replace(
                            ",", "."
                        ),
                        "link": "/canh-bao",
                    }
                    for m in body["muc"]
                    if cham(m)
                ],
            }
        assert path == "/api/tinh/danh-muc"
        return {"luc": "2026-11-25T10:00:06", "tin": [TIN_DM], "loi_gia": []}

    monkeypatch.setattr(web_cw, "fetch", fetch)
    monkeypatch.setattr(web_cw, "compute", compute)
    monkeypatch.setattr(web_alerts, "_now", lambda: state["gio"])
    monkeypatch.setattr(web_alerts, "_cfg", lambda: state["cfg"])
    web_alerts.clear_cache()
    yield state
    web_alerts.clear_cache()


def muc(ma="VPB", chieu="duoi", gia=24500, **them):
    return {"ma": ma, "chieu": chieu, "muc": gia, **them}


def cac_muc(env):
    with env["db"]() as db:
        return db.query(wu.WebPriceLevel).order_by(wu.WebPriceLevel.id).all()


def ghi_lenh(env, user_id):
    """Một lệnh mua nằm sẵn trong danh mục (ghi thẳng vào DB tạm: phần ghi lệnh đã có test ở lát 5b)."""
    with env["db"]() as db:
        db.add(
            wu.WebOrder(
                user_id=user_id,
                loai="cp",
                ma="VRE",
                chieu="MUA",
                so_luong=1000,
                gia=23000.0,
                ngay="2026-11-20",
                chot_loi=0.03,
                ma_yeu_cau=f"yeu-cau-{user_id:04d}",
                tao_luc=wu.now_utc(),
            )
        )
        db.commit()


def test_dat_muc_gia_luu_dung_va_dat_lai_khong_nhan_doi(env, dv):
    an = vao(env, "t-an")
    toi = an.get("/api/toi").json()
    assert toi["hoi_canh_bao_giay"] == 60
    r = an.post(
        "/api/muc-gia", json=muc(ma=" vpb ", ghi_chu="  mua thêm  "), headers=ORIGIN
    )
    assert (
        r.status_code == 200 and r.json()["da_co"] is False and r.json()["ma"] == "VPB"
    )
    (m,) = cac_muc(env)
    assert (m.user_id, m.ma, m.chieu, m.muc, m.ghi_chu, m.xoa_luc) == (
        toi["id"],
        "VPB",
        "duoi",
        24500.0,
        "mua thêm",
        None,
    )
    # trước khi lưu: nhờ dịch vụ chứng quyền kiểm mã có trên bảng giá và mức không sai đơn vị (chỉ kiểm, 1 mức)
    assert dv["compute"] == [
        (
            web_alerts.LEVELS_PATH,
            {
                "muc": [
                    {
                        "id": 1,
                        "ma": "VPB",
                        "chieu": "duoi",
                        "muc": 24500.0,
                        "ghi_chu": "mua thêm",
                    }
                ],
                "chi_kiem": True,
            },
        )
    ]
    # bấm gửi hai lần: mức đang có được trả lại, không thành hai mức, không hỏi dịch vụ lần nữa
    lai = an.post("/api/muc-gia", json=muc(ghi_chu="khác"), headers=ORIGIN)
    assert (
        lai.status_code == 200
        and lai.json()["da_co"] is True
        and lai.json()["id"] == m.id
    )
    assert len(cac_muc(env)) == 1 and len(dv["compute"]) == 1
    assert (toi["id"], "them_muc_gia", f"web_price_levels:{m.id}") in audit(env)
    # cùng mã nhưng khác chiều hoặc khác mức là mức khác
    assert (
        an.post(
            "/api/muc-gia", json=muc(chieu="tren", gia=26000), headers=ORIGIN
        ).json()["da_co"]
        is False
    )
    ds = an.get("/api/muc-gia").json()
    assert [(x["ma"], x["chieu"], x["cham"], x["gia"]) for x in ds["muc"]] == [
        ("VPB", "duoi", True, 24000),
        ("VPB", "tren", False, 24000),
    ]
    assert (
        ds["toi_da"] == 50
        and ds["loi_gia"] is None
        and ds["muc"][0]["tao_luc"].endswith("Z")
    )
    assert ds["muc"][0]["cach"] == pytest.approx(24000 / 24500 - 1)


def test_muc_gia_cua_ai_nguoi_do_thay_ke_ca_quan_tri(env, dv):
    an, binh, sep = vao(env, "t-an"), vao(env, "t-binh"), vao(env, "t-sep")
    id_muc = an.post("/api/muc-gia", json=muc(), headers=ORIGIN).json()["id"]
    dv["compute"].clear()
    # Bình và sếp (Quản trị) không thấy mức của An; chưa đặt mức nào thì không gọi giá
    for nguoi in (binh, sep):
        assert nguoi.get("/api/muc-gia").json()["muc"] == []
        assert nguoi.get("/api/canh-bao").json()["muc_gia"]["muc"] == []
        r = nguoi.post(f"/api/muc-gia/{id_muc}/xoa", json={}, headers=ORIGIN)
        assert r.status_code == 404 and "của bạn" in r.json()["detail"]
    assert dv["compute"] == [] and cac_muc(env)[0].xoa_luc is None
    # An xóa mức của mình: xóa mềm, dòng vẫn còn để truy vết, có nhật ký
    r = an.post(f"/api/muc-gia/{id_muc}/xoa", json={}, headers=ORIGIN)
    assert r.status_code == 200 and r.json() == {"id": id_muc, "da_xoa": True}
    (m,) = cac_muc(env)
    assert m.xoa_luc is not None and an.get("/api/muc-gia").json()["muc"] == []
    assert (m.user_id, "xoa_muc_gia", f"web_price_levels:{id_muc}") in audit(env)
    assert (
        an.post(f"/api/muc-gia/{id_muc}/xoa", json={}, headers=ORIGIN).status_code
        == 404
    )  # xóa lần hai
    # đã xóa thì đặt lại đúng mức đó là mức mới
    assert an.post("/api/muc-gia", json=muc(), headers=ORIGIN).json()["da_co"] is False


def test_qua_so_muc_bi_tu_choi(env, dv):
    dv["cfg"]["max_levels"] = 2
    an, binh = vao(env, "t-an"), vao(env, "t-binh")
    for gia in (24500, 24000):
        assert (
            an.post("/api/muc-gia", json=muc(gia=gia), headers=ORIGIN).status_code
            == 200
        )
    r = an.post("/api/muc-gia", json=muc(gia=23500), headers=ORIGIN)
    assert (
        r.status_code == 422
        and "Tối đa 2 mức" in r.json()["detail"]
        and len(cac_muc(env)) == 2
    )
    # giới hạn tính theo từng người, và mức đã xóa không tính
    assert (
        binh.post("/api/muc-gia", json=muc(gia=23500), headers=ORIGIN).status_code
        == 200
    )
    an.post(f"/api/muc-gia/{cac_muc(env)[0].id}/xoa", json={}, headers=ORIGIN)
    assert (
        an.post("/api/muc-gia", json=muc(gia=23500), headers=ORIGIN).status_code == 200
    )


def test_ma_sai_mau_va_muc_sai_bi_tu_choi_khong_luu(env, dv):
    an = vao(env, "t-an")
    for sai in (
        muc(ma="VP!"),
        muc(ma="AB"),
        muc(ma="DROP TABLE"),
        muc(chieu="xuong"),
        muc(gia=0),
        muc(gia=-5),
    ):
        r = an.post("/api/muc-gia", json=sai, headers=ORIGIN)
        assert r.status_code == 422, sai
    assert (
        dv["compute"] == [] and cac_muc(env) == []
    )  # sai kiểu: không hỏi dịch vụ chứng quyền, không lưu
    # dịch vụ chứng quyền từ chối (mã không có trên bảng giá, nghi sai đơn vị): câu báo đi nguyên văn, không lưu
    cau = "mức 24 đ gấp hoặc chỉ bằng dưới 1/10 giá hiện tại 24.000 đ: kiểm tra đơn vị (nhập bằng đồng)"
    dv["loi_compute"][web_alerts.LEVELS_PATH] = (422, cau)
    r = an.post("/api/muc-gia", json=muc(gia=24.5), headers=ORIGIN)
    # câu báo của dịch vụ giữ nguyên, chỉ viết hoa chữ đầu và bỏ số thứ tự "mức thứ 1"
    assert (
        r.status_code == 422
        and r.json()["detail"] == "M" + cau[1:]
        and cac_muc(env) == []
    )
    dv["loi_compute"][web_alerts.LEVELS_PATH] = (
        422,
        "mức thứ 1: mã phải là chứng quyền, cổ phiếu, ETF",
    )
    r = an.post("/api/muc-gia", json=muc(ma="ABCXYZ9"), headers=ORIGIN)
    assert (
        r.status_code == 422
        and r.json()["detail"] == "Mã phải là chứng quyền, cổ phiếu, ETF"
    )
    dv["loi_compute"][web_alerts.LEVELS_PATH] = (
        503,
        "Đang quét dữ liệu, thử lại sau ít phút.",
    )
    assert (
        an.post("/api/muc-gia", json=muc(), headers=ORIGIN).status_code == 503
        and cac_muc(env) == []
    )


def test_ghi_muc_gia_can_dang_nhap_da_duyet_va_dung_nguon(env, dv):
    assert client().get("/api/canh-bao/tin").status_code == 401
    assert client().post("/api/muc-gia", json=muc(), headers=ORIGIN).status_code == 401
    binh = vao(env, "t-binh", duyet=False)  # chờ duyệt
    for goi in (
        lambda: binh.get("/api/canh-bao"),
        lambda: binh.get("/api/canh-bao/tin"),
        lambda: binh.get("/api/muc-gia"),
        lambda: binh.post("/api/muc-gia", json=muc(), headers=ORIGIN),
    ):
        assert goi().status_code == 403
    an = vao(env, "t-an")
    assert an.post("/api/muc-gia", json=muc()).status_code == 403  # không có Origin
    la = {"Origin": "https://trang-la.example"}
    assert an.post("/api/muc-gia", json=muc(), headers=la).status_code == 403
    assert an.post("/api/muc-gia/1/xoa", json={}, headers=la).status_code == 403
    assert cac_muc(env) == [] and dv["fetch"] == [] and dv["compute"] == []


def test_tin_ngoai_gio_khong_goi_gia(env, dv):
    an = vao(env, "t-an")
    an.post("/api/muc-gia", json=muc(), headers=ORIGIN)
    ghi_lenh(env, an.get("/api/toi").json()["id"])
    dv["compute"].clear()
    dv["tra"][web_alerts.FEED_PATH] = NGOAI_GIO
    d = an.get("/api/canh-bao/tin").json()
    assert d == {"hoi_moi_giay": 60, "ngoai_gio": True, "tin": [], "loi": []}
    # ngoài giờ khớp lệnh: không hỏi giá cho mức giá và danh mục, dù người này có cả hai
    assert dv["compute"] == [] and dv["fetch"] == [web_alerts.FEED_PATH]


def test_tin_trong_gio_gop_ba_nguon_va_rieng_tung_nguoi(env, dv):
    an, binh = vao(env, "t-an"), vao(env, "t-binh")
    id_muc = an.post("/api/muc-gia", json=muc(), headers=ORIGIN).json()["id"]
    an.post(
        "/api/muc-gia", json=muc(chieu="tren", gia=26000), headers=ORIGIN
    )  # chưa chạm: không có tin
    ghi_lenh(env, an.get("/api/toi").json()["id"])
    dv["compute"].clear()
    d = an.get("/api/canh-bao/tin").json()
    assert not d["ngoai_gio"] and d["loi"] == []
    assert [t["id"] for t in d["tin"]] == [
        TIN_CW["id"],
        f"2026-11-25|muc|{id_muc}",
        TIN_DM["id"],
    ]
    # gửi sang dịch vụ chứng quyền đúng mức giá và lệnh của An
    (duong_muc, than_muc), (duong_dm, than_dm) = dv["compute"]
    assert duong_muc == web_alerts.LEVELS_PATH and [
        m["muc"] for m in than_muc["muc"]
    ] == [24500.0, 26000.0]
    assert duong_dm == "/api/tinh/danh-muc" and [l["ma"] for l in than_dm["lenh"]] == [
        "VRE"
    ]
    assert than_dm["lenh"][0]["chot_loi"] == 0.03 and "chi_kiem" not in than_dm
    # Bình không có mức giá, không có lệnh: chỉ nhận tin chung, không gọi giá riêng
    dv["compute"].clear()
    assert (
        binh.get("/api/canh-bao/tin").json()["tin"] == [TIN_CW] and dv["compute"] == []
    )


def test_phan_chung_duoc_nho_va_dung_chung(env, dv):
    an, binh = vao(env, "t-an"), vao(env, "t-binh")
    an.get("/api/canh-bao/tin")
    binh.get("/api/canh-bao/tin")
    # trong giờ, lượt hỏi tin đã mang đủ các bảng: trang Cảnh báo dùng lại, không gọi dịch vụ lần nữa
    trang = an.get("/api/canh-bao").json()
    assert dv["fetch"] == [web_alerts.FEED_PATH]
    assert trang["chung"]["cw"][0]["ma"] == "CVRE2609" and trang["loi_chung"] is None
    assert trang["hoi_moi_giay"] == 60
    dv["gio"] += 44  # còn trong 45 giây
    binh.get("/api/canh-bao/tin")
    assert len(dv["fetch"]) == 1
    dv["gio"] += 2  # quá 45 giây: hỏi lại
    binh.get("/api/canh-bao/tin")
    assert dv["fetch"] == [web_alerts.FEED_PATH] * 2
    # trang Cảnh báo mở sau giờ: kết quả "ngoài giờ" của lượt hỏi tin không có bảng nên phải tải bản đủ; bản đủ
    # ngoài giờ không được dùng làm tin của phiên
    web_alerts.clear_cache()
    dv["fetch"].clear()
    dv["tra"] = {web_alerts.FEED_PATH: NGOAI_GIO, web_alerts.SHARED_PATH: SAU_GIO}
    assert an.get("/api/canh-bao/tin").json()["ngoai_gio"] is True
    trang = an.get("/api/canh-bao").json()
    assert trang["chung"]["ngoai_gio"] is True and trang["chung"]["cw"]
    assert dv["fetch"] == [web_alerts.FEED_PATH, web_alerts.SHARED_PATH]
    dv["gio"] += 46
    dv["tra"][web_alerts.FEED_PATH] = TRONG_GIO  # phiên chiều mở lại
    assert an.get("/api/canh-bao/tin").json()["tin"] == [TIN_CW]
    assert dv["fetch"][-1] == web_alerts.FEED_PATH


def test_dich_vu_loi_thi_bao_ra_khong_im_lang(env, dv):
    an = vao(env, "t-an")
    an.post("/api/muc-gia", json=muc(), headers=ORIGIN)
    dv["loi_fetch"] = (503, "Đang quét dữ liệu, thử lại sau ít phút.")
    d = an.get("/api/canh-bao/tin").json()
    assert (
        d["tin"] == []
        and d["loi"] == ["Đang quét dữ liệu, thử lại sau ít phút."]
        and not d["ngoai_gio"]
    )
    # lỗi được nhớ 10 giây: người khác hỏi ngay sau không phải chờ dịch vụ thêm lượt nữa
    an.get("/api/canh-bao/tin")
    assert dv["fetch"] == [web_alerts.FEED_PATH]
    dv["gio"] += 11
    dv["loi_fetch"] = None
    assert an.get("/api/canh-bao/tin").json()["tin"][0] == TIN_CW
    # trang Cảnh báo: phần chung lỗi thì báo lỗi, mức giá của mình vẫn hiện
    web_alerts.clear_cache()
    dv["loi_fetch"] = (503, "Chưa kết nối được dịch vụ chứng quyền")
    trang = an.get("/api/canh-bao").json()
    assert trang["chung"] is None and "Chưa kết nối" in trang["loi_chung"]
    assert trang["muc_gia"]["muc"][0]["gia"] == 24000
    # không lấy được giá cho mức đã đặt: danh sách vẫn có (để còn xóa), kèm câu báo; không có giá thay thế
    dv["loi_compute"][web_alerts.LEVELS_PATH] = (
        502,
        "Không tải được giá cho các mức đã đặt (URLError)",
    )
    ds = an.get("/api/muc-gia").json()
    assert (
        ds["loi_gia"].startswith("Không tải được giá") and ds["muc"][0]["ma"] == "VPB"
    )
    assert ds["muc"][0]["gia"] is None and ds["muc"][0]["cham"] is None


def test_loi_tung_phan_khong_lam_mat_cac_phan_khac(env, dv):
    an = vao(env, "t-an")
    an.post("/api/muc-gia", json=muc(), headers=ORIGIN)
    ghi_lenh(env, an.get("/api/toi").json()["id"])
    dv["loi_compute"][web_alerts.LEVELS_PATH] = (502, "Không tải được giá (URLError)")
    d = an.get("/api/canh-bao/tin").json()
    assert [t["id"] for t in d["tin"]] == [TIN_CW["id"], TIN_DM["id"]]
    assert d["loi"] == ["mức giá của bạn: Không tải được giá (URLError)"]
    dv["loi_compute"] = {
        "/api/tinh/danh-muc": (502, "Không tính được danh mục (URLError)")
    }
    d = an.get("/api/canh-bao/tin").json()
    assert [t["id"].split("|")[1] for t in d["tin"]] == ["cw", "muc"]
    assert d["loi"] == ["danh mục của bạn: Không tính được danh mục (URLError)"]


def test_schema_them_bang_muc_gia_khong_dung_bang_cu(env):
    with env["db"]() as db:
        assert db.get(wu.WebMeta, "schema_version").gia_tri == "3"
    wu.init_schema(env["engine"])  # chạy lại không tạo trùng, không lỗi
    assert cac_muc(env) == []
