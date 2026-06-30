"""
Lõi định giá DUY NHẤT — hợp nhất CLI/batch/Sheets và Streamlit về cùng một engine.

Trước đây có 2 đường tính khác nhau:
  - batch.value_ticker  → VCBValuationModel (bank) / _dispatch_nonfin (phi TC)
  - views/results.py    → forecast → run_valuation_engine → blend_intrinsic_relative

Hai đường cho ra số khác nhau cho cùng một mã (vd ACB: 47,774 vs 68,929). `valuate()`
gói đúng pipeline của Streamlit (engine đầy đủ: forecast nhiều năm + RI/P/B hoặc
DCF/RNAV/SOTP + pha trộn) để mọi consumer gọi chung → cùng một kết quả.
"""
from __future__ import annotations
from typing import Any, Dict, Union

from valuation.models.financials import Company
from valuation.models.financials_bank import CompanyBank


def valuate(company: Union[Company, CompanyBank], projections=None) -> Dict[str, Any]:
    """
    Định giá 1 doanh nghiệp bằng engine chuẩn (Base case), best-of-both theo ngành:
      - Ngân hàng  → forecast_bank + run_valuation_engine (RI + P/B) + blend  [đường Streamlit]
      - Phi tài chính → _dispatch_nonfin (DCF/RNAV/SOTP/PE/PB/EV_EBITDA đầy đủ) [đường batch]

    Lý do: run_valuation_engine xử lý bank rất tốt nhưng KHÔNG bao phủ các phương pháp
    tương đối của phi tài chính (PE/PB) → FPT/SSI ra 0/âm. Ngược lại _dispatch_nonfin
    bao phủ đủ method phi tài chính. Hợp nhất = lấy nhánh tốt nhất cho mỗi ngành.

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
        }

    # Phi tài chính: dùng dispatch theo method (đầy đủ PE/PB/EV_EBITDA/RNAV/SOTP/DCF)
    from valuation.engine.batch import _dispatch_nonfin
    from valuation.engine.sector_router import route as _route_fn
    plan = _route_fn(company.ticker) or {}
    method = plan.get("method")
    group = plan.get("group")
    model, res = _dispatch_nonfin(company, method, group)
    if model is None:
        raise ValueError(f"METHOD_NOT_IMPLEMENTED:{method}")

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
        "flags": res.get("flags", []),
    }
