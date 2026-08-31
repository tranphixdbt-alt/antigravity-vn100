"""Theme chung cho giao diện Streamlit của hệ thống VN100."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st


def escape_html(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def render_app_theme() -> None:
    """Áp CSS nhẹ, đồng nhất tone xanh tài chính cho toàn bộ app."""
    st.markdown(
        """
<style>
    :root {
        --ag-green-950: #062e25;
        --ag-green-900: #064e3b;
        --ag-green-800: #065f46;
        --ag-green-700: #047857;
        --ag-green-600: #059669;
        --ag-green-500: #10b981;
        --ag-green-100: #d1fae5;
        --ag-green-50: #ecfdf5;
        --ag-ink: #172033;
        --ag-muted: #5f6b7a;
        --ag-soft: #f7fbf8;
        --ag-line: #dce9e2;
        --ag-warn: #b7791f;
        --ag-danger: #b91c1c;
        --ag-card-shadow: 0 10px 28px rgba(8, 47, 73, 0.06);
    }

    html, body, [class*="css"], .stApp {
        font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI",
            sans-serif;
        color: var(--ag-ink);
    }

    .stApp {
        background:
            linear-gradient(180deg, rgba(236,253,245,0.72), rgba(255,255,255,0) 260px),
            #ffffff;
    }

    .block-container {
        padding-top: 2.3rem;
        padding-bottom: 3rem;
        max-width: 1320px;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f1fbf5 0%, #f8fafc 62%, #ffffff 100%);
        border-right: 1px solid var(--ag-line);
    }

    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
        color: var(--ag-green-900);
        letter-spacing: 0;
    }

    h1, h2, h3 {
        color: var(--ag-ink);
        letter-spacing: 0;
        font-weight: 800;
    }

    h1 {
        font-size: clamp(30px, 4vw, 46px);
        line-height: 1.08;
    }

    h2 {
        font-size: 27px;
        line-height: 1.18;
    }

    h3 {
        font-size: 20px;
        line-height: 1.28;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: var(--ag-line);
        border-radius: 8px;
        box-shadow: var(--ag-card-shadow);
    }

    div[data-testid="stMetric"] {
        border: 1px solid var(--ag-line);
        border-radius: 8px;
        padding: 14px 16px;
        background: #ffffff;
        box-shadow: 0 8px 20px rgba(15, 118, 110, 0.05);
    }

    div[data-testid="stMetric"] label,
    div[data-testid="stMetric"] [data-testid="stMetricLabel"] {
        color: var(--ag-muted);
        font-weight: 750;
    }

    div[data-testid="stMetricValue"] {
        color: var(--ag-green-900);
        font-weight: 850;
    }

    button[kind="primary"],
    div[data-testid="stButton"] button[kind="primary"] {
        background: linear-gradient(135deg, var(--ag-green-800), var(--ag-green-600));
        border: 1px solid var(--ag-green-700);
        color: #ffffff;
        box-shadow: 0 9px 18px rgba(5, 150, 105, 0.18);
    }

    div[data-testid="stButton"] button {
        border-radius: 8px;
        border-color: #bfd8ce;
        color: var(--ag-green-900);
        font-weight: 750;
        transition: transform 140ms ease, box-shadow 140ms ease,
            border-color 140ms ease, background-color 140ms ease;
    }

    div[data-testid="stButton"] button:hover {
        transform: translateY(-1px);
        border-color: var(--ag-green-500);
        background: var(--ag-green-50);
        box-shadow: 0 8px 18px rgba(15, 118, 110, 0.10);
    }

    div[data-baseweb="select"] > div,
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input,
    div[data-testid="stTextArea"] textarea {
        border-radius: 8px;
        border-color: #c9ddd3;
        background: #ffffff;
    }

    div[data-testid="stAlert"] {
        border-radius: 8px;
        border: 1px solid var(--ag-line);
        box-shadow: 0 8px 22px rgba(15, 118, 110, 0.04);
    }

    div[data-testid="stExpander"] {
        border: 1px solid var(--ag-line);
        border-radius: 8px;
        background: #ffffff;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.035);
    }

    div[data-testid="stTabs"] [role="tablist"] {
        gap: 4px;
        border-bottom: 1px solid var(--ag-line);
    }

    div[data-testid="stTabs"] [role="tab"] {
        color: #475569;
        border-radius: 8px 8px 0 0;
        padding: 10px 12px;
        font-weight: 750;
    }

    div[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
        color: var(--ag-green-800);
        background: #f3fbf6;
        border-bottom-color: var(--ag-green-600);
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid var(--ag-line);
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 8px 18px rgba(15, 23, 42, 0.035);
    }

    hr {
        border-color: var(--ag-line);
        margin: 1.25rem 0;
    }

    .ag-shell-hero {
        border: 1px solid #b7e4cf;
        border-left: 7px solid var(--ag-green-600);
        border-radius: 8px;
        background:
            linear-gradient(135deg, rgba(236,253,245,0.95), rgba(255,255,255,0.98)),
            #ffffff;
        padding: 22px 26px;
        margin: 4px 0 18px;
        box-shadow: var(--ag-card-shadow);
        animation: agFadeIn 220ms ease-out both;
    }

    .ag-shell-row {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 20px;
        flex-wrap: wrap;
    }

    .ag-kicker {
        color: var(--ag-green-700);
        font-size: 12px;
        font-weight: 850;
        letter-spacing: 0;
        text-transform: uppercase;
        margin-bottom: 7px;
    }

    .ag-shell-title {
        color: var(--ag-green-950);
        font-size: clamp(30px, 4vw, 42px);
        font-weight: 850;
        line-height: 1.1;
        margin: 0;
    }

    .ag-shell-copy {
        color: #334155;
        font-size: 15px;
        line-height: 1.55;
        max-width: 790px;
        margin: 10px 0 0;
    }

    .ag-trust-row {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 16px;
    }

    .ag-trust-pill {
        border: 1px solid #a7f3d0;
        background: #ffffff;
        border-radius: 999px;
        color: var(--ag-green-800);
        display: inline-flex;
        font-size: 13px;
        font-weight: 750;
        padding: 7px 11px;
        white-space: nowrap;
    }

    .ag-summary-card {
        border: 1px solid #b7e4cf;
        border-left: 7px solid var(--ag-summary-color, var(--ag-green-600));
        border-radius: 8px;
        background: var(--ag-summary-bg, var(--ag-green-50));
        padding: 22px 26px;
        margin: 8px 0 18px;
        box-shadow: var(--ag-card-shadow);
        animation: agFadeIn 220ms ease-out both;
    }

    .ag-summary-meta {
        color: #64748b;
        font-size: 13px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0;
        margin-bottom: 8px;
    }

    .ag-summary-title {
        color: var(--ag-summary-text, var(--ag-green-900));
        font-size: clamp(30px, 5vw, 44px);
        font-weight: 900;
        line-height: 1.12;
        margin: 0;
    }

    .ag-summary-price {
        color: #64748b;
        font-size: 13px;
        font-weight: 700;
        margin-bottom: 6px;
        text-align: right;
    }

    .ag-summary-upside {
        color: var(--ag-summary-text, var(--ag-green-900));
        font-size: clamp(26px, 4vw, 36px);
        font-weight: 900;
        line-height: 1.1;
        text-align: right;
        margin: 0;
    }

    @keyframes agFadeIn {
        from { opacity: 0; transform: translateY(5px); }
        to { opacity: 1; transform: translateY(0); }
    }

    @media (prefers-reduced-motion: reduce) {
        .ag-shell-hero, .ag-summary-card, .ca-hero {
            animation: none !important;
        }
        div[data-testid="stButton"] button,
        .ca-card, .ca-stat {
            transition: none !important;
        }
    }

    @media (max-width: 720px) {
        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
        .ag-summary-price,
        .ag-summary-upside {
            text-align: left;
        }
    }
