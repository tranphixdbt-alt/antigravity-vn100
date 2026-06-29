"""
Test batch engine (Phase 3): value_ticker dispatch router-driven đúng phương pháp,
+ build_vn100_dataframe (cột phương pháp, cờ proxy, độ tin cậy). Chạy DB thật.
"""
import pytest
from valuation.db.session import SessionLocalRead
from valuation.engine.batch import value_ticker, value_all
from valuation.output.gsheets_exporter import build_vn100_dataframe


@pytest.fixture
def db():
    s = SessionLocalRead()
    yield s
    s.close()


def test_bank_dispatch(db):
    r = value_ticker(db, "VCB")
    assert r["method"] == "RI_PB"
    assert r.get("fair_value", 0) > 0
    assert r["upside"] is not None


def test_nonfin_dispatch(db):
    r = value_ticker(db, "DCM")
    assert r["method"] == "DCF"
    assert r.get("fair_value", 0) > 0


def test_proxy_flag_propagates(db):
    # RNAV/SOTP phải mang cờ VALUATION_PROXY trong kết quả batch.
    r = value_ticker(db, "NLG")  # RNAV
    assert r["method"] == "RNAV"
    assert "VALUATION_PROXY" in r.get("flags", [])


def test_unknown_ticker_error(db):
    r = value_ticker(db, "ZZZ")
    assert r["error"] == "NOT_IN_VN100"


def test_dataframe_columns_and_proxy_label(db):
    results = value_all(db, ["VCB", "NLG", "DCM"])
    df = build_vn100_dataframe(results)
    for col in ["Mã", "Ngành", "Phương pháp", "FV", "Upside %", "Độ tin cậy", "Cờ"]:
        assert col in df.columns
    # NLG (RNAV) phải gắn nhãn Proxy
    nlg = df[df["Mã"] == "NLG"].iloc[0]
    assert nlg["Độ tin cậy"] == "Proxy"
