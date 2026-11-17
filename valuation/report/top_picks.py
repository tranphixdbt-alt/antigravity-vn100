"""Danh sách tích sản 1–3 năm (D93): chọn mã + độ tin cậy theo quy tắc công khai, không gọi mạng/AI.

Điểm dựa trên điểm hai hồ sơ tích sản có sẵn (`rank_companies`), chuẩn hóa theo phần có dữ liệu
(mọi mã đều thiếu moat/context vì chưa có hồ sơ quản trị đã kiểm chứng → không phạt lệch).
Không phải khuyến nghị đầu tư.
"""

from __future__ import annotations

from typing import Any

from valuation.analysis.investment_ranking import finite
from valuation.engine.flag_descriptions import describe_flags

# Tiêu chí "dữ liệu sạch" = không có cờ mức warning/error của hệ thống (flag_descriptions), trừ cờ gần như
# mã nào cũng có sau mùa BCTC (kỳ mới nạp chưa đối chiếu lại nguồn) — ghi chung ở trang phương pháp.
UNIVERSAL_FLAGS = {"SOURCE_AUDIT_PARTIAL"}
EXCLUDE_FLAGS = {"MATERIAL_EVENT_HOLD"}


def data_warnings(flags: list[str]) -> list[str]:
    return [
        f["code"]
        for f in describe_flags(list(flags))
        if f.get("level") in ("warning", "error")
        and f["code"].split(":", 1)[0] not in UNIVERSAL_FLAGS
    ]


def composite_score(row: dict) -> float | None:
    """Trung bình 2 hồ sơ (thận trọng, tăng trưởng) của điểm ÷ độ phủ × 100."""
    vals = []
    for prof in row.get("profiles", {}).values():
        score, cov = prof.get("score"), prof.get("coverage")
        if not (finite(score) and finite(cov) and cov > 0):
            return None
        vals.append(score / cov * 100)
    return sum(vals) / len(vals) if vals else None


def exclusion_reason(row: dict, cfg: dict) -> str | None:
    """Lý do loại khỏi danh sách (None = được xét). Theo đúng ngưỡng của config xếp hạng."""
    codes = {str(f).split(":", 1)[0] for f in row.get("flags", [])}
    if row.get("error"):
        return "lỗi tạo hồ sơ"
    if composite_score(row) is None:
        return "không đủ cơ sở định giá"
    if codes & (set(cfg["blocking_flags"]) | EXCLUDE_FLAGS):
        return "cờ chặn: " + ", ".join(
            sorted(codes & (set(cfg["blocking_flags"]) | EXCLUDE_FLAGS))
        )
    if any(c.get("severity") == "error" for c in row.get("checks", [])):
        return "kiểm tra dữ liệu báo lỗi"
    up = row.get("upside_pct")
    if not finite(up) or up <= 0:
        return "giá đã vượt giá trị mô hình"
    if up > cfg["max_upside_pct"]:
        return "chênh lệch định giá quá lớn"
    if not row.get("liquidity_ok"):
        return "thanh khoản thấp"
    return None


def select_top(rows: list[dict], cfg: dict, n: int, max_per_sector: int) -> list[dict]:
    """Xếp theo điểm tổng hợp giảm dần; tối đa `max_per_sector` mã mỗi ngành."""
    ranked = sorted(
        (r for r in rows if exclusion_reason(r, cfg) is None),
        key=lambda r: (-composite_score(r), r["ticker"]),  # type: ignore[operator]
    )
    picked: list[dict] = []
    per_sector: dict[str, int] = {}
    for row in ranked:
        sector = row.get("sector") or "Khác"
        if per_sector.get(sector, 0) >= max_per_sector:
            continue
        per_sector[sector] = per_sector.get(sector, 0) + 1
        picked.append(row)
        if len(picked) == n:
            break
    return picked


def confidence(row: dict, consensus: dict[str, Any]) -> dict[str, Any]:
    """Độ tin cậy A/B/C từ 4 tiêu chí; trả kèm từng tiêu chí đạt/không để in ra báo cáo.

    A: ≥3 tiêu chí và mô hình khớp đồng thuận; B: ≥2; C: còn lại.
    """
    fv, med, n = (
        row.get("fair_value"),
        consensus.get("median"),
        consensus.get("count") or 0,
    )
    gap = fv / med - 1 if finite(fv) and finite(med) and med > 0 else None
    sc = row.get("scenarios") or {}
    base, bear, bull = sc.get("Base"), sc.get("Bear"), sc.get("Bull")
    # P/E, EV/EBITDA chỉ có 1 kịch bản (xấu = tốt = cơ sở) → không tính là "kịch bản hẹp".
    spread = (
        (bull - bear) / base
        if all(finite(x) for x in (base, bear, bull)) and base > 0 and bull != bear
        else None
    )
    flags = data_warnings(row.get("flags", []))
    criteria = {
        "coverage": (
            n >= 3,
            f"{n} CTCK theo dõi trong 180 ngày" + (" (≥3)" if n >= 3 else " (<3)"),
        ),
        "agreement": (
            gap is not None and abs(gap) <= 0.20,
            (
                "chưa có giá mục tiêu CTCK để đối chiếu"
                if gap is None
                else f"mô hình lệch đồng thuận {gap:+.0%}"
                + (" (≤20%)" if abs(gap) <= 0.20 else " (>20%)")
            ),
        ),
        "data": (
            not flags,
            "không có cờ dữ liệu" if not flags else "cờ dữ liệu: " + ", ".join(flags),
        ),
        "spread": (
            spread is not None and spread <= 0.40,
            (
                "phương pháp chỉ cho 1 kịch bản"
                if spread is None
                else f"kịch bản xấu–tốt rộng {spread:.0%} giá trị cơ sở"
                + (" (≤40%)" if spread <= 0.40 else " (>40%)")
            ),
        ),
    }
    ok = sum(v[0] for v in criteria.values())
    grade = "A" if ok >= 3 and criteria["agreement"][0] else ("B" if ok >= 2 else "C")
    return {
        "grade": grade,
        "points": ok,
        "gap": gap,
        "spread": spread,
        "criteria": criteria,
    }
