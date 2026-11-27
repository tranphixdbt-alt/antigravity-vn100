"""Công cụ chỉ đọc thêm cho góc chat AI của web hợp nhất (lát 7, D120).

Học cách TCBS MCP chia công cụ theo nhóm (thị trường, mã, kỹ thuật, cùng ngành; mục 15 của
docs/PLAN_WEB_HOP_NHAT.md) nhưng tính hoàn toàn từ dữ liệu của dự án, không gọi TCBS. Các công cụ này chỉ nằm
trong bộ công cụ của web (`WEB_TOOLS`); bot Discord vẫn dùng đúng `assistant.TOOLS` như cũ.

Phạm vi là rổ VN100 (dữ liệu giá của dự án chỉ có VN100 và VN-Index), không phải toàn sàn:
- độ rộng: số mã VN100 tăng, giảm, đứng giá mỗi phiên so với phiên trước;
- mã dẫn dắt: đóng góp của từng mã vào biến động của rổ VN100 tính theo vốn hóa, ước tính
  đóng góp_i = w_i × r_i × 100 (điểm phần trăm), w_i = vốn hóa đầu kỳ của mã ÷ tổng vốn hóa đầu kỳ của rổ,
  r_i = giá cuối kỳ ÷ giá đầu kỳ − 1; tổng các đóng góp bằng mức thay đổi của rổ theo vốn hóa. Không phải điểm VN-Index
  (VN-Index gồm cả các mã ngoài VN100);
- kỹ thuật: giá so với các đường trung bình giản đơn, RSI14 và MACD(12, 26, 9) đúng công thức của
  `technical_chart.add_technical_indicators`; chỉ mô tả, không gắn nhãn mua bán;
- cùng ngành: các chỉ số của đợt xếp hạng VN100 gần nhất cho các mã cùng ngành.
"""

from __future__ import annotations

from math import isfinite
from typing import Any

import pandas as pd

from valuation.services import assistant

SMA_WINDOWS = (
    5,
    10,
    20,
    50,
    100,
    200,
)  # các đường trung bình giản đơn hay dùng (TCBS cũng dùng bộ này)
WEEKS_52 = 250  # số phiên giao dịch trong khoảng một năm


def _num(v: Any, digits: int = 2) -> float | None:
    return assistant._clean(v, digits)


# ---------- thị trường hôm nay ----------


def tool_market_today() -> dict:
    """Bản tóm tắt tab Hôm nay của web (cùng hàm web_market.market), rút gọn cho AI."""
    from valuation.db.session import SessionLocalRead
    from valuation.services import web_market

    db = SessionLocalRead()
    try:
        m = web_market.market(db)
    finally:
        db.close()
    cs = m.get("chi_so") or {}
    return {
        "nhan_thi_truong": m.get("nhan"),
        "tieu_de": m.get("tieu_de"),
        "gia_den": m.get("gia_den"),
        "du_lieu_cu": m.get("cu"),
        "vn_index": {
            "diem": cs.get("diem"),
            "thay_doi": cs.get("thay_doi"),
            "xu_huong": cs.get("xu_huong"),
            "rsi14": cs.get("rsi"),
            "khang_cu": cs.get("khang_cu"),
            "ho_tro": cs.get("ho_tro"),
        },
        "bon_tru_cot": [
            {"ten": p["ten"], "diem": p["diem"], "tom_tat": p["tom_tat"]}
            for p in m.get("tru_cot") or []
        ],
        "so_phien": m.get("so_phien"),
        "nganh_manh": m.get("nganh_manh"),
        "nganh_yeu": m.get("nganh_yeu"),
        "ma_co_luc": m.get("ma_co_luc"),
        "ghi_chu": "diem trụ cột: 1 thuận, 0 trung tính, -1 bất lợi. Ngành và mã tính trên rổ VN100.",
    }


# ---------- độ rộng ----------


