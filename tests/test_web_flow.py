"""Web hợp nhất, lát 1 (docs/PLAN_WEB_HOP_NHAT.md mục 12): API chỉ đọc phải trả đúng số của bộ máy dòng tiền."""

from __future__ import annotations

import datetime as dt
import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from test_money_flow_tab import FIX, _make_db

from valuation.analysis import money_flow as mf
from valuation.analysis.investment_ranking import load_ranking_config
from valuation.api import web_main
from valuation.config import load_defaults
from valuation.db.session import get_read_db
from valuation.services import web_flow, web_live
from valuation.views import money_flow as vmf
from valuation.views.market_overview import sector_map

# từ lát 5a route số liệu đòi tài khoản đã duyệt; các test này kiểm số liệu nên đi qua bằng fixture
pytestmark = pytest.mark.usefixtures("web_approved")


def test_clean_tinh_tay():
    """Ca tính tay: NaN, vô cực, NaT thành None; số numpy thành số Python; ngày thành chuỗi ISO."""
    raw = {
        "a": float("nan"),
        "b": np.float64(1.5),
        "c": np.int64(3),
        "d": pd.Timestamp("2026-11-23"),
        "e": [float("inf"), None, pd.NaT],
        1: np.bool_(True),
        "f": dt.date(2026, 11, 23),
    }
    assert web_flow.clean(raw) == {
        "a": None,
        "b": 1.5,
        "c": 3,
        "d": "2026-11-23",
        "e": [None, None, None],
        "1": True,
        "f": "2026-11-23",
    }


def test_parse_layers():
    assert web_flow.parse_layers(None) == [x for x in vmf.LAYERS if x != "MACD"]
    assert web_flow.parse_layers("3,1") == [vmf.LAYERS[1], vmf.LAYERS[3]]
    assert web_flow.parse_layers("") == []
    for bad in ("9", "x", "1;2", "-1"):
        with pytest.raises(ValueError):
            web_flow.parse_layers(bad)


def test_normalize_ticker_chan_dau_vao_la():
    assert web_flow.normalize_ticker(" vre ") == "VRE"
    for bad in ("AB", "ABCDE", "VR;", "V E", "../x"):
        assert web_flow.normalize_ticker(bad) is None


@pytest.fixture
def web(tmp_path, monkeypatch):
    """TestClient trên DB tạm của bộ test tab dòng tiền; snapshot xếp hạng giả như fixture run_tab."""
    make_session = sessionmaker(
        bind=create_engine(_make_db(tmp_path / "web.db", flow_daily=True))
    )

    def read_db():
        db = make_session()
        try:
            yield db
        finally:
            db.close()

    snap = {
        "run_id": "WEB",
        "completed_at": "2026-10-20T10:00:00+07:00",
        "config": load_ranking_config(),
        "rows": [{"ticker": "FPT", "fair_value": 12_000.0, "flags": []}],
    }
    monkeypatch.setattr(web_flow, "latest_snapshot", lambda: snap)
    # D128: biểu đồ, khối ngoại trong phiên đọc bảng giá Vietcap; test không gọi mạng (ca có phiên đang chạy tự đặt)
    monkeypatch.setattr(web_live, "session_data", lambda now=None: ({}, []))
    web_flow.clear_cache()
    web_main.app.dependency_overrides[get_read_db] = read_db
    yield TestClient(web_main.app), make_session
    web_main.app.dependency_overrides.clear()
    web_flow.clear_cache()


def _engine_result(make_session) -> dict:
    """Gọi thẳng bộ máy, không qua lớp web, để đối chiếu."""
    db = make_session()
    try:
        cfg = load_defaults()["money_flow"]
        p = vmf.load_flow_panel(db, cfg)
        return mf.compute_money_flow(
            p["prices"], p["exact"], p["actions"], sector_map(), cfg, vmf._now_vn()
        )
    finally:
        db.close()


def test_tong_quan_khop_bo_may(web):
    client, make_session = web
    res = _engine_result(make_session)
    for mode in web_flow.MODES:
        r = client.get("/api/dong-tien", params={"che_do": mode})
        assert r.status_code == 200
        body = r.json()
        json.dumps(body, allow_nan=False)  # không còn NaN trong JSON
        assert body["ket_luan"] == res["modes"][mode]["conclusion"]
        assert body["dem_nhan"] == res["label_counts"]
        assert {x["ma"] for x in body["ma"]} == set(FIX) == set(res["tickers"])
        for row in body["ma"]:
            tk = res["tickers"][row["ma"]]
            assert row["nhan"] == tk["label"]["code"]
            assert row["phieu"] == [
                tk["votes"][k]["vote"] for k in ("foreign", "pv", "prop")
            ]
            assert row["boi_canh"] == tk["context"]
        assert [s["sector"] for s in body["nganh"]] == [
            s["sector"] for s in res["modes"][mode]["sectors"]
        ]
        for got, want in zip(body["nganh"], res["modes"][mode]["sectors"], strict=True):
            assert got["f"] == pytest.approx(want["f"])
            assert got["n"] == want["n"]


