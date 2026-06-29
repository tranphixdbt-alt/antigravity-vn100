"""Test convention COE VND-base — chống double-count country risk."""
import pytest

from valuation.config import load_defaults
from valuation.engine.coe import MIN_EQUITY_PREMIUM, compute_coe, get_erp


def test_erp_is_mature_not_total():
    """ERP dùng phải là mature ERP, KHÔNG phải erp_total (chống double-count)."""
    conv = load_defaults().get("coe_convention", {})
    assert get_erp() == pytest.approx(conv["erp_mature"])
    assert get_erp() != pytest.approx(conv["erp_total"])


def test_compute_coe_formula():
    rf, beta = 0.04521, 0.77
    erp = get_erp()
    assert compute_coe(rf, beta) == pytest.approx(rf + beta * erp)


def test_no_double_count_vs_old_behavior():
    """COE đúng phải THẤP hơn cách cũ (rf_VN + erp_total) — bằng chứng đã bỏ CRP."""
    rf, beta = 0.04521, 0.77
    conv = load_defaults().get("coe_convention", {})
    old_double_count = rf + beta * conv["erp_total"]
    correct = compute_coe(rf, beta)
    assert correct < old_double_count
    # Chênh lệch đúng bằng beta * crp_vn
    assert (old_double_count - correct) == pytest.approx(beta * conv["crp_vn"])


def test_floor_allows_vnd_base_coe():
    """Floor mới phải cho phép COE VND-base hợp lệ (beta=0.77) đi qua."""
    rf, beta = 0.04521, 0.77
    coe = compute_coe(rf, beta)
    assert coe >= rf + MIN_EQUITY_PREMIUM  # không bị COE_TOO_LOW
