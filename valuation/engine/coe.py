"""Nguồn sự thật duy nhất cho Cost of Equity (COE) — convention VND-base.

QUYẾT ĐỊNH CHỐT (xem golden rule trong config/defaults.yaml):
    rf  = TPCP VN 10Y (lấy động từ macro_series) — ĐÃ chứa lạm phát + rủi ro
          quốc gia VN.
    erp = mature-market ERP (erp_mature), KHÔNG cộng country risk premium lần
          nữa → chống double-count.
    COE = rf + beta * erp_mature

Trước đây code dùng erp_total (mature + CRP) cộng với rf_VN → double-count CRP,
vi phạm chính golden rule của dự án. File này là chỗ duy nhất quyết định ERP để
mọi nơi (repo, route, ttm_helper) dùng chung.
"""
from __future__ import annotations

from valuation.config import load_defaults

# Equity premium tối thiểu hợp lệ (beta*erp). Dùng cho sanity floor.
# Với convention VND-base (erp_mature ~4.5%, beta 0.5-1.5) premium ~2.2-6.8%.
MIN_EQUITY_PREMIUM = 0.03


def get_erp() -> float:
    """ERP dùng cho COE VND-base = mature-market ERP (KHÔNG gồm CRP)."""
    coe_conv = load_defaults().get("coe_convention", {})
    return float(coe_conv.get("erp_mature", 0.045))


def compute_coe(rf: float, beta: float, erp: float | None = None) -> float:
    """COE = rf + beta * erp. erp mặc định = mature ERP (VND-base)."""
    if erp is None:
        erp = get_erp()
    return rf + beta * erp
