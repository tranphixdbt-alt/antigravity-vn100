from typing import Dict, Any
from .base import BaseValuationModel

class RNAVValuationModel(BaseValuationModel):
    """
    Mô hình Revalued Net Asset Value cho Bất động sản (VHM).
    """
    def __init__(self, ticker: str, current_financials: Dict[str, Any], assumptions: Dict[str, Any]):
        super().__init__(ticker, current_financials, assumptions)
        self.use_wacc = True
        self.validators()

    def forecast_drivers(self) -> Dict[str, Any]:
        """
        Dự phóng dòng tiền (Cash flow) từ các dự án đang triển khai dựa trên:
        - Tổng diện tích đất thương phẩm (sqm)
        - ASP dự kiến (VND/sqm)
        - Tiến độ bán hàng và bàn giao (absorption_rate)
        - Biên lợi nhuận gộp (gross_margin)
        """
        sqm = self.assumptions.get('total_commercial_sqm', 5000000.0)
        asp = self.assumptions.get('asp_per_sqm', 50000000.0)
        margin = self.assumptions.get('project_gross_margin', 0.40)
        sgna_rate = self.assumptions.get('sgna_as_pct_revenue', 0.05)
        tax = self.assumptions.get('tax_rate', 0.20)
        
        # Đơn giản hóa: Phân bổ đều dòng tiền dự án trong 5 năm
        total_revenue = sqm * asp
        annual_revenue = total_revenue / 5.0
        
        annual_gross_profit = annual_revenue * margin
        annual_ebit = annual_gross_profit - (annual_revenue * sgna_rate)
        annual_nopat = annual_ebit * (1 - tax)
        
        forecasts = []
        for year in range(1, 6):
            forecasts.append({
                'year': year,
                'cash_flow': annual_nopat # Giả định working cap & capex bù trừ cho cdt bđs
            })
            
        return {'forecasts': forecasts}

    def perform_valuation(self) -> Dict[str, Any]:
        forecast_data = self.forecast_drivers()
        forecasts = forecast_data['forecasts']
        
        # 1. RNAV = Book Value of Equity + NPV of Project Cash Flows
        npv_projects = 0.0
        for f in forecasts:
            npv_projects += f['cash_flow'] / ((1 + self.wacc) ** f['year'])
            
        book_value = self.current_financials.get('total_equity', 100000.0)
        rnav = book_value + npv_projects
        
        shares_out = self.current_financials.get('shares_outstanding', 1000.0)
        rnav_fvps = rnav / shares_out if shares_out > 0 else 0.0
        
        # 2. P/B Valuation (Tương đối)
        target_pb = self.assumptions.get('target_pb', 1.5)
        pb_fvps = (book_value * target_pb) / shares_out if shares_out > 0 else 0.0
        
        # 3. Blend 50/50
        weight_rnav = self.assumptions.get('weight_rnav', 0.7)
        weight_pb = 1.0 - weight_rnav
        
        blended_fvps = (rnav_fvps * weight_rnav) + (pb_fvps * weight_pb)
        
        return {
            "blended_fair_value_per_share": blended_fvps,
            "rnav_fvps": rnav_fvps,
            "pb_fvps": pb_fvps,
            "weight_rnav": weight_rnav,
            "rnav": rnav
        }
