"""
Test calibration generic non-financial builder (build_company_data):
- EBIT margin dùng MEDIAN (mid-cycle), không phải mean → robust với năm bùng nổ.
- Revenue growth FADE từ median lịch sử về tăng trưởng GDP danh nghĩa dài hạn (năm 5).
Chạy trên DB thật với mã DCM (đã ingest, cyclical điển hình).
"""
import statistics
import pytest

from valuation.db.session import SessionLocalRead
from valuation.data_access.repo import build_company_data
from valuation.config import load_defaults


@pytest.fixture
def db():
    s = SessionLocalRead()
    yield s
    s.close()


def test_ebit_margin_is_median_not_mean(db):
    c = build_company_data(db, "DCM", mode="TTM")
    margins = [is_.ebit / is_.revenue for is_ in c.historical_is if is_.revenue > 0]
    expected_median = statistics.median(margins)
    # ebit_margin dùng trong assumptions = median lịch sử (clamp >= 0)
    assert c.assumptions.ebit_margin[0] == pytest.approx(max(expected_median, 0.0), abs=1e-6)
    # Với cyclical (DCM có năm đỉnh 2022), median < mean → chống extrapolate đỉnh
    assert statistics.median(margins) <= statistics.mean(margins) + 1e-9


def test_revenue_growth_fades_to_gdp(db):
    c = build_company_data(db, "DCM", mode="TTM")
    rg = c.assumptions.revenue_growth
    assert len(rg) == 5
    g_lt = load_defaults().get("long_run_nominal_gdp_growth", 0.08)
    # Năm 5 hội tụ về GDP dài hạn (cho phép lệch nhỏ do macro overlay)
    assert abs(rg[4] - g_lt) < 0.03
    # Toàn bộ schedule bị chặn hợp lý (không có đỉnh chu kỳ extrapolate)
    assert all(0.0 <= g <= 0.25 for g in rg)