def breadth_counts(closes: pd.DataFrame, sessions: int) -> list[dict]:
    """Số mã tăng, giảm, đứng giá ở mỗi phiên trong `sessions` phiên cuối (so với phiên liền trước).

    `closes`: bảng giá đóng cửa, chỉ mục là ngày (tăng dần), mỗi cột một mã. Mã thiếu giá một trong hai phiên thì
    không tính ở phiên đó.
    """
    if closes.shape[0] < 2:
        return []
    diff = closes.diff().iloc[1:]
    out = []
    for day, row in diff.tail(sessions).iterrows():
        row = row.dropna()
        out.append(
            {
                "ngay": pd.Timestamp(day).date().isoformat(),
                "tang": int((row > 0).sum()),
                "giam": int((row < 0).sum()),
                "dung": int((row == 0).sum()),
            }
        )
    return out


def _vn100_closes() -> pd.DataFrame:
    from valuation.config import load_defaults
    from valuation.db.session import SessionLocalRead
    from valuation.views import market_overview as mo

    db = SessionLocalRead()
    try:
        _, closes, _, _ = mo.load_market_data(db, load_defaults()["market_overview"])
    finally:
        db.close()
    return closes


def tool_breadth(sessions: int) -> dict:
    days = breadth_counts(_vn100_closes(), sessions)
    tang = sum(d["tang"] for d in days)
    tong = sum(d["tang"] + d["giam"] + d["dung"] for d in days)
    return {
        "pham_vi": "rổ VN100, không phải toàn sàn",
        "so_phien": len(days),
        "phien": days,
        "phien_tang_nhieu_hon_giam": sum(1 for d in days if d["tang"] > d["giam"]),
        "ty_le_luot_tang_pct": _num(tang / tong * 100, 1) if tong else None,
    }


# ---------- mã dẫn dắt ----------


def contributions(
    first: pd.Series, last: pd.Series, shares: dict[str, float]
) -> pd.DataFrame:
    """Đóng góp của từng mã vào biến động của rổ theo vốn hóa (điểm phần trăm), xem docstring của mô-đun.

    `first`, `last`: giá đầu và cuối kỳ theo mã; `shares`: số cổ phiếu lưu hành (cùng gốc với giá đã điều chỉnh).
    Mã thiếu giá hay thiếu số cổ phiếu bị bỏ, và không tính vào tổng vốn hóa.
    """
    rows = []
    for t in first.index:
        p0, p1, n = first.get(t), last.get(t), shares.get(t)
        if p0 is None or p1 is None or not n or not (p0 > 0) or not isfinite(float(p1)):
            continue
        rows.append(
            {
                "ma": t,
                "von_hoa_dau": float(p0) * float(n),
                "ty_suat": float(p1) / float(p0) - 1.0,
            }
        )
    df = pd.DataFrame(rows, columns=["ma", "von_hoa_dau", "ty_suat"])
    if df.empty:
        return df.assign(ty_trong=[], dong_gop=[])
    df["ty_trong"] = df["von_hoa_dau"] / df["von_hoa_dau"].sum()
    df["dong_gop"] = df["ty_trong"] * df["ty_suat"] * 100.0
    return df.sort_values("dong_gop", ascending=False).reset_index(drop=True)


def _shares(tickers: list[str]) -> dict[str, float]:
    from valuation.data_access.repo import get_shares_outstanding_repo
    from valuation.db.session import SessionLocalRead

    db = SessionLocalRead()
    out: dict[str, float] = {}
    try:
        for t in tickers:
            try:
                out[t] = get_shares_outstanding_repo(db, t)
            except ValueError:
                continue  # mã không có số cổ phiếu hợp lệ: bỏ khỏi phép tính, ghi số mã đã dùng ở kết quả
    finally:
        db.close()
    return out


