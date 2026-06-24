"""
Golden Test VCB — So sánh kết quả định giá VCB với mốc Excel gốc.

Mốc Excel gốc:
  - RI FV per share ≈ 57,600 VND (với r=12%, g=5%, shares=5.589B, NIM=3.2%, non_ii=0)
  
Yêu cầu mới:
  1. COE chốt từ nguyên tắc: rf = TPCP VN 10Y (động), erp = 8.2% (Damodaran VN), beta ước lượng động.
  2. Shares xác minh độc lập từ HOSE = 8,355,675,094.
  3. Lấy non-interest income thực tế từ DB (TOI - NII).
  4. Chạy hai test case:
     - Excel Benchmark Test: dùng assumptions Excel để verify thuật toán (tolerance ±15%).
     - Principled Valuation Test: dùng assumptions động, in bảng so sánh chi tiết.
  5. Thêm sanity checks cho COE_TOO_LOW và implied P/B warnings.
"""
import pytest
import logging
from valuation.db.session import SessionLocalRead
from valuation.engine.models.bank_vcb import VCBValuationModel
from valuation.engine.ttm_helper import (
    build_vcb_current_financials,
    build_vcb_assumptions_from_history,
    get_shares_outstanding,
)

@pytest.fixture
def db():
    session = SessionLocalRead()
    yield session
    session.close()

class TestVCBSharesOutstanding:
    def test_shares_vcb_hose_verified(self, db):
        """Số lượng cổ phiếu lưu hành VCB phải đúng 8,355,675,094 cp (đối chiếu HOSE)."""
        shares = get_shares_outstanding(db, "VCB")
        # Số lượng shares thực tế sau đợt tăng vốn điều lệ lên 83.56T VND (cho phép lệch cực nhỏ do làm tròn Vốn điều lệ trong BCTC)
        assert abs(shares - 8_355_675_094) <= 10, (
            f"Shares={shares:,.0f} lệch quá 10cp so với số liệu xác minh từ HOSE (8,355,675,094)"
        )

class TestVCBAlgorithmIntegrity:
    def test_ri_fv_excel_benchmark(self, db):
        """
        Kiểm chứng thuật toán RI: Khi dùng đúng bộ giả định của Excel, 
        RI FV phải khớp mốc Excel ~57,600 VND với sai số < 15%.
        
        GHI CHÚ: non_interest_income = 0.0 là ĐIỀU KIỆN TÁI LẬP Excel gốc 
        (Excel bỏ qua nguồn thu nhập này khi tính dòng tiền phóng chiếu), 
        KHÔNG PHẢI cách mô hình chạy thật trong production (production lấy động từ DB).
        """
        # Giả lập dữ liệu BCTC cuối 2024 (trước tăng vốn) giống Excel
        cf_excel = {
            'total_equity': 196.21e12,
            'total_assets': 2085.87e12,
            'customer_loans': 1449.20e12,
            'customer_deposits': 1514.66e12,
            'net_income': 33.85e12,
            'net_interest_income': 55.41e12,
            'non_interest_income': 0.0, # Excel bỏ qua non-interest income
            'shares_outstanding': 5_589_091_300, # số cổ phiếu cũ
            'current_price': 92000
        }
        
        assumptions_excel = {
            'credit_growth': 0.15,
            'nim': 0.032,
            'cir': 0.32,
            'credit_cost': 0.008,
            'dividend_payout_ratio': 0.15,
            'risk_free_rate': 0.043,
            'beta': 1.0,
            'erp': 0.077, # coe = 4.3% + 1.0*7.7% = 12.0%
            'terminal_growth_rate': 0.05
        }
        
        model = VCBValuationModel(cf_excel, assumptions_excel)
        ri = model.calculate_residual_income()
        fvps_ri = ri['fair_value_per_share']
        
        excel_ri_fv = 57_600
        error = abs(fvps_ri - excel_ri_fv) / excel_ri_fv
        print(f"\n[Algorithm Verification] RI FV = {fvps_ri:,.0f} VND vs Excel = {excel_ri_fv:,.0f} VND. Sai số = {error:.2%}")
        
        assert error < 0.15, f"Thuật toán RI lệch quá 15% so với Excel (Sai số: {error:.2%})"

