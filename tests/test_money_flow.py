"""Dòng tiền ngành (D73, docs/PLAN_SECTOR_FLOW.md §8): T1–T15, T19–T21 + đường exact (flow_daily).

Mọi fixture dựng tay; không đọc DB thật. GTGD chuẩn của fixture: 10.000 đ × 10 triệu cp = 100 tỷ.
"""

import copy
import datetime as dt
import json
import math
import re
import subprocess
import sys
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest

from valuation.analysis.money_flow import (
    PRICE_COLS,
    adjust_turnover,
    block_badge,
    block_flags,
    ca_break,
    clean_flows,
    cmf,
    compute_money_flow,
    conclusion,
    context,
    implied_domestic,
    label,
    label_history,
    position_size,
    sector_table,
    stock_events,
    top_impact,
    votes,
)
from valuation.config import load_defaults

CFG = copy.deepcopy(load_defaults()["money_flow"])
# Ghim các ngưỡng mà ca tính tay dựa vào (giá trị D73 đã duyệt).
CFG |= {
    "window": 20,
    "min_coverage": 0.5,
    "session_close": "15:00",
    "max_flow_gaps": 0,
    "net_identity_rel_tol": 0.001,
    "small_sector_n": 3,
    "heat_clip": 0.05,
    "big_block_adtv_share": 0.5,
    "cross_foreign_ratio": 0.8,
    "conclusion_max_words": 30,
    "etf_review_dates": [],
}
CFG["signal"] |= {
    "foreign_band": 0.02,
    "same_sign_share": 0.6,
    "min_valid_sessions": 15,
    "prop_band": 0.005,
    "prop_min_session_cov": 0.75,
    "cmf_window": 20,
    "cmf_band": 0.05,
    "cmf_max_flat": 2,
    "sideways_band": 0.05,
    "label_history": 10,
    "rvol_base": 60,
    "rvol_min": 1.3,
}
BN = 1e9
NAN = math.nan
END = "2026-10-22"  # thứ Năm
VN = ZoneInfo("Asia/Ho_Chi_Minh")
NOW = dt.datetime(2026, 10, 22, 20, 0, tzinfo=VN)


def _row(t, d, f, p, close=10_000.0, vol=1e7, high=10_500.0, low=9_500.0):
    """Một dòng prices; F/P (VND) tách mua/bán sao cho net = mua − bán, KL = GT / close."""
    r = {"ticker": t, "trade_date": d, "open": close, "high": high, "low": low}
    r |= {"close": close, "volume": vol}
    for k, x in (("f", f), ("p", p)):
        b, s = (max(x, 0.0), max(-x, 0.0)) if not math.isnan(x) else (NAN, NAN)
        r |= {f"{k}_buy_val": b, f"{k}_sell_val": s, f"{k}_net_val": x}
        r |= {f"{k}_buy_vol": b / close, f"{k}_sell_vol": s / close}
    return r


def prices(f, p=None, ticker="AAA", end=END, **kw):
    """Khung prices 1 mã, len(f) phiên kết thúc ở `end`."""
    days = pd.bdate_range(end=end, periods=len(f))
    p = [NAN] * len(f) if p is None else p
    return pd.DataFrame([_row(ticker, d, a, b, **kw) for d, a, b in zip(days, f, p)])


def window(f, p=None, excl=None, gtgd=100 * BN, close=None):
    """Khung cửa sổ cho votes(): GTGD 100 tỷ/phiên, CMF = 0."""
    n = len(f)
    return pd.DataFrame(
        {
            "gtgd": gtgd,
            "f": f,
            "p": [NAN] * n if p is None else p,
            "excl": [False] * n if excl is None else excl,
            "high": 10_500.0,
            "low": 9_500.0,
            "close": 10_000.0 if close is None else close,
            "vol_adj": 1e7,
        },
        index=pd.bdate_range(end=END, periods=n),
    )


def _strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for k, v in x.items():
            if k != "series":
                yield from _strings(v)
    elif isinstance(x, (list, tuple)):
        for v in x:
            yield from _strings(v)


# ---------- T1 ----------
def test_t1_clean_drops_weekend_and_junk_and_checks_net_identity():
    df = pd.concat(
        [prices([BN] * 3, ticker=t, end="2026-10-21") for t in ("AAA", "BBB", "CCC")]
    )
    sunday = _row("AAA", pd.Timestamp("2026-10-18"), BN, NAN)  # CN
    junk = _row("AAA", pd.Timestamp("2026-10-22"), BN, NAN)  # 1/3 mã < 50% → rác
    bad = _row("BBB", pd.Timestamp("2026-10-20"), BN, NAN) | {"f_net_val": 2 * BN}
    zero = _row("CCC", pd.Timestamp("2026-10-20"), 0.0, NAN)
    df = df[~((df.ticker.isin(["BBB", "CCC"])) & (df.trade_date == "2026-10-20"))]
    df = pd.concat([df, pd.DataFrame([sunday, junk, bad, zero])])
    out, meta = clean_flows(df, CFG, NOW)
    assert meta["dropped"]["weekend"] == 1
    assert meta["dropped"]["non_session"] == 1
    assert list(meta["sessions"].strftime("%d/%m")) == ["19/10", "20/10", "21/10"]
    assert "2026-10-22" not in set(out.trade_date.dt.strftime("%Y-%m-%d"))
    on20 = out[out.trade_date == "2026-10-20"].set_index("ticker")["f_net_val"]
    assert math.isnan(on20["BBB"])  # net ≠ mua − bán → NaN
    assert on20["CCC"] == 0.0  # mua = bán = 0 → 0, không NaN
    assert meta["dropped"]["f_identity_nan"] == 1


# ---------- T2 ----------
def test_t2_block_flag_uses_foreign_plus_prop_sum():
    df = pd.DataFrame(
        [
            {"f_buy_vol": 600e3, "f_sell_vol": 0, "p_buy_vol": 500e3, "p_sell_vol": 0},
            # MCH 09/10 dựng tay (số prices_daily)
            {
                "f_buy_vol": 359_173,
                "f_sell_vol": 64_300_671,
                "p_buy_vol": 112_800,
                "p_sell_vol": 527_700,
                "f_buy_val": 51_257_259_000,
                "f_sell_val": 9_644_905_460_000,
                "p_buy_val": 16_146_760_000,
                "p_sell_val": 75_336_310_000,
                "volume": 804_200,
                "close": 143_000,
            },
            {"f_buy_vol": 600e3, "f_sell_vol": 0, "p_buy_vol": NAN, "p_sell_vol": NAN},
        ]
    )
    df["volume"] = df["volume"].fillna(1e6)
    df["close"] = df["close"].fillna(10_000.0)
    out = block_flags(df, CFG)
    # Fb 600k + Pb 500k = 1,1 triệu > 1,0 triệu → cờ; cận dưới 100k (chỉ ngoại: 600k < 1 triệu → không).
    assert out.loc[0, "block"] and out.loc[0, "lb_vol"] == 100e3
    assert out.loc[1, "block"]
    assert out.loc[1, "lb_vol"] == 64_300_671 + 527_700 - 804_200  # 64.024.171
    # GT ước = cận dưới × VWAP phía bán (F+P) ≈ 9.600 tỷ (thực tế VCI 9.641 tỷ)
    assert abs(out.loc[1, "est_val"] / BN - 9_600) < 1
    assert out.loc[1, "form"] == "ngoại bán"
    # Pb NULL = 0 chỉ trong cờ: 600k < 1 triệu → không cờ; cột gốc vẫn NULL.
    assert not out.loc[2, "block"] and math.isnan(df.loc[2, "p_buy_vol"])