def tool_index_movers(sessions: int, top: int) -> dict:
    closes = _vn100_closes()
    if closes.shape[0] <= sessions:
        return {"error": f"Chưa đủ {sessions + 1} phiên giá để tính"}
    window = closes.iloc[-1 - sessions :]
    first, last = window.iloc[0], window.iloc[-1]
    df = contributions(first, last, _shares(list(closes.columns)))
    rows = lambda d: [
        {
            "ma": r.ma,
            "dong_gop_diem_pct": _num(r.dong_gop, 2),
            "ty_suat_pct": _num(r.ty_suat * 100, 1),
        }
        for r in d.itertuples()
    ]
    return {
        "pham_vi": "rổ VN100 tính theo vốn hóa (số cổ phiếu lưu hành × giá), ước tính; không phải điểm VN-Index",
        "tu_ngay": pd.Timestamp(window.index[0]).date().isoformat(),
        "den_ngay": pd.Timestamp(window.index[-1]).date().isoformat(),
        "so_ma_tinh": len(df),
        "ro_thay_doi_pct": _num(df["dong_gop"].sum(), 2) if len(df) else None,
        "keo_len": rows(df.head(top)),
        "keo_xuong": rows(df.sort_values("dong_gop").head(top)),
    }


# ---------- kỹ thuật ----------


def tech_summary(close: pd.Series) -> dict:
    """Giá so với các đường trung bình, RSI14, MACD; chỉ mô tả trạng thái, không phải tín hiệu mua bán."""
    from valuation.analysis.technical_chart import add_technical_indicators

    close = close.dropna().astype(float)
    if close.empty:
        return {"error": "Không có giá"}
    last = float(close.iloc[-1])
    above, values = {}, {}
    for w in SMA_WINDOWS:
        if len(close) >= w:
            sma = float(close.tail(w).mean())
            values[str(w)] = _num(sma, 0)
            above[str(w)] = last > sma
    ind = add_technical_indicators(
        pd.DataFrame({"close": close, "high": close, "low": close})
    ).iloc[-1]
    year = close.tail(WEEKS_52)
    hi, lo = float(year.max()), float(year.min())
    return {
        "gia": _num(last, 0),
        "duong_trung_binh": values,
        "gia_tren_duong": above,
        "so_duong_gia_dang_tren": sum(above.values()),
        "so_duong_tinh_duoc": len(above),
        "rsi14": _num(ind.get("RSI14"), 1),
        "macd": _num(ind.get("MACD"), 2),
        "macd_tin_hieu": _num(ind.get("MACD_SIGNAL"), 2),
        "macd_tren_tin_hieu": (
            None
            if pd.isna(ind.get("MACD")) or pd.isna(ind.get("MACD_SIGNAL"))
            else bool(ind["MACD"] > ind["MACD_SIGNAL"])
        ),
        "dinh_1_nam": _num(hi, 0),
        "day_1_nam": _num(lo, 0),
        "cach_dinh_pct": _num((last / hi - 1) * 100, 1) if hi else None,
        "cach_day_pct": _num((last / lo - 1) * 100, 1) if lo else None,
        "so_phien_du_lieu": len(close),
    }


def tool_technical(ticker: str) -> dict:
    from valuation.db.models import PricesDaily
    from valuation.db.session import SessionLocalRead

    db = SessionLocalRead()
    try:
        rows = (
            db.query(PricesDaily.trade_date, PricesDaily.close)
            .filter(PricesDaily.ticker == ticker, PricesDaily.close.isnot(None))
            .order_by(PricesDaily.trade_date.desc())
            .limit(WEEKS_52 + 50)
            .all()
        )
    finally:
        db.close()
    if not rows:
        return {"ticker": ticker, "error": "Không có giá"}
    s = pd.Series({d: float(c) for d, c in rows}).sort_index()
    return {
        "ticker": ticker,
        "ngay": pd.Timestamp(s.index[-1]).date().isoformat(),
        **tech_summary(s),
        "ghi_chu": "Mô tả trạng thái kỹ thuật, không phải tín hiệu mua bán.",
    }


# ---------- cùng ngành ----------