</style>
        """,
        unsafe_allow_html=True,
    )


def render_shell_header() -> None:
    st.markdown(
        """
<div class="ag-shell-hero">
    <div class="ag-shell-row">
        <div>
            <div class="ag-kicker">VN100 Valuation Desk</div>
            <h1 class="ag-shell-title">Hệ thống định giá cổ phiếu VN100</h1>
            <p class="ag-shell-copy">
                Một màn hình làm việc cho dữ liệu tài chính, giả định định giá,
                so sánh CTCK, sự kiện vốn và báo cáo kiểm chứng.
            </p>
            <div class="ag-trust-row">
                <span class="ag-trust-pill">Python tính toán lõi</span>
                <span class="ag-trust-pill">Dữ liệu có cache</span>
                <span class="ag-trust-pill">Không tự gọi AI ngoài nút báo cáo</span>
                <span class="ag-trust-pill">Có cảnh báo dữ liệu</span>
            </div>
        </div>
    </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_summary_banner(
    *,
    ticker: str,
    sector: str,
    headline: str,
    current_price: float,
    right_html: str,
    accent_color: str,
    bg_color: str,
    text_color: str,
) -> None:
    st.markdown(
        f"""
<div class="ag-summary-card" style="--ag-summary-color:{accent_color}; --ag-summary-bg:{bg_color}; --ag-summary-text:{text_color};">
    <div class="ag-shell-row">
        <div>
            <div class="ag-summary-meta">{escape_html(ticker)} · {escape_html(sector)} · dữ liệu đang dùng trong mô hình</div>
            <h1 class="ag-summary-title">{escape_html(headline)}</h1>
        </div>
        <div>
            <div class="ag-summary-price">Giá thị trường: {current_price:,.0f} VND</div>
            {right_html}
        </div>
    </div>
</div>
        """,
        unsafe_allow_html=True,
    )