# ---------- T3 ----------
def test_t3_flow_date_backs_off_partial_today_dropped_gap_and_provisional_prop():
    a = prices([BN] * 21, end="2026-10-22", ticker="AAA")
    b = prices([BN] * 21, end="2026-10-22", ticker="BBB")
    df = pd.concat([a, b], ignore_index=True)
    last = df.trade_date == "2026-10-22"
    df.loc[last, ["f_net_val", "f_buy_val", "f_sell_val"]] = NAN  # phiên cuối thiếu F
    _, meta = clean_flows(df, CFG, NOW)
    assert meta["price_date"] == pd.Timestamp("2026-10-22")
    assert meta["flow_date"] == pd.Timestamp("2026-10-21")

    # Phiên hôm nay trước 15:00 bị bỏ.
    _, meta = clean_flows(df, CFG, dt.datetime(2026, 10, 22, 14, 0, tzinfo=VN))
    assert meta["dropped"]["today_partial"] == 2
    assert meta["price_date"] == pd.Timestamp("2026-10-21")

    # 1 phiên thủng → báo và phiếu Ngoại ◌.
    g = prices([BN] * 20)
    g.loc[5, ["f_net_val", "f_buy_val", "f_sell_val", "f_buy_vol", "f_sell_vol"]] = NAN
    h = prices([BN] * 20, ticker="BBB")
    res = compute_money_flow(pd.concat([g, h]), None, None, {}, CFG, NOW)
    fv = res["tickers"]["AAA"]["votes"]["foreign"]
    assert fv["vote"] is None and "1 phiên thủng" in fv["reason"]
    assert res["tickers"]["AAA"]["label"]["code"] == "chua_du"

    # P của phiên hôm nay là "tạm": không vào phiếu.
    g = prices([BN] * 20, p=[BN] * 20)
    res = compute_money_flow(
        g, None, None, {}, CFG, dt.datetime(2026, 10, 22, 16, 0, tzinfo=VN)
    )
    tk = res["tickers"]["AAA"]
    assert tk["votes"]["prop"]["n"] == 19
    assert res["meta"]["provisional_prop"] == "2026-10-22"
    assert any("tự doanh 22/10 là số tạm" in b for b in tk["badges"])


# ---------- T4 ----------
@pytest.mark.parametrize(
    "f, vote, r",
    [
        ([6 * BN] * 14 + [-BN] * 6, 1, 78 / 2000),  # 3,9%, 14/20 ≥ 60%
        ([2 * BN] * 13 + [-BN] * 7, 0, 19 / 2000),  # 0,95% < 2%
        ([10 * BN] * 11 + [-30 / 9 * BN] * 9, 0, 0.04),  # 4% nhưng 11/20 < 60%
        ([-6 * BN] * 14 + [BN] * 6, -1, -78 / 2000),  # đối xứng
    ],
)
def test_t4_foreign_vote_hand_calculated(f, vote, r):
    v = votes(window(f), CFG)["foreign"]
    assert v["vote"] == vote
    assert v["value"] == pytest.approx(r)


def test_t4_band_boundary_passes():
    # 12 × 5 tỷ − 8 × 2,5 tỷ = 40 tỷ / 2.000 tỷ = đúng 2%; 12/20 = đúng 60% → +1.
    v = votes(window([5 * BN] * 12 + [-2.5 * BN] * 8), CFG)["foreign"]
    assert v["value"] == 0.02 and v["vote"] == 1


# ---------- T5 ----------
def _t5_prices(extra_old=False):
    f = [-9_000 * BN] + [6 * BN] * 13 + [-BN] * 6
    if extra_old:
        f = [500 * BN, *f]
    return prices(f, high=10_000.0, low=9_000.0)  # close = high → CMF +1


def test_t5_block_session_excluded_in_loai_and_total_only_in_gom():
    res = compute_money_flow(_t5_prices(), None, None, {}, CFG, NOW)
    tk = res["tickers"]["AAA"]
    fv = tk["votes"]["foreign"]
    assert fv["n"] == 19 and fv["pos"] == 13
    assert fv["value"] == pytest.approx(72 / 1900)  # ≈ 3,8%
    assert fv["vote"] == 1
    assert tk["flows"]["20"]["loai"]["f"] == pytest.approx(72 * BN)
    assert tk["flows"]["20"]["gom"] == {"f": pytest.approx(-8_928 * BN), "p": None}
    assert any(b.startswith("1 phiên thỏa thuận") for b in tk["badges"])
    gom = res["modes"]["gom"]
    assert gom["totals"]["20"]["f"] == pytest.approx(-8_928 * BN)
    assert gom["sectors"][0]["r_f"] is None and gom["sectors"][0]["heat"] is None
    # 21 phiên: W = 20 không kéo phiên thứ 21 vào.
    res21 = compute_money_flow(_t5_prices(extra_old=True), None, None, {}, CFG, NOW)
    assert res21["tickers"]["AAA"]["flows"]["20"]["loai"]["f"] == pytest.approx(72 * BN)
    assert res21["tickers"]["AAA"]["votes"]["foreign"]["n"] == 19


# ---------- T6 ----------
def test_t6_prop_ratio_uses_only_sessions_with_numbers():
    v = votes(window([0.0] * 20, p=[BN] * 15 + [NAN] * 5), CFG)["prop"]
    assert v["value"] == pytest.approx(15 / 1500)  # 1%, không phải 15/2.000
    assert v["coverage"] == 0.75 and v["vote"] == 1
    v = votes(window([0.0] * 20, p=[BN] * 14 + [NAN] * 6), CFG)["prop"]
    assert v["vote"] is None and "14/20" in v["reason"]


