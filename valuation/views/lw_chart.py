"""Biểu đồ dòng tiền kiểu TradingView bằng Lightweight Charts v5.2.1 (D90, người dùng chọn).

Python dựng toàn bộ dữ liệu từng tầng (test được); JS nhúng chỉ vẽ. Thư viện để trong repo
(`assets/vendor/`, Apache-2.0) nên không gọi CDN lúc chạy. Cùng dữ liệu/tầng với `flow_chart` (Plotly).
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

_LIB = (
    Path(__file__).parent
    / "assets"
    / "vendor"
    / "lightweight-charts.standalone.production.js"
)
_UP, _DOWN, _DEAL, _PROP, _DOM = "#089981", "#F23645", "#8E44AD", "#1d4289", "#F59E0B"
_UP_A, _DOWN_A = (
    "rgba(8,153,129,0.45)",
    "rgba(242,54,69,0.45)",
)  # cột KL mờ để không che nến
_PRICE_HEIGHT, _LAYER_HEIGHT = 380, 200
_TY = {"type": "price", "precision": 1, "minMove": 0.1}  # tỷ đồng
_VND = {"type": "price", "precision": 0, "minMove": 1}  # giá đồng/cp


def _times(index: pd.Index) -> list[str]:
    return [pd.Timestamp(t).strftime("%Y-%m-%d") for t in index]


def _points(
    times: list[str], values: pd.Series, colors: list[str] | None = None
) -> list[dict]:
    """Bỏ điểm NaN (không vẽ thành 0 — ngày thiếu số giữ trống như bản Plotly)."""
    out = []
    for i, (t, v) in enumerate(zip(times, values)):
        if v is None or (isinstance(v, float) and math.isnan(v)) or pd.isna(v):
            continue
        point: dict[str, Any] = {"time": t, "value": round(float(v), 4)}
        if colors is not None:
            point["color"] = colors[i]
        out.append(point)
    return out


def _signed_colors(values: pd.Series) -> list[str]:
    return [_UP if (v if pd.notna(v) else 0) >= 0 else _DOWN for v in values]


def stacked_deal(match: pd.Series, deal: pd.Series) -> pd.Series:
    """Cột tím vẽ TRƯỚC cột khớp lệnh để giả lập barmode="relative" của Plotly.

    Cùng dấu → cột tím = khớp + thỏa thuận (phần lộ ra là thỏa thuận); khác dấu/thiếu khớp → thỏa
    thuận đứng riêng từ 0 về phía của nó.
    """
    same = match.notna() & (np.sign(match) == np.sign(deal))
    return (match + deal).where(same, deal)


def _series(kind: str, data: list[dict], scale: str = "right", **options: Any) -> dict:
    return {"type": kind, "scale": scale, "data": data, "options": options}


def volume_profile(
    v: pd.DataFrame, rows: int, value_area: float
) -> dict[str, Any] | None:
    """Volume profile của khung đang xem (cố định theo khung, không theo vùng zoom).

    Mỗi phiên rải KL khớp đều trên [thấp, cao] vào `rows` hàng giá; nến tăng → KL "mua", nến giảm →
    "bán" (xấp xỉ từ nến ngày như TradingView khi không có dữ liệu khung nhỏ). POC = hàng KL lớn nhất;
    vùng giá trị mở rộng từ POC mỗi bước thêm hàng kề lớn hơn (trên/dưới) tới khi đạt `value_area`.
    """
    d = v[["open", "high", "low", "close", "vol_match"]].dropna()
    d = d[d["vol_match"] > 0]
    if d.empty or rows < 1:
        return None
    lo, hi = float(d["low"].min()), float(d["high"].max())
    if hi <= lo:
        return None
    edges = np.linspace(lo, hi, rows + 1)
    low, high = d["low"].to_numpy()[:, None], d["high"].to_numpy()[:, None]
    span = high - low
    overlap = np.clip(
        np.minimum(high, edges[1:]) - np.maximum(low, edges[:-1]), 0, None
    )
    # Nến không biên độ (cao = thấp): dồn cả KL vào hàng chứa giá đó.
    point = np.zeros_like(overlap)
    idx = np.clip(
        np.searchsorted(edges, d["low"].to_numpy(), side="right") - 1, 0, rows - 1
    )
    point[np.arange(len(d)), idx] = 1.0
    share = np.where(span > 0, overlap / np.where(span > 0, span, 1), point)
    vol = share * d["vol_match"].to_numpy()[:, None]
    up_mask = (d["close"] >= d["open"]).to_numpy()
    up, down = vol[up_mask].sum(axis=0), vol[~up_mask].sum(axis=0)
    total_row = up + down
    total = float(total_row.sum())
    poc = int(total_row.argmax())
    top = bottom = poc
    acc = float(total_row[poc])
    while acc < value_area * total and (top < rows - 1 or bottom > 0):
        above = total_row[top + 1] if top < rows - 1 else -1.0
        below = total_row[bottom - 1] if bottom > 0 else -1.0
        if above >= below:
            top += 1
            acc += float(above)
        else:
            bottom -= 1
            acc += float(below)
    return {
        "rows": [
            {
                "lo": float(edges[i]),
                "hi": float(edges[i + 1]),
                "up": float(up[i]),
                "down": float(down[i]),
                "va": bottom <= i <= top,
            }
            for i in range(rows)
        ],
        "poc": float((edges[poc] + edges[poc + 1]) / 2),
        "vah": float(edges[top + 1]),
        "val": float(edges[bottom]),
        "total": total,
    }


def build_payload(
    v: pd.DataFrame,
    layers: list[str],
    mode: str,
    *,
    titles: dict[str, str],
    helps: dict[str, str],
    order: tuple[str, ...],
    profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Dữ liệu các tầng theo thứ tự `order` (LAYERS); cột như `chart_slice` trả về.

    `profile` (từ `volume_profile`, kèm khóa `width`) → vẽ volume profile trên tầng giá.
    """
    t = _times(v.index)
    gom = mode == "gom"
    ohlc = v[["open", "high", "low", "close"]].notna().all(axis=1)
    candles = [
        {
            "time": t[i],
            "open": float(r.open),
            "high": float(r.high),
            "low": float(r.low),
            "close": float(r.close),
        }
        for i, r in enumerate(v[["open", "high", "low", "close"]].itertuples())
        if ohlc.iloc[i]
    ]
    markers = [
        {
            "time": t[i],
            "position": "aboveBar",
            "shape": "circle",
            "color": _DEAL,
            "size": 1,
            "text": "TT",
        }
        for i, big in enumerate(v["big_block"].fillna(False))
        if big
    ] + [
        {
            "time": t[i],
            "position": "belowBar",
            "shape": "arrowUp",
            "color": "#64748B",
            "size": 1,
            "text": str(ev),
        }
        for i, ev in enumerate(v["event"])
        if isinstance(ev, str) and ev
    ]
    markers.sort(key=lambda m: m["time"])
    price = _series(
        "Candlestick",
        candles,
        upColor=_UP,
        downColor=_DOWN,
        borderVisible=False,
        wickUpColor=_UP,
        wickDownColor=_DOWN,
        priceFormat=_VND,
        title="Giá",
    )
    price["markers"] = markers
    if profile:
        price["vp"] = profile
    panes: list[dict[str, Any]] = [
        {
            "key": "Giá",
            "title": titles["Giá"],
            "help": helps.get("Giá", ""),
            "height": _PRICE_HEIGHT,
            "series": [
                price,
                _series(
                    "Line",
                    _points(t, v["MA20"]),
                    color="#F59E0B",
                    lineWidth=1,
                    priceFormat=_VND,
                    title="MA20",
                    priceLineVisible=False,
                    lastValueVisible=False,
                    crosshairMarkerVisible=False,
                ),
                _series(
                    "Line",
                    _points(t, v["MA50"]),
                    color="#2962FF",
                    lineWidth=1,
                    priceFormat=_VND,
                    title="MA50",
                    priceLineVisible=False,
                    lastValueVisible=False,
                    crosshairMarkerVisible=False,
                ),
            ],
        }
    ]
    for name in (x for x in order if x in layers):
        pane: dict[str, Any] = {
            "key": name,
            "title": titles[name],
            "help": helps.get(name, ""),
            "height": _LAYER_HEIGHT,
            "series": [],
        }
        if name == "Khối lượng":
            # Như TradingView: KL khớp lồng vào đáy tầng giá (thang riêng, không trục), không tách tầng.
            up = [_UP_A if c >= o else _DOWN_A for o, c in zip(v["open"], v["close"])]
            vol = [
                _series(
                    "Histogram",
                    _points(t, v["vol_match"], up),
                    "vol",
                    priceFormat={"type": "volume"},
                    title="KL khớp",
                    priceLineVisible=False,
                    lastValueVisible=False,
                )
            ]
            if gom:
                vol.insert(
                    0,
                    _series(
                        "Histogram",
                        _points(t, v["vol_match"].fillna(0) + v["vol_deal"].fillna(0)),
                        "vol",
                        color="rgba(142,68,173,0.45)",
                        priceFormat={"type": "volume"},
                        title="KL thỏa thuận",
                        lastValueVisible=False,
                        priceLineVisible=False,
                    ),
                )
            for item in vol:
                item["margins"] = {"top": 0.78, "bottom": 0}
            price["margins"] = {"top": 0.06, "bottom": 0.24}  # chừa đáy cho cột KL
            panes[0]["series"][:0] = vol  # thêm trước nến → vẽ phía sau nến
            panes[0]["title"] += " · cột đáy: KL khớp"
            continue
        elif name in ("Khối ngoại", "Tự doanh"):
            c = "f" if name == "Khối ngoại" else "p"
            net = v[c] / 1e9
            if gom:
                pane["series"].append(
                    _series(
                        "Histogram",
                        _points(t, stacked_deal(net, v[f"{c}_block"] / 1e9)),
                        "left",
                        color=_DEAL,
                        priceFormat=_TY,
                        title="Thỏa thuận",
                        lastValueVisible=False,
                        priceLineVisible=False,
                    )
                )
            pane["series"].append(
                _series(
                    "Histogram",
                    _points(t, net, _signed_colors(net)),
                    "left",
                    priceFormat=_TY,
                    title="Ròng/ngày",
                    priceLineVisible=False,
                    lastValueVisible=False,
                )
            )
            cum = v[f"cum_{c}_gom" if gom else f"cum_{c}"] / 1e9
            pane["series"].append(
                _series(
                    "Line",
                    _points(t, cum),
                    color="theme",
                    lineWidth=2,
                    priceFormat=_TY,
                    title="Lũy kế",
                    priceLineVisible=False,
                )
            )
        elif name == "Ai gom/xả":
            pane["symmetric"] = (
                True  # 0 của CMF (trái) và 0 của lũy kế (phải) nằm cùng một đường
            )
            pane["series"].append(
                _series(
                    "Baseline",
                    _points(t, v["cmf"]),
                    "left",
                    baseValue={"type": "price", "price": 0},
                    topLineColor="rgba(8,153,129,0.6)",
                    topFillColor1="rgba(8,153,129,0.28)",
                    topFillColor2="rgba(8,153,129,0.05)",
                    bottomLineColor="rgba(242,54,69,0.6)",
                    bottomFillColor1="rgba(242,54,69,0.05)",
                    bottomFillColor2="rgba(242,54,69,0.28)",
                    lineWidth=1,
                    priceFormat={"type": "price", "precision": 2, "minMove": 0.01},
                    title="CMF20",
                    priceLineVisible=False,
                    lastValueVisible=False,
                )
            )
            for c, label, color in (
                ("f", "Khối ngoại", _UP),
                ("p", "Tự doanh", _PROP),
                ("dom", "Trong nước (suy ra)", _DOM),
            ):
                key = f"cum_{c}_gom" if gom and c != "dom" else f"cum_{c}"
                pane["series"].append(
                    _series(
                        "Line",
                        _points(t, v[key] / 1e9),
                        color=color,
                        lineWidth=2,
                        priceFormat=_TY,
                        title=label,
                        priceLineVisible=False,
                    )
                )
        elif name == "MACD":
            pane["series"] += [
                _series(
                    "Histogram",
                    _points(t, v["MACD_HIST"], _signed_colors(v["MACD_HIST"])),
                    priceFormat={"type": "price", "precision": 3, "minMove": 0.001},
                    title="Histogram",
                    priceLineVisible=False,
                    lastValueVisible=False,
                ),
                _series(
                    "Line",
                    _points(t, v["MACD"]),
                    color="#2962FF",
                    lineWidth=1.5,
                    title="MACD",
                    priceLineVisible=False,
                ),
                _series(
                    "Line",
                    _points(t, v["MACD_SIGNAL"]),
                    color="#F59E0B",
                    lineWidth=1.5,
                    title="Tín hiệu",
                    priceLineVisible=False,
                ),
            ]
        panes.append(pane)
    return {"panes": panes}


