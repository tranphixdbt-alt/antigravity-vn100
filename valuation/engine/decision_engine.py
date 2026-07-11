from typing import Dict, Any, List
from valuation.models.financials import GovernanceData

from valuation.models.macro_env import MacroEnvironment

class InvestmentDecisionMaker:
    """
    Quyết định hành động đầu tư dựa trên Hard Gates và Dynamic Margin of Safety (MOS).
    """

    def __init__(self, business_nature: str, current_price: float, fair_value: float, governance: GovernanceData, macro_env: MacroEnvironment = None):
        self.business_nature = business_nature
        self.current_price = current_price
        self.fair_value = fair_value
        self.governance = governance
        self.macro_env = macro_env

    def get_target_mos(self) -> float:
        """
        Xác định Margin of Safety an toàn tối thiểu theo loại hình doanh nghiệp.
        Và tự động nới rộng (+5%) nếu môi trường vĩ mô đang căng thẳng.
        """
        if self.business_nature == "Compounder":
            mos = 0.15
        elif self.business_nature in ["Bank", "Utility"]:
            mos = 0.20
        elif self.business_nature == "Retail":
            mos = 0.25
        elif self.business_nature in ["Cyclical", "Developer", "Securities"]:
            mos = 0.30
        else:
            mos = 0.25 # Default
            
        # Nới rộng MOS nếu vĩ mô xấu
        if self.macro_env and self.macro_env.is_macro_stressed:
            mos += 0.05
            
        return mos

    def evaluate_hard_gates(self) -> List[str]:
        """
        Kiểm tra rủi ro nghiêm trọng. Nếu có bất kỳ lỗi nào, mã sẽ bị Hard Reject.
        """
        violations = []
        if self.governance:
            if self.governance.audit_issue:
                violations.append("Vấn đề ngoại trừ từ kiểm toán")
            if self.governance.legal_issue:
                if self.business_nature == "Developer":
                    violations.append("Rủi ro pháp lý dự án BĐS đặc biệt nghiêm trọng")
                else:
                    violations.append("Rủi ro pháp lý nghiêm trọng")
            if self.governance.liquidity_issue:
                violations.append("Rủi ro thanh khoản")
        return violations

    def make_decision(self) -> Dict[str, Any]:
        """
        Ra quyết định đầu tư cuối cùng (Buy / Hold / Trim / Sell / Hard Reject).
        """
        hard_gates_violations = self.evaluate_hard_gates()
        upside = ((self.fair_value / self.current_price - 1.0) * 100.0) if self.current_price > 0 else 0.0
        target_mos = self.get_target_mos()
        # So sánh upside (%) với target_mos (ratio) → cần nhân target_mos × 100
        target_mos_pct = target_mos * 100.0

        # Epsilon chống lỗi làm tròn số thực ở biên: upside đúng bằng MOS (vd
        # 115/100-1 = 14.999...% do float) vẫn phải được coi là đạt ngưỡng BUY.
        _EPS = 1e-9
        if len(hard_gates_violations) > 0:
            recommendation = "HARD REJECT"
        elif upside >= target_mos_pct - _EPS:
            recommendation = "BUY"
        elif upside >= -_EPS:
            recommendation = "HOLD"
        elif upside >= -10.0 - _EPS:
            recommendation = "TRIM"
        else:
            recommendation = "SELL"

        return {
            "business_nature": self.business_nature,
            "target_mos": target_mos,
            "hard_gates_violations": hard_gates_violations,
            "upside": upside,
            "recommendation": recommendation
        }