# ---------- T7 ----------
def test_t7_cmf_true_range_and_flat_sessions():
    NA = [NAN] * 3
    h, low, c, v = [10, 10, 10], [8, 8, 8], [10, 8, 9.5], [100, 100, 200]
    val, flat = cmf(
        h, low, c, v, NA
    )  # không có C_{t−1} → như CMF gốc: MFM +1, −1, +0,5
    assert val == pytest.approx((100 - 100 + 100) / 400) and flat == 0
    val, flat = cmf(h + [10], low + [10], c + [10], v + [500], NA + [10])  # đứng giá
    assert val == pytest.approx(0.25) and flat == 1
    # tính tay (D76): trần trắng bên H=L=C=11, C_{t−1}=10 → TRH 11, TRL 10 → MFM = +1 (CMF gốc: loại)
    assert cmf([11], [11], [11], [100], [10]) == (pytest.approx(1.0), 0)
    # nhảy giảm, đóng cửa ở đỉnh phiên: H 9, L 8,5, C 9, C_{t−1} 10 → ((9−8,5) − (10−9)) / 1,5 = −1/3
    assert cmf([9], [8.5], [9], [100], [10])[0] == pytest.approx(
        -1 / 3
    )  # CMF gốc ra +1
    w = window([0.0] * 20)
    w.iloc[:3, w.columns.get_loc("high")] = (
        10_000.0  # 3 phiên đứng giá: cao = thấp = đóng = phiên trước
    )
    w.iloc[:3, w.columns.get_loc("low")] = 10_000.0
    vt = votes(w, CFG)
    assert vt["pv"]["vote"] is None and "3 phiên đứng giá" in vt["pv"]["reason"]
    assert label(vt)["code"] == "chua_du"


def test_t7_cmf_band_boundary():
    w = window([0.0] * 20)
    w["high"], w["low"], w["close"] = 10.0, 0.0, 5.25  # MFM đúng 0,05
    assert votes(w, CFG)["pv"]["vote"] == 1


# ---------- T8 ----------
def _v(F, A, P, rf=0.0):
    def mk(x, name):
        return {"vote": x, "value": rf, "reason": None if x is not None else "thiếu",
                "chip": f"{name} {x}"}  # fmt: skip

    return {"foreign": mk(F, "Ngoại"), "pv": mk(A, "Giá-KL"), "prop": mk(P, "Tự doanh")}


@pytest.mark.parametrize(
    "F, A, P, code, reason",
    [
        (1, 1, None, "gom", "đủ phiếu"),
        (1, 0, 1, "gom", "đủ phiếu"),
        (0, 1, 1, "trung_tinh", "chưa đủ mạnh"),  # Q3: bắt buộc phiếu Ngoại (R_F +0,5%)
        (0, 0, 1, "trung_tinh", "chưa đủ mạnh"),
        (1, -1, 1, "trung_tinh", "lẫn lộn"),
        (-1, -1, 1, "xa", "đủ phiếu"),  # tự doanh không chặn được (FPT)
        (1, 1, -1, "gom", "đủ phiếu"),  # DCM
        (None, 1, 1, "chua_du", "thiếu dữ liệu"),
        (1, None, 1, "chua_du", "thiếu dữ liệu"),
        (1, 0, 0, "trung_tinh", "chưa đủ mạnh"),
    ],
)
def test_t8_label_rules(F, A, P, code, reason):
    lab = label(_v(F, A, P, rf=0.005))
    assert lab["code"] == code and lab["reason_code"] == reason


def test_t8_zero_foreign_with_negative_ratio_is_neutral():
    assert label(_v(0, 1, 1, rf=-0.005))["code"] == "trung_tinh"


# ---------- T9 ----------
@pytest.mark.parametrize(
    "ret, text",
    [
        (0.06, "giá đã tăng 6,0%"),
        (0.02, "giá đi ngang (+2,0%)"),
        (0.05, "giá đi ngang (+5,0%)"),
        (-0.05, "giá đi ngang (−5,0%)"),
        (-0.08, "giá đã giảm 8,0%"),
        (None, "chưa đủ 20 phiên giá"),
    ],
)
def test_t9_context_only_describes_price(ret, text):
    s = context(ret, CFG)
    assert s == text and "mua" not in s


# ---------- T10 ----------
def _stats():
    rows = [
        # ngành X (2 mã): F −1,5 −0,51 = −2,01 tỷ trên GTGD 1 tỷ → −201%
        (
            "A",
            "X",
            "xa",
            -1.5 * BN,
            0.6 * BN,
            0.1 * BN,
            0.6 * BN,
            -1.5 * BN,
            0.1 * BN,
            0,
        ),
        ("B", "X", "trung_tinh", -0.51 * BN, 0.4 * BN, NAN, 0.0, -0.51 * BN, NAN, 1),
        ("C", "Y", "gom", 3 * BN, 100 * BN, BN, 80 * BN, 3 * BN, BN, 0),
        ("D", "Y", "trung_tinh", BN, 100 * BN, NAN, 0.0, -5 * BN, NAN, 0),
        ("E", "Y", "trung_tinh", 0.0, 100 * BN, 0.0, 70 * BN, 0.0, 0.0, 0),
    ]
    cols = ["ticker", "sector", "label_code", "f_loai", "g_loai", "p_loai", "gp_loai"]
    cols += ["f_gom", "p_gom", "gaps"]
    st = pd.DataFrame(rows, columns=cols).set_index("ticker")
    st["rel"] = [0.01, -0.02, 0.03, 0.0, -0.01]
    return st


def test_t10_sector_table_hand_calculated():
    rows = sector_table(_stats(), CFG, "loai")
    y, x = rows
    assert [r["sector"] for r in rows] == ["Y", "X"]  # n < 3 xuống cuối
    assert x["f"] == pytest.approx(-2.01 * BN) and x["r_f"] == pytest.approx(-2.01)
    assert x["heat"] == -0.05  # màu cắt ở −5%, chữ vẫn là số thật
    assert x["p"] == pytest.approx(0.1 * BN) and x["p_cov"] == pytest.approx(0.6)
    assert x["p_dim"] is True  # 60% < 75%
    assert x["label_count"] == "0 ▲ · 1 ▼ / 2" and x["small"]
    assert x["dominant"] == "A" and x["dominant_share"] == pytest.approx(1.5 / 2.01)
    # độ rộng tính tay: Y Loại C +3, D +1, E 0 → 2/3 mua ròng; X: A −1,5, B −0,51 → 0/2
    assert (y["breadth_pos"], y["breadth_n"], x["breadth_pos"], x["breadth_n"]) == (
        2,
        3,
        0,
        2,
    )
    y_gom = next(r for r in sector_table(_stats(), CFG, "gom") if r["sector"] == "Y")
    assert (y_gom["breadth_pos"], y_gom["breadth_n"]) == (1, 3)  # Gồm: C +3, D −5, E 0
    assert set(x["flags"]) == {"ít mã", "dòng tiền thủng"}
    assert y["r_f"] == pytest.approx(4 / 300) and y["rs20"] == pytest.approx(0.0)
    assert "đổi dấu Gồm/Loại" in y["flags"]  # Loại +4 tỷ, Gồm −2 tỷ
    s = conclusion(rows, 2 * BN, {"gom": 1, "xa": 1}, CFG, "loai")
    assert "X" not in s.split("·")[1] and "mua mạnh Y" in s
    assert "không ngành nào bán ròng" in s