def test_the_mot_ma_khop_bo_may(web):
    client, make_session = web
    res = _engine_result(make_session)
    ma = next(iter(FIX))
    tk = res["tickers"][ma]
    body = client.get(f"/api/co-phieu/{ma.lower()}/dong-tien").json()
    assert body["ma"] == ma
    assert body["nhan"] == tk["label"]
    assert body["phieu"]["foreign"]["chip"] == tk["votes"]["foreign"]["chip"]
    assert body["phieu"]["pv"]["value"] == pytest.approx(tk["votes"]["pv"]["value"])
    assert body["huy_hieu"] == tk["badges"]
    assert len(body["tia"]) <= int(
        load_defaults()["money_flow_chart"]["spark_sessions"]
    )
    assert body["bang_phieu"], "bảng phiếu phải có dòng"
    json.dumps(body, allow_nan=False)


def test_ma_la_va_tham_so_sai(web):
    client, _ = web
    assert client.get("/api/co-phieu/ZZZ/dong-tien").status_code == 404
    assert client.get("/api/co-phieu/ZZZ/bieu-do").status_code == 404
    assert client.get("/api/co-phieu/AB%3B/dong-tien").status_code == 422
    assert client.get("/api/dong-tien", params={"che_do": "khac"}).status_code == 422
    ma = next(iter(FIX))
    assert (
        client.get(f"/api/co-phieu/{ma}/bieu-do", params={"khung": "9N"}).status_code
        == 422
    )
    assert (
        client.get(f"/api/co-phieu/{ma}/bieu-do", params={"tang": "99"}).status_code
        == 422
    )


def test_bieu_do_la_bieu_do_cua_tab_cu(web):
    client, _ = web
    ma = next(iter(FIX))
    body = client.get(
        f"/api/co-phieu/{ma}/bieu-do",
        params={"khung": "1T", "tang": "1,3", "ho_so": "true"},
    ).json()
    assert body["cao"] > 0
    assert '"panes"' in body["html"]
    assert "phiên" in body["chu_thich"]
    assert set(body["ho_so"]) == {"poc", "vah", "val", "total"}


def test_tim_ma_va_chi_co_route_doc(web):
    client, _ = web
    rows = client.get("/api/ma").json()
    assert {r["ma"] for r in rows} == set(FIX)
    assert all(r["co_dong_tien"] for r in rows)
    # nhóm route số liệu chỉ có GET; route ghi nằm riêng ở web_user_routes và chỉ ghi tệp dữ liệu người dùng
    methods = {m for route in web_main.data.routes for m in route.methods}
    assert methods == {"GET"}, f"nhóm số liệu chỉ được có route đọc, thấy {methods}"


# ---------- D128: phiên đang chạy trên bảng giá ghép vào biểu đồ và dòng tiền (chỉ hiển thị) ----------
BN = 1e9


def _bar(day, gia=10_600.0, rong=2 * BN, nen=True):
    """Một mã trên bảng giá như web_live.session_bars trả (đơn vị đồng)."""
    return {
        "ngay": day,
        "mo": 9_700.0 if nen else None,
        "cao": 10_700.0 if nen else None,
        "thap": 9_650.0 if nen else None,
        "gia": gia,
        "tham_chieu": 9_600.0,
        "kl": 1_000.0,
        "gt": 1.0e7,
        "nn_mua": None if rong is None else max(rong, 0) + BN,
        "nn_ban": None if rong is None else max(-rong, 0) + BN,
        "nn_rong": rong,
        "nen": nen,
    }


def _ngay_sau(make_session):
    db = make_session()
    try:
        h = web_flow._history(db, "FPT")
    finally:
        db.close()
    return h, (h.index.max() + pd.Timedelta(days=1)).date()


def test_with_session_them_nen_hom_nay_tinh_tay(web):
    _, make_session = web
    h, day = _ngay_sau(make_session)
    out, live = web_flow.with_session(h, _bar(day))
    assert live and len(out) == len(h) + 1 and out.index[-1] == pd.Timestamp(day)
    r = out.iloc[-1]
    assert (r.open, r.high, r.low, r.close, r.vol_match, r.f) == (
        9_700.0, 10_700.0, 9_650.0, 10_600.0, 1_000.0, 2 * BN
    )  # fmt: skip
    # bảng giá không có tự doanh, thỏa thuận, CMF: để trống, không thành 0
    assert np.isnan(r.p) and np.isnan(r.dom) and np.isnan(r.cmf) and np.isnan(r.f_block)
    assert not r.block and not r.big_block and r.source == "live"
    # tính tay: 19 phiên đóng cửa 9.600 + phiên hôm nay 10.600 → MA20 = (19 × 9.600 + 10.600) / 20 = 9.650
    assert r.MA20 == pytest.approx(9_650.0)
    pd.testing.assert_frame_equal(out.iloc[:-1], h)  # phiên cũ giữ nguyên
    # DB đã có phiên đó (sau job 15:45), bảng giá thiếu mở/cao/thấp, hay không có mã: giữ nguyên lịch sử
    assert web_flow.with_session(h, _bar(h.index.max().date()))[1] is False
    assert web_flow.with_session(h, _bar(day, nen=False))[1] is False
    assert web_flow.with_session(h, None)[1] is False


