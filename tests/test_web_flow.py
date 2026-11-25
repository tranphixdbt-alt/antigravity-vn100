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
from valuation.services import web_flow
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