# ---------- T11 ----------
def test_t11_big_block_badge_estimate_and_cross_foreign():
    b = block_badge("2026-10-09", 50e3, 0.5 * BN, False, "ngoại bán", BN, CFG)
    assert b is not None and "GT ước ~0,5 tỷ" in b and "KL ≥ 50 nghìn cp" in b
    assert not re.search(r"≥[^,·]*tỷ", b)
    assert block_badge("2026-10-09", 50e3, 0.49 * BN, False, "x", BN, CFG) is None
    base = {"p_buy_vol": 0, "p_sell_vol": 0, "p_buy_val": 0, "p_sell_val": 0}
    df = pd.DataFrame(
        [
            # cận dưới 50k; VWAP danh nghĩa 10.000 (close điều chỉnh 8.000 không dùng)
            base | {"f_buy_vol": 0, "f_sell_vol": 1.05e6, "f_buy_val": 0,
                    "f_sell_val": 1.05e10, "volume": 1e6, "close": 8_000.0},
            base | {"f_buy_vol": 7.95e6, "f_sell_vol": 7.95e6, "f_buy_val": 7.95e10,
                    "f_sell_val": 7.95e10, "volume": 1e6, "close": 10_000.0},
            base | {"f_buy_vol": 1e6, "f_sell_vol": 23e6, "f_buy_val": 1e10,
                    "f_sell_val": 2.3e11, "volume": 1e6, "close": 10_000.0},
        ]
    )  # fmt: skip
    out = block_flags(df, CFG)
    assert out.loc[0, "est_val"] == pytest.approx(0.5 * BN)
    assert out.loc[1, "form"] == "ngoại↔ngoại"
    assert out.loc[2, "form"] == "ngoại bán"


# ---------- T12 ----------
def test_t12_implied_domestic():
    d = implied_domestic(pd.Series([-100.0, -100.0]), pd.Series([30.0, NAN]))
    assert d.iloc[0] == 70.0 and math.isnan(d.iloc[1])


# ---------- T13 ----------
def test_t13_conclusion_format_words_and_empty_state():
    rows = [
        {"sector": "Dầu khí", "small": False, "f": 406 * BN, "r_f": 0.026},
        {"sector": "Xây dựng", "small": False, "f": 60 * BN, "r_f": 0.016},
        {"sector": "Vật liệu xây dựng", "small": False, "f": -9 * BN, "r_f": -0.01},
        {"sector": "Bán lẻ", "small": False, "f": -1697 * BN, "r_f": -0.143},
        {"sector": "Du lịch", "small": True, "f": 50 * BN, "r_f": 0.119},
    ]
    s = conclusion(rows, -8_520 * BN, {"gom": 4, "xa": 23}, CFG, "loai")
    assert s.startswith("20 phiên, loại thỏa thuận: ngoại bán ròng 8.520 tỷ")
    assert "Du lịch" not in s and "dấu hiệu: 4 gom, 23 xả" in s
    assert len([w for w in s.split() if w != "·"]) <= CFG["conclusion_max_words"]
    assert conclusion([], None, {}, CFG, "loai").endswith(
        "chưa đủ dữ liệu dòng tiền ngành để tóm tắt."
    )


def test_t13_dynamic_strings_clean():
    df = pd.concat(
        [
            _t5_prices(),
            prices([-6 * BN] * 14 + [BN] * 6, p=[BN] * 20, ticker="BBB", low=10_000.0),
            prices([BN] * 20, ticker="CCC"),
        ]
    )
    res = compute_money_flow(df, None, None, {"AAA": "X", "BBB": "X"}, CFG, NOW)
    json.dumps(res, ensure_ascii=False)  # JSON được
    texts = list(_strings(res))
    assert texts
    for s in texts:
        low = s.lower()
        assert "nan" not in low.split() and "none" not in low
        assert not any(ph in low for ph in CFG["forbidden_phrases"]), s
    assert "mua ròng" in " ".join(texts) or "bán ròng" in " ".join(texts)


# ---------- T14 ----------
def test_t14_label_history_start_of_current_run():
    days = [d.date().isoformat() for d in pd.bdate_range(end=END, periods=10)]
    hist = [(d, "trung_tinh" if i < 6 else "gom") for i, d in enumerate(days)]
    assert label_history(hist) == (days[6], False)
    assert label_history([(d, "xa") for d in days]) == (days[0], True)


# ---------- T15 ----------
def test_t15_position_size():
    assert position_size(50_000_000, 0.02, 25_000, 20_000, 100) == 200
    assert position_size(100_000_000, 0.01, 23_000, 20_000, 100) == 300  # 333,3 → 300
    with pytest.raises(ValueError):
        position_size(50_000_000, 0.02, 20_000, 20_000, 100)


# ---------- T19 ----------
def _actions(rows):
    cols = ["ticker", "event_type", "ex_right_date", "record_date"]
    cols += ["announcement_date", "exercise_ratio"]
    return pd.DataFrame(rows, columns=cols)


def test_t19_adjusted_turnover_bonus_share():
    df = prices([0.0] * 10, close=52_000.0)
    days = df.trade_date
    ev = stock_events(_actions([("AAA", "BONUS_SHARE", days[9], None, days[0], 0.5)]))
    out = adjust_turnover(df, ev)
    assert (out["gtgd_est"].iloc[:9] == 78_000.0 * 1e7).all()  # phiên 1–9: 52.000 × 1,5
    assert out["gtgd_est"].iloc[9] == 52_000.0 * 1e7
    # cùng ngày 5% + 25% → cộng tỷ lệ (1,30), không nhân (1,3125)
    ev2 = stock_events(
        _actions(
            [
                ("AAA", "BONUS_SHARE", days[5], None, days[0], 0.05),
                ("AAA", "STOCK_DIVIDEND", days[5], None, days[0], 0.25),
                ("AAA", "STOCK_DIVIDEND", days[5], None, days[0], 0.25),  # trùng nguồn
            ]
        )
    )
    assert adjust_turnover(df, ev2)["factor"].iloc[0] == pytest.approx(1.30)


@pytest.mark.parametrize(
    "event, word",
    [
        (("RIGHTS_ISSUE", "2026-10-15", "2026-10-16", "2026-10-01", 0.2), "quyền mua"),
        (("STOCK_DIVIDEND", None, None, "2026-10-12", 0.1), "chưa rõ"),
    ],
)
def test_t19_unadjustable_event_blocks_foreign_and_prop(event, word):
    df = prices([BN] * 20, p=[BN] * 20)
    acts = _actions([("AAA", *event)])
    tk = compute_money_flow(df, None, acts, {}, CFG, NOW)["tickers"]["AAA"]
    assert tk["votes"]["foreign"]["vote"] is None
    assert tk["votes"]["prop"]["vote"] is None
    assert any(word in b for b in tk["badges"])
    assert tk["label"]["code"] == "chua_du"


