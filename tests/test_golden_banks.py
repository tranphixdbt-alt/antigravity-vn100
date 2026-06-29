"""
Golden Test nhóm ngân hàng BID / CTG / TCB.

Mục tiêu: khóa tính toàn vẹn của tầng trích xuất dữ liệu bank (regression guard cho
fix line-item tiếng Anh — xem memory line-items-english-keys). KHÔNG hardcode fair
value vì FV phụ thuộc calibration (ROE cao + COE VND-base → P/B cao, là quyết định
đầu tư, không phải số cố định).

Khóa lại:
  1. shares ≈ vốn điều lệ thật / mệnh giá 10,000 (bắt lỗi dùng nhầm owners_equity → phóng đại ~2.8x).
  2. net_income / total_equity / customer_loans > 0  → keyword tiếng Anh match đúng.
  3. ROE TTM nằm trong vùng hợp lý cho bank VN (5%–30%).
  4. blend_valuation chạy không lỗi và cho FV dương.
"""
import pytest
from valuation.db.session import SessionLocalRead
from valuation.engine.models.bank_vcb import VCBValuationModel
from valuation.engine.ttm_helper import (
    build_vcb_current_financials,
    build_vcb_assumptions_from_history,
    get_shares_outstanding,
)

# Shares xác minh từ vốn điều lệ thật (sau các đợt tăng vốn 2025).
# Tolerance ±20% đủ chặt để bắt lỗi logic (owners_equity proxy gây sai ~180%),
# nhưng nới cho đợt tăng vốn nhỏ; cập nhật mốc khi ngân hàng chia cổ tức cổ phiếu.
GOLDEN_SHARES = {
    "BID": 7_280_065_200,
    "CTG": 7_766_944_600,
    "TCB": 7_086_240_400,
}


@pytest.fixture
def db():
    session = SessionLocalRead()
    yield session
    session.close()


@pytest.mark.parametrize("ticker", ["BID", "CTG", "TCB"])
class TestBankExtractionIntegrity:
    def test_shares_match_charter_capital(self, db, ticker):
        shares = get_shares_outstanding(db, ticker)
        golden = GOLDEN_SHARES[ticker]
        rel = abs(shares - golden) / golden
        assert rel < 0.20, (
            f"{ticker}: shares={shares:,.0f} lệch {rel:.1%} so với mốc vốn điều lệ "
            f"{golden:,.0f}. Lệch lớn thường do dùng nhầm owners_equity làm proxy."
        )

    def test_core_financials_populated(self, db, ticker):
        cf = build_vcb_current_financials(db, ticker)
        assert cf["net_income"] > 0, f"{ticker}: net_income=0 → keyword tiếng Anh trượt"
        assert cf["total_equity"] > 0, f"{ticker}: total_equity=0 → keyword trượt"
        assert cf["customer_loans"] > 0, f"{ticker}: customer_loans=0 → keyword trượt"

    def test_roe_in_sane_range(self, db, ticker):
        cf = build_vcb_current_financials(db, ticker)
        roe = cf["net_income"] / cf["total_equity"]
        assert 0.05 <= roe <= 0.30, (
            f"{ticker}: ROE={roe:.1%} ngoài vùng hợp lý cho bank VN (5%–30%)"
        )

    def test_valuation_runs_positive(self, db, ticker):
        cf = build_vcb_current_financials(db, ticker)
        cf["current_price"] = 50000.0  # giá giả định để model chạy
        a = build_vcb_assumptions_from_history(db, ticker)
        model = VCBValuationModel(cf, a)
        blend = model.blend_valuation()
        fv = blend["blended_fair_value_per_share"]
        assert fv > 0, f"{ticker}: blend FV={fv} không dương"