def test_bieu_do_co_nen_trong_phien_va_chi_du_lieu(web, monkeypatch):
    client, make_session = web
    _, day = _ngay_sau(make_session)
    monkeypatch.setattr(
        web_live, "session_data", lambda now=None: ({"FPT": _bar(day)}, [])
    )
    q = {"khung": "1T", "tang": "1"}  # tầng 1 = Khối ngoại
    body = client.get("/api/co-phieu/FPT/bieu-do", params=q).json()
    assert body["trong_phien"] is True and '"panes"' in body["html"]
    assert body["chu_thich"].startswith(
        f"Nến {day:%d/%m} lấy từ bảng giá Vietcap, chưa chốt"
    )
    d = client.get("/api/co-phieu/FPT/bieu-do", params=q | {"chi_du_lieu": "true"})
    d = d.json()
    assert "html" not in d and d["trong_phien"] is True
    gia, kn = d["du_lieu"]["panes"][0], d["du_lieu"]["panes"][1]
    nen = next(s for s in gia["series"] if s["type"] == "Candlestick")["data"][-1]
    assert nen["time"] == day.isoformat() and nen["close"] == 10_600.0
    rong = next(s for s in kn["series"] if s["options"]["title"] == "Ròng/ngày")
    assert rong["data"][-1] == {
        "time": day.isoformat(),
        "value": 2.0,
        "color": rong["data"][-1]["color"],
    }  # 2 tỷ
    json.dumps(d, allow_nan=False)


def test_khoi_ngoai_trong_phien_theo_ma_va_nganh(web, monkeypatch):
    client, make_session = web
    _, day = _ngay_sau(make_session)
    res = _engine_result(make_session)
    bars = {
        "FPT": _bar(day, rong=2 * BN),
        "VCB": _bar(day, rong=-0.5 * BN),
        "CTG": _bar(day, rong=None),  # thiếu số khối ngoại: không tính là 0
        "ZZZ": _bar(day, rong=9 * BN),  # không thuộc rổ dòng tiền
    }
    monkeypatch.setattr(web_live, "session_data", lambda now=None: (bars, []))
    monkeypatch.setattr(
        web_live,
        "snapshot",
        lambda now=None: {"chi_so": [], "noi_bat": None, "loi": []},
    )
    body = client.get("/api/truc-tiep", params={"dong_tien": "true"}).json()
    dt_ = body["dong_tien"]
    assert dt_["co"] is True and dt_["ngay"] == day.isoformat()
    assert dt_["ma"] == {"FPT": 2 * BN, "VCB": -0.5 * BN} and dt_["so_ma"] == 2
    assert dt_["rong"] == pytest.approx(1.5 * BN)  # tính tay: 2 − 0,5
    want: dict[str, float] = {}
    for ma, v in dt_["ma"].items():
        s = res["tickers"][ma]["sector"]
        want[s] = want.get(s, 0.0) + v
    assert dt_["nganh"] == pytest.approx(want)
    assert isinstance(body["phien_db"], str) and body["phien_db"]
    # không xin thì không gửi số từng mã (lượt hỏi 10 giây của trang Hôm nay nhẹ)
    assert "dong_tien" not in client.get("/api/truc-tiep").json()
    # DB đã có phiên đó: không còn gì để ghép
    last = dt.date.fromisoformat(res["meta"]["price_date"])
    bars2 = {"FPT": _bar(last)}
    monkeypatch.setattr(web_live, "session_data", lambda now=None: (bars2, []))
    body = client.get("/api/truc-tiep", params={"dong_tien": "true"}).json()
    assert body["dong_tien"] == {"co": False, "loi": []}


def test_dau_phien_ban_doi_khi_db_ghi_va_bo_nho_tinh_lai(web):
    """Job 15:45/17:45 vừa ghi thì web tính lại ngay, không chờ hết cache_seconds (600 giây)."""
    from valuation.db.models import PricesDaily

    _, make_session = web
    db = make_session()
    try:
        v1, r1 = web_flow.data_version(db), web_flow._result(db)
        assert web_flow._result(db) is r1  # cùng dấu: dùng lại kết quả đã tính
        row = (
            db.query(PricesDaily)
            .filter(PricesDaily.ticker == "FPT")
            .order_by(PricesDaily.trade_date.desc())
            .first()
        )
        row.proprietary_net_val = 1 * BN  # tự doanh phiên cuối vừa về (job 17:45)
        db.commit()
        assert web_flow.data_version(db) == v1  # dấu nhớ data_version_seconds giây
        web_flow._version.clear()
        assert web_flow.data_version(db) != v1
        assert web_flow._result(db) is not r1
    finally:
        db.close()