# ---------- T20 ----------
def test_t20_gap_vs_block_and_min_valid_sessions():
    v = votes(window([BN] * 19 + [NAN]), CFG)["foreign"]
    assert v["gaps"] == 1 and v["vote"] is None
    v = votes(window([BN] * 20, excl=[True] * 6 + [False] * 14), CFG)["foreign"]
    assert v["gaps"] == 0 and v["n"] == 14  # phiên thỏa thuận ≠ thủng
    assert v["vote"] is None and "14 phiên hợp lệ" in v["reason"]


# ---------- T21 ----------
def test_t21_gom_mode_has_only_absolute_totals_and_same_labels():
    res = compute_money_flow(_t5_prices(), None, None, {"AAA": "X"}, CFG, NOW)
    for r in res["modes"]["gom"]["sectors"]:
        assert all(r[k] is None for k in ("r_f", "heat", "r_p", "p_cov", "p_dim"))
    assert res["modes"]["loai"]["sectors"][0]["r_f"] is not None
    assert set(res["tickers"]["AAA"]["flows"]["20"]["gom"]) == {"f", "p"}
    assert (
        res["tickers"]["AAA"]["label"]["code"] == "gom"
    )  # nhãn duy nhất, tính ở chế độ Loại
    assert res["label_counts"] == {"gom": 1}  # một bộ đếm nhãn cho cả 2 chế độ


# ---------- đường exact (flow_daily, B1) ----------
def _mch(room=1e6, total_room=1e8):
    f = [BN] * 20
    df = prices(
        f, ticker="MCH", close=143_000.0, vol=800_000.0, high=144_000.0, low=141_000.0
    )
    i = int(np.flatnonzero(df.trade_date == "2026-10-09")[0])
    df.loc[i, ["f_sell_vol", "f_sell_val", "f_net_val"]] = [
        64_300_671,
        9_644_905_460_000,
        -9_593_648_201_000,
    ]
    df.loc[i, ["f_buy_vol", "f_buy_val"]] = [359_173, 51_257_259_000]
    ex = pd.DataFrame(
        {
            "ticker": "MCH",
            "trade_date": df.trade_date,
            "source": "VCI",
            "matched_val": 143_000.0 * 800_000.0,
            "matched_vol": 800_000.0,
            "deal_vol": 0.0,
            "deal_val": 0.0,
            "fr_net_match_val": f,
            "fr_net_deal_val": 0.0,
            "fr_buy_deal_vol": 0.0,
            "fr_sell_deal_vol": 0.0,
            "fr_current_room": room,
            "fr_total_room": total_room,
            "prop_net_match_val": NAN,
            "prop_net_deal_val": NAN,
            "is_final": True,
            "fetched_at": "2026-10-22T18:00:00",
            "batch_id": "b1",
            "quality_flags": None,
        }
    )
    ex.loc[i, ["deal_vol", "deal_val", "fr_net_match_val", "fr_net_deal_val"]] = [
        64_274_571,
        9_641.19 * BN,
        47.54 * BN,
        -9_641.19 * BN,
    ]
    ex.loc[i, "fr_sell_deal_vol"] = 64_274_571
    return df, ex


def test_exact_path_mch_uses_matched_foreign_and_exact_deal_badge():
    df, ex = _mch()
    tk = compute_money_flow(df, ex, None, {}, CFG, NOW)["tickers"]["MCH"]
    fv = tk["votes"]["foreign"]
    assert fv["n"] == 20  # không loại cả phiên 09/10
    assert fv["value"] == pytest.approx((19 + 47.54) * BN / (20 * 143_000 * 800_000))
    assert tk["source"] == "exact"
    assert tk["flows"]["20"]["gom"]["f"] == pytest.approx((19 + 47.54 - 9_641.19) * BN)
    big = [b for b in tk["badges"] if b.startswith("Thỏa thuận lớn 09/10")]
    assert big == ["Thỏa thuận lớn 09/10: KL 64,3 triệu cp, GT 9.641 tỷ, ngoại bán"]
    # Đường A trên cùng prices: loại cả phiên, GT chỉ là ước.
    tka = compute_money_flow(df, None, None, {}, CFG, NOW)["tickers"]["MCH"]
    assert tka["votes"]["foreign"]["n"] == 19 and tka["source"] == "A"
    assert any("GT ước ~" in b for b in tka["badges"])


def test_meta_exact_date_is_last_flow_daily_session_with_foreign():
    """D128: dòng trạng thái nói flow_daily chỉ có tới ngày nào (job tắt từ D97), không ghi "job hằng ngày"."""
    df, ex = _mch()
    last = pd.Timestamp(ex["trade_date"].max())
    ex.loc[pd.to_datetime(ex["trade_date"]) == last, "fr_net_match_val"] = NAN
    meta = compute_money_flow(df, ex, None, {}, CFG, NOW)["meta"]
    want = pd.to_datetime(ex.loc[ex["fr_net_match_val"].notna(), "trade_date"]).max()
    assert want < last and meta["exact_date"] == want.date().isoformat()
    assert (
        compute_money_flow(df, None, None, {}, CFG, NOW)["meta"]["exact_date"] is None
    )


def test_exact_path_room_closed_makes_foreign_vote_not_applicable():
    df, ex = _mch(room=0.0)
    tk = compute_money_flow(df, ex, None, {}, CFG, NOW)["tickers"]["MCH"]
    assert tk["votes"]["foreign"]["vote"] is None
    assert "kín room" in tk["votes"]["foreign"]["reason"]
    assert "kín room ngoại" in tk["badges"]


def test_room_unknown_when_total_room_zero_is_not_closed():
    # VCI trả tổng room = 0 và room còn = 0 cho mã không có số room (GVR sở hữu ngoại 0,56%)
    # → là THIẾU dữ liệu, không phải kín room: phiếu Ngoại vẫn tính.
    df, ex = _mch(room=0.0, total_room=0.0)
    tk = compute_money_flow(df, ex, None, {}, CFG, NOW)["tickers"]["MCH"]
    assert tk["votes"]["foreign"]["vote"] is not None
    assert "kín room ngoại" not in tk["badges"]


# ---------- import sạch (một phần T16) ----------
def test_module_does_not_import_network_packages():
    code = (
        "import sys, valuation.analysis.money_flow; "
        "print([m for m in sys.modules if m.split('.')[0] in "
        "{'streamlit','vnstock','vnstock_data','vnii','vnai'} or m.startswith('valuation.ingest')])"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=False
    )
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "[]"


def test_price_contract_columns_required():
    df = prices([BN] * 3).drop(columns=["p_net_val"])
    assert "p_net_val" in PRICE_COLS
    with pytest.raises(KeyError):
        clean_flows(df, CFG, NOW)


