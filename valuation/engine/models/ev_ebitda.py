from typing import Dict, Any
import statistics
from .base import BaseValuationModel
from valuation.models.financials import Company


class EVEBITDAValuationModel(BaseValuationModel):
    """
    Định giá EV/EBITDA chủ đạo cho ngành lợi nhuận biến động mạnh (hàng không, xi măng).

    GUARDRAIL G2: dùng EBITDA CHUẨN HÓA (trung bình 3 năm gần nhất) thay vì EBITDA
    một năm — chống nhiễu chu kỳ/sự kiện bất thường (vd hàng không lãi/lỗ đột biến).
    """

    def __init__(self, ticker: str, current_financials: Dict[str, Any], assumptions: Dict[str, Any]):
        super().__init__(ticker, current_financials, assumptions)
        self.use_wacc = False  # không chiết khấu dòng tiền; định giá bội số

    @classmethod
    def from_pydantic(cls, company: Company) -> "EVEBITDAValuationModel":
        bs = company.historical_bs[-1]
        depr_to_rev = company.assumptions.depr_to_revenue[0]

        # EBITDA từng năm = EBIT + D&A (ước lượng D&A = depr_to_revenue × doanh thu).
        ebitda_hist = [
            is_.ebit + depr_to_rev * is_.revenue
            for is_ in company.historical_is
            if is_.revenue and is_.revenue > 0
        ]

        cf_dict = {
            'ebitda_history': ebitda_hist,            # tỷ đồng
            'total_debt': (bs.short_term_debt + bs.long_term_debt) * 1e9,
            'cash_and_equivalents': bs.cash_and_equivalents * 1e9,
            'shares_outstanding': company.shares_outstanding * 1e6,
            'current_price': company.current_price,
        }
        assumptions = {
            'target_ev_ebitda': company.assumptions.target_ev_ebitda,
            'norm_years': 3,
        }
        return cls(company.ticker, cf_dict, assumptions)

    def perform_valuation(self) -> Dict[str, Any]:
        hist = self.current_financials.get('ebitda_history', []) or []
        n = int(self.assumptions.get('norm_years', 3))
        target = self.assumptions.get('target_ev_ebitda', 7.0) or 7.0

        if not hist:
            return {"blended_fair_value_per_share": 0.0, "flags": ["NO_EBITDA_DATA"]}

        # EBITDA chuẩn hóa = trung bình n năm gần nhất (tỷ đồng → đồng).
        window = hist[-n:] if len(hist) >= n else hist
        norm_ebitda = statistics.mean(window) * 1e9

        ev = norm_ebitda * target
        net_debt = self.current_financials.get('total_debt', 0.0) - self.current_financials.get('cash_and_equivalents', 0.0)
        equity_value = ev - net_debt
        shares = self.current_financials.get('shares_outstanding', 1.0)
        fvps = equity_value / shares if shares > 0 else 0.0
        fvps = max(0.0, fvps)

        # Cảnh báo nếu EBITDA năm gần nhất lệch mạnh khỏi mức chuẩn hóa (chu kỳ/nhiễu).
        flags = []
        latest = window[-1] * 1e9
        if norm_ebitda > 0 and abs(latest - norm_ebitda) / norm_ebitda > 0.30:
            flags.append("EBITDA_NORMALIZED_CYCLICAL")

        return {
            "blended_fair_value_per_share": fvps,
            "normalized_ebitda": norm_ebitda,
            "enterprise_value": ev,
            "equity_value": equity_value,
            "target_ev_ebitda": target,
            "years_averaged": len(window),
            "flags": flags,
        }
