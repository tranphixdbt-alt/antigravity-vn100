"""
Bank General Model — Mô hình định giá ngân hàng tổng quát (Residual Income + Justified P/B).
Kế thừa tinh hoa từ VCB model và mở rộng cho tất cả các ngân hàng thương mại thuộc VN100.
"""
from typing import Dict, Any, List
import numpy as np
from valuation.models.financials_bank import CompanyBank
from valuation.engine.forecast_bank import forecast_bank_financials

class BankGeneralValuationModel:
    """
    Mô hình định giá Ngân hàng dựa trên Pydantic CompanyBank.
    """
    def __init__(self, company: CompanyBank, projections: List[Dict[str, Any]] = None):
        self.company = company
        self.assumptions = company.assumptions
        self.base_bs = company.historical_bs[-1]
        self.base_is = company.historical_is[-1]
        
        # Chi phí vốn cổ phần
        self.rf = self.assumptions.risk_free_rate
        self.beta = self.assumptions.beta
        self.erp = self.assumptions.erp
        self.g = self.assumptions.terminal_growth_rate
        
        if self.assumptions.cost_of_equity is not None:
            self.coe = self.assumptions.cost_of_equity
        else:
            self.coe = self.rf + self.beta * self.erp
            
        # Ràng buộc g < coe
        if self.g >= self.coe:
            self.g = self.coe - 0.005  # clamp

        # Sanity Floor Check cho COE (VND-base: equity premium >= MIN_EQUITY_PREMIUM)
        from valuation.engine.coe import MIN_EQUITY_PREMIUM
        if self.coe < self.rf + MIN_EQUITY_PREMIUM:
            self.company.warnings.append(
                f"COE_TOO_LOW: Chi phí vốn cổ phần COE={self.coe:.2%} quá thấp "
                f"(thấp hơn rf={self.rf:.2%} + {MIN_EQUITY_PREMIUM:.1%}). Kiểm tra lại Beta ({self.beta}) hoặc ERP ({self.erp:.2%})."
            )

        # Dự phóng
        self.projections = projections if projections is not None else forecast_bank_financials(self.company)

    def calculate_residual_income(self) -> Dict[str, float]:
        """Tính giá trị hợp lý theo phương pháp Residual Income (Excess Return)."""
        pv_ri = 0.0
        beg_equity = self.base_bs.total_equity
        ri_list = []
        
        for i, proj in enumerate(self.projections):
            # RI = LNST - (VCSH đầu kỳ * COE)
            ri = proj["net_income"] - (beg_equity * self.coe)
            ri_list.append(ri)
            
            # Chiết khấu về PV
            pv_ri += ri / ((1 + self.coe) ** (i + 1))
            beg_equity = proj["total_equity"]
            
        # Terminal Value cho RI (tăng trưởng vĩnh viễn g)
        terminal_ri = (ri_list[-1] * (1 + self.g)) / (self.coe - self.g)
        pv_terminal_ri = terminal_ri / ((1 + self.coe) ** len(self.projections))
        
        total_ri_equity_value = self.base_bs.total_equity + pv_ri + pv_terminal_ri
        
        # Đổi sang VND mỗi cổ phiếu (VCSH tỷ đồng, shares triệu cp -> tỷ/triệu = nghìn đồng, nhân 1000 ra đồng)
        ri_fvps = (total_ri_equity_value / self.company.shares_outstanding) * 1000.0 if self.company.shares_outstanding > 0 else 0.0
        
        return {
            "pv_ri": pv_ri,
            "pv_terminal_ri": pv_terminal_ri,
            "equity_value": total_ri_equity_value,
            "fair_value_per_share": max(0.0, ri_fvps)
        }

    def calculate_pb_valuation(self) -> Dict[str, float]:
        """Tính giá trị hợp lý theo phương pháp Justified P/B."""
        # Lấy ROE dài hạn = LNST năm 5 / VCSH đầu năm 5 (tức là VCSH cuối năm 4)
        ni_yr5 = self.projections[-1]["net_income"]
        eq_yr4 = self.projections[-2]["total_equity"]  # VCSH cuối năm 4
        long_term_roe = ni_yr5 / eq_yr4 if eq_yr4 > 0 else 0.15
        
        # Target P/B = (ROE - g) / (Re - g)
        if self.coe <= self.g:
            target_pb = 1.0
        else:
            target_pb = (long_term_roe - self.g) / (self.coe - self.g)
            
        # Giới hạn floor tối thiểu cho target_pb
        target_pb = max(0.3, target_pb)
        
        total_pb_equity_value = target_pb * self.base_bs.total_equity
        pb_fvps = (total_pb_equity_value / self.company.shares_outstanding) * 1000.0 if self.company.shares_outstanding > 0 else 0.0
        
        # Implied P/B sanity check warning
        if target_pb > 4.0 or target_pb < 0.5:
            self.company.warnings.append(
                f"IMPLIED_PB_WARNING: P/B ngầm định Justified P/B = {target_pb:.2f}x "
                f"nằm ngoài khoảng hợp lý [0.5, 4.0]. ROE={long_term_roe:.2%}, COE={self.coe:.2%}, g={self.g:.2%}."
            )
            
        return {
            "long_term_roe": long_term_roe,
            "target_pb": target_pb,
            "equity_value": total_pb_equity_value,
            "fair_value_per_share": max(0.0, pb_fvps)
        }

    def perform_valuation(self) -> Dict[str, Any]:
        """Pha trộn kết quả định giá."""
        ri_res = self.calculate_residual_income()
        pb_res = self.calculate_pb_valuation()
        
        weight_ri = self.assumptions.weight_ri
        weight_pb = 1.0 - weight_ri
        
        blended_fvps = (ri_res["fair_value_per_share"] * weight_ri) + (pb_res["fair_value_per_share"] * weight_pb)
        
        return {
            "blended_fair_value_per_share": blended_fvps,
            "ri_fvps": ri_res["fair_value_per_share"],
            "pb_fvps": pb_res["fair_value_per_share"],
            "weight_ri": weight_ri,
            "coe": self.coe,
            "terminal_g": self.g,
            "projections": self.projections
        }