# ---------- màn chi tiết: OBV, CMF trượt ----------
def test_obv_hand_calculated():
    from valuation.analysis.money_flow import obv

    # +200 (tăng), giữ (đi ngang), −400 (giảm), +500 (tăng)
    assert obv([10, 11, 11, 10.5, 12], [100, 200, 300, 400, 500]) == [
        0.0,
        200.0,
        200.0,
        -200.0,
        300.0,
    ]
    assert obv([], []) == []


def test_cmf_series_matches_t7_rows():
    from valuation.analysis.money_flow import cmf_series

    # MFM: +1 (V100), −1 (V100), +0,5 (V200), +1 (V100) — như T7
    h, lo = [10, 10, 10, 10], [8, 8, 8, 8]
    c, v = [10, 8, 9.5, 10], [100, 100, 200, 100]
    out = cmf_series(h, lo, c, v, 2)
    assert out[0] is None
    assert out[1] == pytest.approx(0.0)  # (100 − 100)/200
    assert out[2] == pytest.approx(0.0)  # (−100 + 100)/300
    assert out[3] == pytest.approx(200 / 300)  # (100 + 100)/300
    prev = [
        NAN,
        10,
        8,
        9.5,
    ]  # C_{t−1}; H=10 ≥ mọi C_{t−1}, L=8 ≤ mọi C_{t−1} → giống CMF gốc
    assert cmf_series(h, lo, c, v, 4)[-1] == pytest.approx(cmf(h, lo, c, v, prev)[0])


# ---------- lỗi 24/10/2026: flow_date bỏ qua flow_daily ----------
def test_flow_date_tinh_ca_flow_daily_khi_prices_daily_chua_co_khoi_ngoai():
    """Tái hiện 23/10/2026: prices_daily có giá nhưng 0/107 mã có khối ngoại; flow_daily (VCI) đủ 100/100.

    Trước khi sửa, flow_date chỉ đếm prices_daily → lùi về 22/10 dù số chính xác của 23/10 đã có.
    """
    df, ex = _mch()
    last = df.trade_date == df.trade_date.max()
    df.loc[
        last, ["f_net_val", "f_buy_val", "f_sell_val", "f_buy_vol", "f_sell_vol"]
    ] = NAN
    _, meta = clean_flows(df, CFG, NOW)
    assert (
        meta["flow_date"] < df.trade_date.max()
    )  # không có flow_daily → lùi 1 phiên như cũ
    _, meta = clean_flows(df, CFG, NOW, exact=ex)
    assert meta["flow_date"] == df.trade_date.max()
    res = compute_money_flow(df, ex, None, {"MCH": "X"}, CFG, NOW)
    assert res["meta"]["flow_date"] == df.trade_date.max().strftime("%Y-%m-%d")
    assert (
        res["tickers"]["MCH"]["votes"]["foreign"]["gaps"] == 0
    )  # phiên cuối lấy số VCI


# ---------- D77: Nội gom / Nội xả ----------
def _noi(close: float, recent_vol: float, p=None):
    """80 phiên, ngoại 0; 60 phiên đầu KL 1e7, 20 phiên cuối `recent_vol` → RVOL = recent_vol / 1e7."""
    w = window([0.0] * 80, p=p, close=close)
    w["vol_adj"] = [1e7] * 60 + [recent_vol] * 20
    return votes(w, CFG)


def test_d77_noi_gom_xa_hand_calculated():
    # đóng cửa = cao (10.500), C_{t−1} = 10.500 → TRH 10.500, TRL 9.500 → MFM +1 → CMF +1, Giá-KL ▲
    v = _noi(10_500.0, 1.3e7)
    assert v["foreign"]["vote"] == 0 and v["pv"]["vote"] == 1
    assert (
        v["rvol"]["value"] == pytest.approx(1.3) and v["rvol"]["surge"]
    )  # 1,3e7 / 1e7 = 1,30 ≥ 1,3
    assert label(v)["code"] == "noi_gom" and "×1,30" in label(v)["reason"]
    v = _noi(10_500.0, 1.29e7)  # 1,29 < 1,3 → không đột biến → Trung tính
    assert not v["rvol"]["surge"] and label(v)["code"] == "trung_tinh"
    # đóng cửa = thấp (9.500): TRH max(10.500; 9.500), TRL 9.500 → MFM −1 → Giá-KL ▼; RVOL 1,5 → Nội xả
    assert label(_noi(9_500.0, 1.5e7))["code"] == "noi_xa"
    # tự doanh ngược chiều (mua ròng 1 tỷ/phiên trên GTGD 100 tỷ = +1% ≥ 0,5%) → lẫn lộn, không Nội xả
    v = _noi(9_500.0, 1.5e7, p=[BN] * 80)
    assert v["prop"]["vote"] == 1 and label(v)["code"] == "trung_tinh"
    # chưa đủ 20 + 60 phiên KL → không có RVOL, giữ nhãn cũ
    v = votes(window([0.0] * 20, close=10_500.0), CFG)
    assert v["rvol"]["value"] is None and label(v)["code"] == "trung_tinh"


def test_d77_noi_dem_rieng_o_nganh_va_ket_luan():
    st = _stats()
    st.loc["E", "label_code"] = "noi_gom"
    y = next(r for r in sector_table(st, CFG, "loai") if r["sector"] == "Y")
    assert y["label_count"] == "1 ▲ · 0 ▼ · Nội 1 △ · 0 ▽ / 3" and y["n_gom"] == 1
    rows = sector_table(_stats(), CFG, "loai")
    s = conclusion(rows, 2 * BN, {"gom": 1, "xa": 1, "noi_gom": 2}, CFG, "loai")
    assert s.endswith("dấu hiệu: 1 gom, 1 xả · Nội: 2 gom, 0 xả")


# ---------- rà soát A1/A2: tái hiện lỗi + ca tính tay ----------
def _with_prop(df, p_net, p_buy, p_sell, p_buy_vol, p_sell_vol):
    df = df.copy()
    df[["p_net_val", "p_buy_val", "p_sell_val", "p_buy_vol", "p_sell_vol"]] = [
        p_net,
        p_buy,
        p_sell,
        p_buy_vol,
        p_sell_vol,
    ]
    return df


