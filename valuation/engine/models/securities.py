from typing import Dict, Any
from .base import BaseValuationModel

class SecuritiesValuationModel(BaseValuationModel):
    """
    Mô hình Residual Income (RI) + P/B cho ngành Chứng khoán (SSI, VND...).
    """
    def __init__(self, ticker: str, current_financials: Dict[str, Any], assumptions: Dict[str, Any]):
        super().__init__(ticker, current_financials, assumptions)
        self.use_wacc = False
        self.validators()

    def forecast_drivers(self) -> Dict[str, Any]:
        """
        Dự phóng lợi nhuận của CTCK dựa trên:
        - Thanh khoản thị trường trung bình (market_liquidity_vnd_billion)
        - Tỷ trọng môi giới (brokerage_market_share)
        - Biên lợi nhuận môi giới (brokerage_margin)
        - Dư nợ margin cho vay (margin_loans)
        - Lãi suất margin ròng (net_margin_rate)
        """
        liq = self.assumptions.get('market_liquidity_vnd_billion', 20000.0) * 1e9
        share = self.assumptions.get('brokerage_market_share', 0.10)
        brok_margin = self.assumptions.get('brokerage_margin', 0.0015)
        
        margin_loans = self.assumptions.get('margin_loans', 15000.0) * 1e9
        net_margin_rate = self.assumptions.get('net_margin_rate', 0.05)
        
        prop_trading = self.assumptions.get('prop_trading_income', 2000.0) * 1e9
        opex_ratio = self.assumptions.get('opex_ratio', 0.40)
        tax = self.assumptions.get('tax_rate', 0.20)
        
        # Đơn giản hóa: Cố định lợi nhuận 5 năm
        total_rev = (liq * 250 * share * brok_margin) + (margin_loans * net_margin_rate) + prop_trading
        net_income = total_rev * (1 - opex_ratio) * (1 - tax)
        
        forecasts = []
        book_value = self.current_financials.get('total_equity', 20000.0 * 1e9)
        payout_ratio = self.assumptions.get('payout_ratio', 0.20)
        
        for year in range(1, 6):
            forecasts.append({
                'year': year,
                'net_income': net_income,
                'book_value_start': book_value
            })
            book_value += net_income * (1 - payout_ratio)
            
        return {'forecasts': forecasts, 'terminal_roe': net_income / book_value if book_value > 0 else 0.15}

    def perform_valuation(self) -> Dict[str, Any]:
        forecast_data = self.forecast_drivers()
        forecasts = forecast_data['forecasts']
        term_roe = forecast_data['terminal_roe']
        
        # 1. Residual Income
        pv_ri = 0.0
        current_bv = self.current_financials.get('total_equity', 20000.0 * 1e9)
        
        for f in forecasts:
            ri = f['net_income'] - (f['book_value_start'] * self.coe)
            pv_ri += ri / ((1 + self.coe) ** f['year'])
            
        terminal_bv = forecasts[-1]['book_value_start']
        terminal_ri = (term_roe - self.coe) * terminal_bv
        terminal_value = terminal_ri / (self.coe - self.g)
        pv_tv = terminal_value / ((1 + self.coe) ** 5)
        
        equity_value_ri = current_bv + pv_ri + pv_tv
        shares_out = self.current_financials.get('shares_outstanding', 1500.0 * 1e6)
        ri_fvps = equity_value_ri / shares_out if shares_out > 0 else 0.0
        
        # 2. P/B Valuation
        target_pb = (term_roe - self.g) / (self.coe - self.g)
        if target_pb < 1.0 and term_roe > self.coe:
            target_pb = 1.0 # Floor
        # Đảm bảo target_pb không âm (floor tối thiểu ở mức thanh lý/sách chiết khấu 0.3x)
        if target_pb < 0.3:
            target_pb = 0.3
            
        pb_fvps = (current_bv * target_pb) / shares_out if shares_out > 0 else 0.0
        
        # 3. Blend 50/50
        weight_ri = self.assumptions.get('weight_ri', 0.5)
        weight_pb = 1.0 - weight_ri
        blended_fvps = (ri_fvps * weight_ri) + (pb_fvps * weight_pb)
        
        # Đảm bảo blended_fvps không âm
        if blended_fvps < 0.0:
            blended_fvps = 0.0
            
        return {
            "blended_fair_value_per_share": blended_fvps,
            "ri_fvps": ri_fvps,
            "pb_fvps": pb_fvps,
            "weight_ri": weight_ri
        }
