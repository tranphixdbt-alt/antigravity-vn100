"""
Sensitivity & Scenario analysis module — Tính toán ma trận độ nhạy 2 chiều và 3 kịch bản định giá.
"""
import copy
from typing import List, Dict, Any, Tuple, Union
from valuation.models.financials import Company
from valuation.models.financials_bank import CompanyBank
from valuation.engine.blend import blend_intrinsic_relative

def _scenario_config() -> Dict[str, Any]:
    """Đọc config/scenarios.yaml (D30). Thiếu file -> dict rỗng, dùng mặc định cũ."""
    import yaml
    from valuation.config import PROJECT_ROOT
    path = PROJECT_ROOT / "config" / "scenarios.yaml"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _scaled(values, mult, cap=None, floor=None):
    out = []
    for v in values:
        x = v * mult
        if cap is not None:
            x = min(x, cap)
        if floor is not None:
            x = max(x, floor)
        out.append(x)
    return out


def apply_scenario_adjustments(company: Union[Company, CompanyBank], scenario: str) -> Union[Company, CompanyBank]:
    """
    Áp dụng hệ số điều chỉnh giả định cho kịch bản Bull / Bear.

    D30 — ĐÂY LÀ NGUỒN ĐỊNH NGHĨA KỊCH BẢN DUY NHẤT. `run_scenario_analysis` uỷ
    quyền hoàn toàn cho hàm này; trước đó nó nhân bản logic với ngưỡng KHÁC nhau
    nên cùng một mã ra hai kết quả tuỳ đường gọi.

    Bổ sung quan trọng: kịch bản nay biến thiên cả COE, tăng trưởng vĩnh viễn g
    và ROE BỀN VỮNG — không chỉ credit growth/NIM. Bất định thật của định giá
    ngân hàng nằm gần hết ở khối terminal; bản cũ chỉ nhiễu giai đoạn dự phóng
    nên dải Bull-Bear chỉ ±6%, tạo cảm giác an toàn giả.
    """
    import copy
    comp_copy = copy.deepcopy(company)
    if scenario == "Base" or not scenario:
        return comp_copy

    cfg = (_scenario_config().get(scenario) or {})
    a = comp_copy.assumptions
    is_bank = isinstance(comp_copy, CompanyBank)
    sec = (cfg.get("bank") if is_bank else cfg.get("nonfin")) or {}

    if is_bank:
        a.credit_growth = _scaled(a.credit_growth,
                                  sec.get("credit_growth_mult", 1.0),
                                  sec.get("credit_growth_cap"), sec.get("credit_growth_floor"))
        if getattr(a, "deposit_growth", None):
            a.deposit_growth = _scaled(a.deposit_growth,
                                       sec.get("deposit_growth_mult", 1.0),
                                       sec.get("deposit_growth_cap"), sec.get("deposit_growth_floor"))
        a.nim = _scaled(a.nim, sec.get("nim_mult", 1.0),
                        sec.get("nim_cap"), sec.get("nim_floor"))
        a.cir = _scaled(a.cir, sec.get("cir_mult", 1.0),
                        sec.get("cir_cap"), sec.get("cir_floor"))
        # ROE bền vững chi phối giá trị terminal -> BẮT BUỘC phải biến thiên.
        roe_delta = sec.get("sustainable_roe_delta")
        if roe_delta and getattr(a, "sustainable_roe", None):
            a.sustainable_roe = max(0.0, a.sustainable_roe + roe_delta)
    else:
        a.revenue_growth = _scaled(a.revenue_growth,
                                   sec.get("revenue_growth_mult", 1.0),
                                   sec.get("revenue_growth_cap"), sec.get("revenue_growth_floor"))
        a.ebit_margin = _scaled(a.ebit_margin,
                                sec.get("ebit_margin_mult", 1.0),
                                sec.get("ebit_margin_cap"), sec.get("ebit_margin_floor"))

    # Tham số chung cho cả hai loại hình.
    rf_delta = cfg.get("rf_delta")
    if rf_delta:
        a.risk_free_rate = max(0.01, a.risk_free_rate + rf_delta)
    coe_delta = cfg.get("coe_delta")
    if coe_delta and getattr(a, "cost_of_equity", None) is not None:
        a.cost_of_equity = max(0.05, a.cost_of_equity + coe_delta)
    g_delta = cfg.get("terminal_g_delta")
    if g_delta and getattr(a, "terminal_growth_rate", None) is not None:
        a.terminal_growth_rate = max(0.0, a.terminal_growth_rate + g_delta)

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

    D30 — UỶ QUYỀN 100% cho `apply_scenario_adjustments`. Bản cũ nhân bản logic
    kịch bản NGAY TRONG CÙNG FILE nhưng với ngưỡng KHÁC (bank Bull cap credit
    growth 0,30 vs 0,40; Bear floor +0,02 vs -0,05), nên cùng một mã ra hai kết
    quả khác nhau tuỳ đường gọi — và không ai phát hiện vì không có test đối chiếu.
    """
    from valuation.engine.router import ValuationRouter
    route = ValuationRouter().get_routing(company.ticker)
    weight_intrinsic = route.get("weight_primary", 1.0)

    out: Dict[str, float] = {}
    for scenario in ("Bull", "Base", "Bear"):
        comp = apply_scenario_adjustments(company, scenario)
        # COE/g của kịch bản nằm trong assumptions của bản sao -> model tự đọc.
        intrinsic, relative = run_valuation_engine(comp)
        blended, _, _ = blend_intrinsic_relative(
            intrinsic, relative, weight_intrinsic, company.current_price
        )
        out[scenario] = round(blended, 0)
    return out