def test_exact_path_without_prop_match_drops_block_prop_in_loai():
    # flow_daily có ngoại khớp lệnh nhưng thiếu tự doanh (no_prop): P 09/10 của prices_daily là
    # tổng gồm thỏa thuận → không được vào chế độ Loại. P = +1 tỷ/phiên; 22/10 là số tạm (NOW).
    df, ex = _mch()
    df = _with_prop(df, BN, BN, 0.0, BN / 143_000, 0.0)
    i = int(np.flatnonzero(df.trade_date == "2026-10-09")[0])
    df.loc[i, ["p_net_val", "p_buy_val", "p_sell_val", "p_buy_vol", "p_sell_vol"]] = [
        -59_189_550_000,
        16_146_760_000,
        75_336_310_000,
        112_800,
        527_700,
    ]
    tk = compute_money_flow(df, ex, None, {}, CFG, NOW)["tickers"]["MCH"]
    assert tk["votes"]["foreign"]["n"] == 20  # ngoại vẫn đủ 20 phiên khớp lệnh
    assert tk["votes"]["prop"]["n"] == 18  # 20 − 09/10 (thỏa thuận) − 22/10 (tạm)
    assert tk["flows"]["20"]["loai"]["p"] == pytest.approx(
        18 * BN
    )  # trước sửa: −41,19 tỷ
    assert tk["flows"]["20"]["gom"]["p"] == pytest.approx(18 * BN - 59_189_550_000)
    tka = compute_money_flow(df, None, None, {}, CFG, NOW)["tickers"]["MCH"]
    assert tka["flows"]["20"]["loai"]["p"] == pytest.approx(18 * BN)  # = đường A


def _ca_prices(dev, ticker="AAA", end=END):
    """VWAP ngoại = close × (1 + dev) (chỉ phía mua, KL 100k cp); net = mua để đẳng thức đúng."""
    df = prices([BN] * len(dev), ticker=ticker, end=end)
    df["f_buy_val"] = [BN * (1 + d) for d in dev]
    df["f_net_val"] = df["f_buy_val"]
    return df


def test_ca_break_needs_three_consecutive_sessions_counted_up_to_each_day():
    df = _ca_prices([0, 0.1, 0.1, 0, 0.1, 0.1, 0.1, 0.07, 0.1])
    df["factor"] = 1.0
    # chuỗi lệch 2 phiên → không cờ; chuỗi 3 phiên → cờ CHỈ ở phiên thứ 3 (không nhìn phiên sau);
    # 7% < 8% làm đứt chuỗi.
    assert ca_break(df, CFG).tolist() == [False] * 6 + [True, False, False]


def test_ca_break_does_not_look_past_flow_date():
    # AAA lệch 10% ở 20/10, 21/10 và 22/10; 22/10 chỉ AAA có số ngoại (1/3 < 50%) → flow_date 21/10.
    def run(dev_days):
        dev = [
            0.1 if d in dev_days else 0.0 for d in pd.bdate_range(end=END, periods=21)
        ]
        others = [prices([BN] * 21, ticker=t) for t in ("BBB", "CCC")]
        df = pd.concat([_ca_prices(dev), *others], ignore_index=True)
        last = (df.trade_date == END) & df.ticker.isin(["BBB", "CCC"])
        f_cols = ["f_buy_val", "f_sell_val", "f_net_val", "f_buy_vol", "f_sell_vol"]
        df.loc[last, f_cols] = NAN
        res = compute_money_flow(df, None, None, {}, CFG, NOW)
        assert res["meta"]["flow_date"] == "2026-10-21"
        return res["tickers"]["AAA"]

    tk = run({pd.Timestamp(d) for d in ("2026-10-20", "2026-10-21", "2026-10-22")})
    assert tk["votes"]["foreign"]["reason"] is None  # trước sửa: ◌ nhờ số 22/10
    assert not any("gãy điều chỉnh" in b for b in tk["badges"])
    tk = run({pd.Timestamp(d) for d in ("2026-10-19", "2026-10-20", "2026-10-21")})
    assert tk["votes"]["foreign"]["reason"] == "gãy điều chỉnh giá trong cửa sổ"


def test_top_impact_share_hand_calculated():
    d1, d2 = pd.Timestamp("2026-10-21"), pd.Timestamp("2026-10-22")
    rows = [
        # ticker, ngày, f, p, f_gom, p_gom, excl, ngành — score Loại = |f| + |p| (P thiếu = 0)
        ("A", d1, -6 * BN, 2 * BN, -6 * BN, 2 * BN, False, "X"),  # 8
        ("B", d1, 3 * BN, NAN, 3 * BN, NAN, False, "Y"),  # 3
        ("C", d2, BN, -BN, 10 * BN, -BN, True, "X"),  # Loại bỏ; Gồm 11
    ]
    cols = ["ticker", "trade_date", "f", "p", "f_gom", "p_gom", "excl", "sector"]
    win = pd.DataFrame(rows, columns=cols)
    win["block"], win["block_exact"] = win["excl"], False
    win["lb_vol"], win["est_val"], win["form"] = NAN, NAN, None
    loai = top_impact(win, CFG, "loai")
    assert [(r["ticker"], r["share"]) for r in loai] == [
        ("A", pytest.approx(8 / 11)),
        ("B", pytest.approx(3 / 11)),
    ]
    gom = top_impact(win, CFG, "gom")
    assert [(r["ticker"], r["share"]) for r in gom] == [
        ("C", pytest.approx(11 / 22)),
        ("A", pytest.approx(8 / 22)),
        ("B", pytest.approx(3 / 22)),
    ]
    by = top_impact(win, CFG, "gom", by="sector")
    assert [(r["ticker"], r["share"]) for r in by["X"]] == [
        ("C", pytest.approx(11 / 19)),
        ("A", pytest.approx(8 / 19)),
    ]
    assert by["Y"][0]["share"] == pytest.approx(1.0)


def test_t18_gom_sector_sign_matches_sidebar_leaders():
    # 55 phiên (leaders() cần > 49), không phiên thủng. X: AAA +2, BBB −1 tỷ/phiên; Y: CCC −3,
    # DDD +1. AAA có 1 phiên thỏa thuận −500 tỷ → Gồm X = 19×2 − 500 − 20 = −482 tỷ (Loại +18).
    from valuation.views.market_overview import leaders

    f_aaa = [2 * BN] * 55
    f_aaa[-5] = -500 * BN
    df = pd.concat(
        [
            prices(f_aaa, ticker="AAA"),
            prices([-BN] * 55, ticker="BBB"),
            prices([-3 * BN] * 55, ticker="CCC"),
            prices([BN] * 55, ticker="DDD"),
        ],
        ignore_index=True,
    )
    sectors = {"AAA": "X", "BBB": "X", "CCC": "Y", "DDD": "Y"}
    res = compute_money_flow(df, None, None, sectors, CFG, NOW)
    gom = {r["sector"]: r["f"] for r in res["modes"]["gom"]["sectors"]}
    loai = {r["sector"]: r["f"] for r in res["modes"]["loai"]["sectors"]}
    assert gom["X"] == pytest.approx(-482 * BN) and loai["X"] == pytest.approx(18 * BN)
    closes = df.pivot(index="trade_date", columns="ticker", values="close")
    flows = df.pivot(index="trade_date", columns="ticker", values="f_net_val")
    _, sec = leaders(closes, flows, sectors, load_defaults()["market_overview"])
    for s in ("X", "Y"):
        assert np.sign(gom[s]) == np.sign(sec.at[s, "flow"])
        assert gom[s] == pytest.approx(sec.at[s, "flow"])


