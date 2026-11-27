"""Dữ liệu dòng tiền cho web hợp nhất btinvest.vn (lát 1, docs/PLAN_WEB_HOP_NHAT.md mục 12).

Chỉ đọc. Gọi lại đúng các hàm mà tab "Dòng tiền ngành" đang dùng (D73, D90, D91) rồi đổi kết quả sang
kiểu JSON được; không tính lại, không làm tròn lại con số nào. Không ghi DB, không gọi mạng, không AI.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import math
import re
import threading
import time
from collections.abc import Callable
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import func

from valuation.analysis import money_flow as mf
from valuation.analysis.technical_chart import add_technical_indicators
from valuation.config import load_defaults
from valuation.db.models import PricesDaily
from valuation.services import web_live
from valuation.services.ranking_store import latest_snapshot
from valuation.views import lw_chart
from valuation.views import money_flow as vmf
from valuation.views import money_flow_lessons as lessons
from valuation.views.market_overview import sector_map

MODES = ("loai", "gom")
_TICKER_RE = re.compile(r"^[A-Z0-9]{3,4}$")
_LIST_HEAD = (
    "Mã",
    "Ngành",
    "Nhãn",
    "Phiếu",
    "Bối cảnh",
)  # cột của ticker_frame đã có trường riêng
_lock = threading.Lock()
_compute_lock = (
    threading.RLock()
)  # RLock: ticker_list tính trong khóa rồi gọi tiếp _result cũng cần khóa
_cache: dict[str, tuple[float, Any]] = {}


def clean(o: Any) -> Any:
    """Đổi về kiểu JSON chuẩn: NaN/vô cực/NaT thành None, số numpy thành số Python, ngày thành ISO."""
    if o is None or o is pd.NaT:
        return None
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple, set)):
        return [clean(v) for v in o]
    if isinstance(o, pd.Timestamp):
        return o.strftime("%Y-%m-%d") if o == o.normalize() else o.isoformat()
    if isinstance(o, (dt.datetime, dt.date)):
        return o.isoformat()
    if hasattr(o, "item") and not isinstance(o, (str, bytes)):
        o = o.item()  # numpy.float64, numpy.int64, numpy.bool_
    if isinstance(o, Decimal):
        o = float(o)  # cột NUMERIC của SQLAlchemy (vd tiền cổ tức mỗi cổ phiếu)
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    if isinstance(o, (str, int, bool)):
        return o
    return str(o)


def _web_cfg() -> dict:
    return load_defaults()["web"]


def _cached(key: str, make: Callable[[], Any]) -> Any:
    """Bộ nhớ đệm trong tiến trình, hết hạn sau `web.cache_seconds` giây; một lúc chỉ một luồng tính."""
    ttl = float(_web_cfg()["cache_seconds"])

    def fresh() -> Any:
        hit = _cache.get(key)
        return hit if hit is not None and time.monotonic() - hit[0] < ttl else None

    with _lock:
        hit = fresh()
    if hit is not None:
        return hit[1]
    with _compute_lock:
        with _lock:
            hit = fresh()
        if hit is not None:
            return hit[1]
        value = make()
        with _lock:
            _cache[key] = (time.monotonic(), value)
            limit = int(_web_cfg()["cache_entries"])
            while len(_cache) > limit:
                _cache.pop(min(_cache, key=lambda k: _cache[k][0]))
        return value


def clear_cache() -> None:
    with _lock:
        _cache.clear()
        _version.clear()


_version: dict[str, tuple[float, str]] = {}


def data_version(db: Any) -> str:
    """Dấu phiên bản số giá, khối ngoại, tự doanh trong DB (D128).

    Đổi khi job ghi phiên mới (15:45), tự doanh (17:45) hay sửa số các phiên gần (07:50 tải lại đệm 5 ngày). Bộ nhớ
    đệm của web gắn dấu này vào khóa, nên DB vừa đổi thì lần hỏi sau tính lại ngay, không chờ hết `cache_seconds`;
    trình duyệt thấy dấu đổi thì nạp lại các tab. Hỏi DB nhiều nhất `data_version_seconds` giây một lần.
    """
    cfg = _web_cfg()
    with _lock:
        hit = _version.get("v")
        if hit is not None and time.monotonic() - hit[0] < float(
            cfg["data_version_seconds"]
        ):
            return hit[1]
    since = vmf._now_vn().date() - dt.timedelta(days=int(cfg["data_version_days"]))
    row = (
        db.query(
            func.max(PricesDaily.trade_date),
            func.count(PricesDaily.close),
            func.count(PricesDaily.foreign_net_val),
            func.count(PricesDaily.proprietary_net_val),
            func.sum(PricesDaily.close),
            func.sum(PricesDaily.foreign_net_val),
            func.sum(PricesDaily.proprietary_net_val),
        )
        .filter(PricesDaily.trade_date >= since)
        .one()
    )
    value = hashlib.sha1(repr(tuple(row)).encode()).hexdigest()[:12]
    with _lock:
        _version["v"] = (time.monotonic(), value)
    return value


def _result(db: Any) -> dict:
    """compute_money_flow cho cả VN100, lắp ráp y như `views.money_flow._compute`."""

    def make() -> dict:
        cfg = load_defaults()["money_flow"]
        p = vmf.load_flow_panel(db, cfg)
        res = mf.compute_money_flow(
            p["prices"], p["exact"], p["actions"], sector_map(), cfg, vmf._now_vn()
        )
        res["upside"] = vmf.upsides(db, latest_snapshot())
        return res

    return _cached(f"flow:{data_version(db)}", make)


def model_upsides(db: Any) -> dict:
    """Upside phụ của đợt định giá VN100 gần nhất cho mọi mã: `{"rows": {mã: {upside, note}}, "source": ...}`.

    Cùng kết quả (đã nhớ) mà tab dòng tiền dùng; danh mục (lát 5b) lấy để vẽ thước của cổ phiếu.
    """
    return _result(db)["upside"]


def _history(db: Any, ticker: str) -> pd.DataFrame:
    """Lịch sử một mã cho biểu đồ, lắp ráp y như `views.money_flow._history`."""

    def make() -> pd.DataFrame:
        cfg = load_defaults()["money_flow"]
        days = int(load_defaults()["money_flow_chart"]["history_days"])
        p = vmf.load_flow_panel(db, cfg, ticker=ticker, days=days)
        return mf.ticker_history(
            p["prices"], p["exact"], p["actions"], cfg, vmf._now_vn()
        )

    return _cached(f"history:{ticker}:{data_version(db)}", make)


def with_session(h: pd.DataFrame, bar: dict | None) -> tuple[pd.DataFrame, bool]:
    """Thêm phiên trên bảng giá vào cuối lịch sử biểu đồ khi DB chưa có phiên đó (D128). Chỉ để hiển thị.

    Nến và KL khớp lấy từ bảng giá; khối ngoại ròng = mua − bán tới lúc lấy (cùng định nghĩa cột prices_daily: gộp
    khớp lệnh và thỏa thuận). Tự doanh, phần thỏa thuận, CMF, trong nước để trống (NaN, không thành 0): bảng giá
    không có các số này. MA, MACD tính lại trên cả chuỗi giá. Trả (khung, có thêm phiên không). Không thêm khi bảng
    giá thiếu mở/cao/thấp hoặc DB đã có phiên đó (sau job 15:45).
    """
    if bar is None or not bar.get("nen") or h.empty:
        return h, False
    day = pd.Timestamp(bar["ngay"])
    if day <= h.index.max():
        return h, False
    row: dict[str, Any] = {
        c: False if h[c].dtype == bool else np.nan for c in h.columns
    }
    row |= {
        "open": bar["mo"],
        "high": bar["cao"],
        "low": bar["thap"],
        "close": bar["gia"],
        "vol_match": bar["kl"],
        "deal_is_lb": False,
        "f": bar["nn_rong"],
        "block": False,
        "big_block": False,
        "source": "live",
    }
    idx = pd.DatetimeIndex([day], name=h.index.name)
    out = pd.concat([h, pd.DataFrame([row], index=idx).astype(h.dtypes.to_dict())])
    ind = add_technical_indicators(
        out[["close"]].assign(high=out["high"], low=out["low"])
    )
    for c in ("MA20", "MA50", "MACD", "MACD_SIGNAL", "MACD_HIST"):
        out[c] = ind[c]
    return out, True


def session_flows(db: Any) -> dict:
    """Khối ngoại ròng của phiên trên bảng giá theo từng mã và ngành, khi DB chưa có phiên đó (D128).

    `co` False: bảng giá chưa có phiên nào mới hơn phiên cuối trong DB (ngoài giờ, sau job 15:45) hoặc lỗi nguồn
    (`loi`). Đơn vị đồng; mã không có số khối ngoại thì không có mặt, không tính là 0.
    """
    res = _result(db)
    bars, errors = web_live.session_data()
    day = max((b["ngay"] for b in bars.values()), default=None)
    last = res["meta"]["price_date"]
    if day is None or (last is not None and day <= dt.date.fromisoformat(last)):
        return {"co": False, "loi": errors}
    sector = {ma: tk["sector"] for ma, tk in res["tickers"].items()}
    net = {
        ma: b["nn_rong"]
        for ma, b in bars.items()
        if b["ngay"] == day and ma in sector and b["nn_rong"] is not None
    }
    by_sector: dict[str, float] = {}
    for ma, v in net.items():
        by_sector[sector[ma]] = by_sector.get(sector[ma], 0.0) + v
    return {
        "co": True,
        "ngay": day,
        "rong": sum(net.values()),
        "so_ma": len(net),
        "nganh": by_sector,
        "ma": net,
        "loi": errors,
    }


def normalize_ticker(raw: str) -> str | None:
    """Mã hợp lệ về mặt hình thức (AGENTS.md mục 5: validate input trước khi dùng); None nếu sai."""
    ticker = raw.strip().upper()
    return ticker if _TICKER_RE.fullmatch(ticker) else None


def parse_layers(text: str | None) -> list[str]:
    """`"0,1,3"` → tên các tầng theo thứ tự của `LAYERS`; None = mặc định của tab cũ (mọi tầng trừ MACD)."""
    if text is None:
        return [x for x in vmf.LAYERS if x != "MACD"]
    if text.strip() == "":
        return []
    picked = set()
    for part in text.split(","):
        if not part.strip().isdigit() or int(part) >= len(vmf.LAYERS):
            raise ValueError(f"tầng không hợp lệ: {part!r}")
        picked.add(int(part))
    return [x for i, x in enumerate(vmf.LAYERS) if i in picked]


def chart_options() -> dict:
    ccfg = load_defaults()["money_flow_chart"]
    return {
        "khung": list(ccfg["ranges"]),
        "khung_mac_dinh": ccfg["default_range"],
        "tang": list(vmf.LAYERS),
        "tang_mac_dinh": [i for i, x in enumerate(vmf.LAYERS) if x != "MACD"],
        "tang_dien_thoai": [
            i for i, x in enumerate(vmf.LAYERS) if x in vmf._PHONE_LAYERS
        ],
    }


def ticker_list(db: Any) -> list[dict]:
    """Mọi mã trong bảng `tickers` cho ô tìm kiếm; `co_dong_tien` = mã có trong bảng dòng tiền VN100."""
    from valuation.db.models import Ticker

    def make() -> list[dict]:
        flow = _result(db)["tickers"]
        rows = db.query(
            Ticker.ticker, Ticker.company_name, Ticker.sector, Ticker.is_vn100
        ).all()
        out = [
            {
                "ma": t,
                "ten": name or "",
                "nganh": flow[t]["sector"] if t in flow else (sector or ""),
                "vn100": bool(vn100),
                "co_dong_tien": t in flow,
            }
            for t, name, sector, vn100 in rows
        ]
        return sorted(out, key=lambda r: (not r["co_dong_tien"], r["ma"]))

    return _cached("tickers", make)


def overview(db: Any, mode: str) -> dict:
    """Tóm tắt, bảng ngành và danh sách 100 mã của tab "Dòng tiền ngành" ở một chế độ (loai/gom)."""
    res = _result(db)
    m = res["modes"][mode]
    tickers = []
    for r in vmf.ticker_frame(res, mode).to_dict("records"):
        tk = res["tickers"][r["Mã"]]
        v = tk["votes"]
        tickers.append(
            {
                "ma": r["Mã"],
                "nganh": r["Ngành"],
                "nhan": tk["label"]["code"],
                "phieu": [v[k]["vote"] for k in ("foreign", "pv", "prop")],
                "boi_canh": r["Bối cảnh"],
                # các cột số còn lại giữ nguyên tên và giá trị của bảng cũ (tên cột đổi theo chế độ)
                "cot": {k: x for k, x in r.items() if k not in _LIST_HEAD},
            }
        )
    return clean(
        {
            "che_do": mode,
            "meta": res["meta"],
            "trang_thai": vmf.status_line(res["meta"], mode),
            "ket_luan": m["conclusion"],
            "chi_tiet": m["detail"],
            "dem_nhan": res["label_counts"],
            "ten_nhan": mf.LABELS,
            "tong": m["totals"],
            "nganh": m["sectors"],
            "ma": tickers,
            "upside_nguon": res["upside"]["source"],
            "bieu_do": chart_options(),
            "tim_toi_da": int(_web_cfg()["search_limit"]),
        }
    )


def ticker(db: Any, ma: str, mode: str) -> dict | None:
    """Thẻ dòng tiền một mã: nhãn, ba phiếu, huy hiệu, dải khối ngoại, các bảng chi tiết. None = không có mã."""
    res = _result(db)
    tk = res["tickers"].get(ma)
    if tk is None:
        return None
    cfg = load_defaults()["money_flow"]
    n_spark = int(load_defaults()["money_flow_chart"]["spark_sessions"])
    sf = lessons.series_frame(tk).iloc[-n_spark:]
    # như _card của tab cũ: chế độ Loại bỏ phiên bị loại, chế độ Gồm cộng cả thỏa thuận
    spark = sf["f"].mask(sf["excl"].eq(True)) if mode == "loai" else sf["f_gom"]
    window = str(res["meta"]["window"])
    return clean(
        {
            "ma": ma,
            "che_do": mode,
            "nganh": tk["sector"],
            "nhan": tk["label"],
            "boi_canh": tk["context"],
            "ret20": tk["ret20"],
            "phieu": {k: tk["votes"][k] for k in ("foreign", "pv", "prop", "rvol")},
            "huy_hieu": tk["badges"],
            "giu_tu": tk["held_since"],
            "giu_tu_cat": tk["held_since_truncated"],
            "lich_su_nhan": tk["history"],
            "nguon": tk["source"],
            "tia": spark.tolist(),
            "cua_so": res["meta"]["window"],
            "gom_thoa_thuan": tk["flows"][window]["gom"],
            "trong_nuoc": tk["domestic"],
            "bang_phieu": vmf.votes_frame(tk, cfg).to_dict("records"),
            "bang_cua_so": vmf.windows_frame(tk, mode).to_dict("records"),
            "thoa_thuan": vmf.block_frame(tk).to_dict("records"),
            "upside": res["upside"]["rows"].get(ma),
            "upside_nguon": res["upside"]["source"],
            "gia_den": res["meta"]["price_date"],
            "dong_tien_den": res["meta"]["flow_date"],
        }
    )


def chart(
    db: Any,
    ma: str,
    mode: str,
    rng: str,
    layers: list[str],
    profile_on: bool,
    dark: bool,
    data_only: bool = False,
) -> dict | None:
    """Biểu đồ giá và dòng tiền của tab cũ (Lightweight Charts, D90): HTML để nhúng + chiều cao + chú thích.

    Lắp ráp y như `views.money_flow._chart_block`. None = không có mã; `html` None = mã chưa có giá.
    """
    if ma not in _result(db)["tickers"]:
        return None
    ccfg = load_defaults()["money_flow_chart"]
    h = _history(db, ma)
    if h.empty:
        return {
            "html": None,
            "cao": 0,
            "chu_thich": "Chưa có dữ liệu giá cho mã này.",
            "ho_so": None,
            "trong_phien": False,
        }
    # D128: phiên trên bảng giá mà DB chưa có (trong giờ giao dịch, tới lúc job 15:45 ghi) thành nến cuối
    bars, live_errors = web_live.session_data()
    h, live = with_session(h, bars.get(ma))
    v = vmf.chart_slice(h, int(ccfg["ranges"][rng]))
    vp_cfg = ccfg["volume_profile"]
    profile = (
        lw_chart.volume_profile(v, int(vp_cfg["rows"]), float(vp_cfg["value_area"]))
        if profile_on
        else None
    )
    if profile:
        profile["width"] = float(vp_cfg["width"])
    payload = lw_chart.build_payload(
        v,
        layers,
        mode,
        titles=vmf._LAYER_TITLE,
        helps=lessons.CHART_HELP,
        order=vmf.LAYERS,
        profile=profile,
    )
    src = (
        "VCI khớp lệnh/thỏa thuận (flow_daily)"
        if (v["source"][v["source"] != "live"] == "exact").all()
        else "một phần ước từ prices_daily (KL thỏa thuận chỉ là cận dưới)"
    )
    note = (
        f"{len(v)} phiên {vmf._d(mf._iso(v.index[0]))}–{vmf._d(mf._iso(v.index[-1]))} · nguồn: {src} · "
        "lũy kế tính từ đầu khung; ngày thiếu số không cộng. "
        + (
            "Chế độ Gồm: đường lũy kế cộng cả thỏa thuận."
            if mode == "gom"
            else "Chế độ Loại: lũy kế chỉ khớp lệnh."
        )
    )
    if live:
        note = (
            f"Nến {vmf._d(mf._iso(v.index[-1]))} lấy từ bảng giá Vietcap, chưa chốt: khối ngoại tính tới lúc lấy "
            f"(gồm cả thỏa thuận), tự doanh chưa có. {note}"
        )
    elif live_errors and web_live.in_live_hours(dt.datetime.now(web_live._tz())):
        note = (
            f"Chưa lấy được bảng giá trong phiên, biểu đồ dừng ở phiên đã chốt. {note}"
        )
    out = {
        "cao": lw_chart.chart_height(payload),
        "chu_thich": note,
        "ho_so": clean(
            {k: profile[k] for k in ("poc", "vah", "val", "total")} if profile else None
        ),
        "trong_phien": live,
    }
    # trình duyệt hỏi lại trong phiên chỉ cần dữ liệu để thay vào biểu đồ đang mở (giữ chỗ đang phóng to, kéo)
    return out | (
        {"du_lieu": clean(payload)}
        if data_only
        else {"html": lw_chart.render_html(payload, dark)}
    )
