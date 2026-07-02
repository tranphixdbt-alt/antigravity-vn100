"""
Valuation results view — Render kết quả định giá, heatmap độ nhạy, scenario bull/bear, đối chiếu Consensus time-decay và AI Narrative.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import datetime
import os
import jinja2
import openai
from typing import Union, Dict, Any
from sqlalchemy.orm import Session

from valuation.models.financials import Company
from valuation.models.financials_bank import CompanyBank
from valuation.models.results import ValuationResult
from valuation.engine.blend import blend_intrinsic_relative
from valuation.engine.sensitivity import calculate_sensitivity_matrix, run_scenario_analysis, run_valuation_engine
from valuation.db.models import ValuationRun

from valuation.report.charts import (
    generate_football_field_chart,
    generate_sensitivity_heatmap_chart,
    generate_financial_history_chart,
    generate_profitability_chart,
)
from valuation.report.build_pdf import build_pdf_report
from valuation.report.build_docx import build_docx_report
from valuation.report.report_data import build_report_sections
from valuation.report.ai_narrative import generate_report_narratives, _FALLBACK as NARRATIVE_FALLBACK

def get_consensus_data_with_decay(db: Session, ticker: str) -> Dict[str, Any]:
    """
    Truy vấn consensus_history, tính toán trung vị và trung bình có trọng số time-decay.
    Gắn cờ cảnh báo nếu báo cáo quá hạn 6 tháng.
    """
    from valuation.db.models import Consensus
    
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=360)  # Lấy lịch sử 1 năm
    
    records = db.query(Consensus).filter(
        Consensus.ticker == ticker,
        Consensus.report_date >= start_date,
        Consensus.report_date <= today
    ).order_by(Consensus.report_date.desc()).all()
    
    if not records:
        return {"median": None, "decay_weighted_mean": None, "reports": []}
        
    reports = []
    prices = []
    weights = []
    
    for r in records:
        age_days = (today - r.report_date).days
        is_expired = age_days > 180  # Quá hạn 6 tháng
        
        # Time-decay weight: W = exp(-0.005 * age_days)
        weight = np.exp(-0.005 * age_days)
        
        target = float(r.target_price) if r.target_price is not None else 0.0
        if target > 0:
            prices.append(target)
            weights.append(weight)
            
        reports.append({
            "broker": r.broker,
            "report_date": r.report_date,
            "target_price": target,
            "rating": r.rating,
            "age_days": age_days,
            "is_expired": is_expired,
            "weight": weight
        })
        
    if not prices:
        return {"median": None, "decay_weighted_mean": None, "reports": reports}
        
    median_val = np.median(prices)
    decay_weighted_mean = np.average(prices, weights=weights)
    
    return {
        "median": median_val,
        "decay_weighted_mean": decay_weighted_mean,
        "reports": reports
    }

def format_vnd(val: float) -> str:
    if val is None:
        return ""
    formatted = f"{val:,.1f}"
    parts = formatted.split(".")
    if len(parts) == 2:
        thousand_part = parts[0].replace(",", ".")
        decimal_part = parts[1]
        return f"{thousand_part},{decimal_part}"
    else:
        return formatted.replace(",", ".")

def render_valuation_results(company: Union[Company, CompanyBank], db_write: Session):
    """
    Render kết quả định giá chi tiết, biểu đồ và lưu kịch bản, đối chiếu consensus, AI narrative.
    """
    st.header("🏆 Kết quả Định giá & Đánh giá Khuyến nghị")
    
    is_bank = isinstance(company, CompanyBank)
    
    # ==========================================
    # KHU "QUAN ĐIỂM CỦA TÔI" (Việc 5)
    # ==========================================
    st.subheader("👤 Quan Điểm Của Tôi (Đánh giá chủ quan)")
    
    col_scen, col_pb, col_conf = st.columns(3)
    
    with col_scen:
        # Chọn kịch bản
        scenario_options = ["Base", "Bull", "Bear"]
        curr_scen = st.session_state.get("analyst_scenario", "Base")
        idx_scen = scenario_options.index(curr_scen) if curr_scen in scenario_options else 0
        analyst_scenario = st.selectbox(
            "Kịch bản:",
            scenario_options,
            index=idx_scen,
            key="analyst_scenario_select"
        )
        if analyst_scenario != curr_scen:
            st.session_state["analyst_scenario"] = analyst_scenario
            st.rerun()
            
    with col_pb:
        # P/B mục tiêu ghi đè (cho Ngân hàng) hoặc P/E mục tiêu ghi đè (cho phi tài chính)
        if is_bank:
            curr_pb = st.session_state.get("analyst_pb_override", 0.0)
            pb_override = st.number_input(
                "P/B mục tiêu theo ý tôi (0.0 để dùng mô hình):",
                min_value=0.0,
                max_value=10.0,
                value=float(curr_pb),
                step=0.1,
                key="analyst_pb_select"
            )
            if pb_override != curr_pb:
                st.session_state["analyst_pb_override"] = pb_override
                st.rerun()
        else:
            curr_pe = st.session_state.get("analyst_pe_override", 0.0)
            pe_override = st.number_input(
                "P/E mục tiêu theo ý tôi (0.0 để dùng mô hình):",
                min_value=0.0,
                max_value=100.0,
                value=float(curr_pe),
                step=0.5,
                key="analyst_pe_select"
            )
            if pe_override != curr_pe:
                st.session_state["analyst_pe_override"] = pe_override
                st.rerun()
                
    with col_conf:
        # Mức độ tin tưởng
        conf_options = ["Thấp", "Trung bình", "Cao"]
        curr_conf = st.session_state.get("analyst_confidence", "Trung bình")
        idx_conf = conf_options.index(curr_conf) if curr_conf in conf_options else 1
        analyst_confidence = st.selectbox(
            "Mức độ tin tưởng:",
            conf_options,
            index=idx_conf,
            key="analyst_confidence_select"
        )
        if analyst_confidence != curr_conf:
            st.session_state["analyst_confidence"] = analyst_confidence
            
    # Ô ghi luận điểm (text)
    curr_notes = st.session_state.get("analyst_notes", "")
    analyst_notes = st.text_area(
        "Luận điểm đầu tư (Vì sao tôi nghĩ giá còn tăng/giảm):",
        value=curr_notes,
        key="analyst_notes_select"
    )
    if analyst_notes != curr_notes:
        st.session_state["analyst_notes"] = analyst_notes

    st.markdown("---")

    # 1. Chạy động định giá theo kịch bản và projections đã sửa đổi
    from valuation.engine.sensitivity import apply_scenario_adjustments
    scenario_company = apply_scenario_adjustments(company, analyst_scenario)
    
    # Lấy projections tương ứng cho kịch bản
    if analyst_scenario == "Base":
        scenario_projections = st.session_state.get("projections")
    else:
        from valuation.engine.forecast_bank import forecast_bank_financials
        from valuation.engine.forecast import forecast_company_financials
        if is_bank:
            scenario_projections = forecast_bank_financials(scenario_company)
        else:
            scenario_projections = forecast_company_financials(scenario_company)
            
    try:
        # Engine DUY NHẤT: dùng cùng lõi valuate() với CLI/batch/Sheets → mọi nơi cùng số.
        # valuate xử lý best-of-both: bank (RI+P/B) & phi tài chính (DCF/PE/PB/...) đều đúng.
        from valuation.engine.valuate import valuate
        _res = valuate(scenario_company, projections=scenario_projections)
        int_fv = _res["intrinsic_fv"]
        rel_fv = _res["relative_fv"]
        weight_intrinsic = _res["weight_intrinsic"]

        # Ghi đè chủ quan (chỉ khi analyst nhập > 0)
        pb_override = st.session_state.get("analyst_pb_override", 0.0)
        pe_override = st.session_state.get("analyst_pe_override", 0.0)
        has_override = (is_bank and pb_override > 0.0) or ((not is_bank) and pe_override > 0.0)
        if is_bank and pb_override > 0.0:
            eq_yr1 = scenario_projections[0]["total_equity"]
            shares = scenario_company.shares_outstanding
            rel_fv = (pb_override * eq_yr1 / shares) * 1000.0 if shares > 0 else rel_fv
        elif (not is_bank) and pe_override > 0.0:
            # Fair Value so sánh = P/E * EPS năm dự phóng gần nhất (năm 1)
            eps_yr1 = scenario_projections[0].get("net_income", 0.0) / scenario_company.shares_outstanding if scenario_company.shares_outstanding > 0 else 0.0
            rel_fv = pe_override * eps_yr1 * 1000.0

        from valuation.engine.router import ValuationRouter
        route = ValuationRouter().get_routing(scenario_company.ticker)
        primary_method = route.get("primary", "FCFF" if not is_bank else "RI")
        secondary_method = route.get("secondary", "P/E" if not is_bank else "P/B")

        # Bank: int/rel là 2 chân thực → blend (cho phép override chân relative).
        # Phi tài chính: valuate đã blend sẵn → dùng thẳng; chỉ blend lại khi có P/E override.
        if is_bank or has_override:
            blended_fv, upside, rec = blend_intrinsic_relative(int_fv, rel_fv, weight_intrinsic, scenario_company.current_price)
        else:
            blended_fv, upside, rec = _res["blended_fair_value_per_share"], _res["upside"], _res["recommendation"]
    except Exception as e:
        st.error(f"Lỗi khi chạy định giá: {e}")
        return

    # 2. Render Kênh Khuyến Nghị (Premium Card Layout)
    rec_color = "#10B981" if rec == "MUA" else ("#F59E0B" if rec == "HOLD" else "#EF4444")
    
    st.markdown(
        f"""
        <div style="background-color: #1E293B; padding: 24px; border-radius: 12px; border-left: 8px solid {rec_color}; margin-bottom: 24px;">
            <h3 style="color: #F8FAFC; margin: 0 0 8px 0; font-family: 'Inter', sans-serif;">KHUYẾN NGHỊ ĐẦU TƯ</h3>
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h1 style="color: {rec_color}; margin: 0; font-size: 48px; font-weight: 800; font-family: 'Outfit', sans-serif;">{rec}</h1>
                    <p style="color: #94A3B8; margin: 4px 0 0 0;">Upside kỳ vọng: <b>{upside:+.1f}%</b></p>
                </div>
                <div style="text-align: right;">
                    <p style="color: #94A3B8; margin: 0;">Giá trị hợp lý (Blended):</p>
                    <h2 style="color: #F8FAFC; margin: 0; font-family: 'Outfit', sans-serif;">{format_vnd(blended_fv)} VND</h2>
                    <p style="color: #64748B; margin: 0;">Giá thị trường: {format_vnd(company.current_price)} VND</p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Hiển thị bảng so sánh 2 phương pháp
    st.subheader("Pha Trộn Các Phương Pháp Định Giá")
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            label=f"Giá trị Định giá Chính ({primary_method}):",
            value=f"{format_vnd(int_fv)} VND",
            delta=f"{((int_fv - company.current_price)/company.current_price)*100:+.1f}% so với thị giá" if company.current_price > 0 else None
        )
    with col2:
        st.metric(
            label=f"Giá trị Định giá Phụ ({secondary_method}):",
            value=f"{format_vnd(rel_fv)} VND",
            delta=f"{((rel_fv - company.current_price)/company.current_price)*100:+.1f}% so với thị giá" if company.current_price > 0 else None
        )

    # 3. Football Field Chart (Plotly)
    st.subheader("📊 Biểu đồ Football Field So Sánh Khoảng Định Giá")
    
    fig_ff = go.Figure()
    # Đường giá hiện tại
    fig_ff.add_shape(
        type="line", x0=company.current_price, y0=-0.5, x1=company.current_price, y1=2.5,
        line=dict(color="#64748B", width=3, dash="dash")
    )
    # Range Định giá Nội tại (giả lập biên an toàn ±15%)
    fig_ff.add_trace(go.Bar(
        y=[f"Phương pháp Phụ ({secondary_method})", f"Phương pháp Chính ({primary_method})", "Blended Giá trị (Blended)"],
        x=[rel_fv * 0.3, int_fv * 0.3, blended_fv * 0.3],
        base=[rel_fv * 0.85, int_fv * 0.85, blended_fv * 0.85],
        orientation='h',
        marker=dict(color=["#3B82F6", "#10B981", rec_color], opacity=0.8),
        name="Khoảng giá hợp lý (Fair Value Range ±15%)",
        hoverinfo="x"
    ))
    
    fig_ff.update_layout(
        paper_bgcolor="#0F172A",
        plot_bgcolor="#1E293B",
        font=dict(color="#F8FAFC", family="Inter"),
        title="Khoảng Giá Trị Định Giá So Với Thị Giá",
        xaxis_title="Giá trị cổ phiếu (VND)",
        height=300,
        margin=dict(l=150, r=20, t=40, b=40),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            font=dict(color="#F8FAFC"), bgcolor="rgba(15, 23, 42, 0.9)", bordercolor="#334155", borderwidth=1
        )
    )
    st.plotly_chart(fig_ff, use_container_width=True, theme=None)

    # 3.5. Waterfall Chart (Dòng tiền định giá - FCFF)
    if not is_bank:
        st.subheader("💧 Biểu đồ Waterfall: Dòng tiền tự do (FCFF)")
        
        years_wf = [str(proj["year"]) for proj in scenario_projections]
        fcff_vals = [proj.get("fcff", 0) for proj in scenario_projections]
        
        fig_wf = go.Figure(go.Waterfall(
            name="FCFF",
            orientation="v",
            measure=["relative"] * len(fcff_vals) + ["total"],
            x=years_wf + ["Tổng FCFF 5 năm"],
            y=fcff_vals + [0], # The total is calculated automatically by plotly if y=0 for 'total' or we can just pass sum. Actually plotly calculates total.
            textposition="outside",
            text=[f"{v:.0f}" for v in fcff_vals] + [f"{sum(fcff_vals):.0f}"],
            decreasing={"marker": {"color": "#EF4444"}},
            increasing={"marker": {"color": "#10B981"}},
            totals={"marker": {"color": "#3B82F6"}}
        ))
        
        fig_wf.update_layout(
            paper_bgcolor="#0F172A",
            plot_bgcolor="#1E293B",
            font=dict(color="#F8FAFC", family="Inter"),
            title="Dòng tiền tự do cho hãng (FCFF) dự phóng 5 năm",
            height=400,
            margin=dict(l=40, r=40, t=60, b=40)
        )
        st.plotly_chart(fig_wf, use_container_width=True, theme=None)

    # 4. Sensitivity Analysis (Heatmap 2 chiều)
    st.subheader("🔥 Heatmap Phân Tích Độ Nhạy 2 Chiều (Định giá thay đổi thế nào khi kịch bản thay đổi?)")
    st.markdown("Biểu đồ nhiệt này giúp bạn xem giá trị hợp lý thay đổi ra sao nếu Lãi suất chiết khấu (WACC) hoặc Tốc độ tăng trưởng dài hạn (g) cao hơn hay thấp hơn dự kiến.")
    
    # Xác định biến trục X và Y
    base_x = company.assumptions.cost_of_equity if is_bank else (
        run_valuation_engine(company)[0]  # dummy run to update WACC
    )
    # Lấy WACC chính xác từ model DCF
    if not is_bank:
        from valuation.engine.models.dcf import DCFValuationModel
        model_dcf = DCFValuationModel.from_pydantic(company)
        base_x = model_dcf.wacc
    else:
        base_x = company.assumptions.cost_of_equity or (company.assumptions.risk_free_rate + company.assumptions.beta * company.assumptions.erp)

    base_y = company.assumptions.terminal_growth_rate
    
    x_vals, y_vals, matrix = calculate_sensitivity_matrix(company, base_x, base_y)
    
    x_labels = [f"{x:.2%}" for x in x_vals]
    y_labels = [f"{y:.2%}" for y in y_vals]
    
    fig_heat = px.imshow(
        matrix,
        labels=dict(x="WACC" if not is_bank else "Chi phí vốn (Cost of Equity - Re)", y="Tăng trưởng vĩnh viễn (Terminal Growth - g)", color="Giá hợp lý (Fair Value)"),
        x=x_labels,
        y=y_labels,
        color_continuous_scale="Viridis",
        text_auto=True
    )
    fig_heat.update_layout(
        paper_bgcolor="#0F172A",
        plot_bgcolor="#1E293B",
        font=dict(color="#F8FAFC", family="Inter"),
        height=400
    )
    st.plotly_chart(fig_heat, use_container_width=True, theme=None)

    # --- BIỂU ĐỒ DỰ PHÓNG 5 NĂM ---
    _dark_theme_res = dict(
        paper_bgcolor="#0F172A", plot_bgcolor="#1E293B",
        font=dict(color="#F8FAFC", family="Inter"),
    )

    if scenario_projections:
        from plotly.subplots import make_subplots as _make_subplots

        st.subheader("📈 Biểu đồ Dự phóng 5 Năm")

        proj_years = [str(p["year"]) for p in scenario_projections]

        if is_bank:
            # Ngân hàng: cột NII + PPOP, đường Net Income
            nii_proj = [p.get("net_interest_income", 0.0) for p in scenario_projections]
            ppop_proj = [p.get("pre_provision_profit", 0.0) for p in scenario_projections]
            ni_proj = [p.get("net_income", 0.0) for p in scenario_projections]

            fig_forecast = _make_subplots(specs=[[{"secondary_y": True}]])
            fig_forecast.add_trace(
                go.Bar(x=proj_years, y=nii_proj, name="Thu nhập lãi thuần (Net Interest Income)",
                       marker_color="#3B82F6"),
                secondary_y=False,
            )
            fig_forecast.add_trace(
                go.Bar(x=proj_years, y=ppop_proj, name="LN trước dự phòng (PPOP)",
                       marker_color="#10B981", opacity=0.7),
                secondary_y=False,
            )
            fig_forecast.add_trace(
                go.Scatter(x=proj_years, y=ni_proj, name="Lợi nhuận sau thuế (Net Income)",
                           line=dict(color="#F59E0B", width=3), mode="lines+markers"),
                secondary_y=True,
            )
            fig_forecast.update_yaxes(title_text="Tỷ đồng", secondary_y=False)
            fig_forecast.update_yaxes(title_text="LNST (Tỷ đồng)", secondary_y=True)
            fig_forecast.update_layout(
                title="Dự phóng Thu nhập Ngân hàng (5 năm)",
                barmode="group", height=420, **_dark_theme_res,
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(color="#F8FAFC"), bgcolor="rgba(15, 23, 42, 0.9)", bordercolor="#334155", borderwidth=1
                )
            )
            st.plotly_chart(fig_forecast, use_container_width=True, theme=None)

        else:
            # Phi tài chính: cột Revenue + đường Net Income
            rev_proj = [p.get("revenue", 0.0) for p in scenario_projections]
            ni_proj = [p.get("net_income", 0.0) for p in scenario_projections]

            fig_forecast = _make_subplots(specs=[[{"secondary_y": True}]])
            fig_forecast.add_trace(
                go.Bar(x=proj_years, y=rev_proj, name="Doanh thu thuần (Net Revenue)",
                       marker_color="#3B82F6"),
                secondary_y=False,
            )
            fig_forecast.add_trace(
                go.Scatter(x=proj_years, y=ni_proj, name="Lợi nhuận sau thuế (Net Income)",
                           line=dict(color="#10B981", width=3), mode="lines+markers"),
                secondary_y=True,
            )
            fig_forecast.update_yaxes(title_text="Tỷ đồng", secondary_y=False)
            fig_forecast.update_yaxes(title_text="LNST (Tỷ đồng)", secondary_y=True)
            fig_forecast.update_layout(
                title="Dự phóng Doanh thu & Lợi nhuận (5 năm)",
                barmode="group", height=420, **_dark_theme_res,
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(color="#F8FAFC"), bgcolor="rgba(15, 23, 42, 0.9)", bordercolor="#334155", borderwidth=1
                )
            )
            st.plotly_chart(fig_forecast, use_container_width=True, theme=None)

            # --- BIỂU ĐỒ FCFF WATERFALL (chỉ phi tài chính) ---
            # Lấy năm dự phóng gần nhất (năm 1) làm minh hoạ waterfall
            p1 = scenario_projections[0]
            nopat_val = p1.get("nopat", 0.0)
            da_val = p1.get("depreciation", 0.0)
            capex_val = -abs(p1.get("capex", 0.0))
            dnwc_val = -p1.get("delta_nwc", 0.0)
            fcff_val = p1.get("fcff", 0.0)

            fig_waterfall = go.Figure(go.Waterfall(
                name="FCFF Waterfall",
                orientation="v",
                measure=["absolute", "relative", "relative", "relative", "total"],
                x=["LN HĐ sau thuế<br>(NOPAT)", "+Khấu hao<br>(D&A)", "−Đầu tư TSCĐ<br>(Capex)", "−Vốn lưu động<br>(ΔNWC)", "= Dòng tiền<br>(FCFF)"],
                y=[nopat_val, da_val, capex_val, dnwc_val, fcff_val],
                textposition="outside",
                text=[f"{nopat_val:,.1f}", f"{da_val:,.1f}",
                      f"{capex_val:,.1f}", f"{dnwc_val:,.1f}",
                      f"{fcff_val:,.1f}"],
                connector={"line": {"color": "#64748B"}},
                increasing={"marker": {"color": "#10B981"}},
                decreasing={"marker": {"color": "#EF4444"}},
                totals={"marker": {"color": "#3B82F6"}},
            ))
            fig_waterfall.update_layout(
                title=f"Cầu nối FCFF — Năm {p1['year']}",
                yaxis_title="Tỷ đồng",
                height=420, **_dark_theme_res,
            )
            st.plotly_chart(fig_waterfall, use_container_width=True, theme=None)

    # 5. Scenario Analysis
    st.subheader("🎭 Phân Tích Kịch Bản")
    scenarios = run_scenario_analysis(company)
    
    cols = st.columns(3)
    with cols[0]:
        st.metric("Kịch bản BULL:", f"{format_vnd(scenarios['Bull'])} VND")
    with cols[1]:
        st.metric("Kịch bản BASE (Mặc định):", f"{format_vnd(scenarios['Base'])} VND")
    with cols[2]:
        st.metric("Kịch bản BEAR:", f"{format_vnd(scenarios['Bear'])} VND")

    # 6. Consensus Đối chiếu (TÍNH NĂNG MỚI)
    st.subheader("👥 Đối Chiếu Giá Mục Tiêu Consensus Thị Trường")
    consensus_res = get_consensus_data_with_decay(db_write, company.ticker)
    
    if consensus_res["median"] is not None:
        con_med = consensus_res["median"]
        con_mean_decay = consensus_res["decay_weighted_mean"]
        deviation = ((blended_fv - con_med) / con_med) * 100.0
        
        st.markdown(
            f"""
            - **Giá mục tiêu trung vị (Consensus Median):** `{format_vnd(con_med)} VND` (Lệch so với bạn: **{deviation:+.1f}%**)
            - **Giá trung bình có trọng số time-decay:** `{format_vnd(con_mean_decay)} VND`
            """
        )
        
        # Gắn cờ cảnh báo nếu lệch quá 25%
        if abs(deviation) > 25.0:
            st.warning(f"⚠️ Cảnh báo lệch Consensus cao: Định giá của bạn đang lệch {deviation:+.1f}% so với trung vị thị trường.", icon="🚨")
            
        # Hiển thị bảng chi tiết các báo cáo
        with st.expander("Xem chi tiết các báo cáo consensus của CTCK (1 năm qua)"):
            df_con = pd.DataFrame(consensus_res["reports"])
            if not df_con.empty:
                df_con = df_con.rename(columns={
                    "broker": "CTCK",
                    "report_date": "Ngày báo cáo",
                    "target_price": "Giá mục tiêu (VND)",
                    "rating": "Khuyến nghị",
                    "age_days": "Số ngày tuổi",
                    "is_expired": "Quá hạn (>6T)",
                    "weight": "Trọng số decay"
                })
                # Định dạng bảng Consensus theo chuẩn Việt Nam và tô đỏ báo cáo quá hạn
                def apply_consensus_styling(df: pd.DataFrame) -> Any:
                    styler = df.style.format({
                        "Giá mục tiêu (VND)": lambda v: format_vnd(v) if isinstance(v, (int, float)) else v,
                        "Trọng số decay": "{:.4f}"
                    }, precision=1, decimal=",")
                    # Tô màu đỏ nhạt cho cả dòng nếu báo cáo quá hạn (>6 tháng)
                    styler = styler.map(
                        lambda v: "background-color: #FEF2F2; color: #EF4444; font-weight: 500;" if v is True else "",
                        subset=["Quá hạn (>6T)"]
                    )
                    return styler
                st.dataframe(apply_consensus_styling(df_con), use_container_width=True)
    else:
        st.info("Không tìm thấy dữ liệu consensus của các CTCK khác trong vòng 1 năm qua cho cổ phiếu này.")
    # Nút Lưu Kịch Bản (Append-only) & Xuất Báo Cáo
    st.subheader("💾 Quản lý Kịch Bản & Báo Cáo")
    analyst_name = st.text_input("Tên nhà phân tích:", value="Analyst")
    
    col_save, col_pdf, col_docx = st.columns(3)
    
    with col_save:
        if st.button("Lưu kịch bản vào DB", use_container_width=True):
            with st.spinner("Đang ghi dữ liệu vào PostgreSQL..."):
                try:
                    ass_json = company.assumptions.model_dump()
                    # Lưu kèm các thông tin quan điểm analyst
                    ass_json["pb_override"] = float(st.session_state.get("analyst_pb_override", 0.0))
                    ass_json["pe_override"] = float(st.session_state.get("analyst_pe_override", 0.0))
                    ass_json["confidence_level"] = st.session_state.get("analyst_confidence", "Trung bình")
                    
                    run_record = ValuationRun(
                        ticker=company.ticker,
                        analyst=analyst_name,
                        engine="bank" if is_bank else "dcf",
                        method=f"{primary_method} + {secondary_method}",
                        scenario=analyst_scenario,
                        assumptions_json=ass_json,
                        base_year_mode=st.session_state.get("current_mode", "TTM"),
                        wacc=float(base_x) if not is_bank else None,
                        terminal_g=float(base_y),
                        target_price=float(blended_fv),
                        current_price=float(company.current_price),
                        upside=float(upside),
                        recommendation=rec,
                        notes=analyst_notes
                    )
                    db_write.add(run_record)
                    db_write.commit()
                    st.success(f"Đã lưu kịch bản Vòng {run_record.id} cho {company.ticker}!")
                except Exception as e:
                    db_write.rollback()
                    st.error(f"Lỗi khi ghi DB: {e}")

    # Xuất PDF / Word — báo cáo 11 phần chuẩn quỹ (SPEC PHẦN B)
    temp_dir = "temp_reports"
    os.makedirs(temp_dir, exist_ok=True)
    chart_football_path = os.path.join(temp_dir, f"football_{company.ticker}.png")
    chart_heatmap_path = os.path.join(temp_dir, f"heatmap_{company.ticker}.png")
    chart_history_path = os.path.join(temp_dir, f"history_{company.ticker}.png")
    chart_profit_path = os.path.join(temp_dir, f"profitability_{company.ticker}.png")
    pdf_path = os.path.join(temp_dir, f"Report_Valuation_{company.ticker}.pdf")
    docx_path = os.path.join(temp_dir, f"Report_Valuation_{company.ticker}.docx")

    # Gom dữ liệu định lượng 11 phần (builder thuần, tách GUI)
    report_sections = build_report_sections(company, blended_fv, db=db_write)

    # Tạo các ảnh biểu đồ tạm để chuẩn bị nhúng
    try:
        generate_football_field_chart(blended_fv, company.current_price, int_fv, rel_fv, chart_football_path)
        generate_sensitivity_heatmap_chart(matrix, x_labels, y_labels, is_bank, chart_heatmap_path)
    except Exception as e:
        st.warning(f"Không thể tạo ảnh tĩnh biểu đồ cho báo cáo: {e}")

    # Trích xuất bảng dự phóng chi tiết để đưa vào HTML & Word
    from valuation.engine.forecast import forecast_company_financials
    from valuation.engine.forecast_bank import forecast_bank_financials
    
    proj_rows = []
    proj_headers = []
    if is_bank:
        bank_projs = forecast_bank_financials(company)
        proj_headers = [str(p["year"]) for p in bank_projs]
        
        proj_rows = [
            {"label": "Dư nợ tín dụng", "values": [f"{p['customer_loans']:,.1f}" for p in bank_projs]},
            {"label": "Thu nhập lãi thuần NII", "values": [f"{p['net_interest_income']:,.1f}" for p in bank_projs]},
            {"label": "Tổng thu nhập TOI", "values": [f"{p['total_operating_income']:,.1f}" for p in bank_projs]},
            {"label": "Chi phí hoạt động", "values": [f"{p['operating_expenses']:,.1f}" for p in bank_projs]},
            {"label": "Dự phòng rủi ro", "values": [f"{p['provision_expense']:,.1f}" for p in bank_projs]},
            {"label": "Lợi nhuận sau thuế", "values": [f"{p['net_income']:,.1f}" for p in bank_projs]},
            {"label": "Vốn chủ sở hữu", "values": [f"{p['total_equity']:,.1f}" for p in bank_projs]},
        ]
    else:
        non_bank_projs = forecast_company_financials(company)
        proj_headers = [str(p["year"]) for p in non_bank_projs]
        
        proj_rows = [
            {"label": "Doanh thu thuần", "values": [f"{p['revenue']:,.1f}" for p in non_bank_projs]},
            {"label": "Tăng trưởng doanh thu", "values": [f"{p['growth']:.1%}" for p in non_bank_projs]},
            {"label": "Biên EBIT", "values": [f"{p['ebit_margin']:.1%}" for p in non_bank_projs]},
            {"label": "EBIT", "values": [f"{p['ebit']:,.1f}" for p in non_bank_projs]},
            {"label": "NOPAT", "values": [f"{p['nopat']:,.1f}" for p in non_bank_projs]},
            {"label": "Khấu hao D&A", "values": [f"{p['depreciation']:,.1f}" for p in non_bank_projs]},
            {"label": "Chi phí CapEx", "values": [f"{p['capex']:,.1f}" for p in non_bank_projs]},
            {"label": "Dòng tiền tự do FCFF", "values": [f"{p['fcff']:,.1f}" for p in non_bank_projs]},
        ]

    # Biểu đồ tài chính lịch sử + dự phóng (phần 5 báo cáo)
    _projs = bank_projs if is_bank else non_bank_projs
    _cs = report_sections["historical"]["chart_series"]
    try:
        _f_rev_key = "total_operating_income" if is_bank else "revenue"
        generate_financial_history_chart(
            years=_cs["years"], revenue=_cs["revenue"], net_income=_cs["net_income"],
            revenue_label=_cs["revenue_label"], output_path=chart_history_path,
            forecast_years=[p["year"] for p in _projs],
            forecast_revenue=[p[_f_rev_key] for p in _projs],
            forecast_net_income=[p["net_income"] for p in _projs],
        )
        generate_profitability_chart(
            years=_cs["years"], roe=_cs["roe"], margin=_cs["margin"],
            margin_label=_cs["margin_label"], output_path=chart_profit_path,
        )
    except Exception as e:
        st.warning(f"Không thể tạo biểu đồ tài chính lịch sử: {e}")

    # Nháp văn bản AI (luận điểm/tổng quan/ngành/rủi ro) — sinh 1 lần/mã, cache session.
    _narr_key = f"report_narrative_{company.ticker}"
    if st.button("🪄 Sinh nháp văn bản AI cho báo cáo (DeepSeek)", use_container_width=True):
        with st.spinner("Đang sinh nháp luận điểm/tổng quan/ngành/rủi ro..."):
            st.session_state[_narr_key] = generate_report_narratives(report_sections)
    narrative = st.session_state.get(_narr_key, {**NARRATIVE_FALLBACK, "ai_generated": False})
    if narrative.get("ai_generated"):
        st.caption("✍️ Văn bản AI đã sinh — sẽ được chèn vào báo cáo với dấu *Nháp cần review*.")

    import base64
    def get_b64(path):
        if os.path.exists(path):
            with open(path, "rb") as f:
                return "data:image/png;base64," + base64.b64encode(f.read()).decode("utf-8")
        return ""

    _cover = report_sections["cover"]
    report_data = {
        "ticker": company.ticker,
        "name": company.name,
        "sector": company.sector,
        "date": datetime.date.today().strftime("%Y-%m-%d"),
        "analyst": analyst_name,
        # Khuyến nghị trong BÁO CÁO dùng band 5 mức chuẩn CTCK (SPEC 4.3)
        "recommendation": _cover["recommendation"],
        "rec_color": rec_color,
        "upside": f"{upside:+.2f}",
        "target_price": f"{blended_fv:,.0f}",
        "current_price": f"{company.current_price:,.0f}",
        "shares": f"{company.shares_outstanding:,.2f}",
        "market_cap": f"{_cover['market_cap']:,.0f}",
        "weight_intrinsic": int(weight_intrinsic * 100),
        "weight_relative": int((1 - weight_intrinsic) * 100),
        "intrinsic_method": primary_method,
        "relative_method": secondary_method,
        "intrinsic_price": f"{int_fv:,.0f} VND",
        "relative_price": f"{rel_fv:,.0f} VND",
        "notes": analyst_notes,
        "chart_football": get_b64(chart_football_path),
        "chart_heatmap": get_b64(chart_heatmap_path),
        "chart_history": get_b64(chart_history_path),
        "chart_profitability": get_b64(chart_profit_path),
        "proj_cols": proj_headers,
        "proj_rows": proj_rows,
        # Các khối 11 phần từ builder
        "narrative": narrative,
        "hist": report_sections["historical"],
        "assumptions": report_sections["assumptions"],
        "wacc_rows": report_sections["wacc_breakdown"],
        "consensus": report_sections["consensus"],
        "scenarios": report_sections["scenarios"],
        "appendix": report_sections["appendix"],
        "flags": report_sections["flags"],
    }

    with col_pdf:
        template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "report", "template.html")
        if os.path.exists(template_path):
            with open(template_path, "r", encoding="utf-8") as f:
                template_str = f.read()
                
            template = jinja2.Template(template_str)
            html_rendered = template.render(**report_data)
            
            if build_pdf_report(html_rendered, pdf_path):
                with open(pdf_path, "rb") as fpdf:
                    st.download_button(
                        label="📥 Tải xuống báo cáo PDF",
                        data=fpdf.read(),
                        file_name=f"Bao_cao_dinh_gia_{company.ticker}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
        else:
            st.error("Không tìm thấy tệp template.html!")

    with col_docx:
        _docx_charts = {
            "football": chart_football_path,
            "heatmap": chart_heatmap_path,
            "history": chart_history_path,
            "profitability": chart_profit_path,
        }
        if build_docx_report(report_data, proj_headers, proj_rows, _docx_charts, docx_path):
            with open(docx_path, "rb") as fdocx:
                st.download_button(
                    label="📥 Tải xuống báo cáo Word",
                    data=fdocx.read(),
                    file_name=f"Bao_cao_dinh_gia_{company.ticker}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )

    st.markdown("---")
    st.subheader("☁️ Lưu trữ Đám mây (Google Sheets & Drive)")
    if st.button("Lưu & Upload Báo cáo lên Đám mây", use_container_width=True):
        with st.spinner("Đang đồng bộ dữ liệu..."):
            from valuation.output.gsheets_exporter import update_single_ticker_to_gsheets
            from valuation.output.gdrive_exporter import upload_report_to_drive
            
            # 1. Update Sheets
            res_sheet = update_single_ticker_to_gsheets(
                ticker=company.ticker,
                curr_price=company.current_price,
                blended_fv=blended_fv,
                greeks={},
                qc_flags=[],
                db=db_write
            )
            
            # 2. Upload Drive
            pdf_res = upload_report_to_drive(pdf_path) if os.path.exists(pdf_path) else {"status": "skipped"}
            docx_res = upload_report_to_drive(docx_path) if os.path.exists(docx_path) else {"status": "skipped"}
            
            st.success("✅ Đã hoàn tất đồng bộ!")
            st.json({
                "Google Sheets": res_sheet,
                "Google Drive (PDF)": pdf_res,
                "Google Drive (DOCX)": docx_res
            })