class TestVCBPrincipledValuation:
    def test_principled_valuation_and_comparison(self, db):
        """
        Chạy định giá theo nguyên tắc động (rf từ TPCP VN 10Y, beta ước lượng từ giá, erp=8.2%),
        và in bảng so sánh chi tiết giả định Máy vs Excel.
        """
        # 1. Lấy dữ liệu thật từ DB và tính toán động
        cf_máy = build_vcb_current_financials(db, "VCB")
        cf_máy['current_price'] = 92000
        assumptions_máy = build_vcb_assumptions_from_history(db, "VCB")
        assumptions_máy['terminal_growth_rate'] = 0.02 # g = 2.0% theo nguyên tắc VN
        
        # Tạo mô hình của Máy
        model_máy = VCBValuationModel(cf_máy, assumptions_máy)
        ri_máy = model_máy.calculate_residual_income()
        pb_máy = model_máy.calculate_pb_valuation()
        blend_máy = model_máy.blend_valuation()
        
        # 2. In bảng so sánh chi tiết giả định Máy vs Excel
        print("\n" + "=" * 80)
        print(" BẢNG SO SÁNH GIẢ ĐỊNH & KẾT QUẢ ĐỊNH GIÁ VCB: MÁY VS EXCEL GỐC")
        print("=" * 80)
        
        print(f"{'Thông số / Giả định':<30} | {'Máy tính (Principled)':<23} | {'Excel gốc (Benchmark)':<23}")
        print("-" * 80)
        
        # So sánh COE components
        print(f"{'1. Lợi suất phi rủi ro (rf)':<30} | {model_máy.rf:<23.2%} | {'4.30% (UST 10Y)':<23}")
        print(f"{'2. Hệ số Beta':<30} | {model_máy.beta:<23.4f} | {'1.0000':<23}")
        print(f"{'3. Phần bù rủi ro (erp)':<30} | {model_máy.erp:<23.2%} | {'7.70%':<23}")
        print(f"{'4. Chi phí vốn cổ phần (COE)':<30} | {model_máy.coe:<23.2%} | {'12.00%':<23}")
        print(f"{'5. Tăng trưởng vĩnh viễn (g)':<30} | {model_máy.g:<23.2%} | {'5.00%':<23}")
        print(f"{'6. Số cổ phiếu lưu hành (shares)':<30} | {cf_máy['shares_outstanding']/1e9:<21.3f}B | {'5.589B':<23}")
        
        # So sánh key drivers năm 1
        hist_nim = assumptions_máy['_hist_nim']
        print(f"{'7. NIM năm 1':<30} | {assumptions_máy['nim'][0]:<23.2%} | {'3.20% phẳng':<23}")
        print(f"{'8. Tăng trưởng tín dụng năm 1':<30} | {assumptions_máy['credit_growth'][0]:<23.2%} | {'15.00% phẳng':<23}")
        print(f"{'9. Tỷ lệ CIR năm 1':<30} | {assumptions_máy['cir'][0]:<23.2%} | {'32.00% phẳng':<23}")
        print(f"{'10. Thu nhập ngoài lãi':<30} | {cf_máy['non_interest_income']/1e12:<19.2f}T VND | {'Bỏ qua (0.0)':<23}")
        
        print("-" * 80)
        # Kết quả định giá
        print(f"{'KẾT QUẢ ĐỊNH GIÁ RI':<30} | {ri_máy['fair_value_per_share']:<21,.0f} VND | {'57,600 VND':<23}")
        print(f"{'KẾT QUẢ ĐỊNH GIÁ P/B':<30} | {pb_máy['fair_value_per_share']:<21,.0f} VND | {'N/A':<23}")
        print(f"{'P/B ngầm định (Implied P/B)':<30} | {model_máy.implied_pb:<23.2f}x | {'N/A':<23}")
        print(f"{'ROE thực tế gần nhất':<30} | {model_máy.roe_ttm:<23.2%} | {'18.31% (Q4-24)':<23}")
        print(f"{'ĐỊNH GIÁ BLEND (50/50)':<30} | {blend_máy['blended_fair_value_per_share']:<21,.0f} VND | {'N/A':<23}")
        print("=" * 80)
        
        # Giải thích nguyên nhân lệch
        diff_pct = (ri_máy['fair_value_per_share'] - 57_600) / 57_600
        print(f"GHI CHÚ PHÂN TÍCH CHÊNH LỆCH:")
        print(f"  - Kết quả RI FV của máy ({ri_máy['fair_value_per_share']:,.0f} VND) lệch {diff_pct:+.1%} so với Excel (57,600 VND).")
        print(f"  - Nguyên nhân chính còn lại hoàn toàn nằm ở r (COE: {model_máy.coe:.2%} vs 12.0%) và g (2.0% vs 5.0%):")
        print(f"    a) Chi phí vốn (COE): Máy tính theo nguyên tắc ra {model_máy.coe:.2%} (gần hơn mức 12% nhờ nâng ERP lên 8.2% sát thực tế VN) so với 12% của Excel.")
        print(f"    b) Tăng trưởng vĩnh viễn (g): Máy dùng 2% (phù hợp lạm phát VN) thay vì 5% của Excel (gây lệch lớn ở Terminal Value).")
        print(f"    c) Số lượng cổ phiếu: Máy dùng số lượng thực tế tăng vốn {cf_máy['shares_outstanding']/1e9:.3f}B cp (so với 5.589B cp của Excel).")
        print("=" * 80)
        
        # Assert kết quả định giá theo nguyên tắc nằm trong vùng kỳ vọng hợp lý (50k - 85k) với COE ~9.5%
        assert 50_000 <= blend_máy['blended_fair_value_per_share'] <= 85_000, (
            f"Blend FV={blend_máy['blended_fair_value_per_share']:,.0f} ngoài vùng kỳ vọng hợp lý theo nguyên tắc động (50k-85k)"
        )

