"""
Sensitivity & Scenario analysis module — Tính toán ma trận độ nhạy 2 chiều và 3 kịch bản định giá.
"""
import copy
from typing import List, Dict, Any, Tuple, Union
from valuation.models.financials import Company
from valuation.models.financials_bank import CompanyBank
from valuation.engine.blend import blend_intrinsic_relative

def apply_scenario_adjustments(company: Union[Company, CompanyBank], scenario: str) -> Union[Company, CompanyBank]:
    """
    Áp dụng hệ số điều chỉnh giả định cho kịch bản Bull / Bear.
    """
    import copy
    comp_copy = copy.deepcopy(company)
    if scenario == "Base" or not scenario:
        return comp_copy
        
    is_bank = isinstance(comp_copy, CompanyBank)
    if scenario == "Bull":
        if is_bank:
            comp_copy.assumptions.credit_growth = [min(cg * 1.2, 0.4) for cg in comp_copy.assumptions.credit_growth]
            if hasattr(comp_copy.assumptions, "deposit_growth") and comp_copy.assumptions.deposit_growth:
                comp_copy.assumptions.deposit_growth = [min(dg * 1.2, 0.4) for dg in comp_copy.assumptions.deposit_growth]
            comp_copy.assumptions.nim = [min(n * 1.1, 0.06) for n in comp_copy.assumptions.nim]
            comp_copy.assumptions.cir = [max(c * 0.9, 0.15) for c in comp_copy.assumptions.cir]
            if comp_copy.assumptions.cost_of_equity is not None:
                comp_copy.assumptions.cost_of_equity = max(0.05, comp_copy.assumptions.cost_of_equity - 0.01)
            comp_copy.assumptions.risk_free_rate = max(0.01, comp_copy.assumptions.risk_free_rate - 0.01)
        else:
            comp_copy.assumptions.revenue_growth = [min(g * 1.2, 0.5) for g in comp_copy.assumptions.revenue_growth]
            comp_copy.assumptions.ebit_margin = [min(m * 1.2, 0.6) for m in comp_copy.assumptions.ebit_margin]
            comp_copy.assumptions.risk_free_rate = max(0.01, comp_copy.assumptions.risk_free_rate - 0.01)
    elif scenario == "Bear":
        if is_bank:
            comp_copy.assumptions.credit_growth = [max(cg * 0.8, -0.05) for cg in comp_copy.assumptions.credit_growth]
            if hasattr(comp_copy.assumptions, "deposit_growth") and comp_copy.assumptions.deposit_growth:
                comp_copy.assumptions.deposit_growth = [max(dg * 0.8, -0.05) for dg in comp_copy.assumptions.deposit_growth]
            comp_copy.assumptions.nim = [max(n * 0.9, 0.01) for n in comp_copy.assumptions.nim]
            comp_copy.assumptions.cir = [min(c * 1.1, 0.70) for c in comp_copy.assumptions.cir]
            if comp_copy.assumptions.cost_of_equity is not None:
                comp_copy.assumptions.cost_of_equity = comp_copy.assumptions.cost_of_equity + 0.01
            comp_copy.assumptions.risk_free_rate = comp_copy.assumptions.risk_free_rate + 0.01
        else:
            comp_copy.assumptions.revenue_growth = [max(g * 0.8, -0.2) for g in comp_copy.assumptions.revenue_growth]
            comp_copy.assumptions.ebit_margin = [max(m * 0.8, 0.01) for m in comp_copy.assumptions.ebit_margin]
            comp_copy.assumptions.risk_free_rate = comp_copy.assumptions.risk_free_rate + 0.01
            
    return comp_copy

def run_valuation_engine(company: Union[Company, CompanyBank], wacc_override: float = None, coe_override: float = None, g_override: float = None, projections: List[Dict[str, Any]] = None) -> Tuple[float, float]:
    """
    Hàm helper chạy lại định giá và trả về (intrinsic_fv, relative_fv) dựa trên ValuationRouter.
    """
    from valuation.engine.router import ValuationRouter
    router = ValuationRouter()
    route = router.get_routing(company.ticker)
    primary_method = route.get("primary", "FCFF")
    
    from valuation.engine.models.bank_general import BankGeneralValuationModel
    
    if isinstance(company, Company):
        # Phi tài chính — hợp nhất sâu: delegate sang _dispatch_nonfin (các model
        # .from_pydantic chạy đúng & bao phủ đủ PE/PB/EV_EBITDA/RNAV/SOTP/DCF).
        # Đường dựng cf/ass trực tiếp trước đây khiến SOTP=0 và thiếu PE/PB.
        assumptions = copy.deepcopy(company.assumptions)
        # Assumptions KHÔNG có field 'wacc'; DCF suy WACC từ COE → ánh xạ cả
        # wacc_override lẫn coe_override vào cost_of_equity (đủ cho sensitivity).
        if coe_override is not None:
            assumptions.cost_of_equity = coe_override
        if wacc_override is not None:
            assumptions.cost_of_equity = wacc_override
        if g_override is not None:
            assumptions.terminal_growth_rate = g_override

        comp = copy.deepcopy(company)
        comp.assumptions = assumptions
        from valuation.engine.batch import _dispatch_nonfin
        from valuation.engine.sector_router import route as _route_fn
        plan = _route_fn(company.ticker) or {}
        model, res = _dispatch_nonfin(comp, plan.get("method"), plan.get("group"))
        if model is None or res is None:
            return 0.0, 0.0
        fv = float(res.get("blended_fair_value_per_share", 0.0))
        return fv, fv
        
    else:
        # Ngân hàng
        comp_copy = copy.deepcopy(company)
        if coe_override is not None:
            comp_copy.assumptions.cost_of_equity = coe_override
        if g_override is not None:
            comp_copy.assumptions.terminal_growth_rate = g_override
            
        model = BankGeneralValuationModel(comp_copy, projections=projections)
        ri_res = model.calculate_residual_income()
        pb_res = model.calculate_pb_valuation()
        
        intrinsic_fv = ri_res["fair_value_per_share"]
        if route.get("primary") == "P/B":
            # Nếu Primary là P/B, swap intrinsic and relative để khớp weights
            return pb_res["fair_value_per_share"], ri_res["fair_value_per_share"]
        else:
            return ri_res["fair_value_per_share"], pb_res["fair_value_per_share"]

