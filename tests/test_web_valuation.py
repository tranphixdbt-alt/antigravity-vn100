"""Web hợp nhất, lát 2 (docs/PLAN_WEB_HOP_NHAT.md mục 12): API định giá phải trả đúng số của bộ máy.

Đối chiếu trên DB thật của máy (như các test golden): gọi thẳng `build_company_data` → `valuate` và các hàm
`report_data`, rồi so với JSON của API. Chặn mạng trong suốt test để chắc API không gọi ra ngoài.
"""

from __future__ import annotations

import json
import socket

import pytest
from fastapi.testclient import TestClient

from valuation.api import web_main
from valuation.data_access.repo import build_company_data
from valuation.db.models import Ticker
from valuation.db.session import SessionLocalRead
from valuation.engine.valuate import valuate
from valuation.report import report_data
from valuation.services import web_flow, web_valuation

# từ lát 5a route số liệu đòi tài khoản đã duyệt; các test này kiểm số liệu nên đi qua bằng fixture
pytestmark = pytest.mark.usefixtures("web_approved")

MA = "VRE"  # mã phi tài chính có đủ BCTC, báo cáo CTCK và sự kiện cổ tức trong DB


@pytest.fixture
def web(monkeypatch):
    db = SessionLocalRead()
    try:
        co = db.query(Ticker).filter(Ticker.ticker == MA).first()
    finally:
        db.close()
    if co is None:
        pytest.skip(f"DB của máy không có {MA}")

    def blocked(*a, **k):
        raise OSError("mạng bị chặn trong test")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    web_flow.clear_cache()
    yield TestClient(web_main.app)
    web_flow.clear_cache()


@pytest.fixture
def engine():
    """Gọi thẳng bộ máy, không qua lớp web."""
    db = SessionLocalRead()
    try:
        company = build_company_data(db, MA, mode="TTM", fetch_live=False)
        yield company, valuate(company), db
    finally:
        db.close()


def test_dinh_gia_khop_bo_may(web, engine):
    company, kq, _ = engine
    r = web.get(f"/api/co-phieu/{MA.lower()}/dinh-gia")
    assert r.status_code == 200
    body = r.json()
    json.dumps(body, allow_nan=False)
    assert body["ma"] == MA
    assert body["gia"] == pytest.approx(company.current_price)
    assert body["fv"] == pytest.approx(kq["blended_fair_value_per_share"])
    assert body["upside"] == pytest.approx(kq["upside"])
    assert body["khuyen_nghi"] == kq["recommendation"]
    assert body["chua_xep_hang"] == kq["not_rated"]
    assert body["duoc_cong_bo"] == kq["publication_allowed"]
    assert [c["code"] for c in body["co"]] == [
        c["code"] for c in web_valuation.describe_flags(list(kq["flags"]))
    ]
    assert len(body["du_phong"]) == len(kq["projections"])
    assert body["du_phong"][0]["fcff"] == pytest.approx(kq["projections"][0]["fcff"])


def test_do_nhay_o_giua_bang_kich_ban_co_so(web):
    """Ca kiểm tay: ô giữa bảng độ nhạy (WACC gốc, g gốc) phải bằng giá trị kịch bản Base của mô hình riêng."""
    body = web.get(f"/api/co-phieu/{MA}/dinh-gia").json()
    dn, kb = body["do_nhay"], body["kich_ban"]
    assert dn["ap_dung"] and kb["applicable"]
    giua = len(dn["x"]) // 2
    assert dn["x"][giua] == pytest.approx(dn["goc_x"])
    assert dn["y"][giua] == pytest.approx(dn["goc_y"])
    base = next(x["target"] for x in kb["rows"] if x["scenario"] == "Base")
    assert dn["bang"][giua][giua] == pytest.approx(base)


def test_tai_chinh_va_ctck_khop_report_data(web, engine):
    company, kq, db = engine
    tc = web.get(f"/api/co-phieu/{MA}/tai-chinh").json()
    want = report_data.build_historical_analysis(company)
    assert tc["lich_su"]["headers"] == want["headers"]
    assert tc["lich_su"]["rows"][0] == want["rows"][0]
    assert (
        tc["phu_luc"]["income_statement"][0]
        == report_data.build_appendix_financials(company)["income_statement"][0]
    )
    ctck = web.get(f"/api/co-phieu/{MA}/ctck").json()
    cs = report_data.build_consensus_comparison(
        MA,
        float(kq["blended_fair_value_per_share"]),
        db,
        current_price=company.current_price,
    )
    assert ctck["so_sanh"]["consensus_median"] == pytest.approx(cs["consensus_median"])
    assert [b["broker"] for b in ctck["so_sanh"]["broker_rows"]] == [
        b["broker"] for b in cs["broker_rows"]
    ]
    json.dumps([tc, ctck], allow_nan=False)


def test_co_tuc_va_ai_chi_doc(web):
    ct = web.get(f"/api/co-phieu/{MA}/co-tuc")
    assert ct.status_code == 200
    assert isinstance(ct.json()["su_kien"], list)
    ai = web.get(f"/api/co-phieu/{MA}/ai").json()
    assert ai["co"] in (True, False)
    assert (ai["van_ban"] is None) == (not ai["co"])


def test_ma_la_va_chi_co_route_doc(web):
    for duong in ("dinh-gia", "tai-chinh", "ctck", "co-tuc", "ai"):
        assert web.get(f"/api/co-phieu/ZZZZ/{duong}").status_code == 404
        assert web.get(f"/api/co-phieu/A%3B1/{duong}").status_code == 422
    # nhóm route số liệu chỉ có GET; route ghi nằm riêng ở web_user_routes và chỉ ghi tệp dữ liệu người dùng
    methods = {m for route in web_main.data.routes for m in route.methods}
    assert methods == {"GET"}