def peer_table(rows: list[dict], ticker: str) -> dict:
    """Các mã cùng ngành với `ticker` trong đợt xếp hạng, và hạng của mã đó theo ROE, tăng trưởng doanh thu (1 = cao nhất).

    Mã có `blockers` (chưa qua cổng công bố) thì không đưa giá trị hợp lý và upside.
    """
    own = next((r for r in rows if r.get("ticker") == ticker), None)
    if own is None:
        return {"error": f"{ticker} không có trong đợt xếp hạng"}
    peers = [
        r for r in rows if r.get("sector") == own.get("sector") and not r.get("error")
    ]

    def row(r: dict) -> dict:
        m, prof = r.get("metrics") or {}, r.get("profiles") or {}
        mo = not r.get("blockers")
        return {
            "ma": r.get("ticker"),
            "ten": r.get("name"),
            "roe_pct": (
                _num((m.get("roe") or 0) * 100, 1) if m.get("roe") is not None else None
            ),
            "tang_truong_doanh_thu_pct": (
                _num(m["revenue_cagr"] * 100, 1)
                if m.get("revenue_cagr") is not None
                else None
            ),
            "no_xau_pct": _num(m["npl"] * 100, 2) if m.get("npl") is not None else None,
            "diem_phong_thu": _num((prof.get("defensive") or {}).get("score"), 1),
            "diem_tich_san": _num((prof.get("accumulation") or {}).get("score"), 1),
            "upside_pct": _num(r.get("upside_pct"), 1) if mo else None,
        }

    table = [row(r) for r in peers]
    # cột trống ở mọi mã trong ngành (vd nợ xấu ngoài ngân hàng) thì bỏ, để AI không nhắc tới chỉ số không áp dụng;
    # upside giữ lại vì trống ở đây nghĩa là chưa công bố
    empty = {
        k
        for k in table[0]
        if k not in ("ma", "ten", "upside_pct") and all(x[k] is None for x in table)
    }
    table = [{k: v for k, v in x.items() if k not in empty} for x in table]

    def rank(key: str) -> int | None:
        vals = [x.get(key) for x in table if x.get(key) is not None]
        mine = next(x.get(key) for x in table if x["ma"] == ticker)
        return None if mine is None else 1 + sum(1 for v in vals if v > mine)

    return {
        "ma": ticker,
        "nganh": own.get("sector"),
        "so_ma_cung_nganh": len(table),
        "hang_roe": rank("roe_pct"),
        "hang_tang_truong_doanh_thu": rank("tang_truong_doanh_thu_pct"),
        "cac_ma": table,
        "ghi_chu": "Hạng 1 = cao nhất trong ngành. upside trống khi mã chưa qua cổng công bố.",
    }


def tool_peers(ticker: str) -> dict:
    from valuation.services.ranking_store import latest_snapshot

    snap = latest_snapshot() or {}
    if not snap.get("rows"):
        return {"error": "Chưa có đợt xếp hạng VN100 nào"}
    out = peer_table(list(snap["rows"]), ticker)
    out["dot_xep_hang"] = snap.get("run_id")
    return out


# ---------- khối ngoại ----------

TY = 1e9  # cột khối ngoại trong prices_daily tính bằng đồng; công cụ trả tỷ đồng