def calculate_sensitivity_matrix(
    company: Union[Company, CompanyBank],
    base_x_val: float,  # WACC hoặc Re
    base_y_val: float   # g
) -> Tuple[List[float], List[float], List[List[float]]]:
    """
    Tính ma trận độ nhạy 2 chiều của blended fair value.
    Trục X: WACC hoặc Re (5 giá trị xung quanh base: -1.0%, -0.5%, base, +0.5%, +1.0%)
    Trục Y: g (5 giá trị xung quanh base: -0.5%, -0.25%, base, +0.25%, +0.5%)
    """
    x_steps = [-0.01, -0.005, 0.0, 0.005, 0.01]
    y_steps = [-0.005, -0.0025, 0.0, 0.0025, 0.005]
    
    x_values = [base_x_val + step for step in x_steps]
    y_values = [base_y_val + step for step in y_steps]
    
    matrix = []
    from valuation.engine.router import ValuationRouter
    route = ValuationRouter().get_routing(company.ticker)
    weight_intrinsic = route.get("weight_primary", 1.0)

    
    for g_val in y_values:
        row = []
        for x_val in x_values:
            # Kiểm tra ràng buộc g < x_val
            if g_val >= x_val:
                row.append(0.0)
                continue
                
            try:
                if isinstance(company, Company):
                    # X là WACC
                    int_fv, rel_fv = run_valuation_engine(company, wacc_override=x_val, g_override=g_val)
                else:
                    # X là Re (COE)
                    int_fv, rel_fv = run_valuation_engine(company, coe_override=x_val, g_override=g_val)
                    
                blended, _, _ = blend_intrinsic_relative(int_fv, rel_fv, weight_intrinsic, company.current_price)
                row.append(round(blended, 0))
            except Exception:
                row.append(0.0)
        matrix.append(row)
        
    return x_values, y_values, matrix

def run_scenario_analysis(company: Union[Company, CompanyBank]) -> Dict[str, float]:
    """
    Tính kết quả định giá blended cho 3 kịch bản: Bull, Base, Bear.
    """
    from valuation.engine.router import ValuationRouter
    route = ValuationRouter().get_routing(company.ticker)
    weight_intrinsic = route.get("weight_primary", 1.0)
    
    # 1. Base Scenario
    base_int, base_rel = run_valuation_engine(company)
    base_blended, _, _ = blend_intrinsic_relative(base_int, base_rel, weight_intrinsic, company.current_price)
    
    # 2. Bull Scenario (+20% tăng trưởng & ebit/nim)
    bull_comp = copy.deepcopy(company)
    if isinstance(bull_comp, Company):
        bull_comp.assumptions.revenue_growth = [min(g * 1.2, 0.4) for g in bull_comp.assumptions.revenue_growth]
        bull_comp.assumptions.ebit_margin = [min(m * 1.2, 0.6) for m in bull_comp.assumptions.ebit_margin]
    else:
        bull_comp.assumptions.credit_growth = [min(g * 1.2, 0.3) for g in bull_comp.assumptions.credit_growth]
        bull_comp.assumptions.nim = [min(n * 1.1, 0.06) for n in bull_comp.assumptions.nim]
        
    bull_int, bull_rel = run_valuation_engine(bull_comp)
    bull_blended, _, _ = blend_intrinsic_relative(bull_int, bull_rel, weight_intrinsic, company.current_price)
    
    # 3. Bear Scenario (-20% tăng trưởng & ebit/nim)
    bear_comp = copy.deepcopy(company)
    if isinstance(bear_comp, Company):
        bear_comp.assumptions.revenue_growth = [max(g * 0.8, -0.1) for g in bear_comp.assumptions.revenue_growth]
        bear_comp.assumptions.ebit_margin = [max(m * 0.8, 0.02) for m in bear_comp.assumptions.ebit_margin]
    else:
        bear_comp.assumptions.credit_growth = [max(g * 0.8, 0.02) for g in bear_comp.assumptions.credit_growth]
        bear_comp.assumptions.nim = [max(n * 0.9, 0.015) for n in bear_comp.assumptions.nim]
        
    bear_int, bear_rel = run_valuation_engine(bear_comp)
    bear_blended, _, _ = blend_intrinsic_relative(bear_int, bear_rel, weight_intrinsic, company.current_price)
    
    return {
        "Bull": round(bull_blended, 0),
        "Base": round(base_blended, 0),
        "Bear": round(bear_blended, 0)
    }
