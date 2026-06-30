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


def valuate(company: Union[Company, CompanyBank], projections=None) -> Dict[str, Any]:
    """
    Định giá 1 doanh nghiệp bằng engine chuẩn (Base case).

    projections: dự phóng cho sẵn (vd analyst đã sửa trên UI). Chỉ dùng cho bank;
    nếu None thì tự forecast. Phi tài chính bỏ qua tham số này.
    """
    from valuation.engine.sector_router import ValuationRouter

    route = ValuationRouter().get_routing(company.ticker)
    weight_intrinsic = route.get("weight_primary", 1.0)

    if isinstance(company, CompanyBank):
        from valuation.engine.forecast_bank import forecast_bank_financials
        from valuation.engine.sensitivity import run_valuation_engine
        from valuation.engine.blend import blend_intrinsic_relative

        if projections is None:
            projections = forecast_bank_financials(company)
        intrinsic_fv, relative_fv = run_valuation_engine(company, projections=projections)
        blended_fv, upside, recommendation = blend_intrinsic_relative(
            intrinsic_fv, relative_fv, weight_intrinsic, company.current_price
        )
        return {
            "blended_fair_value_per_share": blended_fv,
            "intrinsic_fv": intrinsic_fv,
            "relative_fv": relative_fv,
            "weight_intrinsic": weight_intrinsic,
            "upside": upside,
            "recommendation": recommendation,
            "projections": projections,
            "flags": [],
        }

    # Phi tài chính: dispatch theo method (đủ PE/PB/EV_EBITDA/RNAV/SOTP/DCF, giữ flags)
    from valuation.engine.batch import _dispatch_nonfin, _collect_flags
    from valuation.engine.sector_router import route as _route_fn
    plan = _route_fn(company.ticker) or {}
    model, res = _dispatch_nonfin(company, plan.get("method"), plan.get("group"))
    if model is None:
        raise ValueError(f"METHOD_NOT_IMPLEMENTED:{plan.get('method')}")

    blended_fv = float(res["blended_fair_value_per_share"])
    price = company.current_price
    upside = ((blended_fv - price) / price * 100.0) if price else 0.0
    return {
        "blended_fair_value_per_share": blended_fv,
        "intrinsic_fv": blended_fv,
        "relative_fv": res.get("multiples_fvps", blended_fv),
        "weight_intrinsic": weight_intrinsic,
        "upside": upside,
        "recommendation": "MUA" if upside > 15 else ("HOLD" if upside >= 0 else "BÁN"),
        "flags": _collect_flags(model, res),
    }
