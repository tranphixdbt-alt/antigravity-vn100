"""
Test ROE fade cho bank (VCBValuationModel):
- terminal_roe chặn trên ROE dùng cho terminal value (RI + justified P/B).
- Không bao giờ NÂNG ROE (bank ROE thấp giữ nguyên).
- Justified P/B dùng terminal_roe, không dùng ROE năm 5 còn cao.
- Fade làm giảm FV so với khi terminal_roe cao.
"""
import pytest
from valuation.engine.models.bank_vcb import VCBValuationModel


def _cf(net_income, equity=100e12):
    return {
        'total_equity': equity,
        'total_assets': equity * 10,
        'customer_loans': equity * 8,
        'customer_deposits': equity * 8,
        'net_income': net_income,
        'net_interest_income': equity * 0.30,
        'shares_outstanding': 1e9,
        'current_price': 50000,
    }


def _assumptions(terminal_roe=None):
    a = {
        'credit_growth': 0.15, 'nim': 0.032, 'cir': 0.32, 'credit_cost': 0.008,
        'dividend_payout_ratio': 0.15, 'risk_free_rate': 0.045, 'beta': 1.0,
        'erp': 0.082, 'terminal_growth_rate': 0.02,
    }
    if terminal_roe is not None:
        a['terminal_roe'] = terminal_roe
    return a


def test_high_roe_is_capped():
    # ROE TTM = 25% → terminal_roe phải bị chặn về 0.15 (default)
    m = VCBValuationModel(_cf(25e12), _assumptions())
    assert m.roe_ttm == pytest.approx(0.25, abs=1e-6)
    assert m.terminal_roe == pytest.approx(0.15, abs=1e-6)


def test_low_roe_not_raised():
    # ROE TTM = 10% < cap 0.15 → terminal_roe giữ 10%, KHÔNG nâng lên
    m = VCBValuationModel(_cf(10e12), _assumptions())
    assert m.terminal_roe == pytest.approx(0.10, abs=1e-6)


def test_pb_uses_terminal_roe_not_yr5():
    # target_pb = (terminal_roe - g)/(coe - g), KHÔNG dùng roe_yr5
    m = VCBValuationModel(_cf(25e12), _assumptions())
    pb = m.calculate_pb_valuation()
    expected = (m.terminal_roe - m.g) / (m.coe - m.g)
    assert pb['target_pb'] == pytest.approx(expected, rel=1e-6)
    # roe_yr5 được báo cáo riêng (minh bạch) và là số dương hợp lý
    assert pb['roe_yr5'] > 0
    # long_term_roe dùng cho P/B chính là terminal_roe (đã fade), KHÔNG phải roe_yr5
    assert pb['long_term_roe'] == pytest.approx(m.terminal_roe, abs=1e-9)


def test_fade_reduces_fair_value():
    # terminal_roe thấp (fade mạnh) → FV thấp hơn terminal_roe cao
    hi = VCBValuationModel(_cf(25e12), _assumptions(terminal_roe=0.20))
    lo = VCBValuationModel(_cf(25e12), _assumptions(terminal_roe=0.12))
    fv_hi = hi.blend_valuation()['blended_fair_value_per_share']
    fv_lo = lo.blend_valuation()['blended_fair_value_per_share']
    assert fv_lo < fv_hi
