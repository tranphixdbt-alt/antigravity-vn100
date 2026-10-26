"""Dòng tiền ngành VN100 — hàm thuần cho tab "Dòng tiền ngành" (D73, docs/PLAN_SECTOR_FLOW.md v2.1).

Không gọi mạng/AI; không import streamlit, vnstock, vnstock_data, vnii, vnai, valuation.ingest.
Ngưỡng: config/defaults.yaml → money_flow. Nhãn/phiếu là HEURISTIC của repo (chưa backtest);
ROC (ret20), OBV, position sizing là CHUẨN StockCharts; CMF tính trên biên độ thực (True Range,
kiểu Twiggs Money Flow — D76). Chỉ mô tả dữ liệu quá khứ.

Đơn vị VND và cổ phiếu. OHLC là giá ĐIỀU CHỈNH hồi tố, còn KL và giá trị dòng tiền là DANH NGHĨA,
nên GTGD = close × hệ số sự kiện cổ phiếu × KL (§4.2). Có số flow_daily (B1) thì dùng số chính xác.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
from collections import Counter
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from valuation.views.market_overview import _chg, _vi

_VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
PRICE_COLS = [
    "open", "high", "low", "close", "volume",
    "f_buy_val", "f_sell_val", "f_net_val", "f_buy_vol", "f_sell_vol",
    "p_buy_val", "p_sell_val", "p_net_val", "p_buy_vol", "p_sell_vol",
]  # fmt: skip
EXACT_COLS = [
    "matched_val", "matched_vol", "deal_vol", "deal_val", "fr_net_match_val", "fr_net_deal_val",
    "fr_buy_deal_vol", "fr_sell_deal_vol", "fr_current_room", "fr_total_room",
    "prop_net_match_val", "prop_net_deal_val", "is_final", "fetched_at",
]  # fmt: skip
_ADJ = {
    "BONUS_SHARE": "thưởng",
    "STOCK_DIVIDEND": "cổ tức CP",
}  # điều chỉnh được ×(1+ratio)
_UNADJ = {"RIGHTS_ISSUE": "quyền mua"}  # hệ số phụ thuộc giá phát hành → ◌
# chỉ huy hiệu, không ◌: chưa có công thức điều chỉnh GTGD theo cổ tức tiền đã duyệt (luật vàng #1)
_INFO = {"CASH_DIVIDEND": "cổ tức tiền"}
SYM: dict[int | None, str] = {1: "▲", 0: "0", -1: "▼", None: "◌"}
LABELS = {
    "gom": "Dấu hiệu gom",
    "xa": "Dấu hiệu xả",
    "noi_gom": "Nội gom",
    "noi_xa": "Nội xả",
    "trung_tinh": "Trung tính",
    "chua_du": "Chưa đủ dữ liệu",
}
MODES = ("loai", "gom")
DISCLAIMER = "Mô tả dữ liệu quá khứ, không phải khuyến nghị, không dự báo giá."


# ---------- định dạng ----------
def _num(x: Any) -> float | None:
    return None if x is None or pd.isna(x) else float(x)


def _iso(ts: Any) -> str:
    return pd.Timestamp(ts).date().isoformat()


def _dm(ts: Any) -> str:
    return pd.Timestamp(ts).strftime("%d/%m")


def _signed(x: float, digits: int = 0) -> str:
    return ("+" if x >= 0 else "−") + _vi(abs(x), digits)


def _bn(x: float) -> str:
    """Tỷ đồng không dấu; dưới 100 tỷ giữ 1 chữ số thập phân."""
    b = abs(x) / 1e9
    return f"{_vi(b, 1 if b < 100 else 0)} tỷ"


def _ty(x: float) -> str:
    return ("+" if x >= 0 else "−") + _bn(x)


def _shares(x: float) -> str:
    if x >= 1e6:
        return f"{_vi(x / 1e6, 1)} triệu cp"
    return (
        f"{_vi(x / 1e3, 0)} nghìn cp" if x >= 1e3 else f"{_vi(x, 0)} cp"
    )  # < 1.000 cp: không in "0 nghìn"


def _pct(x: float) -> str:
    return _vi(x * 100, 1).removesuffix(",0") + "%"


def _now_vn(now: dt.datetime) -> dt.datetime:
    return now.astimezone(_VN_TZ).replace(tzinfo=None) if now.tzinfo else now


# ---------- A1: làm sạch ----------
def clean_flows(
    prices: pd.DataFrame,
    cfg: dict,
    now: dt.datetime,
    exact: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Làm sạch khung prices (hợp đồng dữ liệu (1)) và dựng lịch phiên.

    - Bỏ dòng T7/CN, dòng sau hôm nay, và phiên hôm nay khi `now` (giờ VN) < `session_close`.
    - Phiên lịch = ngày có ≥ min_coverage × số mã có giá; ngày khác là dòng rác.
    - |net − (mua − bán)| > tol × max(|mua|, |bán|, 1) → net = NaN (ngoại và tự doanh).
    - flow_date = phiên cuối có ≥ min_coverage × số mã có số khối ngoại, đếm cả `exact` (flow_daily VCI,
      fr_net_match_val) vì prices_daily có thể có giá phiên mới trước khi có khối ngoại (lỗi 23/10/2026).
    Trả (df dài đã sạch, meta: universe, today, sessions, flow_sessions, price_date, flow_date, dropped).
    """
    universe = int(prices["ticker"].nunique())
    df = prices[["ticker", "trade_date", *PRICE_COLS]].copy()
    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.normalize()
    df[PRICE_COLS] = df[PRICE_COLS].astype(float)
    nowv = _now_vn(now)
    today = pd.Timestamp(nowv.date())
    weekend = df["trade_date"].dt.dayofweek >= 5
    future = df["trade_date"] > today
    partial = (df["trade_date"] == today) & (
        nowv.time() < dt.time.fromisoformat(cfg["session_close"])
    )
    dropped = {
        "weekend": int(weekend.sum()),
        "future": int(future.sum()),
        "today_partial": int((partial & ~weekend).sum()),
    }
    df = df[~(weekend | future | partial)]
    need = float(cfg["min_coverage"]) * universe
    cov = df.groupby("trade_date")["close"].count()
    sessions = pd.DatetimeIndex(cov.index[cov >= need])
    keep = df["trade_date"].isin(sessions)
    dropped["non_session"] = int((~keep).sum())
    df = df[keep].copy()
    tol = float(cfg["net_identity_rel_tol"])
    for k in ("f", "p"):
        b, s, n = (df[f"{k}_{c}_val"] for c in ("buy", "sell", "net"))
        bad = (n - (b - s)).abs() > tol * np.maximum(np.maximum(b.abs(), s.abs()), 1.0)
        df.loc[bad, f"{k}_net_val"] = np.nan
        dropped[f"{k}_identity_nan"] = int(bad.sum())
    has_f = df.loc[df["f_net_val"].notna(), ["ticker", "trade_date"]]
    if exact is not None and not exact.empty:
        ex = exact.loc[exact["fr_net_match_val"].notna(), ["ticker", "trade_date"]]
        ex = ex.assign(trade_date=pd.to_datetime(ex["trade_date"]).dt.normalize())
        has_f = pd.concat([has_f, ex]).drop_duplicates()
    fcov = (
        has_f.groupby("trade_date")["ticker"].nunique().reindex(sessions, fill_value=0)
    )
    flow_sessions = sessions[(fcov >= need).to_numpy()]
    meta = {
        "universe": universe,
        "today": today,
        "sessions": sessions,
        "flow_sessions": flow_sessions,
        "price_date": sessions[-1] if len(sessions) else None,
        "flow_date": flow_sessions[-1] if len(flow_sessions) else None,
        "dropped": dropped,
    }
    return df.sort_values(["ticker", "trade_date"]).reset_index(drop=True), meta


def stock_events(actions: pd.DataFrame | None) -> pd.DataFrame:
    """Sự kiện cổ phiếu làm giá điều chỉnh hồi tố, khử trùng nguồn (VCI/VSDC).

    Mốc = ex_right_date, NULL thì record_date rồi announcement_date (như _event_anchor).
    """
    cols = ["ticker", "event_type", "ex", "anchor", "ratio"]
    if actions is None or actions.empty:
        typed = {"ex": "datetime64[ns]", "anchor": "datetime64[ns]", "ratio": float}
        return pd.DataFrame(columns=cols).astype(typed)
    a = actions[actions["event_type"].isin([*_ADJ, *_UNADJ, *_INFO])].copy()
    for c in ("ex_right_date", "record_date", "announcement_date"):
        a[c] = pd.to_datetime(a[c])
    a["ex"] = a["ex_right_date"]
    a["anchor"] = a["ex"].fillna(a["record_date"]).fillna(a["announcement_date"])
    a["ratio"] = a["exercise_ratio"].astype(float)
    return a[cols].dropna(subset=["anchor"]).drop_duplicates().reset_index(drop=True)


