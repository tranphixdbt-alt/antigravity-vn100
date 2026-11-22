"""Tab VN100 (D55): xếp hạng theo upside mô hình + 5 mã tích sản (lọc dữ liệu, ngưỡng, thanh khoản, ngành)."""

from datetime import date

import pandas as pd
import pytest

from valuation.views.vn100_ranking import accumulation_picks, ranking_table

CFG = {
    "blocking_flags": ["NOT_RATED", "UPSIDE_EXTREME_REVIEW"],
    "max_upside_pct": 100,
    "scales": {"min_traded_value_vnd": 10e9},
}
D = date(2026, 10, 9)
LIQ = 50e9  # 50 tỷ/phiên — đạt ngưỡng 10 tỷ


def _row(t, fv, sector, flags=()):
    return {
        "ticker": t,
        "fair_value": fv,
        "sector": sector,
        "flags": list(flags),
        "price": 1,
    }


def test_ranking_table_hand_calculated():
    # Upside = GTHL / giá − 1: AAA 15.000/10.000 = +50%; BBB 22.000/20.000 = +10%;
    # CCC 25.000/10.000 = +150% (> 100% → cần rà soát); DDD chưa định giá; EEE thanh khoản 5 tỷ.
    snap = {
        "rows": [
            _row("BBB", 22000, "X"),
            _row("AAA", 15000, "X"),
            _row("CCC", 25000, "Y"),
            _row("DDD", None, "Y"),
            _row("EEE", 12000, "Z"),
        ]
    }
    market = {
        "AAA": (10000, D, LIQ),
        "BBB": (20000, D, LIQ),
        "CCC": (10000, D, LIQ),
        "DDD": (5000, D, LIQ),
        "EEE": (10000, D, 5e9),
    }
    t = ranking_table(snap, market, CFG).set_index("Mã")
    assert t.loc["AAA", "Upside (%)"] == pytest.approx(50.0)
    assert t.loc["BBB", "Upside (%)"] == pytest.approx(10.0)
    assert list(t.index) == [
        "CCC",
        "AAA",
        "EEE",
        "BBB",
        "DDD",
    ]  # theo upside, chưa định giá cuối
    assert t.loc["CCC", "Hạng"] == 1 and pd.isna(t.loc["DDD", "Hạng"])
    assert t.loc["CCC", "Ghi chú"] == "Upside > 100%: cần rà soát"
    assert t.loc["EEE", "Ghi chú"] == "Thanh khoản < 10 tỷ/phiên"
    assert t.loc["DDD", "Ghi chú"] == "Chưa định giá được"
    assert t.loc["AAA", "Ghi chú"] == ""


def test_data_error_flags_excluded_but_undated_corporate_action_only_warns():
    snap = {
        "rows": [
            _row("AAA", 15000, "X", ["CORPORATE_ACTION_UNDATED"]),
            _row("BBB", 15000, "X", ["NOT_RATED: lý do"]),
            _row(
                "CCC", 15000, "X", ["JV_VALUED_AT_PE"]
            ),  # cờ thông tin, không phải lỗi
        ]
    }
    market = {t: (10000, D, LIQ) for t in ("AAA", "BBB", "CCC")}
    t = ranking_table(snap, market, CFG).set_index("Mã")
    # D86: cổ tức CP/thưởng thiếu GDKHQ chỉ cảnh báo, vẫn được xếp hạng.
    assert t.loc["AAA", "Ghi chú"] == "" and t.loc["AAA", "Hạng"] == 1
    assert t.loc["BBB", "Ghi chú"] == "Lỗi dữ liệu: NOT_RATED"
    assert t.loc["CCC", "Ghi chú"] == ""


def test_accumulation_picks_top_upside_max_two_per_sector():
    # 4 mã ngành X (upside 60/50/40/30) + 2 mã ngành Y (20/10): tối đa 2/ngành →
    # X60, X50, Y20, Y10 (bỏ X40, X30); chỉ 4 mã qua lọc nên trả 4.
    snap = {
        "rows": [_row(f"X{u}", 10000 * (1 + u / 100), "X") for u in (60, 50, 40, 30)]
        + [_row(f"Y{u}", 10000 * (1 + u / 100), "Y") for u in (20, 10)]
    }
    market = {r["ticker"]: (10000, D, LIQ) for r in snap["rows"]}
    picks = accumulation_picks(ranking_table(snap, market, CFG), max_per_sector=2)
    assert list(picks["Mã"]) == ["X60", "X50", "Y20", "Y10"]


# ---------------------------------------------------------------------------
# D99: giá trị hợp lý (FV) của snapshot phải cùng thang giá với giá hiện tại.
# Giá trong DB được điều chỉnh hồi tố khi có cổ tức/chia tách SAU đợt định giá, còn FV trong snapshot
# vẫn ở thang giá cũ. Lỗi thật 20/11/2026: TCB chia cổ tức CP 50% (GDKHQ 29/10) sau đợt 27/10 →
# FV 41.121 (thang cũ, giá 33.800) so với giá 20.600 (thang mới) → upside +99,6% thay vì ~+33%.
# ---------------------------------------------------------------------------
from valuation.views.vn100_ranking import fv_scale_factor, snapshot_closes

RESCALE = {"tolerance": 0.005, "min_factor": 0.2}
CFG_R = {**CFG, "fv_rescale": RESCALE}
SNAP_DATE = "2026-10-26"


def _snap_row(t, fv, snap_price, sector="X"):
    return {
        "ticker": t,
        "fair_value": fv,
        "sector": sector,
        "flags": [],
        "price": snap_price,
        "price_date": SNAP_DATE,
    }


