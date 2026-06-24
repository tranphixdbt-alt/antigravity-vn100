from typing import Dict, Any
from .base import BaseValuationModel

class SOTPValuationModel(BaseValuationModel):
    """
    Mô hình Sum-Of-The-Parts (SOTP) dùng cho Đa ngành (VD: MSN).
    """
    def __init__(self, ticker: str, current_financials: Dict[str, Any], assumptions: Dict[str, Any]):
        super().__init__(ticker, current_financials, assumptions)
        self.use_wacc = True
        self.validators()

    def perform_valuation(self) -> Dict[str, Any]:
        """
        Định giá bằng tổng EV của các mảnh ghép trừ đi Net Debt của Holding.
        """
        # Part 1: Bán lẻ (WCM)
        wcm_rev = self.assumptions.get('wcm_revenue', 30000.0) * 1e9
        wcm_ev_sales = self.assumptions.get('wcm_target_ev_sales', 1.5)
        wcm_ev = wcm_rev * wcm_ev_sales
        
        # Part 2: Hàng tiêu dùng (MCH)
        mch_ebitda = self.assumptions.get('mch_ebitda', 8000.0) * 1e9
        mch_ev_ebitda = self.assumptions.get('mch_target_ev_ebitda', 15.0)
        mch_ev = mch_ebitda * mch_ev_ebitda
        
        # Part 3: Khoáng sản/Vật liệu (MHT)
        mht_ebitda = self.assumptions.get('mht_ebitda', 2000.0) * 1e9
        mht_ev_ebitda = self.assumptions.get('mht_target_ev_ebitda', 6.0)
        mht_ev = mht_ebitda * mht_ev_ebitda
        
        total_enterprise_value = wcm_ev + mch_ev + mht_ev
        
        holding_discount = self.assumptions.get('holding_discount', 0.15)
        adjusted_ev = total_enterprise_value * (1 - holding_discount)
        
        net_debt = self.current_financials.get('total_debt', 40000.0 * 1e9) - self.current_financials.get('cash_and_equivalents', 10000.0 * 1e9)
        
        equity_value = adjusted_ev - net_debt
        shares_out = self.current_financials.get('shares_outstanding', 1400.0 * 1e6)
        
        blended_fvps = equity_value / shares_out if shares_out > 0 else 0.0
        
        return {
            "blended_fair_value_per_share": blended_fvps,
            "sotp_components": {
                "WCM_EV": wcm_ev,
                "MCH_EV": mch_ev,
                "MHT_EV": mht_ev
            },
            "adjusted_ev": adjusted_ev,
            "equity_value": equity_value
        }

    def forecast_drivers(self):
        # Không dùng chung pattern với DCF
        pass
