"""Tab "Dòng tiền ngành" VN100 (D73, docs/PLAN_SECTOR_FLOW.md v2.1 §1, §3, §4, §5, §7).

Chỉ đọc: session DB do app truyền vào + snapshot xếp hạng VN100. Không gọi mạng, không AI, không ghi
DB. Mọi con số tính ở valuation/analysis/money_flow.py; file này nạp dữ liệu, cache và hiển thị.
Mô tả dữ liệu quá khứ, không phải khuyến nghị, không dự báo giá.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import textwrap
from functools import partial
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from valuation.analysis import money_flow as mf
from valuation.config import load_defaults
from valuation.services.ranking_store import latest_snapshot
from valuation.views import money_flow_lessons as lessons
from valuation.views.device import is_phone, phone_collapsible, render_alerts
from valuation.views.market_overview import _chg, _vi, sector_map

_VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
_MODES = {"Loại": "loai", "Gồm": "gom"}
_LABEL_SYM = {
    "gom": "▲",
    "xa": "▼",
    "noi_gom": "△",
    "noi_xa": "▽",
    "trung_tinh": "0",
    "chua_du": "◌",
}
_LABEL_COLOR = {
    "gom": "green",
    "xa": "red",
    "noi_gom": "green",
    "noi_xa": "red",
    "trung_tinh": "gray",
    "chua_du": "gray",
}
_VOTE_COLOR: dict[int | None, str] = {1: "green", -1: "red", 0: "gray", None: "gray"}
_ALL = "Tất cả"
_SCAN = "«Quét VN100 hàng tuần»"  # đúng tên nút ở thanh bên (select_ticker.py)
_MD_ESC = str.maketrans({c: "\\" + c for c in "\\`*_~$[]"})


def _now_vn() -> dt.datetime:
    return dt.datetime.now(_VN_TZ).replace(tzinfo=None)


def _md(s: Any) -> str:
    """Thoát ký tự markdown (vd «ước ~» hai lần trên một dòng thành gạch ngang)."""
    return str(s).translate(_MD_ESC)


def _d(iso: str | None) -> str:
    return mf._dm(iso) if iso else "—"


def _arrow(x: float) -> str:
    return "▲" if x > 0 else ("▼" if x < 0 else "0")


def _tybn(x: float | None) -> float | None:
    return None if x is None else x / 1e9


def _pct100(x: float | None) -> float | None:
    return None if x is None else x * 100


# ---------- nạp dữ liệu (chỉ đọc) ----------
def has_flow_daily(db: Any) -> bool:
    from sqlalchemy import inspect

    return bool(inspect(db.get_bind()).has_table("flow_daily"))


def _price_cols() -> dict[str, Any]:
    from valuation.db.models import PricesDaily as P

    return {
        "ticker": P.ticker,
        "trade_date": P.trade_date,
        "open": P.open,
        "high": P.high,
        "low": P.low,
        "close": P.close,
        "volume": P.volume,
        "value": P.value,
        "f_buy_val": P.foreign_buy_val,
        "f_sell_val": P.foreign_sell_val,
        "f_net_val": P.foreign_net_val,
        "f_buy_vol": P.foreign_buy_vol,
        "f_sell_vol": P.foreign_sell_vol,
        "p_buy_val": P.proprietary_buy_val,
        "p_sell_val": P.proprietary_sell_val,
        "p_net_val": P.proprietary_net_val,
        "p_buy_vol": P.proprietary_buy_vol,
        "p_sell_vol": P.proprietary_sell_vol,
    }


def load_flow_panel(
    db: Any, cfg: dict, ticker: str | None = None, days: int | None = None
) -> dict[str, Any]:
    """Panel theo hợp đồng dữ liệu D73: prices (1), exact (2) hoặc None, actions (3).

    1 SELECT prices_daily JOIN tickers.is_vn100 trong `history_days` ngày lịch; corporate_actions của
    VN100; flow_daily chỉ khi bảng tồn tại (sqlalchemy.inspect) và có dòng. NULL giữ NaN.
    """
    from sqlalchemy import select, true

    from valuation.db.models import CorporateAction as CA
    from valuation.db.models import PricesDaily, Ticker

    start = _now_vn().date() - dt.timedelta(days=int(days or cfg["history_days"]))
    one = (lambda col: col == ticker) if ticker else (lambda col: true())
    cols = _price_cols()
    rows = (
        db.query(*cols.values())
        .join(Ticker, Ticker.ticker == PricesDaily.ticker)
        .filter(
            Ticker.is_vn100, PricesDaily.trade_date >= start, one(PricesDaily.ticker)
        )
        .all()
    )
    prices = pd.DataFrame.from_records(rows, columns=list(cols), coerce_float=True)
    prices["trade_date"] = pd.to_datetime(prices["trade_date"])
    acols = {
        "ticker": CA.ticker,
        "event_type": CA.event_type,
        "ex_right_date": CA.ex_right_date,
        "record_date": CA.record_date,
        "announcement_date": CA.announcement_date,
        "exercise_ratio": CA.exercise_ratio,
    }
    arows = (
        db.query(*acols.values())
        .join(Ticker, Ticker.ticker == CA.ticker)
        .filter(Ticker.is_vn100, one(CA.ticker))
        .all()
    )
    actions = pd.DataFrame.from_records(arows, columns=list(acols), coerce_float=True)
    exact = None
    if has_flow_daily(db):
        from valuation.db.flow_models import flow_daily as fd

        res = db.execute(
            select(fd)
            .join(Ticker, Ticker.ticker == fd.c.ticker)
            .where(Ticker.is_vn100, fd.c.trade_date >= start, one(fd.c.ticker))
        )
        cols_fd = list(res.keys())
        exact = pd.DataFrame.from_records(
            res.fetchall(), columns=cols_fd, coerce_float=True
        )
        exact = exact if len(exact) else None
    return {"prices": prices, "exact": exact, "actions": actions}


def panel_key(db: Any, cfg_all: dict, snap: dict | None, now: dt.datetime) -> tuple:
    """Khóa cache (§7): ngày giá cuối, ngày cuối có ngoại, số dòng/số ô ngoại/tự doanh, số sự kiện,
    flow_daily (có/không, số dòng, fetched_at mới nhất), run_id snapshot, hash cấu hình money_flow +
    market_overview, ngày hôm nay và đã qua session_close chưa (phiên hôm nay bị bỏ khi dở phiên).
    Thêm checksum rẻ để bắt UPDATE tại chỗ: tổng ngoại/tự doanh/close/KL, sự kiện (updated_at mới
    nhất, số ex_right_date đã điền) và hash bảng mã → ngành.
    """
    from sqlalchemy import case, func, select

    from valuation.db.models import CorporateAction, Ticker
    from valuation.db.models import PricesDaily as P

    cfg = cfg_all["money_flow"]
    start = now.date() - dt.timedelta(days=int(cfg["history_days"]))
    agg = (
        db.query(
            func.max(P.trade_date),
            func.max(case((P.foreign_net_val.isnot(None), P.trade_date))),
            func.count(),
            func.count(P.foreign_net_val),
            func.count(P.proprietary_net_val),
            func.sum(P.foreign_net_val),
            func.sum(P.proprietary_net_val),
            func.sum(P.close),
            func.sum(P.volume),
        )
        .join(Ticker, Ticker.ticker == P.ticker)
        .filter(Ticker.is_vn100, P.trade_date >= start)
        .one()
    )
    CA = CorporateAction
    ca = db.query(
        func.count(), func.max(CA.updated_at), func.count(CA.ex_right_date)
    ).one()
    sectors = json.dumps(sector_map(), sort_keys=True, ensure_ascii=False)
    flow = None
    if has_flow_daily(db):
        from valuation.db.flow_models import flow_daily as fd

        flow = tuple(
            db.execute(
                select(func.count(), func.max(fd.c.fetched_at)).where(
                    fd.c.trade_date >= start
                )
            ).one()
        )
    blob = json.dumps(
        [cfg, cfg_all.get("market_overview")],
        sort_keys=True,
        default=str,
        ensure_ascii=False,
    )
    after_close = now.time() >= dt.time.fromisoformat(cfg["session_close"])
    return (
        *(str(x) for x in agg),
        *(str(x) for x in ca),
        hashlib.sha256(sectors.encode()).hexdigest()[:8],
        str(flow),
        (snap or {}).get("run_id"),
        hashlib.sha256(blob.encode()).hexdigest()[:8],
        now.date().isoformat(),
        after_close,
    )


def upsides(db: Any, snap: dict | None) -> dict:
    """Upside phụ như tab VN100 (ranking_table: giá trị hợp lý của đợt ÷ giá mới nhất trong DB − 1)."""
    if not snap:
        return {"rows": {}, "source": None}
    from valuation.analysis.investment_ranking import load_ranking_config
    from valuation.views.vn100_ranking import (
        market_data,
        ranking_table,
        snapshot_closes,
    )

    table = ranking_table(
        snap,
        market_data(db),
        snap.get("config") or load_ranking_config(),
        snap_closes=snapshot_closes(db, snap),
    )
    rows = {
        r["Mã"]: {
            "upside": (
                None if pd.isna(r["Upside (%)"]) else float(r["Upside (%)"]) / 100
            ),
            "note": r["Ghi chú"],
        }
        for r in table.to_dict("records")
    }
    done = str(snap.get("completed_at", ""))[:10]
    when = dt.date.fromisoformat(done).strftime("%d/%m/%Y") if done else "?"
    return {"rows": rows, "source": f"đợt định giá VN100 {when}"}


@st.cache_data(show_spinner="Đang tính dòng tiền ngành…", max_entries=4)
def _compute(key: tuple, _db: Any, _snap: dict | None) -> dict:
    """Tính một lần cho mỗi `key` (st.cache_data không băm tham số bắt đầu bằng _)."""
    cfg = load_defaults()["money_flow"]
    p = load_flow_panel(_db, cfg)
    res = mf.compute_money_flow(
        p["prices"], p["exact"], p["actions"], sector_map(), cfg, _now_vn()
    )
    res["upside"] = upsides(_db, _snap)
    return res


# ---------- định dạng (thuần, test được) ----------
def status_line(meta: dict, mode: str) -> str:
    """Dải trạng thái (truy vết AGENTS #5): ngày giá/dòng tiền, độ phủ, cửa sổ, nguồn, cấu hình."""
    src = meta.get("sources") or {}
    n_ex = src.get("exact", 0) + src.get("mixed", 0)
    tail = [
        (
            f"flow_daily theo job hằng ngày; prices_daily khi bấm {_SCAN}"
            if n_ex
            else f"chỉ cập nhật khi bấm {_SCAN}"
        ),
        f"cấu hình money_flow #{meta['config_hash']} (D73)",
    ]
    if meta.get("flow_date") is None:
        head = (
            f"Giá đến {_d(meta['price_date'])}"
            if meta.get("price_date")
            else "Chưa có giá VN100"
        )
        return " · ".join([head, "chưa có phiên đủ số khối ngoại", *tail])
    source = (
        f"nguồn flow_daily {n_ex} mã + prices_daily" if n_ex else "nguồn prices_daily"
    )
    word = "Loại" if mode == "loai" else "Gồm"
    return " · ".join(
        [
            f"Giá đến {_d(meta['price_date'])}",
            (
                f"Dòng tiền đến {_d(meta['flow_date'])} (ngoại {meta['flow_coverage']}/"
                f"{meta['universe']} mã, tự doanh {meta['prop_coverage']} mã)"
            ),
            f"{meta['n_sessions']} phiên từ {_d(meta['window_start'])}",
            f"{word} thỏa thuận",
            f"{meta['gap_sessions']} phiên thủng",
            source,
            *tail,
        ]
    )


def flow_alerts(meta: dict) -> list[tuple[str, str, str | None]]:
    out: list[tuple[str, str, str | None]] = []
    if meta.get("gap_sessions"):
        out.append(
            (
                "warning",
                (
                    f"Cửa sổ có {meta['gap_sessions']} phiên thiếu số khối ngoại (có giá) — mã bị thủng "
                    f"có phiếu Ngoại ◌. Bấm {_SCAN} ở thanh bên để cập nhật."
                ),
                ":material/warning:",
            )
        )
    if meta.get("flow_date") and meta["flow_date"] != meta.get("price_date"):
        out.append(
            (
                "info",
                (
                    f"Dòng tiền mới đến {_d(meta['flow_date'])}, giá đến {_d(meta['price_date'])}: "
                    "nhãn và tổng tính đến ngày dòng tiền."
                ),
                ":material/info:",
            )
        )
    if meta.get("provisional_prop"):
        out.append(
            (
                "info",
                (
                    f"Tự doanh {_d(meta['provisional_prop'])} là số tạm (chưa chốt), không tính vào "
                    "phiếu và tổng."
                ),
                ":material/info:",
            )
        )
    return out


def _money(
    x: float | None, ratio: float | None = None, cov: float | None = None
) -> str:
    if x is None:
        return "◌ —"
    s = f"{_arrow(x)} {mf._ty(x)}"
    if ratio is not None:
        s += f" · {_chg(ratio)}"
    if cov is not None:
        s += f" · phủ {cov:.0%}"
    return s


def sector_frame(rows: list[dict], mode: str, window: int) -> pd.DataFrame:
    """Bản đồ ngành §3 dạng chữ, giữ thứ tự sector_table. Loại: tổng + R_F/R_P; Gồm: chỉ tổng tỷ."""
    fcol, pcol = f"Ngoại {window}p", f"Tự doanh {window}p"
    loai = mode == "loai"
    recs = [
        {
            "Ngành": r["sector"],
            "n": r["n"],
            fcol: _money(r["f"], r["r_f"] if loai else None),
            "Độ rộng ngoại": (
                f"{r['breadth_pos']}/{r['breadth_n']} mua ròng"
                if r["breadth_n"]
                else "—"
            ),
            pcol: _money(r["p"], r["r_p"], r["p_cov"]) if loai else _money(r["p"]),
            "Gom / xả": r["label_count"],
            "Mã chi phối": (
                f"{r['dominant']} {r['dominant_share']:.0%}" if r["dominant"] else "—"
            ),
            "RS20": "—" if r["rs20"] is None else _chg(r["rs20"]),
            "Cờ": ", ".join(r["flags"]),
        }
        for r in rows
    ]
    return pd.DataFrame(
        recs,
        columns=[
            "Ngành",
            "n",
            fcol,
            "Độ rộng ngoại",
            pcol,
            "Gom / xả",
            "Mã chi phối",
            "RS20",
            "Cờ",
        ],
    )


def _heat_css(heat: float | None, clip: float) -> str:
    if not heat:
        return ""
    a = 0.12 + 0.48 * min(abs(heat) / clip, 1.0)
    rgb = "0,183,79" if heat > 0 else "214,40,57"
    return f"background-color: rgba({rgb},{a:.2f})"


def _sector_styler(df: pd.DataFrame, rows: list[dict], mode: str, cfg: dict) -> Any:
    """Màu theo R_F cắt ±heat_clip (chỉ chế độ Loại); ô tự doanh phủ thấp để mờ."""
    clip = float(cfg["heat_clip"])
    fcol = next(c for c in df.columns if c.startswith("Ngoại"))
    sty = df.style.apply(
        lambda col: [_heat_css(r["heat"], clip) for r in rows], subset=[fcol]
    )
    pcol = next((c for c in df.columns if c.startswith("Tự doanh")), None)
    if pcol and mode == "loai":
        sty = sty.apply(
            lambda col: ["opacity: 0.55" if r["p_dim"] else "" for r in rows],
            subset=[pcol],
        )
    return sty


def ticker_frame(
    res: dict, mode: str, sector: str = _ALL, label_code: str | None = None
) -> pd.DataFrame:
    """Danh sách mã §4.3 (số để sắp xếp được); lọc theo ngành/nhãn."""
    W = str(res["meta"]["window"])
    ups = res.get("upside", {}).get("rows", {})
    recs = []
    for t, tk in sorted(res["tickers"].items()):
        lab = tk["label"]
        if (sector != _ALL and tk["sector"] != sector) or (
            label_code and lab["code"] != label_code
        ):
            continue
        fl, v = tk["flows"][W][mode], tk["votes"]
        rec = {
            "Mã": t,
            "Ngành": tk["sector"],
            "Nhãn": f"{_LABEL_SYM[lab['code']]} {lab['text']}",
            "Phiếu": " · ".join(
                mf.SYM[v[k]["vote"]] for k in ("foreign", "pv", "prop")
            ),
            "Bối cảnh": tk["context"],
            "Ngoại (tỷ)": _tybn(fl["f"]),
            "R_F (%)": _pct100(fl.get("r_f")),
            "Tự doanh (tỷ)": _tybn(fl["p"]),
            "CMF20": v["pv"]["value"] if v["pv"]["vote"] is not None else None,
            "ret20 (%)": _pct100(tk["ret20"]),
            "Giữ nhãn từ": ("≤ " if tk["held_since_truncated"] else "")
            + _d(tk["held_since"]),
            "Upside (%)": _pct100((ups.get(t) or {}).get("upside")),
            "Huy hiệu": "; ".join(tk["badges"]),
        }
        recs.append(rec)
    df = pd.DataFrame(recs, columns=list(rec) if recs else ["Mã"])
    return df.drop(columns="R_F (%)") if mode == "gom" and len(df) else df


def votes_frame(tk: dict, cfg: dict) -> pd.DataFrame:
    """Bảng phiếu (chi tiết a): giá trị đo, ngưỡng config, số phiên cùng dấu, độ phủ, lý do ◌."""
    s, v = cfg["signal"], tk["votes"]
    f, a, p, r = v["foreign"], v["pv"], v["prop"], v["rvol"]

    def ratio(x: dict) -> str:
        return "—" if x["value"] is None else f"{_chg(x['value'])} GTGD"

    def sess(x: dict) -> str:
        return f"{x['pos']} mua / {x['neg']} bán / {x['n']} phiên" if x["n"] else "—"

    return pd.DataFrame(
        [
            {
                "Phiếu": f"Ngoại (chính) {mf.SYM[f['vote']]}",
                "Đo": ratio(f),
                "Ngưỡng": f"|R_F| ≥ {_vi(s['foreign_band'] * 100)}% và ≥ "
                f"{_vi(s['same_sign_share'] * 100)}% phiên cùng dấu; ≥ "
                f"{s['min_valid_sessions']} phiên hợp lệ, ≤ {cfg['max_flow_gaps']} phiên thủng",
                "Phiên": f"{sess(f)}, {f['gaps']} thủng",
                "Ghi chú": f["reason"] or "",
            },
            {
                "Phiếu": f"Giá-KL (xác nhận) {mf.SYM[a['vote']]}",
                "Đo": (
                    "—"
                    if a["value"] is None
                    else f"CMF{s['cmf_window']} {_vi(a['value'], 2)}"
                ),
                "Ngưỡng": f"|CMF| ≥ {_vi(s['cmf_band'], 2)}; ≤ {s['cmf_max_flat']} phiên đứng giá",
                "Phiên": f"{a['n']} phiên giá, {a['flat']} phiên đứng giá",
                "Ghi chú": a["reason"] or "",
            },
            {
                "Phiếu": f"Tự doanh (phụ) {mf.SYM[p['vote']]}",
                "Đo": ratio(p),
                "Ngưỡng": f"|R_P| ≥ {_vi(s['prop_band'] * 100, 1)}% và ≥ "
                f"{_vi(s['same_sign_share'] * 100)}% phiên cùng dấu; phủ ≥ "
                f"{_vi(s['prop_min_session_cov'] * 100)}% phiên",
                "Phiên": f"{sess(p)}, phủ {p['coverage']:.0%}",
                "Ghi chú": p["reason"] or "",
            },
            {
                "Phiếu": "KL đột biến (chỉ cho Nội gom/xả) "
                + ("✓" if r["surge"] else "—"),
                "Đo": "—" if r["value"] is None else f"×{_vi(r['value'], 2)}",
                "Ngưỡng": f"KL TB {s['cmf_window']} phiên ÷ KL TB {s['rvol_base']} phiên liền trước "
                f"≥ {_vi(s['rvol_min'], 1)}",
                "Phiên": f"{s['cmf_window']} + {s['rvol_base']} phiên có giá",
                "Ghi chú": r["reason"] or "",
            },
        ]
    )


def windows_frame(tk: dict, mode: str) -> pd.DataFrame:
    recs = []
    for n, fl in sorted(tk["flows"].items(), key=lambda x: int(x[0])):
        x = fl[mode]
        rec = {
            "Cửa sổ": f"{n} phiên",
            "Ngoại (tỷ)": _tybn(x["f"]),
            "Tự doanh (tỷ)": _tybn(x["p"]),
        }
        if mode == "loai":
            rec |= {"R_F (%)": _pct100(x["r_f"]), "Phủ TD (%)": _pct100(x["p_cov"])}
        recs.append(rec)
    return pd.DataFrame(recs)


def _block_text(lb: float | None, est: float | None, exact: bool) -> str:
    if lb is None or pd.isna(lb):
        return ""
    gt = (
        ""
        if est is None or pd.isna(est)
        else (mf._bn(est) if exact else f"ước ~{mf._bn(est)}")
    )
    return f"KL {'' if exact else '≥ '}{mf._shares(lb)}" + (f", GT {gt}" if gt else "")


def block_frame(tk: dict) -> pd.DataFrame:
    """Phiên có cờ thỏa thuận trong chuỗi chi tiết (60 phiên): KL mua/bán ngoại, tự doanh, cận dưới."""
    s = pd.DataFrame(tk["series"])
    b = s[s["block"]]
    return pd.DataFrame(
        [
            {
                "Ngày": _d(r.date),
                "Ngoại mua (cp)": r.f_buy_vol,
                "Ngoại bán (cp)": r.f_sell_vol,
                "TD mua (cp)": r.p_buy_vol,
                "TD bán (cp)": r.p_sell_vol,
                "KL khớp (cp)": r.volume,
                "Thỏa thuận": _block_text(r.lb_vol, r.est_val, bool(r.block_exact)),
                "Dạng": r.form or "",
            }
            for r in b.itertuples()
        ]
    )


# ---------- tương tác ----------
def _pick(table_key: str, order_key: str, target: str) -> None:
    """Callback bấm dòng bảng → ghi lựa chọn vào widget đích (chạy trước lượt rerun)."""
    rows = st.session_state[table_key].selection.rows
    order = st.session_state.get(order_key) or []
    if rows and rows[0] < len(order):
        st.session_state[target] = order[rows[0]]


def _sync_ticker(ticker: str | None, opts: list[str]) -> str | None:
    """Mã sidebar đổi → ô tra mã đổi theo; mã ngoài VN100 bị từ chối (trả câu báo)."""
    note = None
    if ticker is not None and ticker not in opts:
        note = f"{_md(ticker)} không thuộc VN100 (hoặc chưa có giá) — tab này chỉ tra mã VN100."
    elif ticker is not None and st.session_state.get("_flow_sidebar") != ticker:
        st.session_state["flow_ticker"] = ticker
    st.session_state["_flow_sidebar"] = ticker
    if st.session_state.get("flow_ticker") not in opts:
        st.session_state["flow_ticker"] = opts[0]
    return note


# ---------- khối hiển thị ----------
def _help_cfg(df: pd.DataFrame, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """column_config có dòng giải thích khi rê chuột vào tiêu đề MỌI cột có trong lessons.COLUMN_HELP;
    giữ nguyên định dạng/pinned/help đã đặt riêng."""
    out = dict(cfg or {})
    for col in df.columns:
        h = lessons.column_help(str(col))
        if not h:
            continue
        c = dict(out.get(col) or st.column_config.Column())
        c["help"] = c.get("help") or h
        out[col] = c
    return out


_SECTOR_HELP = {
    "Ngành": lessons.HELP["sector"],
    "Gom / xả": lessons.HELP["labels"],
    "Mã chi phối": lessons.HELP["dominant"],
    "Độ rộng ngoại": lessons.HELP["breadth"],
    "RS20": lessons.HELP["rs20"],
    "Cờ": lessons.HELP["flags"],
}


def _sector_block(
    rows: list[dict], mode: str, cfg: dict, window: int, *, compact: bool, key: str
) -> None:
    word = "loại" if mode == "loai" else "gồm"
    st.markdown(
        f"**Bản đồ ngành · {window} phiên · {word} thỏa thuận** — bấm một ngành để lọc danh sách mã",
        help=lessons.read_sector(cfg),
    )
    if not rows:
        st.caption("Chưa có ngành nào đủ dữ liệu.")
        return
    df = sector_frame(rows, mode, window)
    fcol, pcol = f"Ngoại {window}p", f"Tự doanh {window}p"
    if compact:
        df = df[["Ngành", fcol, "Gom / xả"]]
    ccfg: dict[str, Any] = {
        c: st.column_config.TextColumn(help=h) for c, h in _SECTOR_HELP.items()
    }
    ccfg["Ngành"] = st.column_config.TextColumn(
        help=lessons.HELP["sector"], pinned=True
    )
    ccfg[fcol] = st.column_config.TextColumn(help=lessons.HELP["foreign"])
    ccfg[pcol] = st.column_config.TextColumn(help=lessons.HELP["prop"])
    st.session_state["_flow_sector_order"] = df["Ngành"].tolist()
    tbl = f"flow_sector_tbl_{key}"
    st.dataframe(
        _sector_styler(df, rows, mode, cfg),
        hide_index=True,
        placeholder="—",
        width="stretch",
        column_config=_help_cfg(df, ccfg),
        key=tbl,
        on_select=partial(_pick, tbl, "_flow_sector_order", "flow_sector"),
        selection_mode="single-row",
    )
    if mode == "gom":
        st.caption("Chế độ Gồm: chỉ tổng tỷ đồng, không tỷ lệ, không tô màu.")


def _card(t: str, tk: dict, res: dict, mode: str, cfg: dict) -> None:
    """Thẻ 5 giây §4.1: nhãn + hậu tố · 3 chip · huy hiệu · lý do (màu luôn kèm ▲ ▼ 0 ◌)."""
    lab, v = tk["label"], tk["votes"]
    code = lab["code"]
    W = str(res["meta"]["window"])
    with st.container(border=True):
        st.markdown(f"**{t}** · {_md(tk['sector'])}", help=lessons.read_card(cfg))
        st.markdown(
            f"#### :{_LABEL_COLOR[code]}[{_LABEL_SYM[code]} {lab['text']}] · "
            f"{_md(tk['context'])}"
        )
        n_sp = int(load_defaults()["money_flow_chart"]["spark_sessions"])
        sf = lessons.series_frame(tk).iloc[-n_sp:]
        fs = sf["f"].mask(sf["excl"].eq(True)) if mode == "loai" else sf["f_gom"]
        st.markdown(
            f"{spark(fs.tolist())} &nbsp;<small>khối ngoại {len(sf)} phiên (cũ → mới)</small>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "  \n".join(
                f":{_VOTE_COLOR[v[k]['vote']]}[{_md(v[k]['chip'])}]"
                for k in ("foreign", "pv", "prop")
            )
        )
        if tk["badges"]:
            st.markdown("\n".join(f"- {_md(b)}" for b in tk["badges"]))
        st.caption(_md(lab["reason"]))
        extra = []
        if tk["held_since"]:
            le = "≤ " if tk["held_since_truncated"] else ""
            extra.append(f"Giữ nhãn từ {le}{_d(tk['held_since'])}")
        if mode == "gom":
            g = tk["flows"][W]["gom"]
            extra.append(
                f"Gồm thỏa thuận {W} phiên: ngoại {_money(g['f'])}, tự doanh {_money(g['p'])}"
            )
        up = res.get("upside", {})
        row = up.get("rows", {}).get(t)
        if row and row["upside"] is not None:
            note = f" · {row['note']}" if row["note"] else ""
            extra.append(
                f"Upside mô hình (phụ): {_chg(row['upside'])} · {up['source']}{note}"
            )
        else:
            extra.append("Upside mô hình (phụ): chưa có từ đợt định giá VN100")
        st.caption(_md(" · ".join(extra)))


def _lookup(opts: list[str], note: str | None, res: dict, mode: str, cfg: dict) -> str:
    st.selectbox(
        "Tra mã VN100",
        opts,
        key="flow_ticker",
        help="Chỉ gồm mã VN100 có giá; mặc định theo mã đang chọn ở thanh bên.",
    )
    if note:
        st.caption(note)
    t = st.session_state["flow_ticker"]
    _card(t, res["tickers"][t], res, mode, cfg)
    return t


def _filters_and_list(res: dict, mode: str, cfg: dict) -> None:
    sectors = sorted({tk["sector"] for tk in res["tickers"].values()})
    if st.session_state.get("flow_sector") not in (_ALL, *sectors):
        st.session_state["flow_sector"] = _ALL
    c1, c2 = st.columns(2)
    sec = c1.selectbox("Lọc ngành", [_ALL, *sectors], key="flow_sector")
    lab = c2.selectbox("Lọc nhãn", [_ALL, *mf.LABELS.values()], key="flow_label")
    code = next((k for k, x in mf.LABELS.items() if x == lab), None)
    # D73: bỏ bảng "Phiên ảnh hưởng lớn nhất" (xếp theo tỷ đồng → chỉ lặp lại mã vốn hóa lớn); thay bằng
    # huy hiệu ⚠ "Dồn 1 phiên" theo từng mã trong danh sách (money_flow.concentration_badge).
    num = st.column_config.NumberColumn(format="%.1f")
    df = ticker_frame(res, mode, sec, code)
    with phone_collapsible(f"Danh sách mã ({len(df)})"):
        st.markdown(
            f"**Danh sách mã · {len(df)} mã** — bấm một dòng để xem thẻ",
            help=lessons.read_list(cfg),
        )
        st.session_state["_flow_list_order"] = df["Mã"].tolist()
        tc = st.column_config.TextColumn
        st.dataframe(
            df,
            hide_index=True,
            placeholder="—",
            width="stretch",
            column_config=_help_cfg(
                df,
                {
                    "Mã": tc(pinned=True),
                    "Phiếu": tc(help=lessons.HELP["votes"]),
                    "Bối cảnh": tc(help=lessons.HELP["context"]),
                    "Giữ nhãn từ": tc(help=lessons.HELP["held"]),
                    "Ngoại (tỷ)": num,
                    "R_F (%)": num,
                    "Tự doanh (tỷ)": num,
                    "CMF20": st.column_config.NumberColumn(format="%.2f"),
                    "ret20 (%)": num,
                    "Upside (%)": st.column_config.NumberColumn(
                        format="%.1f", help=lessons.HELP["upside"]
                    ),
                },
            ),
            key="flow_list_tbl",
            on_select=partial(
                _pick, "flow_list_tbl", "_flow_list_order", "flow_ticker"
            ),
            selection_mode="single-row",
        )


LAYERS = ("Khối lượng", "Khối ngoại", "Tự doanh", "Ai gom/xả", "MACD")
_PHONE_LAYERS = ("Khối ngoại", "Ai gom/xả")
_LAYER_TITLE = {
    "Giá": "Giá (điều chỉnh) · MA20/MA50 · ◆ thỏa thuận lớn · ▲ GDKHQ",
    "Khối lượng": "Khối lượng khớp lệnh (xanh/đỏ) · chế độ Gồm: + thỏa thuận (tím)",
    "Khối ngoại": "Khối ngoại ròng/ngày (tỷ) · đường: lũy kế · chế độ Gồm: + thỏa thuận (tím)",
    "Tự doanh": "Tự doanh ròng/ngày (tỷ) · đường: lũy kế · chế độ Gồm: + thỏa thuận (tím)",
    "Ai gom/xả": "Ai đang gom, ai đang xả · đường: lũy kế (tỷ, trục phải) · nền: CMF20 (trục trái)",
    "MACD": "MACD (12, 26, 9)",
}
_UP, _DOWN, _DEAL, _PROP, _DOM = "#089981", "#F23645", "#8E44AD", "#1d4289", "#F59E0B"


@st.cache_data(ttl=600, show_spinner=False, max_entries=32)
def _history(key: tuple, ticker: str, _db: Any) -> pd.DataFrame:
    """Lịch sử 1 mã cho biểu đồ (chỉ nạp khi mở chi tiết); khóa = khóa panel + mã."""
    days = int(load_defaults()["money_flow_chart"]["history_days"])
    cfg = load_defaults()["money_flow"]
    p = load_flow_panel(_db, cfg, ticker=ticker, days=days)
    return mf.ticker_history(p["prices"], p["exact"], p["actions"], cfg, _now_vn())


def chart_slice(h: pd.DataFrame, sessions: int) -> pd.DataFrame:
    """N phiên giá cuối + cột lũy kế tính TỪ đầu khung (ngày thiếu số không cộng, không thành 0)."""
    v = h[h["close"].notna()].iloc[-sessions:].copy()
    for c in ("f", "p", "f_block", "p_block", "dom"):
        v[f"cum_{c}"] = v[c].cumsum().where(v[c].notna()).ffill()
    for c in ("f", "p"):
        tot = v[c].fillna(0) + v[f"{c}_block"].fillna(0)
        v[f"cum_{c}_gom"] = (
            tot.where(v[c].notna() | v[f"{c}_block"].notna()).cumsum().ffill()
        )
    return v


def flow_chart(v: pd.DataFrame, layers: list[str], mode: str, dark: bool) -> Any:
    """Biểu đồ dòng tiền nhiều tầng chung trục ngày (D74): giá → các tầng chọn trong LAYERS."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    from valuation.views.tradingview_chart import (
        _add_macd,
        _add_overlays,
        _add_price_trace,
        _theme_colors,
    )

    colors = _theme_colors(dark)
    rows = ["Giá", *[x for x in LAYERS if x in layers]]
    sec = {"Khối ngoại", "Tự doanh"}
    dual = {*sec, "Ai gom/xả"}  # tầng có trục phải
    fig = make_subplots(
        rows=len(rows),
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.34] + [0.66 / max(1, len(rows) - 1)] * (len(rows) - 1),
        specs=[[{"secondary_y": r in dual}] for r in rows],
        subplot_titles=[f"{_LAYER_TITLE[r]} (?)" for r in rows],
    )
    # Rê chuột vào tiêu đề / dấu (?) → hiện giải thích, đưa chuột ra → ẩn (hovertext của annotation).
    for ann, layer in zip(fig.layout.annotations, rows):
        ann.hovertext = "<br>".join(textwrap.wrap(lessons.CHART_HELP[layer], 80))
    x = v.index
    frame = v.assign(time=x)
    _add_price_trace(fig, frame, "Nến")
    _add_overlays(fig, frame, ["MA 20", "MA 50"])
    big = v[v["big_block"]]
    fig.add_trace(
        go.Scatter(
            x=big.index,
            y=big["high"] * 1.02,
            mode="markers",
            name="Thỏa thuận lớn",
            marker={"symbol": "diamond", "size": 10, "color": _DEAL},
            customdata=big["vol_deal"],
            hovertemplate="Thỏa thuận: %{customdata:,.0f} cp<extra></extra>",
        ),
        row=1,
        col=1,
    )
    ev = v[v["event"].notna()]
    fig.add_trace(
        go.Scatter(
            x=ev.index,
            y=ev["low"] * 0.98,
            mode="markers+text",
            name="GDKHQ",
            text=ev["event"],
            textposition="bottom center",
            marker={"symbol": "triangle-up", "size": 9, "color": colors["muted"]},
            hovertemplate="GDKHQ: %{text}<extra></extra>",
        ),
        row=1,
        col=1,
    )
    gom = mode == "gom"
    for r, name in enumerate(rows[1:], start=2):
        if name == "Khối lượng":
            up = [_UP if c >= o else _DOWN for o, c in zip(v["open"], v["close"])]
            fig.add_trace(
                go.Bar(
                    x=x,
                    y=v["vol_match"],
                    name="KL khớp",
                    marker_color=up,
                    hovertemplate="KL khớp: %{y:,.0f}<extra></extra>",
                ),
                row=r,
                col=1,
            )
            if (
                gom
            ):  # Loại: thỏa thuận cực lớn làm méo trục → chỉ ◆ trên tầng giá + bảng (d)
                fig.add_trace(
                    go.Bar(
                        x=x,
                        y=v["vol_deal"],
                        name="KL thỏa thuận",
                        marker_color=_DEAL,
                        hovertemplate="KL thỏa thuận: %{y:,.0f}<extra></extra>",
                    ),
                    row=r,
                    col=1,
                )
        elif name in sec:
            c = "f" if name == "Khối ngoại" else "p"
            y = v[c] / 1e9
            fig.add_trace(
                go.Bar(
                    x=x,
                    y=y,
                    name=f"{name} khớp lệnh",
                    marker_color=[_UP if (b or 0) >= 0 else _DOWN for b in y],
                    hovertemplate=f"{name}: %{{y:,.1f}} tỷ<extra></extra>",
                ),
                row=r,
                col=1,
            )
            if gom:
                fig.add_trace(
                    go.Bar(
                        x=x,
                        y=v[f"{c}_block"] / 1e9,
                        name=f"{name} thỏa thuận",
                        marker_color=_DEAL,
                        hovertemplate="Thỏa thuận: %{y:,.1f} tỷ<extra></extra>",
                    ),
                    row=r,
                    col=1,
                )
            cum = v[f"cum_{c}_gom" if gom else f"cum_{c}"] / 1e9
            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=cum,
                    name=f"{name} lũy kế",
                    line={"color": colors["text"], "width": 1.6},
                    hovertemplate="Lũy kế: %{y:,.1f} tỷ<extra></extra>",
                ),
                row=r,
                col=1,
                secondary_y=True,
            )
        elif name == "Ai gom/xả":
            # Nền CMF20 ở trục trái, 3 đường lũy kế ở trục phải (trục phải vẽ đè lên → đường không bị nền che).
            for sign, col in ((1, _UP), (-1, _DOWN)):
                part = v["cmf"].where(v["cmf"] * sign >= 0)
                fig.add_trace(
                    go.Scatter(
                        x=x,
                        y=part,
                        fill="tozeroy",
                        mode="lines",
                        line={"color": col, "width": 0.5},
                        opacity=0.35,
                        name="CMF20 > 0" if sign > 0 else "CMF20 < 0",
                        hovertemplate="CMF20: %{y:.2f}<extra></extra>",
                    ),
                    row=r,
                    col=1,
                )
            cums = []
            for c, label, col in (
                ("f", "Khối ngoại", _UP),
                ("p", "Tự doanh", _PROP),
                ("dom", "Trong nước (suy ra)", _DOM),
            ):
                key = f"cum_{c}_gom" if gom and c != "dom" else f"cum_{c}"
                cums.append(v[key] / 1e9)
                fig.add_trace(
                    go.Scatter(
                        x=x,
                        y=cums[-1],
                        name=label,
                        mode="lines",
                        line={"color": col, "width": 2.2},
                        hovertemplate=f"{label}: %{{y:,.1f}} tỷ<extra></extra>",
                    ),
                    row=r,
                    col=1,
                    secondary_y=True,
                )
            fig.add_hline(
                y=0, line={"color": colors["border"], "width": 1}, row=r, col=1
            )
            # Hai trục đối xứng quanh 0 → đường 0 của CMF và của lũy kế trùng nhau.
            for sy, s_ in ((False, v["cmf"]), (True, pd.concat(cums))):
                m = s_.abs().max()
                if pd.notna(m) and m > 0:
                    fig.update_yaxes(
                        range=[-1.1 * m, 1.1 * m], row=r, col=1, secondary_y=sy
                    )
        elif name == "MACD":
            _add_macd(fig, frame, r, colors)
    fig.update_layout(
        height=300 + 150 * (len(rows) - 1),
        barmode="relative",
        bargap=0.15,
        paper_bgcolor=colors["paper"],
        plot_bgcolor=colors["plot"],
        font={"color": colors["text"], "size": 12},
        margin={"l": 10, "r": 10, "t": 60, "b": 10},
        legend={
            "orientation": "h",
            "y": 1.02,
            "yanchor": "bottom",
            "x": 0,
            "font": {"size": 11},
        },
        hovermode="x unified",
        dragmode="pan",
        xaxis_rangeslider_visible=False,
    )
    fig.update_annotations(
        font={"size": 12, "color": colors["muted"]}, x=0, xanchor="left"
    )
    # Bỏ cả ngày nghỉ lễ (không chỉ T7/CN) để không có khoảng trống giữa biểu đồ.
    holidays = pd.bdate_range(x.min(), x.max()).difference(x)
    fig.update_xaxes(
        showgrid=False,
        rangebreaks=[
            {"bounds": ["sat", "mon"]},
            {"values": holidays.strftime("%Y-%m-%d").tolist()},
        ],
    )
    fig.update_yaxes(
        showgrid=True, gridcolor=colors["grid"], zeroline=False, automargin=True
    )
    return fig


def _chart_block(t: str, key: tuple, db: Any, mode: str) -> None:
    ccfg = load_defaults()["money_flow_chart"]
    h = _history(key, t, db)
    if h.empty:
        st.caption("Chưa có dữ liệu giá cho mã này.")
        return
    c1, c2 = st.columns([2, 3])
    rng = (
        c1.segmented_control(
            "Khung thời gian",
            list(ccfg["ranges"]),
            default=ccfg["default_range"],
            key="flow_range",
        )
        or ccfg["default_range"]
    )
    default = list(_PHONE_LAYERS) if is_phone() else [x for x in LAYERS if x != "MACD"]
    layers = c2.multiselect(
        "Các tầng", list(LAYERS), default=default, key="flow_layers"
    )
    v = chart_slice(h, int(ccfg["ranges"][rng]))
    dark = st.context.theme.type == "dark"
    if ccfg.get("engine", "lightweight") == "lightweight":
        # D90: Lightweight Charts (TradingView) — cùng dữ liệu/tầng; "plotly" trong config để quay lại bản cũ.
        import streamlit.components.v1 as components

        from valuation.views import lw_chart

        vp_cfg = ccfg["volume_profile"]
        # Volume profile: tắt mặc định, người dùng bật khi cần (D91).
        profile = (
            lw_chart.volume_profile(v, int(vp_cfg["rows"]), float(vp_cfg["value_area"]))
            if st.toggle(
                "Volume profile",
                value=False,
                key="flow_vp",
                help="Khối lượng khớp theo vùng giá trong khung đang chọn (rải đều KL mỗi phiên "
                "trên biên độ cao–thấp). Xanh = phiên tăng, vàng = phiên giảm; đậm = vùng giá trị "
                f"{float(vp_cfg['value_area']):.0%}. POC = vùng giá khớp nhiều nhất.",
            )
            else None
        )
        if profile:
            profile["width"] = float(vp_cfg["width"])
        payload = lw_chart.build_payload(
            v,
            layers,
            mode,
            titles=_LAYER_TITLE,
            helps=lessons.CHART_HELP,
            order=LAYERS,
            profile=profile,
        )
        components.html(
            lw_chart.render_html(payload, dark), height=lw_chart.chart_height(payload)
        )
        if profile:
            st.caption(
                f"Volume profile {len(v)} phiên: POC {profile['poc']:,.0f} · VAH {profile['vah']:,.0f} · "
                f"VAL {profile['val']:,.0f} · tổng KL khớp {profile['total']:,.0f} cp. "
                "Cố định theo khung thời gian đang chọn (zoom không tính lại).".replace(
                    ",", "."
                )
            )
    else:
        st.plotly_chart(
            flow_chart(v, layers, mode, dark),
            width="stretch",
            theme=None,
            config={"displaylogo": False, "scrollZoom": True},
        )
    src = (
        "VCI khớp lệnh/thỏa thuận (flow_daily)"
        if (v["source"] == "exact").all()
        else ("một phần ước từ prices_daily (KL thỏa thuận chỉ là cận dưới)")
    )
    st.caption(
        f"{len(v)} phiên {_d(mf._iso(v.index[0]))}–{_d(mf._iso(v.index[-1]))} · nguồn: {src} · "
        "lũy kế tính từ đầu khung; ngày thiếu số không cộng. "
        + (
            "Chế độ Gồm: đường lũy kế cộng cả thỏa thuận."
            if mode == "gom"
            else "Chế độ Loại: lũy kế chỉ khớp lệnh."
        )
    )


def spark(values: list[float | None]) -> str:
    """Dải cột khối ngoại trên thẻ (cũ → mới): độ cao ▁…█ theo |giá trị| / max, xanh mua đỏ bán, · thiếu."""
    bars = "▁▂▃▄▅▆▇█"
    nums = [abs(x) for x in values if x is not None and not pd.isna(x)]
    top = max(nums) if nums else 0.0
    out = []
    for x in values:
        if x is None or pd.isna(x) or top == 0:
            out.append(":gray[·]")
            continue
        b = bars[min(len(bars) - 1, int(abs(x) / top * (len(bars) - 1)))]
        out.append(f":{'green' if x > 0 else 'red' if x < 0 else 'gray'}[{b}]")
    return "".join(out)


def sector_heatmap(sd: dict, cfg: dict, dark: bool) -> Any:
    """Bản đồ nhiệt Ngành × Ngày (chế độ Loại): màu = ngoại ròng / GTGD, cắt ±heat_clip; chữ = tỷ."""
    import plotly.graph_objects as go

    clip = float(cfg["heat_clip"])
    z = [
        [None if r is None else max(-clip, min(clip, r)) for r in row]
        for row in sd["r"]
    ]
    f = [[None if x is None else x / 1e9 for x in row] for row in sd["f"]]
    days = [_d(d) for d in sd["dates"]]
    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=days,
            y=sd["sectors"],
            zmin=-clip,
            zmax=clip,
            customdata=f,
            colorscale=[[0, _DOWN], [0.5, "#2b2f3a" if dark else "#ffffff"], [1, _UP]],
            hovertemplate="%{y} · %{x}<br>Ngoại ròng: %{customdata:,.1f} tỷ<extra></extra>",
            colorbar={"tickformat": ".0%", "title": "% GTGD", "thickness": 10},
            xgap=1,
            ygap=1,
        )
    )
    fig.update_layout(
        height=28 * len(sd["sectors"]) + 90,
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        yaxis={"autorange": "reversed", "automargin": True},  # tên ngành không bị cắt
        xaxis={"automargin": True, "tickangle": -45},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#e6edf3" if dark else "#1d1d1f", "size": 11},
    )
    return fig


def _heat_block(res: dict, mode: str, cfg: dict) -> None:
    st.markdown(
        f"**Bản đồ nhiệt Ngành × Ngày · {res['meta']['window']} phiên · khối ngoại**"
    )
    sd = res["modes"]["loai"].get("sector_daily")
    if mode == "gom":
        st.caption(
            "Bản đồ nhiệt chỉ có ở chế độ Loại (Gồm không tính tỷ lệ, không tô màu)."
        )
        return
    if not sd or not sd["dates"]:
        st.caption("Chưa đủ dữ liệu.")
        return
    st.plotly_chart(
        sector_heatmap(sd, cfg, st.context.theme.type == "dark"),
        width="stretch",
        theme=None,
        config={"displaylogo": False},
    )
    st.caption(
        "Mỗi ô: khối ngoại mua/bán ròng của ngành trong ngày so với GTGD ngày đó "
        "(đã loại thỏa thuận). Nhìn theo hàng ngang để thấy ngành nào đang được gom dần."
    )


def _detail(t: str, tk: dict, mode: str, cfg: dict, key: tuple, db: Any) -> None:
    """Chi tiết §4.3 (chỉ tính khi bật toggle): biểu đồ · bảng phiếu + trong nước suy ra · thỏa thuận + huy hiệu."""
    num = st.column_config.NumberColumn(format="%.1f")
    st.markdown(f"#### Chi tiết {t}", help=lessons.read_detail(cfg))
    chart, votes, blocks = st.tabs(["Biểu đồ", "Bảng phiếu", "Phiên thỏa thuận"])
    with chart:
        _chart_block(t, key, db, mode)
    with votes:
        st.markdown(f"**Bảng phiếu {t}** — luôn tính ở chế độ Loại")
        vdf, wdf = votes_frame(tk, cfg), windows_frame(tk, mode)
        st.dataframe(
            vdf,
            hide_index=True,
            placeholder="—",
            width="stretch",
            column_config=_help_cfg(vdf),
        )
        st.dataframe(
            wdf,
            hide_index=True,
            placeholder="—",
            width="stretch",
            column_config=_help_cfg(
                wdf,
                {
                    c: num
                    for c in ("Ngoại (tỷ)", "Tự doanh (tỷ)", "R_F (%)", "Phủ TD (%)")
                },
            ),
        )
        d = tk["domestic"]
        st.markdown("**Trong nước suy ra D = −(ngoại + tự doanh)** — chế độ Loại")
        if d["value"] is None or not d["n"]:
            st.caption("Chưa có phiên nào có cả số ngoại lẫn tự doanh trong cửa sổ.")
        else:
            st.markdown(
                f"{_money(d['value'])} trên {d['n']} phiên có cả số ngoại lẫn tự doanh"
            )
        st.caption(
            "Chỉ đúng khi: (1) có số cả hai nhóm, (2) ngoại và tự doanh không trùng người, (3) cùng phạm "
            "vi giao dịch. D phụ thuộc tuyến tính vào ngoại và tự doanh nên không phải phiếu."
        )
    with blocks:
        n = len(tk["series"]["date"])
        st.markdown(f"**Phiên thỏa thuận trong {n} phiên**")
        bf = block_frame(tk)
        if bf.empty:
            st.caption("Không có phiên nào bị gắn cờ thỏa thuận.")
        else:
            loc = st.column_config.NumberColumn(format="localized")
            st.dataframe(
                bf,
                hide_index=True,
                placeholder="—",
                width="stretch",
                column_config=_help_cfg(
                    bf, {c: loc for c in bf.columns if c.endswith("(cp)")}
                ),
            )
        st.markdown("**Huy hiệu sự kiện**")
        st.markdown("\n".join(f"- {_md(b)}" for b in tk["badges"]) or "Không có.")


def render_money_flow(db: Any, ticker: str | None = None) -> None:
    """Tab "Dòng tiền ngành": trạng thái → kết luận → ngành (tổng | theo ngày) → danh sách | thẻ mã → chi tiết → học.

    db: session chỉ đọc do app truyền vào (như market_overview.load_market_data). ticker: mã sidebar.
    """
    cfg_all = load_defaults()
    cfg = cfg_all["money_flow"]
    snap = latest_snapshot()
    key = panel_key(db, cfg_all, snap, _now_vn())
    res = _compute(key, db, snap)
    meta = res["meta"]
    W = int(meta["window"])

    head, sw = st.columns([4, 1], vertical_alignment="bottom")
    head.subheader("Dòng tiền ngành VN100")
    word = sw.radio(
        "Phiên thỏa thuận",
        list(_MODES),
        index=0 if cfg["exclude_block_default"] else 1,
        horizontal=True,
        key="flow_mode",
        help=lessons.HELP["mode"],
    )
    mode = _MODES[word]
    st.caption(status_line(meta, mode))
    render_alerts(flow_alerts(meta))
    md = res["modes"][mode]
    st.markdown(f"**{_md(md['conclusion'])}**")
    st.caption(_md(f"{meta['disclaimer']} {md.get('detail', '')}".strip()))
    if not res["tickers"]:
        st.info(f"Chưa đủ dữ liệu giá/dòng tiền VN100 — bấm {_SCAN} ở thanh bên.")
        return

    opts = sorted(res["tickers"])
    note = _sync_ticker(ticker, opts)
    phone = is_phone()
    # Thị trường → Ngành → Cổ phiếu → Chi tiết 1 mã (bấm ngành lọc danh sách, bấm mã đổi thẻ).
    st.markdown("#### Theo ngành")
    total, daily = st.tabs([f"Tổng {W} phiên", "Theo ngày"])
    with total:
        if phone:
            _sector_block(md["sectors"], mode, cfg, W, compact=True, key="compact")
            with phone_collapsible("Bản đồ ngành đầy đủ"):
                _sector_block(md["sectors"], mode, cfg, W, compact=False, key="full")
        else:
            _sector_block(md["sectors"], mode, cfg, W, compact=False, key="full")
    with daily:
        _heat_block(res, mode, cfg)
    st.markdown("#### Theo cổ phiếu")
    if phone:
        t = _lookup(opts, note, res, mode, cfg)
        detail = st.toggle("Xem biểu đồ & chi tiết mã này", key="flow_detail")
        _filters_and_list(res, mode, cfg)
    else:
        left, right = st.columns([3, 2], gap="large")
        with right:
            t = _lookup(opts, note, res, mode, cfg)
            detail = st.toggle("Xem biểu đồ & chi tiết mã này", key="flow_detail")
        with left:
            _filters_and_list(res, mode, cfg)
    if detail:
        _detail(t, res["tickers"][t], mode, cfg, key, db)
    lessons.render_lessons(res, t, cfg)
