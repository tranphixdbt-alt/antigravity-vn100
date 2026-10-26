"""Bản tóm tắt tuần vòng học — hàm thuần, số tính tay (docs/PLAN_LEARNING_LOOP.md)."""

import datetime as dt

import pandas as pd
import pytest

from valuation.services import learning_digest as ld


def test_valuation_summary_tinh_tay():
    rows = [
        {"ticker": "A", "group": "NH", "published": True, "synth": False, "fv": 110, "cons_median": 100, "cons_n": 3},
        {"ticker": "B", "group": "X", "published": True, "synth": False, "fv": 70, "cons_median": 100, "cons_n": 2},
        {"ticker": "C", "group": "X", "published": True, "synth": True, "fv": 90, "cons_median": 100, "cons_n": 5},
        {"ticker": "D", "group": "X", "published": True, "synth": False, "fv": 200, "cons_median": 100, "cons_n": 1},
        {"ticker": "E", "group": "X", "published": False, "synth": False, "fv": None, "cons_median": 100, "cons_n": 4},
    ]
    s = ld.valuation_summary(rows)
    # Lệch đo được (≥ 2 CTCK, đã công bố): +10%, −30%, −10% → |lệch| trung vị 10%, có dấu −10%.
    assert (s["total"], s["published"], s["own_model"], s["broker_synth"]) == (5, 4, 3, 1)
    assert s["all"]["n"] == 3 and s["all"]["in15"] == 2 and s["all"]["in25"] == 2
    assert s["all"]["median_abs"] == pytest.approx(0.10) and s["all"]["median_signed"] == pytest.approx(-0.10)
    assert set(s["by_group"]) == {"BROKER_SYNTH", "Ngân hàng", "Mô hình riêng"}


def test_ai_issue_counts_moi_bao_cao_mot_lan():
    idx = [
        {"date": "2026-10-20", "issues": [{"metric": "net_income (2026)"}, {"metric": "Net_Income"}]},
        {"date": "2026-10-25", "issues": [{"metric": "credit_growth"}, {"metric": "net_income"}]},
    ]
    assert ld.ai_issue_counts(idx) == {"net_income": 2, "credit_growth": 1}
    assert ld.ai_issue_counts(idx, since=dt.date(2026, 10, 22)) == {"credit_growth": 1, "net_income": 1}


def test_forward_excess_va_khong_lookahead():
    days = [dt.date(2026, 1, d) for d in (5, 6, 7, 8)]
    close = pd.DataFrame({"A": [100, 110, 121, 130], "B": [100, 100, 100, 100], "C": [100, 90, 95, 99]}, index=days)
    ex = ld.forward_excess(close, dt.date(2026, 1, 5), 2)  # A +21%, B 0, C −5% → trung vị 0
    assert ex.round(4).to_dict() == {"A": 0.21, "B": 0.0, "C": -0.05}
    assert ld.forward_excess(close, dt.date(2026, 1, 7), 2).empty  # chưa đủ 2 phiên phía sau → không dùng


def test_label_stats_tach_trong_ngoai_mau():
    ev = pd.DataFrame({
        "date": ["2025-06-13", "2025-06-13", "2026-05-08"], "ticker": ["A", "B", "A"], "label": ["gom"] * 3,
        "excess_5": [0.02, -0.01, 0.03], "excess_20": [0.05, None, -0.02]})
    st = ld.label_stats(ev).set_index("period")
    assert st.loc["trong mẫu", "n"] == 2 and st.loc["trong mẫu", "hit_5_pct"] == 50.0
    assert st.loc["trong mẫu", "excess_5_mean_pct"] == 0.5 and st.loc["trong mẫu", "n_20"] == 1
    assert st.loc["ngoài mẫu", "hit_20_pct"] == 0.0


def test_week_ends_lay_phien_cuoi_tuan():
    ds = [dt.date(2026, 10, d) for d in (19, 20, 23, 26)]
    assert ld.week_ends(ds, dt.date(2026, 10, 1), dt.date(2026, 10, 31)) == [dt.date(2026, 10, 23), dt.date(2026, 10, 26)]


def test_forward_excess_chi_muc_trung_ngay():
    # Ngày trùng trong chỉ mục (gộp nhiều nguồn) không được làm hỏng vị trí phiên.
    days = [dt.date(2026, 1, 5), dt.date(2026, 1, 5), dt.date(2026, 1, 6), dt.date(2026, 1, 7)]
    close = pd.DataFrame({"A": [99, 100, 110, 120], "B": [100, 100, 100, 100]}, index=days)
    assert ld.forward_excess(close, dt.date(2026, 1, 5), 1).round(4).to_dict() == {"A": 0.05, "B": -0.05}


def test_close_matrix_chi_muc_dong_trung():
    # Hai khung ghép lại có chỉ mục 0,1 lặp → gán cột ngày theo chỉ mục sẽ lệch; close_matrix phải giữ đúng ngày.
    a = pd.DataFrame({"ticker": ["A", "A"], "trade_date": pd.to_datetime(["2026-01-05", "2026-01-06"]), "close": [1.0, 2.0]})
    b = pd.DataFrame({"ticker": ["B", "B"], "trade_date": pd.to_datetime(["2026-01-05", "2026-01-06"]), "close": [3.0, 4.0]})
    m = ld.close_matrix(pd.concat([a, b]))
    assert m.index.tolist() == [dt.date(2026, 1, 5), dt.date(2026, 1, 6)]
    assert m.loc[dt.date(2026, 1, 6)].to_dict() == {"A": 2.0, "B": 4.0}


def test_close_matrix_khung_lon_dung_nhan_ngay():
    # Hồi quy lỗi pandas 2.3.3/Python 3.14: unstack/pivot_table khung ~544×100 cho nhãn ngày sai/lặp.
    days = pd.bdate_range("2024-08-19", periods=544)
    rows = [(t, d, float(i)) for i, d in enumerate(days) for t in (f"T{k:02d}" for k in range(100))]
    m = ld.close_matrix(pd.DataFrame(rows, columns=["ticker", "trade_date", "close"]))
    assert m.shape == (544, 100) and m.index.is_unique and m.index.is_monotonic_increasing
    assert m.index[-1] == days[-1].date() and m.loc[days[300].date(), "T42"] == 300.0
