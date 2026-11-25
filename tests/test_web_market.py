"""Web hợp nhất, lát 3 (docs/PLAN_WEB_HOP_NHAT.md mục 12): thị trường, vĩ mô, xếp hạng, lịch quyền.

Đối chiếu JSON của API với chính các hàm mà app cũ dùng, trên DB thật của máy, có chặn mạng.
"""

from __future__ import annotations

import datetime as dt
import json
import socket
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from valuation.analysis.investment_ranking import load_ranking_config
from valuation.api import web_main
from valuation.config import get_macro_series_registry, load_defaults
from valuation.data_access.corporate_actions import (
    load_upcoming_vn100_corporate_actions,
)
from valuation.db.models import PricesDaily
from valuation.db.session import SessionLocalRead
from valuation.services import web_flow
from valuation.services.ranking_store import latest_snapshot
from valuation.views import macro_panel as mp
from valuation.views import market_overview as mo
from valuation.views import vn100_ranking as vr

# từ lát 5a route số liệu đòi tài khoản đã duyệt; các test này kiểm số liệu nên đi qua bằng fixture
pytestmark = pytest.mark.usefixtures("web_approved")


def test_clean_decimal_tinh_tay():
    """Ca tính tay: cột NUMERIC (Decimal) phải ra số, không ra chuỗi."""
    assert web_flow.clean({"tien": Decimal("2500.0000000000")}) == {"tien": 2500.0}
    assert web_flow.clean([Decimal("0.25"), dt.date(2026, 11, 26)]) == [
        0.25,
        "2026-11-26",
    ]


@pytest.fixture
def db():
    session = SessionLocalRead()
    try:
        if session.query(PricesDaily).first() is None:
            pytest.skip("DB của máy chưa có giá")
        yield session
    finally:
        session.close()


@pytest.fixture
def web(monkeypatch, db):
    def blocked(*a, **k):
        raise OSError("mạng bị chặn trong test")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    web_flow.clear_cache()
    yield TestClient(web_main.app)
    web_flow.clear_cache()


def _freqs() -> dict[str, str]:
    return {
        k: v.get("frequency", "DAILY") for k, v in get_macro_series_registry().items()
    }


def test_thi_truong_khop_ham_goc(web, db):
    body = web.get("/api/thi-truong").json()
    json.dumps(body, allow_nan=False)
    defaults = load_defaults()
    cfg, mcfg = defaults["market_overview"], defaults.get("macro_dashboard") or {}
    vni, closes, flows, universe = mo.load_market_data(db, cfg)
    ups, src = mo.model_upsides(closes)
    pillars = [
        mo.macro_pillar(mp.build_snapshot(db, mcfg, _freqs()), mcfg, cfg),
        mo.trend_pillar(vni, closes, cfg),
        mo.foreign_pillar(flows, universe, cfg),
        mo.valuation_pillar(ups, src, cfg),
    ]
    label = mo.overall(pillars, cfg)[0]
    assert body["nhan"] == label
    assert body["tieu_de"] == mo.headline(label, pillars)
    assert [(p["ten"], p["diem"], p["tom_tat"]) for p in body["tru_cot"]] == [
        (p.name, p.score, p.summary) for p in pillars
    ]
    view = mo.index_view(vni, cfg)
    if view:
        assert body["chi_so"]["diem"] == pytest.approx(view.last)
        assert body["chi_so"]["sap_toi"] == mo.outlook(view, label, pillars, cfg)
    tk, _ = mo.leaders(closes, flows, mo.sector_map(), cfg)
    want = [] if tk.empty else tk[tk.support]["Mã"].head(int(cfg["top_n"])).tolist()
    assert body["ma_co_luc"] == want


def test_vi_mo_khop_ham_goc(web, db):
    body = web.get("/api/vi-mo").json()
    cfg = load_defaults().get("macro_dashboard") or {}
    snap = mp.build_snapshot(db, cfg, _freqs())
    assert [r["ma"] for r in body["chi_so"]] == [code for code, _, _ in mp.PANEL]
    for row, (code, _, kind) in zip(body["chi_so"], mp.PANEL, strict=True):
        obs = snap.get(code)
        if obs is None:
            assert row["gia_tri"] is None
        elif code != "FED_FUNDS_UPPER":
            assert (row["gia_tri"], row["thay_doi"]) == mp._fmt_value(obs, kind)
        else:
            assert row["gia_tri"].endswith(mp._fmt_value(obs, kind)[0])
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=7))).date()
    assert body["nhan_dinh"] == mp.quick_takes(snap, cfg, today)
    assert isinstance(body["ban_tin"], str)


def test_xep_hang_va_lich_quyen_khop_ham_goc(web, db):
    body = web.get("/api/xep-hang").json()
    json.dumps(body, allow_nan=False)
    snapshot = latest_snapshot()
    if not snapshot:
        assert body == {"co": False}
    else:
        cfg = snapshot.get("config", load_ranking_config())
        table = vr.ranking_table(
            snapshot,
            vr.market_data(db),
            cfg,
            snap_closes=vr.snapshot_closes(db, snapshot),
        )
        assert body["so_ma"] == len(table)
        assert [r["Mã"] for r in body["bang"]] == table["Mã"].tolist()
        assert body["so_dinh_gia"] == int(table["Hạng"].notna().sum())
        picks = vr.accumulation_picks(table, int(cfg.get("max_per_sector", 2)))
        assert [r["Mã"] for r in body["tich_san"]] == (
            [] if picks.empty else picks["Mã"].tolist()
        )
    lich = web.get("/api/lich-quyen").json()
    days = int(load_defaults()["corporate_actions"]["market_upcoming_days"])
    want = load_upcoming_vn100_corporate_actions(db, future_days=days)
    assert lich["so_ngay"] == days
    assert [(r["ma"], r["ngay"]) for r in lich["su_kien"]] == [
        (r.action.ticker, r.event_date.isoformat()) for r in want
    ]
    assert all(
        r["tien_mat"] is None or isinstance(r["tien_mat"], float)
        for r in lich["su_kien"]
    )


def test_chi_co_route_doc(web):
    # nhóm route số liệu chỉ có GET; route ghi nằm riêng ở web_user_routes và chỉ ghi tệp dữ liệu người dùng
    methods = {m for route in web_main.data.routes for m in route.methods}
    assert methods == {"GET"}
