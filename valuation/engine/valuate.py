"""
Lõi định giá DUY NHẤT — hợp nhất CLI/batch/Sheets và Streamlit về cùng một engine.

Trước đây có 2 đường tính khác nhau cho cùng một mã (vd ACB: 47,774 vs 68,929):
  - batch.value_ticker  → VCBValuationModel (bank) / _dispatch_nonfin (phi TC)
  - views/results.py    → forecast → run_valuation_engine → blend_intrinsic_relative

`valuate()` là lõi chung best-of-both theo ngành:
  - Ngân hàng     → forecast_bank + run_valuation_engine (RI + P/B) + blend
  - Phi tài chính → _dispatch_nonfin (DCF/RNAV/SOTP/PE/PB/EV_EBITDA, giữ cả flags)

Lưu ý: run_valuation_engine (dùng cho ma trận độ nhạy/scenario của UI) cũng đã được
sửa để delegate non-fin sang _dispatch_nonfin → mọi đường ra cùng một con số.
"""
from __future__ import annotations
from typing import Any, Dict, Union

from valuation.models.financials import Company
from valuation.models.financials_bank import CompanyBank
from valuation.engine.decision_engine import InvestmentDecisionMaker
from valuation.engine.sector_router import route as _route_fn

from valuation.models.macro_env import MacroEnvironment


def _review_flags(upside_pct: float) -> list:
    """Cờ review khi upside cực đoan — buộc analyst rà lại giả định thay vì tin mù.

    upside_pct: upside tính theo % (vd 302.8 = +302.8%). Ngưỡng đặt rộng để chỉ
    bắt trường hợp thực sự bất thường (giá hợp lý > 2.5× hoặc < 0.4× thị giá).
    """
    if upside_pct is None:
        return []
    if upside_pct > 150.0:
        return ["UPSIDE_EXTREME_REVIEW"]
    if upside_pct < -60.0:
        return ["DOWNSIDE_EXTREME_REVIEW"]
    return []


def valuate(company: Union[Company, CompanyBank], projections=None, macro_env: MacroEnvironment = None) -> Dict[str, Any]:
    """
    Định giá 1 doanh nghiệp bằng engine chuẩn (Base case).

    projections: dự phóng cho sẵn (vd analyst đã sửa trên UI). Chỉ dùng cho bank;
    nếu None thì tự forecast. Phi tài chính bỏ qua tham số này.
    macro_env: Thông số vĩ mô để điều chỉnh định giá.
    """
    from valuation.engine.sector_router import ValuationRouter

    route = ValuationRouter().get_routing(company.ticker)
    weight_intrinsic = route.get("weight_primary", 1.0)

    # Nâng cấp vĩ mô: Ghi đè giả định ERP (Equity Risk Premium) nếu vĩ mô căng thẳng
    if macro_env is not None and macro_env.is_macro_stressed:
        company.assumptions.erp = macro_env.get_adjusted_crp(company.assumptions.erp)

    if isinstance(company, CompanyBank):
        from valuation.engine.forecast_bank import forecast_bank_financials
        from valuation.engine.sensitivity import run_valuation_engine
        from valuation.engine.blend import blend_intrinsic_relative

        if projections is None:
            projections = forecast_bank_financials(company)
        intrinsic_fv, relative_fv = run_valuation_engine(company, projections=projections)
        blended_fv, upside_val, _ = blend_intrinsic_relative(
            intrinsic_fv, relative_fv, weight_intrinsic, company.current_price
        )
        
        # Decision Engine cho Ngân hàng
        plan = _route_fn(company.ticker) or {}
        business_nature = plan.get("business_nature", "Bank")
        decision_engine = InvestmentDecisionMaker(
            business_nature=business_nature,
            current_price=company.current_price,
            fair_value=blended_fv,
            governance=company.governance,
            macro_env=macro_env
        )
        decision = decision_engine.make_decision()
        
        return {
            "blended_fair_value_per_share": blended_fv,
            "intrinsic_fv": intrinsic_fv,
            "relative_fv": relative_fv,
            "weight_intrinsic": weight_intrinsic,
            "upside": decision["upside"],
            "recommendation": decision["recommendation"],
            "projections": projections,
            "flags": _review_flags(decision["upside"]) + list(getattr(company, "data_flags", []) or []),
            "decision": decision
        }

    # Phi tài chính: dispatch theo method (đủ PE/PB/EV_EBITDA/RNAV/SOTP/DCF, giữ flags)
    from valuation.engine.batch import _dispatch_nonfin, _collect_flags
    plan = _route_fn(company.ticker) or {}
    model, res = _dispatch_nonfin(company, plan.get("method"), plan.get("group"), macro_env=macro_env)
    if model is None:
        raise ValueError(f"METHOD_NOT_IMPLEMENTED:{plan.get('method')}")

    blended_fv = float(res["blended_fair_value_per_share"])

    # Land Bank add-on: cộng thêm giá trị quỹ đất CHƯA phản ánh trong BCTC
    # (nông nghiệp/cao su/KCN...) — độc lập với phương pháp chính. Mặc định 0
    # khi analyst chưa nhập dữ liệu (không bịa số liệu).
    from valuation.engine.land_bank import compute_land_bank_value_per_share
    land_bank = compute_land_bank_value_per_share(company)
    blended_fv += land_bank["land_bank_value_per_share"]

    # Decision Engine cho Phi tài chính
    business_nature = plan.get("business_nature", "Unknown")
    # D28: model tự nhận không đủ cơ sở định giá (proxy lệch phi lý, thiếu dữ
    # liệu cấu trúc tập đoàn...) -> không phát khuyến nghị MUA/BÁN.
    not_rated = bool(res.get("not_rated"))
    decision_engine = InvestmentDecisionMaker(
        business_nature=business_nature,
        current_price=company.current_price,
        fair_value=blended_fv,
        governance=company.governance,
        macro_env=macro_env,
        not_rated=not_rated,
    )
    decision = decision_engine.make_decision()

    return {
        "not_rated": not_rated,
        "blended_fair_value_per_share": blended_fv,
        "intrinsic_fv": blended_fv,
        "relative_fv": res.get("multiples_fvps", blended_fv),
        "weight_intrinsic": weight_intrinsic,
        "upside": decision["upside"],
        "recommendation": decision["recommendation"],
        "flags": _collect_flags(model, res) + land_bank["flags"] + _review_flags(decision["upside"])
                 + list(getattr(company, "data_flags", []) or []),
        "land_bank_npv": land_bank["land_bank_npv"],
        "decision": decision,
        "projections": res.get("forecasts", None)
    }