def chart_height(payload: dict[str, Any]) -> int:
    return sum(int(p["height"]) for p in payload["panes"]) + 40


_TEMPLATE = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;padding:0;background:__BG__;font-family:-apple-system,BlinkMacSystemFont,"Trebuchet MS",Roboto,sans-serif}
#wrap{position:relative;width:100%;height:__H__px}
#chart{position:absolute;inset:0}
.lg{position:absolute;left:8px;z-index:3;pointer-events:none;font-size:12px;line-height:18px;color:__TEXT__;
  max-width:calc(100% - 90px);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.lg b{font-weight:600}.lg .t{color:__MUTED__}.lg .q{pointer-events:auto;cursor:help;color:__MUTED__;margin-left:4px;
  border:1px solid __MUTED__;border-radius:50%;display:inline-block;width:14px;height:14px;line-height:13px;
  text-align:center;font-size:10px}
.lg .v{margin-right:10px}
</style></head><body><div id="wrap"><div id="chart"></div></div>
<script>__LIB__</script>
<script>
const P = __DATA__, D = __THEME__, LW = LightweightCharts;
const wrap = document.getElementById('wrap');
const chart = LW.createChart(document.getElementById('chart'), {
  autoSize: true,
  layout: {background: {type: 'solid', color: D.bg}, textColor: D.text, fontSize: 11,
           panes: {separatorColor: D.grid, separatorHoverColor: D.hover, enableResize: true}},
  grid: {vertLines: {color: D.grid}, horzLines: {color: D.grid}},
  crosshair: {mode: LW.CrosshairMode.Normal},
  rightPriceScale: {borderColor: D.grid, minimumWidth: 64},
  leftPriceScale: {visible: __LEFT__, borderColor: D.grid, minimumWidth: 52},
  timeScale: {borderColor: D.grid, rightOffset: 4, barSpacing: 6, minBarSpacing: 1},
  localization: {locale: 'vi-VN', dateFormat: 'dd/MM/yyyy'},
});
const fmt = (s, x) => {
  const f = s.options().priceFormat || {};
  if (f.type === 'volume') return Intl.NumberFormat('vi-VN', {notation: 'compact', maximumFractionDigits: 1}).format(x);
  return Intl.NumberFormat('vi-VN', {maximumFractionDigits: f.precision ?? 0}).format(x);
};
// Volume profile (primitive v5): thanh ngang bám mép phải tầng giá, vẽ dưới nến.
class VolumeProfile {
  constructor(d) { this.d = d; }
  attached(p) { this.series = p.series; }
  paneViews() { return [{zOrder: () => 'bottom', renderer: () => ({draw: t => this.draw(t)})}]; }
  draw(target) {
    const d = this.d, s = this.series; if (!s) return;
    target.useBitmapCoordinateSpace(sc => {
      const ctx = sc.context, hr = sc.horizontalPixelRatio, vr = sc.verticalPixelRatio, W = sc.bitmapSize.width;
      const max = Math.max(...d.rows.map(r => r.up + r.down)) || 1;
      d.rows.forEach(r => {
        const y1 = s.priceToCoordinate(r.hi), y2 = s.priceToCoordinate(r.lo);
        if (y1 === null || y2 === null) return;
        const top = Math.round(Math.min(y1, y2) * vr), h = Math.max(1, Math.round(Math.abs(y2 - y1) * vr) - Math.round(vr));
        const len = (r.up + r.down) / max * W * d.width, upLen = len * r.up / ((r.up + r.down) || 1);
        ctx.fillStyle = r.va ? 'rgba(41,98,255,0.55)' : 'rgba(41,98,255,0.18)';
        ctx.fillRect(W - len, top, upLen, h);
        ctx.fillStyle = r.va ? 'rgba(251,192,45,0.65)' : 'rgba(251,192,45,0.22)';
        ctx.fillRect(W - len + upLen, top, len - upLen, h);
      });
      const fmtP = x => Intl.NumberFormat('vi-VN', {maximumFractionDigits: 0}).format(x);
      [['POC', d.poc, '#F23645', []], ['VAH', d.vah, '#2962FF', [4, 3]], ['VAL', d.val, '#2962FF', [4, 3]]].forEach(([k, p, c, dash]) => {
        const y = s.priceToCoordinate(p); if (y === null) return;
        ctx.save(); ctx.strokeStyle = c; ctx.lineWidth = Math.max(1, hr); ctx.setLineDash(dash.map(x => x * hr));
        ctx.beginPath(); ctx.moveTo(0, Math.round(y * vr) + 0.5); ctx.lineTo(W, Math.round(y * vr) + 0.5); ctx.stroke();
        ctx.setLineDash([]); ctx.fillStyle = c; ctx.font = `${11 * vr}px sans-serif`;
        ctx.fillText(`${k} ${fmtP(p)}`, 6 * hr, Math.round(y * vr) - 3 * vr); ctx.restore();
      });
    });
  }
  updateAllViews() {}
}
const legends = [];
P.panes.forEach((pane, i) => {
  const made = [];
  pane.series.forEach(s => {
    const opts = Object.assign({}, s.options, {priceScaleId: s.scale});
    if (opts.color === 'theme') opts.color = s.options.color = D.text;  // đường lũy kế: màu chữ theo nền
    if (pane.symmetric) opts.autoscaleInfoProvider = orig => {
      const r = orig(); if (!r || !r.priceRange) return r;
      const m = Math.max(Math.abs(r.priceRange.minValue), Math.abs(r.priceRange.maxValue)) * 1.08;
      return {priceRange: {minValue: -m, maxValue: m}};
    };
    const api = chart.addSeries(LW[s.type + 'Series'], opts, i);
    if (s.margins) api.priceScale().applyOptions({scaleMargins: s.margins});
    api.setData(s.data);
    const mk = s.type === 'Candlestick' || (s.markers && s.markers.length) ? LW.createSeriesMarkers(api, s.markers || []) : null;
    const vp = s.vp ? new VolumeProfile(s.vp) : null;
    if (vp) api.attachPrimitive(vp);
    made.push({api, s, mk, vp});
  });
  if (i > 0) chart.panes()[i].setStretchFactor(pane.height / P.panes[0].height);
  const el = document.createElement('div'); el.className = 'lg'; wrap.appendChild(el);
  const head = document.createElement('div');
  const title = document.createElement('span'); title.className = 't'; title.textContent = pane.title;
  head.appendChild(title);
  if (pane.help) { const q = document.createElement('span'); q.className = 'q'; q.textContent = '?'; q.title = pane.help; head.appendChild(q); }
  const vals = document.createElement('div');
  el.appendChild(head); el.appendChild(vals);
  legends.push({el, vals, made});
});
const dateOf = t => typeof t === 'string' ? t.split('-').reverse().join('/') : '';
function draw(param) {
  legends.forEach((lg, i) => {
    lg.vals.textContent = '';
    if (i === 0 && param && param.time) {
      const d = document.createElement('span'); d.className = 'v'; d.innerHTML = '<b></b>'; d.firstChild.textContent = dateOf(param.time);
      lg.vals.appendChild(d);
    }
    // Nến (OHLC) luôn đứng đầu chú thích dù cột KL được thêm trước để vẽ phía sau.
    [...lg.made].sort((a, b) => (b.s.type === 'Candlestick') - (a.s.type === 'Candlestick')).forEach(({api, s}) => {
      const data = param && param.time ? param.seriesData.get(api) : api.data()[api.data().length - 1];
      if (!data) return;
      const span = document.createElement('span'); span.className = 'v';
      if (data.open !== undefined) {
        span.textContent = `O ${fmt(api, data.open)}  H ${fmt(api, data.high)}  L ${fmt(api, data.low)}  C ${fmt(api, data.close)}`;
        span.style.color = data.close >= data.open ? '__UP__' : '__DOWN__';
      } else if (data.value !== undefined) {
        span.textContent = `${s.options.title}: ${fmt(api, data.value)}`;
        span.style.color = data.color || s.options.color || s.options.topLineColor || D.text;
      }
      lg.vals.appendChild(span);
    });
  });
}
function place() {
  const top = wrap.getBoundingClientRect().top;
  const left = (chart.options().leftPriceScale.visible ? chart.priceScale('left', 0).width() : 0) + 8;
  chart.panes().forEach((p, i) => {
    const e = p.getHTMLElement(); if (!e || !legends[i]) return;
    legends[i].el.style.top = (e.getBoundingClientRect().top - top + 4) + 'px';
    legends[i].el.style.left = left + 'px';
  });
}
chart.subscribeCrosshairMove(draw);
draw(null);
// D128: trang chứa gửi dữ liệu mới (cùng các tầng) trong phiên → thay số, giữ nguyên chỗ đang phóng to, kéo
window.addEventListener('message', e => {
  const N = e.source === window.parent && e.data && e.data.loai === 'bt-bieu-do' ? e.data.du_lieu : null;
  if (!N || !N.panes || N.panes.length !== legends.length) return;
  if (N.panes.some((p, i) => p.series.length !== legends[i].made.length)) return;
  N.panes.forEach((p, i) => p.series.forEach((s, k) => {
    const m = legends[i].made[k];
    m.api.setData(s.data); m.s.data = s.data;
    if (m.mk) m.mk.setMarkers(s.markers || []);
    if (m.vp && s.vp) m.vp.d = s.vp;
  }));
  draw(null);
});
chart.timeScale().fitContent();
requestAnimationFrame(() => requestAnimationFrame(place));
new ResizeObserver(() => requestAnimationFrame(place)).observe(wrap);
wrap.addEventListener('mouseup', () => setTimeout(place, 30));
</script></body></html>"""


def render_html(payload: dict[str, Any], dark: bool) -> str:
    """HTML tự chứa (thư viện + dữ liệu). JSON đã chặn '</' để dữ liệu không đóng thẻ <script>."""
    theme = (
        {
            "bg": "#131722",
            "text": "#D1D4DC",
            "muted": "#787B86",
            "grid": "#2A2E39",
            "hover": "rgba(120,123,134,0.3)",
        }
        if dark
        else {
            "bg": "#FFFFFF",
            "text": "#131722",
            "muted": "#787B86",
            "grid": "#F0F3FA",
            "hover": "rgba(120,123,134,0.2)",
        }
    )
    left = any(s["scale"] == "left" for p in payload["panes"] for s in p["series"])
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html = (
        _TEMPLATE.replace("__DATA__", data)
        .replace("__THEME__", json.dumps(theme))
        .replace("__LEFT__", "true" if left else "false")
        .replace("__H__", str(chart_height(payload)))
        .replace("__BG__", theme["bg"])
        .replace("__TEXT__", theme["text"])
        .replace("__MUTED__", theme["muted"])
        .replace("__UP__", _UP)
        .replace("__DOWN__", _DOWN)
    )
    return html.replace(
        "__LIB__", _LIB.read_text(encoding="utf-8")
    )  # cuối cùng: không thay nhầm trong thư viện
