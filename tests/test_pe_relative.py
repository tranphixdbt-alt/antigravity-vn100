"""
Test P/E relative (Phase 2): EPS CHUẨN HÓA median lịch sử × P/E mục tiêu ngành.
Guardrail: chống nhiễu lợi nhuận 1 năm; LN âm → không ra số rác.
"""
import pytest
from valuation.engine.models.pe_relative import PERelativeValuationModel


def _pe(ni_history, sector="Dệt may/TS", shares=200e6, price=50000):
    cf = {"net_income_history": ni_history, "shares_outstanding": shares, "current_price": price}
    a = {"target_pe": PERelativeValuationModel._target_pe(sector), "norm_years": 3}
    return PERelativeValuationModel("ZZPE", cf, a)


def test_pe_uses_median_not_latest():
    # LN [100, 120, 500] (500 là năm đột biến) → median 3 năm = 120, không lấy 500.
    m = _pe([100.0, 120.0, 500.0])
    r = m.perform_valuation()
    # eps = median(120)*1e9 / 200e6 = 600 VND; FV = 600 * 8 (dệt may) = 4800
    assert r["normalized_eps"] == pytest.approx(120e9 / 200e6, rel=1e-9)
    assert r["blended_fair_value_per_share"] == pytest.approx(120e9 / 200e6 * 8.0, rel=1e-9)


def test_pe_flags_cyclical_spike():
    m = _pe([100.0, 110.0, 300.0])  # năm gần vọt
    assert "EARNINGS_NORMALIZED_CYCLICAL" in m.perform_valuation()["flags"]


def test_pe_negative_earnings_no_garbage():
    m = _pe([-50.0, -30.0, -40.0])
    r = m.perform_valuation()
    assert r["blended_fair_value_per_share"] == 0.0
    assert "NEGATIVE_NORMALIZED_EARNINGS" in r["flags"]


def test_pe_sector_target():
    assert PERelativeValuationModel._target_pe("Dệt may/TS") == 8.0
    assert PERelativeValuationModel._target_pe("Xây dựng") == 9.0
    assert PERelativeValuationModel._target_pe("Dược") == 13.0
