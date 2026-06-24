from typing import Dict, Any
from .base import BaseValuationModel

class DCFValuationModel(BaseValuationModel):
    """
    Mô hình định giá DCF (FCFF) + Multiples.
    Dùng chung cho các ngành phi tài chính: FPT, HPG, VNM, GAS...
    """
    def __init__(self, ticker: str, current_financials: Dict[str, Any], assumptions: Dict[str, Any]):
        super().__init__(ticker, current_financials, assumptions)
        self.use_wacc = True
        self.validators()

    def forecast_drivers(self) -> Dict[str, Any]:
        """
        Dự phóng cơ bản 5 năm.
        Drivers:
        - revenue_growth_1_to_3
        - revenue_growth_4_to_5
        - ebit_margin
        - tax_rate
        - reinvestment_rate (Reinvestment / EBIT(1-t))
        """
        rev_g_1_3 = self.assumptions.get('revenue_growth_1_to_3', 0.1)
        rev_g_4_5 = self.assumptions.get('revenue_growth_4_to_5', 0.08)
        ebit_m = self.assumptions.get('ebit_margin', 0.15)
        tax = self.assumptions.get('tax_rate', 0.20)
        reinv_rate = self.assumptions.get('reinvestment_rate', 0.40)
        
        # Lấy base revenue
        base_rev = self.current_financials.get('total_revenue', 100000.0)
        if base_rev is None or base_rev == 0.0:
            base_rev = 100000.0 * 1e9 # Giả định 100,000 tỷ nếu thiếu data
            
        forecasts = []
        curr_rev = base_rev
        
        for year in range(1, 6):
            if year <= 3:
                curr_rev *= (1 + rev_g_1_3)
            else:
                curr_rev *= (1 + rev_g_4_5)
                
            ebit = curr_rev * ebit_m
            nopat = ebit * (1 - tax)
            reinvestment = nopat * reinv_rate
            fcff = nopat - reinvestment
            
            forecasts.append({
                'year': year,
                'revenue': curr_rev,
                'ebit': ebit,
                'nopat': nopat,
                'reinvestment': reinvestment,
                'fcff': fcff
            })
            
        return {'forecasts': forecasts, 'terminal_nopat': forecasts[-1]['nopat']}

    def perform_valuation(self) -> Dict[str, Any]:
        forecast_data = self.forecast_drivers()
        forecasts = forecast_data['forecasts']
        term_nopat = forecast_data['terminal_nopat']
        
        # 1. DCF Valuation (FCFF)
        pv_fcff = 0.0
        for f in forecasts:
            pv_fcff += f['fcff'] / ((1 + self.wacc) ** f['year'])
            
        term_reinv_rate = self.g / self.assumptions.get('roic_terminal', self.wacc)
        # Bắt buộc reinv_rate <= 1.0
        term_reinv_rate = min(term_reinv_rate, 1.0)
        
        term_fcff = (term_nopat * (1 + self.g)) * (1 - term_reinv_rate)
        terminal_value = term_fcff / (self.wacc - self.g)
        pv_tv = terminal_value / ((1 + self.wacc) ** 5)
        
        enterprise_value_dcf = pv_fcff + pv_tv
        
        # Từ EV ra Equity Value
        net_debt = self.current_financials.get('total_debt', 0.0) - self.current_financials.get('cash_and_equivalents', 0.0)
        equity_value_dcf = enterprise_value_dcf - net_debt
        shares_out = self.current_financials.get('shares_outstanding', 1000.0)
        dcf_fvps = equity_value_dcf / shares_out if shares_out > 0 else 0.0
        
        # 2. Multiples Valuation (EV/EBITDA)
        target_ev_ebitda = self.assumptions.get('target_ev_ebitda', 8.0)
        base_ebitda = self.current_financials.get('ebitda', term_nopat) # Fallback
        ev_multiples = base_ebitda * target_ev_ebitda
        equity_value_multi = ev_multiples - net_debt
        multi_fvps = equity_value_multi / shares_out if shares_out > 0 else 0.0
        
        # 3. Blend 50/50
        weight_dcf = self.assumptions.get('weight_dcf', 0.5)
        weight_multi = 1.0 - weight_dcf
        
        blended_fvps = (dcf_fvps * weight_dcf) + (multi_fvps * weight_multi)
        
        return {
            "blended_fair_value_per_share": blended_fvps,
            "dcf_fvps": dcf_fvps,
            "multiples_fvps": multi_fvps,
            "weight_dcf": weight_dcf,
            "enterprise_value_dcf": enterprise_value_dcf,
            "equity_value_dcf": equity_value_dcf
        }