def test_fv_scale_factor_hand_calculated():
    # Thưởng 50%: giá ngày định giá 15.000 (snapshot) → DB điều chỉnh còn 10.000 → k = 2/3.
    assert fv_scale_factor(15000, 10000, **RESCALE) == (
        pytest.approx(2 / 3),
        "ADJUSTED",
    )
    # Lệch ≤ 0,5% (làm tròn, khác nguồn FHSC/VCI) → coi là cùng thang, k = 1.
    assert fv_scale_factor(33800, 33900, **RESCALE) == (1.0, "SAME")
    # Điều chỉnh hồi tố chỉ làm giá cũ GIẢM: k > 1 + dung sai là dữ liệu bất thường, không quy đổi.
    assert fv_scale_factor(33800, 40000, **RESCALE) == (1.0, "INCONSISTENT")
    # k < min_factor (giảm > 5 lần) cũng bất thường.
    assert fv_scale_factor(50000, 5000, **RESCALE) == (1.0, "INCONSISTENT")
    # Thiếu dữ liệu → không quy đổi được, giữ nguyên như trước.
    assert fv_scale_factor(None, 10000, **RESCALE) == (1.0, "UNVERIFIED")
    assert fv_scale_factor(15000, None, **RESCALE) == (1.0, "UNVERIFIED")


def test_ranking_table_rescales_fv_after_stock_dividend():
    # FV 30.000 ở thang cũ (giá 15.000); giá hiện tại 12.500 ở thang mới.
    # Đúng: FV quy đổi = 30.000 × 10.000/15.000 = 20.000 → upside = 20.000/12.500 − 1 = +60%.
    # Lỗi cũ: 30.000/12.500 − 1 = +140% (bị đẩy qua ngưỡng rà soát).
    snap = {"rows": [_snap_row("AAA", 30000, 15000)]}
    market = {"AAA": (12500, D, LIQ)}
    t = ranking_table(snap, market, CFG_R, snap_closes={"AAA": 10000}).set_index("Mã")
    assert t.loc["AAA", "Giá trị hợp lý (đ)"] == pytest.approx(20000)
    assert t.loc["AAA", "Upside (%)"] == pytest.approx(60.0)
    assert t.loc["AAA", "_fv_scale"] == pytest.approx(2 / 3)
    assert t.loc["AAA", "Ghi chú"] == ""


def test_ranking_table_tcb_regression_20261120():
    # Số thật: đợt 20261027T000935 FV 41.121,07 với giá 33.800 (26/10); DB nay ghi 26/10 = 22.530; giá 20.600.
    # Tính tay: 41.121,07 × 22.530/33.800 = 27.409,99 → upside = 27.409,99/20.600 − 1 = +33,06% (lỗi cũ +99,62%).
    snap = {"rows": [_snap_row("TCB", 41121.069451564654, 33800.0, "Ngân hàng")]}
    market = {"TCB": (20600.0, D, LIQ)}
    t = ranking_table(snap, market, CFG_R, snap_closes={"TCB": 22530.0}).set_index("Mã")
    assert t.loc["TCB", "Giá trị hợp lý (đ)"] == pytest.approx(27409.99, abs=0.01)
    assert t.loc["TCB", "Upside (%)"] == pytest.approx(33.06, abs=0.01)


def test_ranking_table_inconsistent_scale_is_flagged_not_silently_used():
    snap = {"rows": [_snap_row("AAA", 30000, 15000)]}
    market = {"AAA": (12500, D, LIQ)}
    t = ranking_table(snap, market, CFG_R, snap_closes={"AAA": 18000}).set_index("Mã")
    assert t.loc["AAA", "Giá trị hợp lý (đ)"] == pytest.approx(30000)  # không quy đổi
    assert t.loc["AAA", "Ghi chú"].startswith("Thang giá lệch đợt định giá")
    assert accumulation_picks(
        ranking_table(snap, market, CFG_R, snap_closes={"AAA": 18000}), 2
    ).empty


def test_ranking_table_same_scale_and_missing_close_unchanged():
    snap = {"rows": [_snap_row("AAA", 15000, 10000), _snap_row("BBB", 15000, 10000)]}
    market = {"AAA": (10000, D, LIQ), "BBB": (10000, D, LIQ)}
    t = ranking_table(snap, market, CFG_R, snap_closes={"AAA": 10020}).set_index("Mã")
    assert t.loc["AAA", "Upside (%)"] == pytest.approx(50.0)  # lệch 0,2% → cùng thang
    assert t.loc["AAA", "_fv_scale"] == 1.0
    assert t.loc["BBB", "Upside (%)"] == pytest.approx(
        50.0
    )  # thiếu giá ngày định giá → giữ nguyên
    assert pd.isna(t.loc["BBB", "_fv_scale"])


def test_snapshot_closes_reads_close_on_each_snapshot_price_date():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from valuation.db.models import PricesDaily
    from valuation.db.session import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    d0, d1 = date(2026, 10, 26), date(2026, 10, 23)
    db.add_all(
        [
            PricesDaily(ticker="AAA", trade_date=d0, close=10000),
            PricesDaily(ticker="AAA", trade_date=date(2026, 10, 27), close=11000),
            PricesDaily(
                ticker="BBB", trade_date=d1, close=5000
            ),  # mã có ngày giá riêng
            PricesDaily(ticker="BBB", trade_date=d0, close=5100),
        ]
    )
    db.commit()
    snap = {
        "rows": [
            {"ticker": "AAA", "price_date": "2026-10-26"},
            {"ticker": "BBB", "price_date": "2026-10-23"},
            {
                "ticker": "CCC",
                "price_date": "2026-10-26",
            },  # không có giá → không có trong kết quả
            {"ticker": "DDD", "price_date": None},
        ]
    }
    assert snapshot_closes(db, snap) == {"AAA": 10000.0, "BBB": 5000.0}
    db.close()
