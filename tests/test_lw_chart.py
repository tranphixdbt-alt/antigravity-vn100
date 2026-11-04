"""Biểu đồ Lightweight Charts (D90): dữ liệu các tầng dựng ở Python — kiểm bằng số tay."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from valuation.views import lw_chart
from valuation.views.money_flow import _LAYER_TITLE, LAYERS, chart_slice


def _history() -> pd.DataFrame:
    idx = pd.to_datetime(["2026-10-28", "2026-10-29", "2026-10-30"])
    return pd.DataFrame(
        {
            "open": [100.0, 102.0, 101.0],
            "high": [103.0, 104.0, 102.0],
            "low": [99.0, 100.0, 97.0],
            "close": [102.0, 101.0, 98.0],
            "vol_match": [1000.0, 2000.0, 1500.0],
            "vol_deal": [0.0, 500.0, np.nan],
            "f": [2e9, -1e9, np.nan],
            "f_block": [np.nan, -3e9, 1e9],
            "p": [1e9, 1e9, -2e9],
            "p_block": [np.nan, np.nan, np.nan],
            "dom": [-3e9, 0.0, np.nan],
            "cmf": [0.1, -0.2, 0.05],
            "big_block": [False, True, False],
            "event": [None, None, "cổ tức tiền"],
            "MA20": [np.nan, 101.0, 100.0],
            "MA50": [np.nan, np.nan, np.nan],
            "MACD": [0.1, 0.2, 0.0],
            "MACD_SIGNAL": [0.1, 0.1, 0.1],
            "MACD_HIST": [0.0, 0.1, -0.1],
            "source": ["exact"] * 3,
        },
        index=idx,
    )


def _payload(layers: list[str], mode: str = "gom") -> dict:
    v = chart_slice(_history(), 3)
    return lw_chart.build_payload(
        v, layers, mode, titles=_LAYER_TITLE, helps={}, order=LAYERS
    )


def test_stacked_deal_matches_plotly_relative_bars() -> None:
    # Tính tay: cùng dấu −1 & −3 → cột tím −4 (lộ phần −3); thiếu khớp → thỏa thuận riêng +1; khác dấu → giữ.
    out = lw_chart.stacked_deal(
        pd.Series([-1.0, np.nan, 2.0]), pd.Series([-3.0, 1.0, -0.5])
    )
    assert out.tolist() == [-4.0, 1.0, -0.5]


def test_panes_follow_layer_order_and_nan_is_skipped() -> None:
    p = _payload(["Ai gom/xả", "Khối ngoại"])
    assert [x["key"] for x in p["panes"]] == ["Giá", "Khối ngoại", "Ai gom/xả"]
    ma50 = p["panes"][0]["series"][2]["data"]
    assert ma50 == []  # NaN không vẽ thành 0
    f_net = p["panes"][1]["series"][1]["data"]
    assert [(d["time"], d["value"], d["color"]) for d in f_net] == [
        ("2026-10-28", 2.0, lw_chart._UP),
        ("2026-10-29", -1.0, lw_chart._DOWN),
    ]
    cum = {d["time"]: d["value"] for d in p["panes"][1]["series"][2]["data"]}
    # Gồm: 2 → 2 + (−1 − 3) = −2 → −2 + 1 = −1 (tỷ)
    assert cum == {"2026-10-28": 2.0, "2026-10-29": -2.0, "2026-10-30": -1.0}
    assert p["panes"][2].get("symmetric") is True


def test_markers_for_big_deal_and_ex_rights() -> None:
    markers = _payload([])["panes"][0]["series"][0]["markers"]
    assert [(m["time"], m["text"]) for m in markers] == [
        ("2026-10-29", "TT"),
        ("2026-10-30", "cổ tức tiền"),
    ]


def test_loai_mode_has_no_deal_series() -> None:
    p = _payload(["Khối lượng", "Khối ngoại"], mode="loai")
    titles = [s["options"]["title"] for pane in p["panes"] for s in pane["series"]]
    assert "KL thỏa thuận" not in titles and "Thỏa thuận" not in titles


def test_html_is_self_contained_and_escapes_script_close() -> None:
    payload = _payload(["MACD"])
    payload["panes"][0]["title"] = "</script><script>alert(1)</script>"
    html = lw_chart.render_html(payload, dark=False)
    assert "TradingView Lightweight Charts" in html and "https://unpkg" not in html
    data = html.split("const P = ", 1)[1].split(", D = ", 1)[0]
    assert "</script>" not in data and json.loads(data.replace("<\\/", "</"))["panes"][
        0
    ]["title"].startswith("</")


def test_volume_overlays_price_pane_instead_of_own_pane() -> None:
    p = _payload(["Khối lượng", "Khối ngoại"])
    assert [x["key"] for x in p["panes"]] == ["Giá", "Khối ngoại"]
    price = p["panes"][0]["series"]
    # Gồm: cột tím thỏa thuận rồi KL khớp, đều trước nến (vẽ phía sau), cùng thang "vol" ở đáy.
    assert [s["options"]["title"] for s in price[:3]] == [
        "KL thỏa thuận",
        "KL khớp",
        "Giá",
    ]
    assert {s["scale"] for s in price[:2]} == {"vol"} and price[1]["margins"][
        "top"
    ] == 0.78
    assert [d["value"] for d in price[0]["data"]] == [
        1000.0,
        2500.0,
        1500.0,
    ]  # khớp + thỏa thuận


def test_volume_profile_checked_by_hand() -> None:
    # A: 10–12, 100 cp, tăng → 50/50 vào hàng 10–11, 11–12. B: 11–13, 50 cp, giảm → 25/25 vào 11–12, 12–13.
    # Tổng hàng: 50, 75, 25 → POC 11–12 (giữa 11,5). VA 70% × 150 = 105: 75 + max(trên 25, dưới 50) = 125.
    idx = pd.to_datetime(["2026-10-28", "2026-10-29"])
    v = pd.DataFrame(
        {
            "open": [10.5, 12.5],
            "high": [12.0, 13.0],
            "low": [10.0, 11.0],
            "close": [11.5, 11.5],
            "vol_match": [100.0, 50.0],
        },
        index=idx,
    )
    vp = lw_chart.volume_profile(v, rows=3, value_area=0.70)
    assert [(r["up"], r["down"], r["va"]) for r in vp["rows"]] == [
        (50.0, 0.0, True),
        (50.0, 25.0, True),
        (0.0, 25.0, False),
    ]
    assert (vp["poc"], vp["val"], vp["vah"], vp["total"]) == (11.5, 10.0, 12.0, 150.0)


def test_profile_attached_to_price_series_only_when_on() -> None:
    v = chart_slice(_history(), 3)
    off = lw_chart.build_payload(
        v, [], "gom", titles=_LAYER_TITLE, helps={}, order=LAYERS
    )
    assert "vp" not in off["panes"][0]["series"][0]
    vp = {**lw_chart.volume_profile(v, 4, 0.7), "width": 0.3}
    on = lw_chart.build_payload(
        v, [], "gom", titles=_LAYER_TITLE, helps={}, order=LAYERS, profile=vp
    )
    assert on["panes"][0]["series"][0]["vp"]["width"] == 0.3