class TestVCBSanityChecks:
    def test_coe_sanity_floor(self):
        """Nếu COE quá thấp (< rf + 5%), mô hình phải raise ValueError với thông báo COE_TOO_LOW."""
        cf = {
            'total_equity': 196.21e12,
            'total_assets': 2085.87e12,
            'customer_loans': 1449.20e12,
            'customer_deposits': 1514.66e12,
            'net_income': 33.85e12,
            'net_interest_income': 55.41e12,
            'shares_outstanding': 5_589_091_300,
            'current_price': 92000
        }
        # ERP quá nhỏ (1%) làm COE = 4.3% + 1.0 * 1% = 5.3% < rf (4.3%) + 5% = 9.3% -> raise
        assumptions_low_coe = {
            'credit_growth': 0.15,
            'nim': 0.032,
            'cir': 0.32,
            'credit_cost': 0.008,
            'dividend_payout_ratio': 0.15,
            'risk_free_rate': 0.043,
            'beta': 1.0,
            'erp': 0.01,
            'terminal_growth_rate': 0.02
        }
        with pytest.raises(ValueError, match="COE_TOO_LOW"):
            VCBValuationModel(cf, assumptions_low_coe)

    def test_implied_pb_sanity_check(self, caplog):
        """Nếu P/B ngầm định ngoài khoảng [0.5, 4.0], phải bắn log warning với IMPLIED_PB_WARNING."""
        cf = {
            'total_equity': 100e12,
            'total_assets': 1000e12,
            'customer_loans': 800e12,
            'customer_deposits': 800e12,
            # ROE cực cao: 90%
            'net_income': 90e12,
            'net_interest_income': 50e12,
            'shares_outstanding': 1e9,
            'current_price': 92000
        }
        # COE = 4.3% + 1.0 * 8.2% = 12.5%
        # Implied P/B = (90% - 2%) / (12.5% - 2%) = 88% / 10.5% = 8.38x > 4.0 -> warning
        assumptions = {
            'credit_growth': 0.15,
            'nim': 0.032,
            'cir': 0.32,
            'credit_cost': 0.008,
            'dividend_payout_ratio': 0.15,
            'risk_free_rate': 0.043,
            'beta': 1.0,
            'erp': 0.082,
            'terminal_growth_rate': 0.02
        }
        
        with caplog.at_level(logging.WARNING):
            model = VCBValuationModel(cf, assumptions)
            assert model.implied_pb is not None
            assert model.implied_pb > 4.0
            
        warnings = [rec.message for rec in caplog.records if "IMPLIED_PB_WARNING" in rec.message]
        assert len(warnings) > 0, "Không bắn cảnh báo IMPLIED_PB_WARNING khi P/B ngầm định quá cao"