def adjust_turnover(df: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """Thêm `factor` và `gtgd_est` = close × factor × volume (VND danh nghĩa).

    Phiên trước GDKHQ của thưởng/cổ tức CP: factor × (1 + ratio). Nhiều sự kiện cùng ngày cộng tỷ
    lệ (HDB 5% + 25% → 1,30), khác ngày nhân dồn. Chỉ tính GDKHQ ≤ phiên giá cuối.
    """
    out = df.copy()
    out["factor"] = 1.0
    ev = events[
        events["event_type"].isin(list(_ADJ))
        & events["ex"].notna()
        & events["ratio"].notna()
        & (events["ex"] <= out["trade_date"].max())
        & (events["ex"] > out["trade_date"].min())
    ]
    for (t, ex), r in ev.groupby(["ticker", "ex"])["ratio"].sum().items():
        m = (out["ticker"] == t) & (out["trade_date"] < ex)
        out.loc[m, "factor"] *= 1.0 + float(r)
    out["gtgd_est"] = out["close"] * out["factor"] * out["volume"]
    return out


def block_flags(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Cờ thỏa thuận (§6). Trả cột block, lb_vol, est_val, block_exact, form.

    Đường A: max(Fb+Pb, Fs+Ps) (KL) > KL khớp → có thỏa thuận; cận dưới KL = phần vượt; GT ước =
    cận dưới × VWAP danh nghĩa phía áp đảo (không có VWAP thì close danh nghĩa). NULL = 0 CHỈ ở
    đây (vẫn là cận dưới); giả định ngoại và tự doanh không trùng người. ngoại↔ngoại khi
    min/max(Fb, Fs) ≥ cross_foreign_ratio. Có flow_daily (has_exact): lấy thẳng deal_vol/deal_val.
    """
    fb, fs, pb, ps = (
        df[c].fillna(0.0)
        for c in ("f_buy_vol", "f_sell_vol", "p_buy_vol", "p_sell_vol")
    )
    buy, sell = fb + pb, fs + ps
    top = np.maximum(buy, sell)
    vol = df["volume"]
    block = vol.notna() & (top > vol)
    buy_side = buy >= sell
    bval = df["f_buy_val"].fillna(0.0) + df["p_buy_val"].fillna(0.0)
    sval = df["f_sell_val"].fillna(0.0) + df["p_sell_val"].fillna(0.0)
    side_val, side_vol = bval.where(buy_side, sval), buy.where(buy_side, sell)
    close_nom = df["close"] * df.get("factor", 1.0)
    vwap = (side_val / side_vol).where((side_vol > 0) & (side_val > 0), close_nom)
    lb = (top - vol).where(block)
    est = lb * vwap
    who = pd.Series("tự doanh ", index=df.index).where(
        pb.where(buy_side, ps) > fb.where(buy_side, fs), "ngoại "
    )
    form = who + pd.Series("bán", index=df.index).where(~buy_side, "mua")
    ratio = float(cfg["cross_foreign_ratio"])
    cross = np.minimum(fb, fs) / np.maximum(fb, fs).replace(0, np.nan) >= ratio
    form = form.where(~cross, "ngoại↔ngoại")
    exact = pd.Series(False, index=df.index)
    if "has_exact" in df:
        ex = df["has_exact"].eq(True) & df["deal_vol"].notna()
        dv = df["deal_vol"]
        block = block.where(~ex, dv > 0)
        lb = lb.where(~ex, dv.where(dv > 0))
        est = est.where(~ex, df["deal_val"].where(dv > 0))
        fbd, fsd = df["fr_buy_deal_vol"].fillna(0.0), df["fr_sell_deal_vol"].fillna(0.0)
        xform = pd.Series("không có ngoại", index=df.index)
        xform = xform.where(~(fbd > fsd), "ngoại mua").where(~(fsd > fbd), "ngoại bán")
        xcross = np.minimum(fbd, fsd) / np.maximum(fbd, fsd).replace(0, np.nan) >= ratio
        form = form.where(~ex, xform.where(~xcross, "ngoại↔ngoại"))
        exact = ex & (dv > 0)
    block = block.astype(bool)
    return pd.DataFrame(
        {
            "block": block,
            "lb_vol": lb,
            "est_val": est,
            "block_exact": exact,
            "form": form.where(block),
        }
    )


def ca_break(df: pd.DataFrame, cfg: dict) -> pd.Series:
    """Cờ gãy điều chỉnh (§6, HEURISTIC): |VWAP ngoại / close danh nghĩa − 1| > ca_break_tol trong
    ≥ ca_break_min_sessions phiên liên tiếp của mã. df phải sắp theo (ticker, trade_date).

    Chuỗi chỉ đếm TỚI phiên đang xét (không nhìn phiên sau → không lookahead): phiên j bật cờ khi
    j là phiên thứ ≥ k của chuỗi lệch. "Cửa sổ có gãy" = có phiên bật cờ trong cửa sổ.
    """
    q = df["f_buy_vol"].fillna(0.0) + df["f_sell_vol"].fillna(0.0)
    v = df["f_buy_val"].fillna(0.0) + df["f_sell_val"].fillna(0.0)
    vwap = (v / q).where(q > 0)
    bad = (vwap / (df["close"] * df["factor"]) - 1).abs() > float(cfg["ca_break_tol"])
    run = bad.groupby([df["ticker"], (~bad).cumsum()]).cumsum()
    return run >= int(cfg["ca_break_min_sessions"])


def _with_exact(df: pd.DataFrame, exact: pd.DataFrame | None) -> pd.DataFrame:
    """Ghép khung exact (flow_daily); nhiều nguồn cùng (mã, phiên) → ưu tiên is_final rồi mới nhất."""
    if exact is None or exact.empty:
        out = df.copy()
        for c in EXACT_COLS:
            out[c] = np.nan
        out["has_exact"] = False
        return out
    ex = exact[["ticker", "trade_date", *EXACT_COLS]].copy()
    ex["trade_date"] = pd.to_datetime(ex["trade_date"]).dt.normalize()
    ex["is_final"] = ex["is_final"].fillna(False).astype(bool)
    ex["fetched_at"] = pd.to_datetime(ex["fetched_at"])
    num = [c for c in EXACT_COLS if c not in ("is_final", "fetched_at")]
    ex[num] = ex[num].astype(float)
    ex = ex.sort_values(["is_final", "fetched_at"]).drop_duplicates(
        ["ticker", "trade_date"], keep="last"
    )
    out = df.merge(ex, on=["ticker", "trade_date"], how="left")
    out["has_exact"] = out["fr_net_match_val"].notna()
    return out


def _paths(df: pd.DataFrame, today: pd.Timestamp) -> pd.DataFrame:
    """Chọn số theo đường: exact (khớp lệnh chính xác) hoặc A (suy từ prices_daily).

    f/p: số cho chế độ Loại; f_gom/p_gom: tổng gồm thỏa thuận; excl: phiên-mã bị loại ở chế độ
    Loại (chỉ đường A — đường exact đã tách khớp lệnh). Tự doanh "tạm" (phiên hôm nay ở đường A,
    is_final = False ở đường exact) không vào phiếu và không vào tổng. Phiên exact có thỏa thuận
    nhưng thiếu số tự doanh khớp lệnh: P tổng của prices_daily gồm cả thỏa thuận → bỏ ở chế độ Loại.
    """
    out = df.copy()
    ex = df["has_exact"].eq(True)
    out["f"] = df["fr_net_match_val"].where(ex, df["f_net_val"])
    fdeal = ex & df["fr_net_deal_val"].notna()
    out["f_gom"] = (df["fr_net_match_val"] + df["fr_net_deal_val"]).where(
        fdeal, df["f_net_val"]
    )
    out["excl"] = df["block"] & ~ex
    pex = ex & df["prop_net_match_val"].notna()
    final = df["is_final"].eq(True)
    out["p_prov"] = (pex & ~final) | (~pex & (df["trade_date"] == today))
    out["p_raw"] = df["prop_net_match_val"].where(pex, df["p_net_val"])
    pdeal = pex & df["prop_net_deal_val"].notna()
    p_gom = (df["prop_net_match_val"] + df["prop_net_deal_val"]).where(
        pdeal, df["p_net_val"]
    )
    out["p"] = out["p_raw"].mask(out["p_prov"] | (ex & ~pex & df["block"]))
    out["p_gom"] = p_gom.mask(out["p_prov"])
    mv = ex & df["matched_val"].notna()
    out["gtgd"] = df["matched_val"].where(mv, df["gtgd_est"])
    out["gtgd_is_est"] = ~mv
    out["vol_adj"] = (
        df["volume"] * df["factor"]
    )  # KL theo đơn vị cp sau điều chỉnh (cho CMF)
    return out


# ---------- A2: phiếu, nhãn ----------
def cmf(
    high: Any, low: Any, close: Any, volume: Any, prev_close: Any
) -> tuple[float | None, int]:
    """CMF trên BIÊN ĐỘ THỰC (D76): MFM = ((C−TRL) − (TRH−C)) / (TRH−TRL); CMF = Σ(MFM·V) / ΣV.

    TRH = max(H, C_{t−1}), TRL = min(L, C_{t−1}) như True Range (Wilder, ATR) — cùng ý tưởng Twiggs
    Money Flow (Twiggs làm mượt mũ; app vẫn cộng `cmf_window` phiên như CMF StockCharts). Khác CMF gốc
    (H/L trong phiên): phiên nhảy giá được tính, vd trần trắng bên H=L=C > C_{t−1} → MFM = +1.
    C_{t−1} thiếu (NaN) → dùng H/L của phiên. Phiên TRH = TRL (đứng giá cả so với phiên trước) bị
    loại khỏi tử lẫn mẫu — quy ước repo. Trả (CMF, None khi ΣV = 0; số phiên đứng giá).
    """
    hi, lo, c, v = (np.asarray(x, dtype=float) for x in (high, low, close, volume))
    pc = np.asarray(prev_close, dtype=float)
    hi, lo = np.fmax(hi, pc), np.fmin(lo, pc)  # fmax/fmin bỏ qua NaN của C_{t−1}
    rng = hi - lo
    flat = rng == 0
    ok = ~flat & ~np.isnan(rng) & ~np.isnan(v)
    den = float(v[ok].sum())
    if den <= 0:
        return None, int(flat.sum())
    mfm = ((c[ok] - lo[ok]) - (hi[ok] - c[ok])) / rng[ok]
    return float((mfm * v[ok]).sum()) / den, int(flat.sum())


_VOTE_COLS = ("gtgd", "f", "p", "high", "low", "close", "vol_adj")


def _arrays(
    h: pd.DataFrame, cols: tuple[str, ...] = _VOTE_COLS
) -> dict[str, np.ndarray]:
    a = {c: h[c].to_numpy(dtype=float) for c in cols}
    a["excl"] = h["excl"].eq(True).to_numpy()
    return a


def _masks(a: dict[str, np.ndarray]) -> tuple[np.ndarray, ...]:
    """(có giá, phiên hợp lệ, phiên thủng, phiên hợp lệ có số tự doanh)."""
    has = ~np.isnan(a["close"]) & ~np.isnan(a["gtgd"])
    fok = ~np.isnan(a["f"])
    valid = has & fok & ~a["excl"]
    return has, valid, has & ~fok, valid & ~np.isnan(a["p"])


def _ratio_vote(x: np.ndarray, g: np.ndarray, band: float, share: float) -> dict:
    """R = Σx / ΣGTGD trên cùng tập phiên; ±1 khi |R| ≥ band và ≥ share số phiên cùng dấu."""
    n, gs = len(x), float(g.sum())
    pos, neg = int((x > 0).sum()), int((x < 0).sum())
    if n == 0 or gs <= 0:
        return {"vote": None, "value": None, "n": n, "pos": pos, "neg": neg}
    r = float(x.sum()) / gs
    vote = 0
    if r >= band and pos / n >= share:
        vote = 1
    elif r <= -band and neg / n >= share:
        vote = -1
    return {"vote": vote, "value": r, "n": n, "pos": pos, "neg": neg}


def votes(
    hist: pd.DataFrame,
    cfg: dict,
    *,
    unadjustable: str | None = None,
    room_closed: bool = False,
) -> dict:
    """3 phiếu §4.2 của 1 mã tại phiên cuối của `hist` (luôn ở chế độ Loại).

    hist: các phiên lịch đến flow_date, dòng không có giá để NaN; cột gtgd, f, excl, p, high, low,
    close, vol_adj. Ngoại/Tự doanh dùng `window` phiên cuối; Giá-KL dùng `cmf_window` phiên có giá.
    Trả {"foreign"|"pv"|"prop": {vote: 1|0|-1|None (◌), value, n, pos, neg, reason, chip, ...},
    "rvol": {value, surge, reason, chip}} (rvol chỉ dùng cho nhãn Nội gom/xả, D77).
    """
    return _votes(_arrays(hist), cfg, unadjustable, room_closed)


def _votes(
    a: dict[str, np.ndarray], cfg: dict, unadjustable: str | None, room_closed: bool
) -> dict:
    s = cfg["signal"]
    W = int(cfg["window"])
    w = {k: x[-W:] for k, x in a.items()}
    _, valid, gap, pm = _masks(w)
    n, ng = int(valid.sum()), int(gap.sum())
    fv = _ratio_vote(
        w["f"][valid], w["gtgd"][valid], s["foreign_band"], s["same_sign_share"]
    )
    why = None
    if room_closed:
        why = "kín room ngoại — phiếu Ngoại không áp dụng"
    elif unadjustable:
        why = unadjustable
    elif ng > int(cfg["max_flow_gaps"]):
        why = f"{ng} phiên thủng dòng tiền ngoại (tối đa {cfg['max_flow_gaps']})"
    elif n < int(s["min_valid_sessions"]):
        why = f"chỉ {n} phiên hợp lệ (cần ≥ {s['min_valid_sessions']})"
    elif fv["value"] is None:
        why = "không có GTGD"
    foreign = {**fv, "vote": None if why else fv["vote"], "reason": why, "gaps": ng}

    npn = int(pm.sum())
    cov = npn / n if n else 0.0
    pv_ = _ratio_vote(w["p"][pm], w["gtgd"][pm], s["prop_band"], s["same_sign_share"])
    why = None
    if unadjustable:
        why = unadjustable
    elif npn == 0:
        why = "không có số tự doanh"
    elif cov < float(s["prop_min_session_cov"]):
        why = f"tự doanh chỉ có số {npn}/{n} phiên hợp lệ (cần ≥ {_pct(s['prop_min_session_cov'])})"
    prop = {**pv_, "vote": None if why else pv_["vote"], "reason": why, "coverage": cov}

    cw = int(s["cmf_window"])
    priced = np.flatnonzero(~np.isnan(a["close"]))
    prev = np.r_[np.nan, a["close"][priced[:-1]]][
        -cw:
    ]  # đóng cửa phiên có giá liền trước
    ix = priced[-cw:]
    val, flat = cmf(a["high"][ix], a["low"][ix], a["close"][ix], a["vol_adj"][ix], prev)
    why = None
    if len(ix) < cw:
        why = f"chưa đủ {cw} phiên giá"
    elif flat > int(s["cmf_max_flat"]):
        why = f"{flat} phiên đứng giá (cao = thấp = giá phiên trước), tối đa {s['cmf_max_flat']}"
    elif val is None:
        why = "không có KL ở phiên H≠L"
    vote = None
    if not why and val is not None:
        b = float(s["cmf_band"])
        vote = 1 if val >= b else (-1 if val <= -b else 0)
    pv = {"vote": vote, "value": val, "n": len(ix), "flat": flat, "reason": why}

    # D77: đột biến KL khớp (đã điều chỉnh sự kiện) — chỉ dùng cho nhãn Nội gom/xả khi Ngoại = 0
    rb = int(s["rvol_base"])
    vol = a["vol_adj"][priced]
    rv: float | None = None
    why = f"chưa đủ {cw + rb} phiên KL"
    if len(vol) >= cw + rb:
        base = float(np.nanmean(vol[-cw - rb : -cw]))
        why = "KL nền bằng 0" if not base > 0 else None
        rv = float(np.nanmean(vol[-cw:])) / base if why is None else None
    surge = rv is not None and rv >= float(s["rvol_min"])
    rvol = {"value": rv, "surge": surge, "reason": why}
    rvol["chip"] = (
        f"KL {cw}p ×{_vi(rv, 2)} so {rb}p trước" if rv is not None else f"KL ◌ ({why})"
    )

    foreign["chip"] = _flow_chip("Ngoại", foreign, "phiên")
    prop["chip"] = _flow_chip("Tự doanh", prop, "phiên có số") + " (phụ)"
    pv["chip"] = (
        f"Giá-KL {SYM[vote]} CMF{cw} {_signed(val, 2)}"
        if vote is not None and val is not None
        else f"Giá-KL ◌ ({pv['reason']})"
    )
    return {"foreign": foreign, "pv": pv, "prop": prop, "rvol": rvol}


def _chip_pct(x: float) -> str:
    """% 1 chữ số, CẮT về phía 0: −1,968% → −1,9% (làm tròn ra −2,0% trông như đã đạt ngưỡng 2%)."""
    t = (
        math.trunc(round(abs(x) * 1000, 6)) / 10
    )  # round(…, 6) khử nhiễu float (0,03 → 2,9…)
    return ("+" if x >= 0 else "−") + f"{t:.1f}".replace(".", ",") + "%"


def _flow_chip(name: str, v: dict, unit: str) -> str:
    r = v["value"]
    if r is None:
        return f"{name} ◌ ({v['reason']})"
    side, k = ("mua", v["pos"]) if r >= 0 else ("bán", v["neg"])
    text = (
        f"{name} {SYM[v['vote']]} {_chip_pct(r)} GTGD, {k}/{v['n']} {unit} {side} ròng"
    )
    return text + (f" ({v['reason']})" if v["vote"] is None else "")


def label(v: dict) -> dict:
    """Nhãn §4.2 (HEURISTIC), xét theo thứ tự.

    1. Ngoại hoặc Giá-KL ◌ → Chưa đủ dữ liệu.
    2. Ngoại +1, thêm ≥ 1 phiếu +1 (Giá-KL/Tự doanh), Giá-KL không −1 → Dấu hiệu gom.
    3. Đối xứng → Dấu hiệu xả.
    4. (D77) Ngoại 0, Giá-KL ±1, KL đột biến (RVOL ≥ rvol_min), Tự doanh không ngược → Nội gom / Nội xả.
       Là áp lực giá-KL khi ngoại không có chiều, KHÔNG phải số mua ròng trong nước (= −(F + P)).
    5. Còn lại → Trung tính ("lẫn lộn" nếu có phiếu ngược dấu, ngược lại "chưa đủ mạnh").
    Tự doanh chỉ xác nhận: không chặn được nhãn (FPT (−,−,+) vẫn Xả) và một mình không tạo nhãn;
    (0,+,+) là Trung tính (không đếm trùng đà giá).
    """
    F, A, P = (v[k]["vote"] for k in ("foreign", "pv", "prop"))
    if F is None or A is None:
        why = v["foreign"]["reason"] if F is None else v["pv"]["reason"]
        return _lab("chua_du", "thiếu dữ liệu", f"Chưa đủ dữ liệu: {why}")
    named = (("pv", A), ("prop", P))
    for code, sign in (("gom", 1), ("xa", -1)):
        if F == sign and sign in (A, P) and A != -sign:
            conf = "; ".join(v[k]["chip"] for k, x in named if x == sign)
            return _lab(code, "đủ phiếu", f"{v['foreign']['chip']}; xác nhận: {conf}")
    rv = v.get("rvol") or {}
    if F == 0 and A in (1, -1) and P != -A and rv.get("surge"):
        conf = f"; {v['prop']['chip']}" if P == A else ""
        return _lab(
            "noi_gom" if A == 1 else "noi_xa",
            "giá-KL + KL đột biến",
            f"{v['foreign']['chip']} (ngoại không có chiều); {v['pv']['chip']}; {rv['chip']}{conf}",
        )
    signs = {F, A, P} - {None, 0}
    if {1, -1} <= signs:
        chips = "; ".join(
            v[k]["chip"] for k in ("foreign", "pv", "prop") if v[k]["vote"]
        )
        return _lab("trung_tinh", "lẫn lộn", f"Các phiếu ngược chiều: {chips}")
    if F == 0:
        tail = " dù Giá-KL/Tự doanh cùng chiều" if A == P != 0 else ""
        return _lab(
            "trung_tinh",
            "chưa đủ mạnh",
            f"Phiếu Ngoại chưa đạt ngưỡng ({v['foreign']['chip']}){tail}",
        )
    return _lab(
        "trung_tinh", "chưa đủ mạnh", f"{v['foreign']['chip']}; chưa có phiếu xác nhận"
    )


def _lab(code: str, reason_code: str, reason: str) -> dict:
    return {
        "code": code,
        "text": LABELS[code],
        "reason_code": reason_code,
        "reason": reason,
    }


def context(ret20: float | None, cfg: dict) -> str:
    """Hậu tố bối cảnh — CHỈ mô tả giá, không đổi nhãn."""
    if ret20 is None or pd.isna(ret20):
        return f"chưa đủ {cfg['window']} phiên giá"
    if abs(ret20) <= float(cfg["signal"]["sideways_band"]):
        return f"giá đi ngang ({_chg(ret20)})"
    return f"giá đã {'tăng' if ret20 > 0 else 'giảm'} {_vi(abs(ret20) * 100, 1)}%"


def label_history(hist: list[tuple[str, str]]) -> tuple[str | None, bool]:
    """(ngày bắt đầu chuỗi nhãn hiện tại, True nếu chuỗi phủ hết lịch sử đã xét → "từ ≤ ngày")."""
    if not hist:
        return None, False
    i = len(hist) - 1
    while i > 0 and hist[i - 1][1] == hist[-1][1]:
        i -= 1
    return hist[i][0], i == 0


def event_status(
    ev: Any, start: pd.Timestamp, end: pd.Timestamp
) -> tuple[str | None, list[str]]:
    """Sự kiện cổ phiếu có mốc trong [start, end] → (lý do ◌ hoặc None, huy hiệu).

    Thưởng/cổ tức CP có GDKHQ và tỷ lệ: đã điều chỉnh GTGD. Quyền mua, GDKHQ chưa rõ hoặc tỷ lệ
    chưa rõ: chưa điều chỉnh được → phiếu Ngoại và Tự doanh ◌. ev: khung stock_events hoặc list
    các dòng itertuples của khung đó.
    """
    bad, badges = [], []
    for r in ev.itertuples() if isinstance(ev, pd.DataFrame) else ev:
        if not start <= r.anchor <= end:
            continue
        if r.event_type in _INFO:
            if pd.notna(r.ex):
                badges.append(
                    f"GDKHQ {_dm(r.ex)}: {_INFO[r.event_type]} — GTGD chưa điều chỉnh theo"
                    " cổ tức tiền"
                )
            continue
        name = _ADJ.get(r.event_type) or _UNADJ[r.event_type]
        pct = "" if pd.isna(r.ratio) else f" {_pct(r.ratio)}"
        if pd.isna(r.ex):
            msg = f"{name}{pct}: ngày GDKHQ chưa rõ (mốc {_dm(r.anchor)})"
        elif r.event_type in _UNADJ or pd.isna(r.ratio):
            msg = f"GDKHQ {_dm(r.ex)}: {name}{pct or ' (tỷ lệ chưa rõ)'} — chưa điều chỉnh được GTGD"
        else:
            badges.append(f"GDKHQ {_dm(r.ex)}: {name}{pct} (đã điều chỉnh GTGD)")
            continue
        bad.append(msg)
        badges.append(msg)
    why = "sự kiện cổ phiếu chưa điều chỉnh được GTGD (xem huy hiệu)" if bad else None
    return why, list(dict.fromkeys(badges))  # VCI/VSDC trùng sự kiện → 1 huy hiệu


def block_badge(
    date: Any,
    lb_vol: float,
    est_val: float,
    exact: bool,
    form: str,
    adtv: float,
    cfg: dict,
) -> str | None:
    """Huy hiệu "Thỏa thuận lớn" khi GT ≥ big_block_adtv_share × GTGD bình quân cửa sổ (HEURISTIC).

    Đường A: chỉ KL là cận dưới ("KL ≥"); GT ghi "ước ~" (không bao giờ "≥ … tỷ").
    """
    if (
        pd.isna(est_val)
        or not adtv
        or est_val < float(cfg["big_block_adtv_share"]) * adtv
    ):
        return None
    if exact:
        return f"Thỏa thuận lớn {_dm(date)}: KL {_shares(lb_vol)}, GT {_bn(est_val)}, {form}"
    return f"Thỏa thuận lớn {_dm(date)}: KL ≥ {_shares(lb_vol)}, GT ước ~{_bn(est_val)}, {form}"


def _block_f(blk: pd.DataFrame) -> float | None:
    """Ngoại ròng của các phiên thỏa thuận: exact → phần thỏa thuận; đường A → tổng (gồm khớp)."""
    f = blk["fr_net_deal_val"].where(blk["block_exact"].eq(True), blk["f_gom"])
    return _num(f.sum(min_count=1))


def concentration_badge(w: pd.DataFrame, cfg: dict) -> str | None:
    """Cảnh báo tín hiệu ngoại dồn vào MỘT phiên: |ngoại ròng| phiên lớn nhất ≥ single_session_share ×
    Σ|ngoại ròng| từng phiên trong cửa sổ (chế độ Loại — bỏ phiên thỏa thuận). HEURISTIC, người dùng duyệt 50%.
    """
    f = w["f"].where(~w["excl"].eq(True)).dropna()
    tot = float(f.abs().sum())
    if len(f) < 2 or tot <= 0:
        return None
    d = f.abs().idxmax()
    share = abs(float(f[d])) / tot
    # Phiên lớn nhất làm tròn hiển thị ra 0,0 tỷ (KOS 20/10) → % trên số quá nhỏ, không có nghĩa.
    if (
        share < float(cfg["single_session_share"])
        or round(abs(float(f[d])) / 1e9, 1) == 0
    ):
        return None
    return (
        f"⚠ Dồn 1 phiên: {_dm(d)} ngoại {'mua' if f[d] > 0 else 'bán'} ròng {_ty(float(f[d]))}, chiếm "
        f"{_pct(share)} tổng |ngoại ròng| {len(f)} phiên — tín hiệu kém tin cậy hơn mua/bán đều"
    )


def badges(
    w: pd.DataFrame,
    cfg: dict,
    *,
    flat: int,
    event_badges: list[str],
    broke: bool,
    room_closed: bool,
) -> list[str]:
    """Huy hiệu sự kiện của cửa sổ (không bỏ phiếu): thỏa thuận, GDKHQ, đứng giá, gãy điều chỉnh,
    kín room, phiên cơ cấu ETF, tự doanh tạm."""
    out: list[str] = [b for b in [concentration_badge(w, cfg)] if b]
    blk = w[w["block"].eq(True)]
    if len(blk):
        f = _block_f(blk)
        if f is None:
            tail = "ngoại chưa có số"
        elif (
            round(abs(f) / 1e9, 1) == 0
        ):  # làm tròn hiển thị ra 0,0 tỷ → nói thẳng, không in "−0,0"
            tail = "khối ngoại hầu như không tham gia"
        else:
            tail = f"ngoại {_ty(f)}"
        out.append(f"{len(blk)} phiên thỏa thuận trong cửa sổ, {tail}")
        adtv = float(w["gtgd"].mean())
        for d, r in blk.iterrows():
            b = block_badge(
                d,
                r["lb_vol"],
                r["est_val"],
                bool(r["block_exact"]),
                r["form"],
                adtv,
                cfg,
            )
            if b:
                out.append(b)
    out += event_badges
    if flat:
        out.append(f"{flat} phiên đứng giá (cao = thấp = giá phiên trước)")
    if broke:
        out.append(
            f"gãy điều chỉnh giá: VWAP ngoại lệch giá đóng cửa > {_pct(cfg['ca_break_tol'])}"
            f" trong ≥ {cfg['ca_break_min_sessions']} phiên liên tiếp"
        )
    if room_closed:
        out.append("kín room ngoại")
    for d in pd.to_datetime(cfg["etf_review_dates"]):
        if w.index[0] <= d <= w.index[-1]:
            out.append(f"phiên cơ cấu ETF {_dm(d)}")
    for d in w.index[w["p_prov"].eq(True) & w["p_raw"].notna()]:
        out.append(f"tự doanh {_dm(d)} là số tạm, chưa tính")
    return out


def implied_domestic(f: pd.Series, p: pd.Series) -> pd.Series:
    """Trong nước suy ra D = −(F + P) (người mua = người bán); thiếu F hoặc P → NaN."""
    return -(f + p)


# ---------- A2: ngành, tổng hợp ----------
def sector_table(stats: pd.DataFrame, cfg: dict, mode: str) -> list[dict]:
    """Bản đồ ngành §3 từ bảng thống kê từng mã (cửa sổ `window`).

    stats: index mã; cột sector, label_code, rel (ret20 − trung vị VN100), gaps, f_loai, g_loai
    (GTGD trên phiên hợp lệ), p_loai, gp_loai (GTGD trên phiên có tự doanh), f_gom, p_gom.
    Loại: f, r_f, heat (r_f cắt ±heat_clip), p, r_p, p_cov (theo GTGD), p_dim. Gồm: CHỈ tổng tuyệt
    đối f, p (r_f/heat/r_p/p_cov = None). Ngành n < small_sector_n xếp cuối (small = True).
    breadth_pos/breadth_n: số mã có ngoại ròng > 0 / số mã có số (theo chế độ) — độ rộng cùng trọng số.
    """
    loai = mode == "loai"
    fc, pc = ("f_loai", "p_loai") if loai else ("f_gom", "p_gom")
    clip = float(cfg["heat_clip"])
    rows = []
    for sec, g in stats.groupby("sector"):
        f, p = _num(g[fc].sum(min_count=1)), _num(g[pc].sum(min_count=1))
        absf = g[fc].abs()
        dom = absf.idxmax() if absf.notna().any() and absf.sum() > 0 else None
        n = len(g)
        nz = g[fc].dropna()  # độ rộng (D76): mỗi mã 1 phiếu, không theo vốn hóa
        n_gom, n_xa = int((g["label_code"] == "gom").sum()), int(
            (g["label_code"] == "xa").sum()
        )
        ng, nx = (int((g["label_code"] == c).sum()) for c in ("noi_gom", "noi_xa"))
        noi = (
            f" · Nội {ng} △ · {nx} ▽" if ng or nx else ""
        )  # D77: đếm riêng, không trộn
        fl, fg = g["f_loai"].sum(min_count=1), g["f_gom"].sum(min_count=1)
        flags = []
        if np.sign(fl) * np.sign(fg) < 0:
            flags.append("đổi dấu Gồm/Loại")
        if n < int(cfg["small_sector_n"]):
            flags.append("ít mã")
        if g["gaps"].sum() > 0:
            flags.append("dòng tiền thủng")
        row = {
            "sector": sec,
            "n": n,
            "f": f,
            "p": p,
            "n_gom": n_gom,
            "n_xa": n_xa,
            "n_noi_gom": ng,
            "n_noi_xa": nx,
            "label_count": f"{n_gom} ▲ · {n_xa} ▼{noi} / {n}",
            "dominant": dom,
            "dominant_share": _num(absf.max() / absf.sum()) if dom else None,
            "breadth_pos": int((nz > 0).sum()),
            "breadth_n": len(nz),
            "rs20": _num(g["rel"].dropna().median()),
            "small": n < int(cfg["small_sector_n"]),
            "flags": flags,
            "r_f": None,
            "heat": None,
            "r_p": None,
            "p_cov": None,
            "p_dim": None,
        }
        if loai:
            gs, gp = g["g_loai"].sum(), g["gp_loai"].sum()
            r_f = f / gs if f is not None and gs > 0 else None
            cov = gp / gs if gs > 0 else None
            row |= {
                "r_f": r_f,
                "heat": None if r_f is None else max(-clip, min(clip, r_f)),
                "r_p": p / gp if p is not None and gp > 0 else None,
                "p_cov": cov,
                "p_dim": bool(
                    cov is None or cov < float(cfg["prop_sector_min_value_cov"])
                ),
            }
        rows.append(row)
    key = "r_f" if loai else "f"
    return sorted(
        rows, key=lambda r: (r["small"], r[key] is None, -(r[key] or 0.0), r["sector"])
    )


def top_impact(
    win: pd.DataFrame, cfg: dict, mode: str, by: str | None = None
) -> list[dict] | dict[str, list[dict]]:
    """Top N phiên-mã theo |F| + |P| (P thiếu = 0) trong cửa sổ, kèm tỷ trọng trên Σ(|F|+|P|).

    win: khung dài (ticker, trade_date, f, f_gom, p, p_gom, excl, block, lb_vol, est_val,
    block_exact, form). Chế độ Loại bỏ phiên-mã có cờ thỏa thuận ở đường A. by = tên cột nhóm
    (vd "sector") → {nhóm: top N}, tỷ trọng tính trong từng nhóm.
    """
    d = win[~win["excl"].eq(True)] if mode == "loai" else win
    fc, pc = ("f", "p") if mode == "loai" else ("f_gom", "p_gom")
    score = d[fc].abs().fillna(0.0) + d[pc].abs().fillna(0.0)
    tot = score.groupby(d[by]).transform("sum") if by else score.sum()
    d = d.assign(
        score=score,
        tot=tot,
        block=d["block"].eq(True),
        block_exact=d["block_exact"].eq(True),
    )
    d = d[(d["score"] > 0) & (d["tot"] > 0)].sort_values("score", ascending=False)
    n = int(cfg["top_impact_n"])
    top = d.groupby(by).head(n) if by else d.head(n)
    rows = [
        {
            "ticker": r.ticker,
            "date": _iso(r.trade_date),
            "f": _num(getattr(r, fc)),
            "p": _num(getattr(r, pc)),
            "share": r.score / r.tot,
            "block": bool(r.block),
            "lb_vol": _num(r.lb_vol),
            "est_val": _num(r.est_val),
            "exact": bool(r.block_exact),
            "form": r.form if isinstance(r.form, str) else None,
            "_g": getattr(r, by) if by else None,
        }
        for r in top.itertuples()
    ]
    if not by:
        return [{k: v for k, v in r.items() if k != "_g"} for r in rows]
    out: dict[str, list[dict]] = {}
    for r in rows:
        out.setdefault(r.pop("_g"), []).append(r)
    return out


def _words(s: str) -> int:
    return len([x for x in s.split() if x != "·"])


def conclusion(
    sector_rows: list[dict], total_f: float | None, counts: dict, cfg: dict, mode: str
) -> str:
    """Câu kết luận 1 dòng (template số, không AI), ≤ conclusion_max_words chữ (không đếm "·").

    Ngành small không được nêu tên; Loại xếp theo r_f, Gồm theo tổng f. Thiếu dữ liệu → câu trạng thái.
    """
    W = cfg["window"]
    big = [r for r in sector_rows if not r["small"] and r["f"] is not None]
    if total_f is None or not big:
        return f"{W} phiên: chưa đủ dữ liệu dòng tiền ngành để tóm tắt."
    key = "r_f" if mode == "loai" else "f"
    pos = sorted([r for r in big if (r[key] or 0) > 0], key=lambda r: -r[key])
    neg = sorted([r for r in big if (r[key] or 0) < 0], key=lambda r: r[key])
    head = (
        f"{W} phiên, {'loại' if mode == 'loai' else 'gồm'} thỏa thuận: ngoại "
        f"{'mua' if total_f >= 0 else 'bán'} ròng {_bn(total_f)}"
    )
    tail = f"dấu hiệu: {counts.get('gom', 0)} gom, {counts.get('xa', 0)} xả"
    ng, nx = counts.get("noi_gom", 0), counts.get("noi_xa", 0)
    if ng or nx:  # D77: nhãn Nội đếm riêng
        tail += f" · Nội: {ng} gom, {nx} xả"
    s = ""
    for k in (2, 1, 0):
        parts = [head]
        if k:
            parts.append(
                "mua mạnh " + ", ".join(r["sector"] for r in pos[:k])
                if pos
                else "không ngành nào mua ròng"
            )
            parts.append(
                "bán mạnh " + ", ".join(r["sector"] for r in neg[:k])
                if neg
                else "không ngành nào bán ròng"
            )
        s = " · ".join([*parts, tail])
        if _words(s) <= int(cfg["conclusion_max_words"]):
            return s
    return s


def position_size(
    capital: float, risk_pct: float, entry: float, stop: float, lot: int
) -> int:
    """CHUẨN StockCharts: floor(vốn × % rủi ro / (giá vào − stop) / lô) × lô (lô = quy ước app)."""
    if stop >= entry:
        raise ValueError("Giá stop phải thấp hơn giá vào")
    if capital <= 0 or risk_pct <= 0 or lot <= 0:
        raise ValueError("Vốn, % rủi ro và lô phải dương")
    return math.floor(round(capital * risk_pct / (entry - stop) / lot, 9)) * lot


# ---------- tổng hợp ----------
def _nsum(x: np.ndarray) -> float:
    return float(x.sum()) if len(x) else math.nan


def _sums(a: dict[str, np.ndarray]) -> dict:
    has, valid, _, pm = _masks(a)
    fg, pg = a["f_gom"], a["p_gom"]
    return {
        "f_loai": _nsum(a["f"][valid]),
        "g_loai": float(a["gtgd"][valid].sum()),
        "p_loai": _nsum(a["p"][pm]),
        "gp_loai": float(a["gtgd"][pm].sum()),
        "f_gom": _nsum(fg[has & ~np.isnan(fg)]),
        "p_gom": _nsum(pg[has & ~np.isnan(pg)]),
    }


def _flows_out(sm: dict) -> dict:
    g, gp = sm["g_loai"], sm["gp_loai"]
    return {
        "loai": {
            "f": _num(sm["f_loai"]),
            "p": _num(sm["p_loai"]),
            "gtgd": _num(g),
            "r_f": _num(sm["f_loai"] / g) if g > 0 else None,
            "r_p": _num(sm["p_loai"] / gp) if gp > 0 else None,
            "p_cov": gp / g if g > 0 else None,
        },
        "gom": {"f": _num(sm["f_gom"]), "p": _num(sm["p_gom"])},
    }


def _gates(
    evt: list | None,
    a: dict[str, np.ndarray],
    start: pd.Timestamp,
    price_date: pd.Timestamp,
) -> tuple[str | None, list[str], bool, bool]:
    """(lý do ◌ do sự kiện/gãy điều chỉnh, huy hiệu sự kiện, gãy?, kín room?) cho cửa sổ a."""
    why, ev_badges = (None, []) if evt is None else event_status(evt, start, price_date)
    broke = bool(a["ca_break"].any())
    if broke and not why:
        why = "gãy điều chỉnh giá trong cửa sổ"
    if not a["est"].any():
        why = None  # GTGD lấy hết từ flow_daily (danh nghĩa) → không cần điều chỉnh
    # Kín room = có tổng room (> 0) mà room còn ≤ 0. Tổng room = 0 là VCI không có số (GVR, HT1, PHR).
    ok = ~np.isnan(a["room"]) & ~np.isnan(a["room_total"])
    room, total = a["room"][ok], a["room_total"][ok]
    return why, ev_badges, broke, bool(len(room) and total[-1] > 0 and room[-1] <= 0)


def obv(close: Any, volume: Any) -> list[float]:
    """OBV CHUẨN StockCharts: OBV_t = OBV_{t−1} + sign(C_t − C_{t−1})·V_t, OBV_0 = 0.

    Chỉ minh họa ở màn chi tiết (không bỏ phiếu); phiên thiếu giá/KL góp 0.
    """
    c, v = np.asarray(close, dtype=float), np.asarray(volume, dtype=float)
    step = np.nan_to_num(np.sign(np.diff(c)) * v[1:])
    return [0.0, *np.cumsum(step).tolist()] if len(c) else []


def cmf_series(
    high: Any, low: Any, close: Any, volume: Any, window: int
) -> list[float | None]:
    """CMF trượt `window` phiên (cmf() trên từng cửa sổ); chưa đủ phiên → None."""
    a = [np.asarray(x, dtype=float) for x in (high, low, close, volume)]
    a.append(
        pd.Series(a[2]).ffill().shift(1).to_numpy()
    )  # C_{t−1} của phiên có giá liền trước
    out: list[float | None] = [None] * min(window - 1, len(a[2]))
    for i in range(window - 1, len(a[2])):
        out.append(cmf(*(x[i + 1 - window : i + 1] for x in a))[0])
    return out


def _series(h: pd.DataFrame) -> dict:
    cols = ["close", "gtgd", "f", "f_gom", "p", "p_gom", "lb_vol", "est_val"]
    # cho màn chi tiết: H/L/KL điều chỉnh (CMF, OBV) và KL mua/bán danh nghĩa (bảng thỏa thuận)
    cols += ["high", "low", "vol_adj", "volume"]
    cols += ["f_buy_vol", "f_sell_vol", "p_buy_vol", "p_sell_vol"]
    out: dict[str, list] = {"date": [_iso(d) for d in h.index]}
    for c in cols:
        out[c] = [_num(x) for x in h[c]]
    out["block"] = h["block"].eq(True).tolist()
    out["block_exact"] = h["block_exact"].eq(True).tolist()
    out["excl"] = h["excl"].eq(True).tolist()
    out["flat"] = [bool(a == b) for a, b in zip(h["high"], h["low"])]
    out["form"] = [x if isinstance(x, str) else None for x in h["form"]]
    return out


def _empty(meta: dict, cfg: dict) -> dict:
    status = f"{cfg['window']} phiên: chưa đủ dữ liệu dòng tiền ngành để tóm tắt."
    mode = {
        "sectors": [],
        "totals": {},
        "top_impact": [],
        "top_impact_by_sector": {},
        "conclusion": status,
        "detail": "",
    }
    return {
        "meta": meta,
        "label_counts": {},
        "tickers": {},
        "modes": {m: dict(mode) for m in MODES},
    }


def sector_daily(win: pd.DataFrame, order: list[str]) -> dict:
    """Bản đồ nhiệt Ngành × Ngày (chỉ chế độ Loại, D74): R = Σ ngoại ròng / Σ GTGD của các
    phiên-mã hợp lệ (có ngoại, không bị loại vì thỏa thuận, GTGD > 0) trong từng ngày.

    Trả {sectors, dates, f (VND), r (tỷ lệ)} — ô thiếu dữ liệu là None, không phải 0.
    """
    ok = win["f"].notna() & ~win["excl"].eq(True) & (win["gtgd"] > 0)
    w = win.assign(f_ok=win["f"].where(ok), g_ok=win["gtgd"].where(ok))
    g = w.groupby(["sector", "trade_date"])[["f_ok", "g_ok"]].sum(min_count=1)
    fp = g["f_ok"].unstack().reindex(order)
    gp = g["g_ok"].unstack().reindex(order)
    rp = fp / gp.where(gp > 0)
    dates = sorted(w["trade_date"].unique())
    fp, rp = fp.reindex(columns=dates), rp.reindex(columns=dates)
    return {
        "sectors": order,
        "dates": [_iso(pd.Timestamp(d)) for d in dates],
        "f": [[_num(x) for x in row] for row in fp.to_numpy()],
        "r": [[_num(x) for x in row] for row in rp.to_numpy()],
    }


def ticker_history(
    prices: pd.DataFrame,
    exact: pd.DataFrame | None,
    actions: pd.DataFrame | None,
    cfg: dict,
    now: dt.datetime,
) -> pd.DataFrame:
    """Lịch sử theo ngày của MỘT mã cho biểu đồ chi tiết (D74) — cùng pipeline với thẻ mã
    (clean_flows → flow_daily → GTGD điều chỉnh → cờ thỏa thuận → chọn đường số).

    Cột: open/high/low/close (giá điều chỉnh), vol_match (KL khớp), vol_deal (KL thỏa thuận;
    đường A chỉ là cận dưới → deal_is_lb), f/p (ngoại/tự doanh ròng chế độ Loại = khớp lệnh),
    f_block/p_block (exact: phần thỏa thuận; đường A: cả phiên có thỏa thuận, gồm khớp), dom
    (trong nước suy ra −(f+p), chỉ ngày có cả hai), block, big_block, cmf, event (GDKHQ), source,
    cùng MA20/MA50/MACD/MACD_SIGNAL/MACD_HIST (technical_chart). NULL giữ NaN, không thành 0.
    """
    from valuation.analysis.technical_chart import add_technical_indicators

    df, cm = clean_flows(prices, cfg, now, exact)
    if df.empty:
        return pd.DataFrame()
    ev = stock_events(actions)
    df = _with_exact(df, exact)
    df = adjust_turnover(df, ev)
    df = df.join(block_flags(df, cfg))
    df = _paths(df, cm["today"])
    h = df.set_index("trade_date").sort_index()
    ex = h["has_exact"].eq(True)
    out = h[["open", "high", "low", "close"]].copy()
    out["vol_match"] = h["matched_vol"].where(
        ex & h["matched_vol"].notna(), h["volume"]
    )
    out["vol_deal"] = h["deal_vol"].where(ex, h["lb_vol"].where(h["block"]))
    out["deal_is_lb"] = ~ex
    excl = h["excl"].eq(True)
    out["f"], out["p"] = h["f"].mask(excl), h["p"].mask(excl)
    out["f_block"] = h["fr_net_deal_val"].where(ex, h["f_gom"].where(excl))
    out["p_block"] = h["prop_net_deal_val"].where(ex, h["p_gom"].where(excl))
    both = out["f"].notna() & out["p"].notna()
    out["dom"] = implied_domestic(out["f"], out["p"]).where(both)
    deal_val = h["deal_val"].where(ex, h["est_val"])
    adtv = h["gtgd"].rolling(int(cfg["window"]), min_periods=1).mean()
    out["block"] = h["block"].eq(True)
    out["big_block"] = out["block"] & (
        deal_val >= float(cfg["big_block_adtv_share"]) * adtv
    )
    w = int(cfg["signal"]["cmf_window"])
    out["cmf"] = cmf_series(h["high"], h["low"], h["close"], h["vol_adj"], w)
    tk = ev[ev["ticker"].isin(h["ticker"].unique()) & ev["ex"].notna()]
    names = {**_ADJ, **_UNADJ, **_INFO}
    labels = tk.groupby("ex")["event_type"].agg(
        lambda x: ", ".join(dict.fromkeys(names.get(e, e) for e in x))
    )
    out["event"] = labels.reindex(out.index)
    out["source"] = np.where(ex, "exact", "A")
    ind = add_technical_indicators(
        out[["close"]].assign(high=out["high"], low=out["low"])
    )
    for c in ("MA20", "MA50", "MACD", "MACD_SIGNAL", "MACD_HIST"):
        out[c] = ind[c]
    return out


def compute_money_flow(
    prices: pd.DataFrame,
    exact: pd.DataFrame | None,
    actions: pd.DataFrame | None,
    sectors: dict[str, str],
    cfg: dict,
    now: dt.datetime,
) -> dict:
    """Tính toàn bộ tab "Dòng tiền ngành" cho CẢ 2 chế độ. Kết quả là dict thuần (JSON/pickle được).

    prices/exact/actions: khung theo hợp đồng dữ liệu (1)/(2)/(3); exact có thể None. sectors: mã →
    ngành (market_overview.sector_map()). cfg = load_defaults()["money_flow"]. now: giờ hiện tại
    (naive = giờ VN). Ngày dạng "YYYY-MM-DD"; tiền VND; tỷ lệ là số thập phân (0,02 = 2%).

    {
      "meta": {price_date, flow_date, window, window_start, n_sessions, gap_sessions, universe,
               flow_coverage (số mã có ngoại ở flow_date), prop_coverage, config_hash,
               sources {"A"|"exact"|"mixed": số mã}, block_ticker_sessions, dropped {...},
               provisional_prop (ngày tự doanh tạm | None), disclaimer},
      "label_counts": {"gom"|"xa"|"trung_tinh"|"chua_du": int},
      "tickers": {mã: {
          sector, label {code, text, reason_code, reason}, context (hậu tố giá), ret20, rel20,
          votes {"foreign"|"pv"|"prop": {vote 1|0|-1|None, value, n, reason, chip, ...}},
          badges [str], held_since "YYYY-MM-DD", held_since_truncated, history [[ngày, code]],
          source "A"|"exact"|"mixed",
          flows {"<n phiên>": {"loai": {f, p, gtgd, r_f, r_p, p_cov}, "gom": {f, p}}}  # windows_show
          domestic {value, n}  # D = −(F+P), Loại, phiên có cả F lẫn P
          series {date, close, high, low, vol_adj, volume, gtgd, f, f_gom, p, p_gom,
                  f_buy_vol, f_sell_vol, p_buy_vol, p_sell_vol, lb_vol, est_val, block,
                  block_exact, excl, flat, form}}},
      "modes": {"loai"|"gom": {
          sectors [sector_table], totals {"<n phiên>": {f, p (None = không mã nào có số), p_n
                  (số mã có số tự doanh), gtgd?, p_cov?}, block_n, block_f},
          top_impact [top_impact], top_impact_by_sector {ngành: [...]},
          conclusion str, detail str (dòng phụ chữ nhỏ)}}
    }
    Nhãn/phiếu luôn tính ở chế độ Loại; chế độ Gồm chỉ có tổng tuyệt đối (§4.2).
    """
    W = int(cfg["window"])
    df, cm = clean_flows(prices, cfg, now, exact)
    fd, pd_ = cm["flow_date"], cm["price_date"]
    h_cfg = json.dumps(cfg, sort_keys=True, default=str, ensure_ascii=False)
    meta: dict[str, Any] = {
        "price_date": _iso(pd_) if pd_ is not None else None,
        "flow_date": _iso(fd) if fd is not None else None,
        "window": W,
        "universe": cm["universe"],
        "config_hash": hashlib.sha256(h_cfg.encode()).hexdigest()[:8],
        "dropped": cm["dropped"],
        "disclaimer": DISCLAIMER,
    }
    if fd is None:
        return _empty(meta, cfg)
    ev = stock_events(actions)
    df = _with_exact(df, exact)
    df = adjust_turnover(df, ev)
    df = df.join(block_flags(df, cfg))
    df = _paths(df, cm["today"])
    df["ca_break"] = ca_break(df, cfg)

    cal = cm["sessions"][cm["sessions"] <= fd]
    ends = cm["flow_sessions"][-int(cfg["signal"]["label_history"]) :]
    show = sorted({int(n) for n in cfg["windows_show"]} | {W})
    tickers: dict[str, dict] = {}
    stats, wins = [], []
    ev = ev[ev["anchor"] >= cal[0]]
    ev_by = {t: list(g.itertuples()) for t, g in ev.groupby("ticker")}
    pos_end = cal.get_indexer(ends)
    cols = (*_VOTE_COLS, "f_gom", "p_gom", "fr_current_room", "fr_total_room")
    for t, g in df.groupby("ticker"):
        h = g.set_index("trade_date").reindex(cal)
        a = _arrays(h, cols)
        a["room"] = a.pop("fr_current_room")
        a["room_total"] = a.pop("fr_total_room")
        a["ca_break"] = h["ca_break"].eq(True).to_numpy()
        a["est"] = (h["close"].notna() & h["gtgd_is_est"].eq(True)).to_numpy()
        hist: list[tuple[str, str]] = []
        for e, pe in zip(ends, pos_end):
            ae = {k: x[: pe + 1] for k, x in a.items()}
            st0 = max(0, pe + 1 - W)
            why, ev_badges, broke, room = _gates(
                ev_by.get(t), {k: x[st0:] for k, x in ae.items()}, cal[st0], pd_
            )
            v = _votes(ae, cfg, why, room)
            lab = label(v)
            hist.append((_iso(e), lab["code"]))
        w = h.iloc[-W:]
        aw = {k: x[-W:] for k, x in a.items()}
        closes = h["close"].dropna()
        ret = (
            float(closes.iloc[-1] / closes.iloc[-1 - W] - 1)
            if len(closes) > W
            else None
        )
        since, trunc = label_history(hist)
        _, valid, gap, _ = _masks(aw)
        both = valid & ~np.isnan(aw["p"])
        sm = _sums(aw)
        stats.append(
            {
                "ticker": t,
                "sector": sectors.get(t, "Chưa rõ"),
                "label_code": lab["code"],
                "ret": ret,
                "gaps": int(gap.sum()),
                **sm,
            }
        )
        wins.append(w.assign(ticker=t).rename_axis("trade_date").reset_index())
        n_ex = int((w["close"].notna() & w["has_exact"].eq(True)).sum())
        n_has = int(w["close"].notna().sum())
        dom = implied_domestic(aw["f"][both], aw["p"][both])
        tickers[t] = {
            "sector": sectors.get(t, "Chưa rõ"),
            "label": lab,
            "context": context(ret, cfg),
            "ret20": ret,
            "votes": v,
            "badges": badges(
                w,
                cfg,
                flat=v["pv"]["flat"],
                event_badges=ev_badges,
                broke=broke,
                room_closed=room,
            ),
            "held_since": since,
            "held_since_truncated": trunc,
            "history": [list(x) for x in hist],
            "source": "exact" if n_ex and n_ex == n_has else ("mixed" if n_ex else "A"),
            "flows": {
                str(n): _flows_out(_sums({k: x[-n:] for k, x in a.items()}))
                for n in show
            },
            "domestic": {"value": _num(_nsum(dom)), "n": int(both.sum())},
            "series": _series(h.iloc[-max(show) :]),
        }
    st = pd.DataFrame(stats).set_index("ticker")
    st["ret"] = st["ret"].astype(float)
    st["rel"] = st["ret"] - st["ret"].dropna().median()
    for t, tk in tickers.items():
        tk["rel20"] = _num(st.at[t, "rel"])
    counts = dict(Counter(st["label_code"]))
    win = pd.concat(wins, ignore_index=True)
    win["sector"] = win["ticker"].map(lambda x: sectors.get(x, "Chưa rõ"))

    modes: dict[str, dict] = {}
    for m in MODES:
        rows = sector_table(st, cfg, m)
        totals: dict[str, Any] = {}
        for n in show:
            fs = [tk["flows"][str(n)][m] for tk in tickers.values()]
            f = sum(x["f"] for x in fs if x["f"] is not None)
            ps = [x["p"] for x in fs if x["p"] is not None]
            # NULL = thiếu: không mã nào có số tự doanh → None, không phải 0
            totals[str(n)] = {"f": f, "p": sum(ps) if ps else None, "p_n": len(ps)}
            if m == "loai":
                gs = sum(x["gtgd"] or 0.0 for x in fs)
                gp = sum((x["gtgd"] or 0.0) * (x["p_cov"] or 0.0) for x in fs)
                totals[str(n)] |= {"gtgd": gs, "p_cov": gp / gs if gs > 0 else None}
        blk = win[win["block"].eq(True)]
        totals["block_n"] = len(blk)
        totals["block_f"] = _block_f(blk)
        modes[m] = {
            "sectors": rows,
            "totals": totals,
            "top_impact": top_impact(win, cfg, m),
            "top_impact_by_sector": top_impact(win, cfg, m, by="sector"),
            "conclusion": conclusion(rows, totals[str(W)]["f"], counts, cfg, m),
        }
    modes["loai"]["sector_daily"] = sector_daily(
        win, [r["sector"] for r in modes["loai"]["sectors"]]
    )
    lt, gt = (modes[m]["totals"][str(W)] for m in MODES)

    def _prop(tot: dict, cov: str) -> str:
        return (
            "Tự doanh ◌ chưa có số"
            if tot["p"] is None
            else f"Tự doanh {_ty(tot['p'])}{cov}"
        )

    cov = f" (phủ {lt['p_cov']:.0%} GTGD)" if lt["p_cov"] is not None else ""
    gcov = f" ({gt['p_n']}/{len(tickers)} mã có số)"
    modes["loai"]["detail"] = f"{_prop(lt, cov)} · gồm thỏa thuận: ngoại {_ty(gt['f'])}"
    modes["gom"][
        "detail"
    ] = f"{_prop(gt, gcov)} · loại thỏa thuận: ngoại {_ty(lt['f'])}"
    in_win = cal[-W:]
    last = df[df["trade_date"] == fd]
    prov = df[df["p_prov"] & df["p_raw"].notna()]
    meta |= {
        "window_start": _iso(in_win[0]),
        "n_sessions": len(in_win),
        "gap_sessions": int((~in_win.isin(cm["flow_sessions"])).sum()),
        "flow_coverage": int(last["f"].notna().sum()),
        "prop_coverage": int(last["p_raw"].notna().sum()),
        "sources": dict(Counter(tk["source"] for tk in tickers.values())),
        "block_ticker_sessions": modes["loai"]["totals"]["block_n"],
        "provisional_prop": _iso(prov["trade_date"].max()) if len(prov) else None,
    }
    return {"meta": meta, "label_counts": counts, "tickers": tickers, "modes": modes}
