from typing import Dict, Any
import statistics
from .base import BaseValuationModel
from valuation.models.financials import Company
from valuation.config import load_defaults


class DDMValuationModel(BaseValuationModel):
    """
    Dividend Discount Model (DDM) — cross-check cho điện (genco trả cổ tức ổn định).

    Multi-stage Gordon: cổ tức = EPS chuẩn hóa × payout, tăng near_growth 5 năm rồi
    về terminal_growth vĩnh viễn, chiết khấu theo COE.
    EPS CHUẨN HÓA = median LN lịch sử / số cp (chống nhiễu năm bất thường).
    """

    def __init__(self, ticker: str, current_financials: Dict[str, Any], assumptions: Dict[str, Any]):
        super().__init__(ticker, current_financials, assumptions)
        self.use_wacc = False

    @classmethod
    def from_pydantic(cls, company: Company) -> "DDMValuationModel":
        a = company.assumptions
        cfg = load_defaults().get("ddm", {})
        coe = (a.cost_of_equity if a.cost_of_equity else a.risk_free_rate + a.beta * a.erp)
        cf_dict = {
            "net_income_history": [is_.net_income for is_ in company.historical_is],  # tỷ
            "shares_outstanding": company.shares_outstanding * 1e6,
            "current_price": company.current_price,
        }
        assumptions = {
            "cost_of_equity": coe,
            "payout_ratio": cfg.get("power_payout", 0.50),
            "near_growth": cfg.get("near_growth", 0.05),
            "long_term_growth": cfg.get("terminal_growth", 0.03),
        }
        return cls(company.ticker, cf_dict, assumptions)

    def perform_valuation(self) -> Dict[str, Any]:
        hist = [x for x in self.current_financials.get("net_income_history", []) if x is not None]
        shares = self.current_financials.get("shares_outstanding", 1.0)
        coe = self.coe
        g_term = self.g
        g_near = self.assumptions.get("near_growth", 0.05)
        payout = self.assumptions.get("payout_ratio", 0.50)

        if not hist or shares <= 0:
            return {"blended_fair_value_per_share": 0.0, "flags": ["NO_DDM_DATA"]}

        window = hist[-3:] if len(hist) >= 3 else hist
        norm_ni = statistics.median(window) * 1e9
        if norm_ni <= 0:
            return {"blended_fair_value_per_share": 0.0, "flags": ["NEGATIVE_EARNINGS"]}

        eps0 = norm_ni / shares
        # Guardrail Gordon: spread COE − g_term phải dương.
        if coe <= g_term:
            g_term = coe - 0.02

        # 5 năm cổ tức tăng near_growth, rồi terminal Gordon.
        pv = 0.0
        d_t = eps0 * payout
        for t in range(1, 6):
            d_t = eps0 * payout * (1 + g_near) ** t
            pv += d_t / (1 + coe) ** t
        d_terminal = d_t * (1 + g_term)
        tv = d_terminal / (coe - g_term)
        pv += tv / (1 + coe) ** 5

        return {
            "blended_fair_value_per_share": max(0.0, pv),
            "normalized_eps": eps0,
            "payout_ratio": payout,
            "implied_div_yield": (eps0 * payout) / self.current_financials.get("current_price", 1)
            if self.current_financials.get("current_price") else None,
            "flags": [],
        }