def test_chip_truncates_toward_zero_near_band():
    # R_F = −39,36 / 2.000 = −1,968% < 2% → phiếu 0; chip không được hiện "−2,0%".
    v = votes(window([-39.36 / 20 * BN] * 20), CFG)["foreign"]
    assert v["vote"] == 0 and "−1,9% GTGD" in v["chip"]
    v = votes(window([5 * BN] * 12 + [-2.5 * BN] * 8), CFG)["foreign"]  # đúng 2% → +1
    assert v["vote"] == 1 and "+2,0% GTGD" in v["chip"]


def test_cash_dividend_is_badge_only():
    df = prices([BN] * 20)
    day = df.trade_date.iloc[10]
    acts = _actions(
        [
            ("AAA", "CASH_DIVIDEND", day, None, df.trade_date.iloc[0], 0.05),
            ("AAA", "CASH_DIVIDEND", None, None, df.trade_date.iloc[1], 0.05),
        ]
    )
    tk = compute_money_flow(df, None, acts, {}, CFG, NOW)["tickers"]["AAA"]
    assert tk["votes"]["foreign"]["reason"] is None  # không ◌
    cash = [b for b in tk["badges"] if "cổ tức tiền" in b]
    assert cash == [
        f"GDKHQ {day:%d/%m}: cổ tức tiền — GTGD chưa điều chỉnh theo cổ tức tiền"
    ]


def test_block_badge_without_foreign_says_so_not_minus_zero():
    # Phiên 10: tự doanh mua 200 tỷ = 20 triệu cp > KL khớp 10 triệu → cờ thỏa thuận; ngoại = 0.
    f, p = [BN] * 20, [BN] * 20
    f[10], p[10] = 0.0, 200 * BN
    tk = compute_money_flow(prices(f, p), None, None, {}, CFG, NOW)["tickers"]["AAA"]
    assert (
        "1 phiên thỏa thuận trong cửa sổ, khối ngoại hầu như không tham gia"
        in tk["badges"]
    )
    assert not any("−0,0" in b for b in tk["badges"])


def test_shares_format_small_volume_not_zero_thousand():
    from valuation.analysis.money_flow import _shares

    assert _shares(64_274_571) == "64,3 triệu cp"
    assert _shares(20_000) == "20 nghìn cp"
    assert _shares(300) == "300 cp"


def test_totals_prop_missing_is_none_not_zero():
    res = compute_money_flow(prices([BN] * 20), None, None, {}, CFG, NOW)
    assert res["modes"]["loai"]["totals"]["20"]["p"] is None
    assert res["modes"]["loai"]["detail"].startswith("Tự doanh ◌ chưa có số")
    assert res["modes"]["gom"]["detail"].startswith("Tự doanh ◌ chưa có số")
    res = compute_money_flow(prices([BN] * 20, p=[BN] * 20), None, None, {}, CFG, NOW)
    assert res["modes"]["gom"]["detail"].startswith("Tự doanh +19,0 tỷ (1/1 mã có số)")


# ---------- D74: lịch sử 1 mã cho biểu đồ, bản đồ nhiệt ----------
def test_ticker_history_exact_deal_and_domestic():
    from valuation.analysis.money_flow import ticker_history

    df, ex = _mch()
    h = ticker_history(df, ex, None, CFG, NOW)
    d = h.loc["2026-10-09"] if "2026-10-09" in h.index else h[h["block"]].iloc[0]
    assert d["vol_deal"] == 64_274_571 and d["big_block"]
    assert d["f"] == pytest.approx(47.54 * BN)  # khớp lệnh
    assert d["f_block"] == pytest.approx(-9_641.19 * BN)  # phần thỏa thuận
    assert math.isnan(
        d["dom"]
    )  # tự doanh NULL → không suy ra trong nước (không thành 0)
    assert not h["deal_is_lb"].any() and (h["source"] == "exact").all()
    assert {"MA20", "MACD", "cmf"} <= set(h.columns) and "RSI14" not in h.columns


def test_sector_daily_hand_calculated_excludes_block_sessions():
    from valuation.analysis.money_flow import sector_daily

    d1, d2 = pd.Timestamp("2026-10-21"), pd.Timestamp("2026-10-22")
    win = pd.DataFrame(
        {
            "sector": ["Ngân hàng", "Ngân hàng", "Ngân hàng", "Thép"],
            "trade_date": [d1, d1, d2, d2],
            "f": [3 * BN, -1 * BN, 5 * BN, -2 * BN],
            "gtgd": [100 * BN, 100 * BN, 100 * BN, 50 * BN],
            "excl": [False, False, True, False],  # NH 22/10: phiên thỏa thuận → loại
        }
    )
    sd = sector_daily(win, ["Ngân hàng", "Thép"])
    assert sd["dates"] == ["2026-10-21", "2026-10-22"]
    assert sd["r"][0] == [
        pytest.approx(2 / 200),
        None,
    ]  # (3 − 1) / 200; 22/10 chỉ có phiên bị loại
    assert sd["r"][1] == [None, pytest.approx(-2 / 50)]
    assert sd["f"][0][0] == pytest.approx(2 * BN)


def test_canh_bao_don_1_phien_tinh_tay():
    from valuation.analysis.money_flow import concentration_badge

    idx = pd.to_datetime(["2026-10-12", "2026-10-13", "2026-10-14", "2026-10-15"])
    # |ngoại ròng| = 250 + 20 + 10 + 20 = 300 tỷ; phiên 12/10 = 250/300 = 83,3% ≥ 50% → cảnh báo.
    w = pd.DataFrame({"f": [250e9, 20e9, -10e9, 20e9], "excl": [False] * 4}, index=idx)
    b = concentration_badge(w, CFG)
    assert (
        b.startswith("⚠ Dồn 1 phiên: 12/10 ngoại mua ròng")
        and "83,3%" in b
        and "4 phiên" in b
    )
    # Phiên thỏa thuận (excl) bị loại như chế độ Loại → còn 20 + 10 + 20: 20/50 = 40% < 50% → không cảnh báo.
    assert concentration_badge(w.assign(excl=[True, False, False, False]), CFG) is None
    # Mua đều → không cảnh báo; thiếu dữ liệu → không cảnh báo.
    assert concentration_badge(w.assign(f=[10e9] * 4), CFG) is None
    assert concentration_badge(w.assign(f=[float("nan")] * 4), CFG) is None
    # Số quá nhỏ (phiên lớn nhất 0,04 tỷ → hiển thị 0,0 tỷ) → không cảnh báo dù chiếm 80%.
    assert concentration_badge(w.assign(f=[40e6, 5e6, 3e6, 2e6]), CFG) is None
