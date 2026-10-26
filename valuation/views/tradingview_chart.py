"""Hàm vẽ dùng chung cho biểu đồ giá & dòng tiền (tab "Dòng tiền ngành", D74).

Biểu đồ kỹ thuật riêng ở tab Định giá đã chuyển hẳn sang tab money; RSI đã bỏ cho gọn.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

OVERLAY_OPTIONS = {
    "MA 20": "MA20",
    "MA 50": "MA50",
    "EMA 20": "EMA20",
    "Dải Bollinger": "BOLLINGER",
}


def _theme_colors(dark_mode: bool) -> dict[str, str]:
    if dark_mode:
        return {
            "paper": "#0B1220",
            "plot": "#111827",
            "text": "#E5E7EB",
            "muted": "#9CA3AF",
            "grid": "#273449",
            "border": "#374151",
            "hover": "#172033",
        }
    return {
        "paper": "#FFFFFF",
        "plot": "#FFFFFF",
        "text": "#111827",
        "muted": "#64748B",
        "grid": "#E5E7EB",
        "border": "#CBD5E1",
        "hover": "#F8FAFC",
    }


def _add_price_trace(fig: go.Figure, frame: pd.DataFrame, chart_type: str) -> None:
    if chart_type == "Nến":
        fig.add_trace(
            go.Candlestick(
                x=frame["time"],
                open=frame["open"],
                high=frame["high"],
                low=frame["low"],
                close=frame["close"],
                increasing={
                    "line": {"color": "#089981", "width": 1},
                    "fillcolor": "#089981",
                },
                decreasing={
                    "line": {"color": "#F23645", "width": 1},
                    "fillcolor": "#F23645",
                },
                name="Giá",
                hoverlabel={"namelength": 0},
            ),
            row=1,
            col=1,
        )
    elif chart_type == "OHLC":
        fig.add_trace(
            go.Ohlc(
                x=frame["time"],
                open=frame["open"],
                high=frame["high"],
                low=frame["low"],
                close=frame["close"],
                increasing_line_color="#089981",
                decreasing_line_color="#F23645",
                name="Giá",
            ),
            row=1,
            col=1,
        )
    else:
        fig.add_trace(
            go.Scatter(
                x=frame["time"],
                y=frame["close"],
                mode="lines",
                line={"color": "#2563EB", "width": 2},
                fill="tozeroy",
                fillcolor="rgba(37, 99, 235, 0.08)",
                name="Giá đóng cửa",
                hovertemplate="<b>%{x|%d/%m/%Y}</b><br>Giá: %{y:.2f}<extra></extra>",
            ),
            row=1,
            col=1,
        )


def _add_overlays(fig: go.Figure, frame: pd.DataFrame, overlays: list[str]) -> None:
    styles = {
        "MA20": ("MA 20", "#F59E0B"),
        "MA50": ("MA 50", "#2563EB"),
        "EMA20": ("EMA 20", "#8B5CF6"),
    }
    selected = {OVERLAY_OPTIONS[label] for label in overlays}
    for code, (label, color) in styles.items():
        if code not in selected:
            continue
        fig.add_trace(
            go.Scatter(
                x=frame["time"],
                y=frame[code],
                mode="lines",
                line={"color": color, "width": 1.6},
                name=label,
                hovertemplate=f"{label}: %{{y:.2f}}<extra></extra>",
            ),
            row=1,
            col=1,
        )

    if "BOLLINGER" in selected:
        fig.add_trace(
            go.Scatter(
                x=frame["time"],
                y=frame["BB_LOWER"],
                mode="lines",
                line={"color": "rgba(14, 116, 144, 0.45)", "width": 1},
                name="Bollinger dưới",
                hovertemplate="BB dưới: %{y:.2f}<extra></extra>",
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=frame["time"],
                y=frame["BB_UPPER"],
                mode="lines",
                line={"color": "rgba(14, 116, 144, 0.65)", "width": 1},
                fill="tonexty",
                fillcolor="rgba(14, 116, 144, 0.08)",
                name="Bollinger trên",
                hovertemplate="BB trên: %{y:.2f}<extra></extra>",
            ),
            row=1,
            col=1,
        )


def _add_macd(
    fig: go.Figure, frame: pd.DataFrame, row: int, colors: dict[str, str]
) -> None:
    """MACD (12, 26, 9): histogram xanh/đỏ + đường MACD và tín hiệu (cột từ technical_chart)."""
    hist = frame["MACD_HIST"]
    fig.add_trace(
        go.Bar(
            x=frame["time"],
            y=hist,
            marker={
                "color": ["#089981" if x >= 0 else "#F23645" for x in hist.fillna(0)],
                "line": {"width": 0},
            },
            opacity=0.62,
            name="MACD Histogram",
            hovertemplate="Histogram: %{y:.3f}<extra></extra>",
        ),
        row=row,
        col=1,
    )
    for col, label, color in (
        ("MACD", "MACD", "#2563EB"),
        ("MACD_SIGNAL", "Tín hiệu MACD", "#F59E0B"),
    ):
        fig.add_trace(
            go.Scatter(
                x=frame["time"],
                y=frame[col],
                mode="lines",
                line={"color": color, "width": 1.5},
                name=label,
                hovertemplate=f"{label}: %{{y:.3f}}<extra></extra>",
            ),
            row=row,
            col=1,
        )
    fig.add_hline(y=0, line={"color": colors["border"], "width": 1}, row=row, col=1)
