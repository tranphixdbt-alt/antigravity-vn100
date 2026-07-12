"""
Tab "So sánh CTCK" — đối chiếu định giá mô hình VN100 với các công ty chứng khoán.

Nội dung:
  1. KPI hàng đầu: FV mô hình | Median CTCK | Chênh lệch | Số CTCK.
  2. Biểu đồ football-field ngang: giá mục tiêu từng CTCK vs FV mô hình vs thị giá.
  3. Bảng chi tiết từng CTCK (giá mục tiêu, khuyến nghị, ngày, chênh so mô hình).
  4. AI tổng hợp (consensus_synthesis): điểm CHUNG / điểm RIÊNG / điểm MẤU CHỐT /
     đối chiếu mô hình nội bộ.

Dữ liệu: consensus_history (64 CTCK — 24hmoney + Simplize + Vietcap) và
consensus_synthesis (DeepSeek tổng hợp, chạy lại bằng import_synthesis).
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Union

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy.orm import Session

from valuation.models.financials import Company
from valuation.models.financials_bank import CompanyBank
from valuation.report.report_data import build_consensus_comparison

# Bảng màu đồng bộ giao diện báo cáo
_C_MODEL = "#1F4E78"     # xanh navy — mô hình VN100
_C_PRICE = "#EF4444"     # đỏ — thị giá
_C_BROKER = "#94A3B8"    # xám xanh — CTCK
_C_MEDIAN = "#F59E0B"    # cam — median CTCK


def _fmt_vnd(v: Optional[float]) -> str:
    return f"{v:,.0f}".replace(",", ".") if v is not None else "—"


def _football_field(data: Dict[str, Any]) -> go.Figure:
    """Bar ngang: giá mục tiêu từng CTCK; vline FV mô hình / thị giá / median."""
    rows = data["broker_rows"]
    brokers = [r["broker"] for r in rows][::-1]          # đảo để cao nhất nằm trên
    tps = [r["target_price"] for r in rows][::-1]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=brokers, x=tps, orientation="h",
        marker=dict(color=_C_BROKER, opacity=0.85),
        text=[_fmt_vnd(v) for v in tps], textposition="outside",
        hovertemplate="%{y}: %{x:,.0f} VND<extra></extra>",
        name="Giá mục tiêu CTCK",
    ))

    def _vline(x, color, label, dash):
        fig.add_vline(x=x, line_width=2, line_dash=dash, line_color=color)
        fig.add_annotation(x=x, y=1.06, yref="paper", showarrow=False,
                           text=f"<b>{label}</b>", font=dict(color=color, size=12))

    _vline(data["our_target"], _C_MODEL, f"Mô hình {_fmt_vnd(data['our_target'])}", "solid")
    if data.get("current_price"):
        _vline(data["current_price"], _C_PRICE, f"Thị giá {_fmt_vnd(data['current_price'])}", "dash")
    _vline(data["consensus_median"], _C_MEDIAN, f"Median {_fmt_vnd(data['consensus_median'])}", "dot")

    fig.update_layout(
        height=max(320, 60 + 42 * len(brokers)),
        margin=dict(l=10, r=90, t=60, b=10),
        xaxis=dict(title="VND/cổ phiếu", tickformat=",.0f", showgrid=True,
                   gridcolor="rgba(148,163,184,0.25)"),
        yaxis=dict(title=None),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return fig


def _panel(title: str, icon: str, color: str, items) -> None:
    """Panel gạch đầu dòng có viền màu (điểm chung/riêng/mấu chốt)."""
    if not items:
        return
    if isinstance(items, str):
        items = [items]
    lis = "".join(f"<li style='margin-bottom:6px;'>{it}</li>" for it in items)
    st.markdown(
        f"""
        <div style="border-left:4px solid {color}; background:{color}12;
                    border-radius:0 8px 8px 0; padding:12px 16px; margin-bottom:12px;">
          <div style="font-weight:700; color:{color}; margin-bottom:6px;">{icon} {title}</div>
          <ul style="margin:0; padding-left:18px; font-size:14px;">{lis}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_consensus_compare(company: Union[Company, CompanyBank],
                             blended_fv: float, db: Session) -> None:
    """Render tab So sánh CTCK cho 1 mã."""
    st.header("🏦 So sánh với định giá các Công ty Chứng khoán")

    data = build_consensus_comparison(company.ticker, blended_fv, db,
                                      current_price=company.current_price)
    if not data or not data.get("broker_rows"):
        st.info(
            "Chưa có dữ liệu khuyến nghị CTCK trong 180 ngày cho mã này. "
            "Chạy `import_reports` (Simplize) / `import_broker_reports` (24hmoney) để nạp.",
            icon="ℹ️",
        )
        return

    # ---- 1. KPI hàng đầu -------------------------------------------------
    dev = data["deviation"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🎯 FV mô hình VN100", f"{_fmt_vnd(data['our_target'])} đ")
    c2.metric("🏦 Median CTCK", f"{_fmt_vnd(data['consensus_median'])} đ",
              help=f"Trung vị {data['n_reports']} báo cáo trong 180 ngày")
    c3.metric("↔️ Mô hình vs CTCK", f"{dev:+.1%}",
              delta=f"{dev:+.1%}", delta_color="normal")
    c4.metric("📄 Số CTCK theo dõi", f"{data['n_brokers']}",
              help=f"Dải giá mục tiêu: {_fmt_vnd(data['range_min'])} – {_fmt_vnd(data['range_max'])} đ")

    if data["flag_high"]:
        st.warning(
            f"Mô hình lệch **{dev:+.1%}** so với trung vị CTCK (>25%) — rà soát giả định "
            "hoặc xem mục *Đối chiếu mô hình nội bộ* bên dưới.",
            icon="🚨",
        )

    # ---- 2. Football field ------------------------------------------------
    st.subheader("📊 Giá mục tiêu từng CTCK vs Mô hình vs Thị giá")
    st.plotly_chart(_football_field(data), use_container_width=True, theme=None)

    # ---- 3. Bảng chi tiết -------------------------------------------------
    st.subheader("📋 Chi tiết khuyến nghị từng CTCK (mới nhất/CTCK, 180 ngày)")
    df = pd.DataFrame(data["broker_rows"])
    df = df.rename(columns={
        "broker": "CTCK", "report_date": "Ngày BC", "target_price": "Giá mục tiêu (đ)",
        "rating": "Khuyến nghị", "vs_model": "Mô hình so với CTCK", "age_days": "Tuổi (ngày)",
    })
    styler = (df.style
              .format({"Giá mục tiêu (đ)": lambda v: _fmt_vnd(v),
                       "Mô hình so với CTCK": "{:+.1%}"})
              .map(lambda v: "color:#EF4444;font-weight:600;" if isinstance(v, float) and v < -0.25
                   else ("color:#16A34A;font-weight:600;" if isinstance(v, float) and v > 0.25 else ""),
                   subset=["Mô hình so với CTCK"])
              .map(lambda v: "color:#EF4444;" if isinstance(v, int) and v > 120 else "",
                   subset=["Tuổi (ngày)"]))
    st.dataframe(styler, use_container_width=True, hide_index=True)
    st.caption("🔴 chênh >25% (mô hình thấp hơn) · 🟢 chênh >25% (mô hình cao hơn) · tuổi đỏ = báo cáo >120 ngày")

    # ---- 4. AI tổng hợp điểm chung / riêng --------------------------------
    st.subheader("🤖 AI tổng hợp luận điểm các CTCK")
    synth = data.get("synthesis")
    if synth:
        gen_at = synth.get("generated_at")
        gen_str = gen_at.strftime("%d/%m/%Y") if gen_at else "—"
        st.caption(
            f"Tổng hợp từ {synth['n_reports']} báo cáo ({synth['brokers']}) · "
            f"sinh ngày {gen_str} · ⚠️ AI tổng hợp từ báo cáo CTCK — cần analyst review"
        )
        col_l, col_r = st.columns(2)
        with col_l:
            _panel("Điểm CHUNG các CTCK đồng thuận", "🤝", "#16A34A", synth["diem_chung"])
            _panel("Điểm MẤU CHỐT / thị trường dễ bỏ sót", "💡", "#1D4ED8", synth["diem_mau_chot"])
        with col_r:
            _panel("Điểm RIÊNG / khác biệt giữa CTCK", "⚖️", "#D97706", synth["diem_rieng"])
            _panel("Đối chiếu mô hình nội bộ", "🧭", "#7C3AED", synth["doi_chieu_noi_bo"])
    else:
        st.info(
            "Chưa có bản AI tổng hợp cho mã này. Chạy:\n"
            "`python3 -c \"from valuation.engine.consensus_synthesis import import_synthesis; "
            f"import_synthesis('{company.ticker}')\"`",
            icon="🤖",
        )
