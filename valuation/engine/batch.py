"""
Batch valuation — định giá router-driven cho toàn VN100.

`value_ticker` là điểm dispatch DUY NHẤT: route(ticker) → đúng model theo bảng CTCK.
Trả về dict chuẩn (method, FV, upside, flags) — dùng cho batch + export Sheets.
Mỗi mã bọc try/except: 1 mã lỗi không làm hỏng cả batch.
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from valuation.engine.sector_router import route
from valuation.data_access.repo import get_latest_price, build_company_data
from valuation.config import load_defaults


def _collect_flags(model, result: Dict[str, Any]) -> List[str]:
    flags = list(getattr(model, "valuation_warnings", []) or [])
    for f in result.get("flags", []) or []:
        if f not in flags:
            flags.append(f)
    return flags


def value_ticker(db: Session, ticker: str) -> Dict[str, Any]:
    """Định giá 1 mã theo đúng phương pháp router. Trả dict chuẩn hoặc {error}."""
    plan = route(ticker)
    if not plan:
        return {"ticker": ticker, "error": "NOT_IN_VN100"}

    method, status, group = plan["method"], plan["status"], plan["group"]
    price = get_latest_price(db, ticker)
    base = {
        "ticker": ticker, "method": method, "status": status,
        "group": group, "verified": plan["verified"], "price": price,
    }
    try:
        if method == "RI_PB":
            from valuation.engine.ttm_helper import (
                build_vcb_current_financials, build_vcb_assumptions_from_history,
            )
            from valuation.engine.models.bank_vcb import VCBValuationModel
            cf = build_vcb_current_financials(db, ticker)
            cf["current_price"] = price
            model = VCBValuationModel(cf, build_vcb_assumptions_from_history(db, ticker))
            res = model.blend_valuation()
        else:
            company = build_company_data(db, ticker, mode="TTM")
            from valuation.models.financials_bank import CompanyBank
            if isinstance(company, CompanyBank):
                return {**base, "error": "BANK_NOT_IN_BANK_TICKERS"}
            model, res = _dispatch_nonfin(company, method, group)
            if model is None:
                return {**base, "error": f"METHOD_NOT_IMPLEMENTED:{method}"}

        fv = float(res["blended_fair_value_per_share"])
        upside = (fv / price - 1.0) if price else None
        return {**base, "fair_value": fv, "upside": upside, "flags": _collect_flags(model, res)}
    except Exception as e:  # 1 mã lỗi không phá batch
        return {**base, "error": f"{type(e).__name__}: {str(e)[:80]}"}


def _dispatch_nonfin(company, method: str, group: Optional[str]):
    """Chọn model phi tài chính theo method. Trả (model, result) hoặc (None, None)."""
    from valuation.engine.models.dcf import DCFValuationModel
    if method == "RNAV":
        from valuation.engine.models.rnav import RNAVValuationModel
        m = RNAVValuationModel.from_pydantic(company)
    elif method == "SOTP":
        from valuation.engine.models.sotp import SOTPValuationModel
        m = SOTPValuationModel.from_pydantic(company)
    elif method == "EV_EBITDA":
        from valuation.engine.models.ev_ebitda import EVEBITDAValuationModel
        m = EVEBITDAValuationModel.from_pydantic(company)
    elif method == "PE":
        from valuation.engine.models.pe_relative import PERelativeValuationModel
        m = PERelativeValuationModel.from_pydantic(company, sector=group)
    elif method == "PB":
        from valuation.engine.models.pb_relative import PBRelativeValuationModel
        m = PBRelativeValuationModel.from_pydantic(company)
    elif method in ("DCF", "DCF_EVEBITDA"):
        m = DCFValuationModel.from_pydantic(company)
        res = m.perform_valuation()
        # ĐIỆN: blend DCF (chủ đạo) + DDM cross-check.
        if group == "Điện":
            from valuation.engine.models.ddm import DDMValuationModel
            w = load_defaults().get("ddm", {}).get("power_dcf_weight", 0.6)
            ddm_fv = DDMValuationModel.from_pydantic(company).perform_valuation()["blended_fair_value_per_share"]
            if ddm_fv > 0:
                res["blended_fair_value_per_share"] = w * res["blended_fair_value_per_share"] + (1 - w) * ddm_fv
                res.setdefault("flags", []).append("DDM_BLEND")
        return m, res
    else:
        return None, None
    return m, m.perform_valuation()


def value_all(db: Session, tickers: List[str] = None) -> List[Dict[str, Any]]:
    """Định giá hàng loạt. Mặc định toàn bộ mã có trong bảng routing (VN100)."""
    if tickers is None:
        from valuation.engine.sector_router import _router
        tickers = sorted(_router().routing_data.keys())
    return [value_ticker(db, t) for t in tickers]
