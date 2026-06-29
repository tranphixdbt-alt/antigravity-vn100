from typing import Dict, Any
import statistics
from .base import BaseValuationModel
from valuation.models.financials import Company


class PBRelativeValuationModel(BaseValuationModel):
    """
    Justified P/B cho định chế tài chính phi-ngân-hàng (chứng khoán, bảo hiểm).

    GUARDRAIL (reviewer): P/B PHẢI link ROE — justified P/B = (ROE − g)/(COE − g),
    KHÔNG dùng P/B cố định. ROE = LN chuẩn hóa (median) / vốn CSH.
    Sanity: ROE phi lý (>40% hoặc <0) hoặc vốn CSH<=0 → cờ DATA_SUSPECT; P/B kẹp [0.3, 4.0].
    """

    def __init__(self, ticker: str, current_financials: Dict[str, Any], assumptions: Dict[str, Any]):
        super().__init__(ticker, current_financials, assumptions)
        self.use_wacc = False

    @classmethod
    def from_pydantic(cls, company: Company) -> "PBRelativeValuationModel":
        bs = company.historical_bs[-1]
        a = company.assumptions
        cf_dict = {
            "total_equity": bs.total_equity * 1e9,            # đồng
            "net_income_history": [is_.net_income for is_ in company.historical_is],  # tỷ
            "shares_outstanding": company.shares_outstanding * 1e6,
            "current_price": company.current_price,
        }
        coe = (a.cost_of_equity if a.cost_of_equity else a.risk_free_rate + a.beta * a.erp)
        assumptions = {
            "cost_of_equity": coe,
            "long_term_growth": a.terminal_growth_rate,
            "norm_years": 3,
        }
        return cls(company.ticker, cf_dict, assumptions)

    def perform_valuation(self) -> Dict[str, Any]:
        equity = self.current_financials.get("total_equity", 0.0)
        hist = [x for x in self.current_financials.get("net_income_history", []) if x is not None]
        shares = self.current_financials.get("shares_outstanding", 1.0)
        g = self.g
        coe = self.coe

        if equity <= 0 or not hist or shares <= 0:
            return {"blended_fair_value_per_share": 0.0, "flags": ["NO_PB_DATA"]}

        n = int(self.assumptions.get("norm_years", 3))
        window = hist[-n:] if len(hist) >= n else hist
        norm_ni = statistics.median(window) * 1e9
        roe = norm_ni / equity

        flags = []
        # ROE phi lý → dữ liệu khả nghi (vd bảo hiểm: LN bị map nhầm doanh thu phí).
        if roe > 0.40 or roe < 0:
            flags.append("DATA_SUSPECT_ROE")

        if coe <= g:
            justified_pb = 1.0
        else:
            justified_pb = (roe - g) / (coe - g)
        justified_pb = max(0.3, min(justified_pb, 4.0))  # kẹp chống số rác

        bvps = equity / shares
        fvps = max(0.0, justified_pb * bvps)

        return {
            "blended_fair_value_per_share": fvps,
            "justified_pb": justified_pb,
            "roe": roe,
            "book_value_per_share": bvps,
            "flags": flags,
        }
