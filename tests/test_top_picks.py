"""Danh sách tích sản (D93): điểm tổng hợp, loại mã, giới hạn ngành, độ tin cậy — số tính tay."""

from __future__ import annotations

import pytest

from valuation.report.top_picks import (
    composite_score,
    confidence,
    exclusion_reason,
    select_top,
)

CFG = {"blocking_flags": ["UPSIDE_EXTREME_REVIEW"], "max_upside_pct": 100}


def _row(ticker: str, sector: str, d: float, g: float, cov: int = 50, **kw) -> dict:
    base = {
        "ticker": ticker,
        "sector": sector,
        "flags": [],
        "checks": [],
        "upside_pct": 30.0,
        "liquidity_ok": True,
        "fair_value": 130.0,
        "profiles": {
            "defensive": {"score": d, "coverage": cov},
            "growth": {"score": g, "coverage": cov},
        },
        "scenarios": {"Base": 130.0, "Bear": 110.0, "Bull": 150.0},
    }
    return {**base, **kw}


def test_composite_normalizes_by_coverage() -> None:
    # Tính tay: (30/50×100 + 40/50×100)/2 = (60 + 80)/2 = 70.
    assert composite_score(_row("A", "X", 30, 40)) == pytest.approx(70.0)
    assert composite_score(_row("A", "X", None, 40)) is None  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("kw", "reason"),
    [
        ({"flags": ["MATERIAL_EVENT_HOLD"]}, "cờ chặn: MATERIAL_EVENT_HOLD"),
        ({"upside_pct": -5.0}, "giá đã vượt giá trị mô hình"),
        ({"upside_pct": 140.0}, "chênh lệch định giá quá lớn"),
        ({"liquidity_ok": False}, "thanh khoản thấp"),
        ({"checks": [{"severity": "error"}]}, "kiểm tra dữ liệu báo lỗi"),
    ],
)
def test_exclusions(kw: dict, reason: str) -> None:
    assert exclusion_reason(_row("A", "X", 30, 30, **kw), CFG) == reason


def test_select_top_caps_sector_and_orders_by_score() -> None:
    rows = [
        _row("B1", "Bank", 45, 45),
        _row("B2", "Bank", 44, 44),
        _row("B3", "Bank", 43, 43),
        _row("T1", "Tech", 30, 30),
        _row("X1", "Bank", 49, 49, upside_pct=-1.0),
    ]
    assert [r["ticker"] for r in select_top(rows, CFG, n=3, max_per_sector=2)] == [
        "B1",
        "B2",
        "T1",
    ]


def test_confidence_grades_checked_by_hand() -> None:
    # FV 130, đồng thuận 120 → lệch +8,3% (≤20%); 4 CTCK; không cờ; (150−110)/130 = 30,8% ≤ 40% → A.
    a = confidence(_row("A", "X", 30, 30), {"median": 120.0, "count": 4})
    assert (
        a["grade"] == "A"
        and a["points"] == 4
        and a["gap"] == pytest.approx(130 / 120 - 1)
    )
    # Lệch +62,5% (FV 130 / 80), 1 CTCK, cờ dữ liệu, kịch bản rộng 30,8% → chỉ 1 tiêu chí → C.
    c = confidence(
        _row("C", "X", 30, 30, flags=["CORPORATE_ACTION_UNDATED"]),
        {"median": 80.0, "count": 1},
    )
    assert c["grade"] == "C" and c["points"] == 1
    # Không có đồng thuận: tối đa B dù các tiêu chí khác đạt.
    b = confidence(_row("B", "X", 30, 30), {"median": None, "count": 0})
    assert b["grade"] == "B" and b["gap"] is None


def test_universal_and_info_flags_do_not_count_as_data_warnings() -> None:
    from valuation.report.top_picks import data_warnings

    flags = [
        "SOURCE_AUDIT_PARTIAL:2026Q3",
        "JV_VALUED_AT_PE",
        "UNEXPLAINED_CURRENT_ASSETS:2026",
    ]
    assert data_warnings(flags) == ["UNEXPLAINED_CURRENT_ASSETS:2026"]


def test_single_scenario_methods_do_not_pass_spread() -> None:
    # P/E: xấu = tốt = cơ sở → không coi là kịch bản hẹp (3 tiêu chí còn lại đạt vẫn ra A).
    row = _row(
        "P", "X", 30, 30, scenarios={"Base": 130.0, "Bear": 130.0, "Bull": 130.0}
    )
    res = confidence(row, {"median": 120.0, "count": 4})
    assert (
        res["spread"] is None
        and res["criteria"]["spread"][0] is False
        and res["points"] == 3
    )