def _foreign_frame(days_back: int) -> pd.DataFrame:
    """Khối ngoại của rổ VN100 (đồng), mỗi dòng một mã một phiên có giá. NaN = phiên đó nguồn không có khối ngoại."""
    from datetime import timedelta

    from valuation.db.models import PricesDaily, Ticker
    from valuation.db.session import SessionLocalRead

    since = assistant._today() - timedelta(days=days_back)
    db = SessionLocalRead()
    try:
        q = (
            db.query(
                PricesDaily.ticker,
                PricesDaily.trade_date,
                PricesDaily.foreign_buy_val,
                PricesDaily.foreign_sell_val,
                PricesDaily.foreign_net_val,
                PricesDaily.foreign_net_vol,
            )
            .join(Ticker, Ticker.ticker == PricesDaily.ticker)
            .filter(
                Ticker.is_vn100,
                PricesDaily.trade_date >= since,
                PricesDaily.close.isnot(None),
            )
        )
        df = pd.DataFrame(
            q.all(), columns=["ma", "ngay", "mua", "ban", "rong", "rong_kl"]
        )
    finally:
        db.close()
    for c in ("mua", "ban", "rong", "rong_kl"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def _last_days(df: pd.DataFrame, sessions: int) -> list:
    return sorted(df["ngay"].unique())[-sessions:]


def foreign_ticker_table(df: pd.DataFrame, ticker: str, sessions: int) -> dict:
    """Khối ngoại từng phiên của một mã trong `sessions` phiên giao dịch gần nhất của rổ (tỷ đồng).

    Phiên mã có giá mà không có số khối ngoại thì ghi `thieu`, không tính vào tổng.
    """
    days = _last_days(df, sessions)
    own = df[(df["ma"] == ticker) & df["ngay"].isin(days)].set_index("ngay")
    rows, missing = [], []
    for d in days:
        r = own.loc[d] if d in own.index else None
        if r is None or pd.isna(r["rong"]):
            missing.append(pd.Timestamp(d).date().isoformat())
            continue
        rows.append(
            {
                "ngay": pd.Timestamp(d).date().isoformat(),
                "mua_ty": _num(r["mua"] / TY),
                "ban_ty": _num(r["ban"] / TY),
                "rong_ty": _num(r["rong"] / TY),
                "rong_cp": _num(r["rong_kl"], 0),
            }
        )
    net = own.loc[own.index.isin(days), "rong"].sum(min_count=1) / TY
    return {
        "ma": ticker,
        "don_vi": "tỷ đồng; gồm khớp lệnh và thỏa thuận",
        "so_phien": len(days),
        "phien": rows,
        "phien_thieu": missing,
        "tong_rong_ty": _num(net),
        "phien_mua_rong": sum(1 for x in rows if (x["rong_ty"] or 0) > 0),
        "phien_ban_rong": sum(1 for x in rows if (x["rong_ty"] or 0) < 0),
    }


def foreign_rank(df: pd.DataFrame, sessions: int, top: int) -> dict:
    """Mã VN100 khối ngoại mua ròng, bán ròng nhiều nhất cộng dồn `sessions` phiên (tỷ đồng)."""
    days = _last_days(df, sessions)
    w = df[df["ngay"].isin(days)]
    have = w.groupby("ngay")["rong"].apply(lambda s: s.notna().mean())
    missing = [
        pd.Timestamp(d).date().isoformat() for d, share in have.items() if share < 0.5
    ]
    net = w.groupby("ma")["rong"].sum(min_count=1).dropna() / TY
    row = lambda s: [{"ma": m, "rong_ty": _num(v)} for m, v in s.items()]
    return {
        "pham_vi": "rổ VN100, không phải toàn sàn; gồm khớp lệnh và thỏa thuận",
        "tu_ngay": pd.Timestamp(days[0]).date().isoformat() if days else None,
        "den_ngay": pd.Timestamp(days[-1]).date().isoformat() if days else None,
        "so_phien": len(days),
        "phien_thieu_khoi_ngoai": missing,
        "ro_rong_ty": _num(net.sum()) if len(net) else None,
        "mua_rong_nhieu_nhat": row(net[net > 0].sort_values(ascending=False).head(top)),
        "ban_rong_nhieu_nhat": row(net[net < 0].sort_values().head(top)),
    }


def tool_foreign_flow(ticker: str, sessions: int) -> dict:
    return foreign_ticker_table(
        _foreign_frame(int(sessions * 1.6) + 15), ticker, sessions
    )


def tool_foreign_top(sessions: int, top: int) -> dict:
    return foreign_rank(_foreign_frame(int(sessions * 1.6) + 15), sessions, top)


# ---------- chứng quyền, ETF, hợp đồng tương lai (người dùng 27/11/2026: "cho Ếch đọc hết số liệu") ----------
# Lấy đúng số các tab của web đang hiện, từ dịch vụ chứng quyền (`web_cw.fetch`, repo cw_scanner); không tính lại gì.

CW_GROUPS = {"nen_xem_xet": "NÊN XEM XÉT", "theo_doi": "THEO DÕI", "bo_qua": "BỎ QUA"}
CW_SORTS = {
    "re": ("dat_re", False),
    "don_bay": ("don_bay", True),
    "kl": ("kl", True),
    "hoa_von": ("hoa_von", False),
}
CW_FIELDS = (
    "ma",
    "cs",
    "tcph",
    "con_ngay",
    "gd_cuoi",
    "gia_cs",
    "gia_th",
    "ty_le",
    "gia_mua",
    "hop_ly",
    "dat_re",
    "hoa_von",
    "don_bay",
    "delta",
    "hv",
    "iv",
    "iv_hv",
    "kl",
    "kl_chao_ban",
    "nhom",
    "ly_do",
)
CW_NOTE = (
    "dat_re: % giá mua so với giá hợp lý Black-Scholes theo HV (âm là rẻ hơn); hoa_von: % cổ phiếu cơ sở phải tăng để"
    " hòa vốn tới đáo hạn; hv, iv: %/năm; iv_hv: điểm %; con_ngay: ngày tới đáo hạn; giá đồng. Số lúc quét."
)


def _cw_fetch(path: str) -> Any:
    from valuation.services import web_cw

    try:
        return web_cw.fetch(path)
    except web_cw.CwServiceError as exc:
        return {"error": f"Dịch vụ chứng quyền: {exc.detail}"}


def _pick(row: dict, keys: tuple[str, ...]) -> dict:
    return {k: row.get(k) for k in keys}


def cw_table(
    data: dict, underlying: str | None, group: str | None, sort: str | None, top: int
) -> dict:
    """Lọc, xếp danh sách chứng quyền của lần quét mới nhất. Không có cách xếp: giữ thứ tự của tab (theo nhóm)."""
    if data.get("error") or not data.get("co"):
        return {"error": data.get("error") or "Chưa có lần quét chứng quyền nào"}
    rows = list(data["cw"])
    if underlying:
        rows = [r for r in rows if r.get("cs") == underlying]
    if group:
        rows = [r for r in rows if r.get("nhom") == CW_GROUPS[group]]
    if sort:
        key, desc = CW_SORTS[sort]
        rows = [r for r in rows if r.get(key) is not None]
        rows.sort(key=lambda r: float(r[key]), reverse=desc)
    return {
        "lan_quet": data.get("lan_quet"),
        "quet_cu": data.get("cu"),
        "tong_so_cw": data.get("tong"),
        "so_theo_nhom": {g["ten"]: g["so"] for g in data.get("nhom", [])},
        "tieu_chi_nhom": "Nên xem xét = đạt cả 4 tiêu chí (ngày còn lại, IV − HV, % hòa vốn, khối lượng); Theo dõi = trượt 1",
        "nguong": data.get("nguong"),
        "so_dong_khop_loc": len(rows),
        "cw": [_pick(r, CW_FIELDS) for r in rows[:top]],
        "ghi_chu": CW_NOTE,
    }


def tool_cw_list(
    underlying: str | None, group: str | None, sort: str | None, top: int
) -> dict:
    return cw_table(_cw_fetch("/api/chung-quyen"), underlying, group, sort, top)


def tool_cw_detail(code: str) -> dict:
    d = _cw_fetch(f"/api/chung-quyen/{code}")
    if d.get("error"):
        return d
    return {
        "lan_quet": d.get("lan_quet"),
        "cw": _pick(d["cw"], CW_FIELDS),
        "tieu_chi": d.get("tieu_chi"),
        "ngay_dao_han": d.get("ngay_dao_han"),
        "lai_suat_phi_rui_ro_pct": d.get("r"),
        "cung_co_phieu_co_so": [
            _pick(
                r,
                (
                    "ma",
                    "tcph",
                    "con_ngay",
                    "gia_mua",
                    "dat_re",
                    "iv_hv",
                    "hoa_von",
                    "nhom",
                ),
            )
            for r in d.get("cung_cs", [])[:12]
        ],
        "ghi_chu": CW_NOTE,
    }


ETF_FIELDS = (
    "Mã",
    "Chỉ số",
    "Đạt",
    "Giá chào bán",
    "KL chào bán",
    "iNAV",
    "Chiết khấu mua được %",
    "Lãi ròng nếu về NAV %",
    "Mua được đạt ngưỡng (đ)",
    "CL NAV trung vị 20P %",
    "CL NAV trung vị 1N %",
    "GTGD TB20 (tỷ)",
    "Phí quản lý %",
    "Cảnh báo",
)


def etf_table(data: dict, code: str | None, top: int) -> dict:
    if data.get("error") or not data.get("co"):
        return {"error": data.get("error") or "Chưa có kết quả ETF"}
    rows = data["chiet_khau"]["dong"]  # đã xếp theo lãi ròng nếu về NAV, cao trước
    if code:
        rows = [r for r in rows if r.get("Mã") == code]
        if not rows:
            return {"error": f"Không có quỹ {code} trong bảng ETF"}
    return {
        "luc": data.get("luc"),
        "so_quy": data.get("so_quy"),
        "nguong": data.get("nguong"),
        "so_quy_dat_nguong": sum(1 for r in data["chiet_khau"]["dong"] if r.get("Đạt")),
        "quy": [_pick(r, ETF_FIELDS) for r in rows[:top]],
        "chi_so": [
            _pick(
                r,
                (
                    "Mã",
                    "Giá",
                    "1T %",
                    "3T %",
                    "1N %",
                    "Xu hướng",
                    "RSI14",
                    "Cách đỉnh 1N %",
                ),
            )
            for r in data["chi_so"]["dong"]
        ],
        "ghi_chu": "Chiết khấu dương: mua được dưới iNAV. Đạt: lãi ròng nếu về NAV ≥ ngưỡng và mua được ≥ mức tối thiểu. CL = chênh lệch giá so với NAV.",
    }


def tool_etf(code: str | None, top: int) -> dict:
    return etf_table(_cw_fetch("/api/etf"), code, top)


def tool_futures() -> dict:
    d = _cw_fetch("/api/phai-sinh")
    if d.get("error"):
        return d
    keys = (
        "ma",
        "thang",
        "gia",
        "ngay_gia",
        "kl",
        "gd_cuoi",
        "con_ngay",
        "so_phien",
        "basis",
        "basis_pt",
        "nam_hoa",
        "ky_quy",
    )
    return {
        "luc": d.get("luc"),
        "he_so_nhan": d.get("he_so_nhan"),
        "lai_suat_phi_rui_ro_pct": d.get("r"),
        "chi_so": [
            {
                "chi_so": n["chi_so"],
                "diem": n["diem"],
                "ngay": n["ngay"],
                "ty_le_ky_quy_pct": n["ty_le_ky_quy"],
                "hop_dong": [_pick(h, keys) for h in n["hop_dong"]],
            }
            for n in d.get("nhom", [])
        ],
        "canh_bao": d.get("canh_bao"),
        "ghi_chu": "basis = giá hợp đồng − điểm chỉ số (điểm); basis_pt, nam_hoa: %; ky_quy: đồng ký quỹ ban đầu mỗi hợp đồng.",
    }


def tool_alerts() -> dict:
    """Cảnh báo bất thường đang mua được, cùng số với chuông Cảnh báo của web."""
    from valuation.services import web_alerts, web_cw

    try:
        c = web_alerts._shared(False)
    except web_cw.CwServiceError as exc:
        return {"error": f"Dịch vụ chứng quyền: {exc.detail}"}
    hd = (
        "bi_danh",
        "chi_so",
        "gia",
        "basis",
        "hop_ly",
        "lech",
        "lai_khoa",
        "tin_hieu",
        "ly_do",
    )
    return {
        "luc": c.get("luc"),
        "ngoai_gio": c.get("ngoai_gio"),
        "nguong": c.get("nguong"),
        "cw_re_bat_thuong": (c.get("cw") or [])[:10],
        "cw_giam_manh_hom_nay": (c.get("giam_manh") or [])[:10],
        "etf_bat_thuong": (c.get("etf") or [])[:10],
        "hop_dong_tuong_lai": [_pick(h, hd) for h in c.get("hd") or []],
        "loi": c.get("loi") or [],
    }


WEB_TOOLS: dict = {
    **assistant.TOOLS,
    "market_today": (
        tool_market_today,
        "Thị trường hôm nay: nhãn thị trường, bốn trụ cột, VN-Index (xu hướng, kháng cự, hỗ trợ), ngành mạnh yếu, mã có lực.",
        "{}",
    ),
    "breadth": (
        tool_breadth,
        "Độ rộng thị trường: số mã VN100 tăng, giảm, đứng giá mỗi phiên trong N phiên gần nhất.",
        '{"sessions": 10}',
    ),
    "index_movers": (
        tool_index_movers,
        "Mã kéo rổ VN100 lên và xuống nhiều nhất trong N phiên (ước tính theo vốn hóa).",
        '{"sessions": 20, "top": 5}',
    ),
    "technical": (
        tool_technical,
        "Trạng thái kỹ thuật của 1 mã: giá so với đường trung bình 5-200 phiên, RSI14, MACD, đỉnh đáy 1 năm.",
        '{"ticker": "HPG"}',
    ),
    "foreign_flow": (
        tool_foreign_flow,
        "Khối ngoại mua, bán, ròng từng phiên của 1 mã VN100 trong N phiên gần nhất (tỷ đồng), tổng ròng.",
        '{"ticker": "FPT", "sessions": 10}',
    ),
    "foreign_top": (
        tool_foreign_top,
        "Mã VN100 khối ngoại mua ròng, bán ròng nhiều nhất cộng dồn N phiên, và tổng ròng cả rổ.",
        '{"sessions": 5, "top": 5}',
    ),
    "cw_list": (
        tool_cw_list,
        "Chứng quyền của lần quét mới nhất: lọc theo mã cơ sở, nhóm (nen_xem_xet, theo_doi, bo_qua), xếp theo re (rẻ nhất so với giá hợp lý), don_bay, kl, hoa_von; số theo nhóm.",
        '{"underlying": "VRE"|null, "group": "nen_xem_xet"|null, "sort": "re"|null, "top": 10}',
    ),
    "cw_detail": (
        tool_cw_detail,
        "Một chứng quyền: giá, giá hợp lý, đắt rẻ, IV, HV, đòn bẩy, hòa vốn, 4 tiêu chí, ngày đáo hạn, các chứng quyền cùng mã cơ sở.",
        '{"code": "CVRE2609"}',
    ),
    "etf": (
        tool_etf,
        "Quỹ ETF: chiết khấu so với iNAV, lãi ròng nếu về NAV, quỹ đạt ngưỡng mua dưới NAV, biến động các chỉ số; code để xem 1 quỹ.",
        '{"code": "FUEVFVND"|null, "top": 10}',
    ),
    "futures": (
        tool_futures,
        "Hợp đồng tương lai VN30, VN100: giá, basis, basis năm hóa, ngày đáo hạn, ký quỹ.",
        "{}",
    ),
    "alerts": (
        tool_alerts,
        "Cảnh báo hôm nay: chứng quyền rẻ bất thường, chứng quyền giảm mạnh, ETF bất thường, hợp đồng tương lai lệch giá hợp lý.",
        "{}",
    ),
    "peers": (
        tool_peers,
        "So 1 mã với các mã cùng ngành: ROE, tăng trưởng doanh thu, điểm phòng thủ và tích sản, upside.",
        '{"ticker": "VCB"}',
    ),
}
