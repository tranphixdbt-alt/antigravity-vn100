"""
Blend Valuation module — Pha trộn kết quả định giá và đưa ra khuyến nghị đầu tư.
"""
from typing import Tuple

def blend_intrinsic_relative(
    intrinsic_fv: float, 
    relative_fv: float, 
    weight_intrinsic: float, 
    current_price: float
) -> Tuple[float, float, str]:
    """
    Pha trộn kết quả định giá nội tại và so sánh.
    Trả về: (blended_fair_value, upside, recommendation)
    """
    weight_relative = 1.0 - weight_intrinsic
    blended_fv = (intrinsic_fv * weight_intrinsic) + (relative_fv * weight_relative)
    
    if current_price > 0:
        upside = ((blended_fv - current_price) / current_price) * 100.0
    else:
        upside = 0.0
        
    # Xác định khuyến nghị dựa trên upside
    if upside > 15.0:
        recommendation = "MUA"
    elif upside >= 0.0:
        recommendation = "HOLD"
    else:
        recommendation = "BÁN"
        
    return blended_fv, upside, recommendation
