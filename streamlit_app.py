"""
Streamlit App Entrypoint — Giao diện phân tích và định giá tự động VN100.
Đặt trực tiếp tại thư mục gốc của dự án.
"""
import streamlit as st
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Thêm đường dẫn dự án vào PYTHONPATH để import đồng bộ
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load biến môi trường từ .env
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

# Cấu hình giao diện Streamlit (Premium Styling)
st.set_page_config(
    page_title="VN100 Valuation - Hệ thống định giá tự động chuẩn quỹ",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Thêm Google Fonts
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Outfit:wght@400;600;800&display=swap');
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }
        h1, h2, h3 {
            font-family: 'Outfit', sans-serif;
            font-weight: 600;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# 1. Cấu hình DB engine cache để tránh cạn kiệt connection pool
@st.cache_resource
def get_db_engines():
    db_url_read = os.getenv("DATABASE_URL_READONLY") or "postgresql://readonly_user:readonly_pass@localhost:5432/vn100"
    db_url_write = os.getenv("DATABASE_URL_WRITE") or "postgresql://write_user:write_pass@localhost:5432/vn100"
    
    # pool_pre_ping giúp tự động reconnect nếu connection bị đứt
    engine_read = create_engine(db_url_read, pool_pre_ping=True)
    engine_write = create_engine(db_url_write, pool_pre_ping=True)
    
    return engine_read, engine_write

engine_read, engine_write = get_db_engines()
SessionRead = sessionmaker(bind=engine_read)
SessionWrite = sessionmaker(bind=engine_write)

# 2. Main app flow
st.title("📈 Hệ Thống Định Giá Cổ Phiếu Tự Động VN100")
st.markdown("---")

# Mở session DB ngắn cho mỗi lượt rerun
db_read = SessionRead()
db_write = SessionWrite()

try:
    # Import các view
    from valuation.views.select_ticker import render_select_ticker
    from valuation.views.input_financials import render_input_financials
    from valuation.views.input_assumptions import render_input_assumptions
    from valuation.views.results import render_valuation_results
    
    # Render sidebar
    render_select_ticker(db_read, db_write)
    
    # Render các tab chính
    if "company" in st.session_state:
        company = st.session_state["company"]
        
        # Đảm bảo projections được khởi tạo và đồng bộ
        from valuation.models.financials_bank import CompanyBank
        is_bank = isinstance(company, CompanyBank)
        base_year_mode = st.session_state.get("current_mode", "TTM")
        
        # 1. Khởi tạo projections nếu chưa có
        if "projections" not in st.session_state or st.session_state.get("projections_ticker") != company.ticker or st.session_state.get("projections_mode") != base_year_mode:
            from valuation.engine.forecast_bank import forecast_bank_financials
            from valuation.engine.forecast import forecast_company_financials
            if is_bank:
                st.session_state["projections"] = forecast_bank_financials(company)
            else:
                st.session_state["projections"] = forecast_company_financials(company)
            st.session_state["projections_ticker"] = company.ticker
            st.session_state["projections_mode"] = base_year_mode
            st.session_state["last_assumptions"] = company.assumptions.model_dump()
            
        # 2. Định giá real-time cho Summary Banner (áp dụng kịch bản và ghi đè của analyst)
        from valuation.engine.sensitivity import run_valuation_engine, apply_scenario_adjustments
        from valuation.engine.blend import blend_intrinsic_relative
        from valuation.engine.forecast_bank import forecast_bank_financials
        from valuation.engine.forecast import forecast_company_financials
        
        analyst_scenario = st.session_state.get("analyst_scenario", "Base")
        scenario_company = apply_scenario_adjustments(company, analyst_scenario)
        
        # Tạo projections động cho kịch bản
        if is_bank:
            scenario_projections = forecast_bank_financials(scenario_company)
        else:
            scenario_projections = forecast_company_financials(scenario_company)
            
        # Nếu kịch bản là Base, sử dụng projections lưu trong session state (có thể chứa chỉnh sửa của analyst)
        if analyst_scenario == "Base":
            int_fv, rel_fv = run_valuation_engine(scenario_company, projections=st.session_state.get("projections"))
        else:
            int_fv, rel_fv = run_valuation_engine(scenario_company, projections=scenario_projections)
        
        # Áp dụng ghi đè chủ quan
        if is_bank:
            pb_override = st.session_state.get("analyst_pb_override", 0.0)
            if pb_override > 0.0:
                eq_yr1 = scenario_projections[0]["total_equity"] if analyst_scenario != "Base" else st.session_state["projections"][0]["total_equity"]
                shares = scenario_company.shares_outstanding
                rel_fv = (pb_override * eq_yr1 / shares) * 1000.0 if shares > 0 else rel_fv
        else:
            pe_override = st.session_state.get("analyst_pe_override", 0.0)
            if pe_override > 0.0:
                target_projections = st.session_state["projections"] if analyst_scenario == "Base" else scenario_projections
                eps_yr1 = target_projections[0].get("net_income", 0.0) / scenario_company.shares_outstanding if scenario_company.shares_outstanding > 0 else 0.0
                rel_fv = pe_override * eps_yr1 * 1000.0
            
        weight_intrinsic = scenario_company.assumptions.weight_ri if is_bank else scenario_company.assumptions.weight_dcf
        blended_fv, upside, rec = blend_intrinsic_relative(int_fv, rel_fv, weight_intrinsic, scenario_company.current_price)
        
        # Hiển thị các cảnh báo Model Integrity (nếu có)
        if scenario_company.warnings:
            st.warning("⚠️ **Cảnh báo tính toàn vẹn mô hình (Model Integrity):**")
            for warn in scenario_company.warnings:
                st.error(f"- {warn}")
                
        # 3. Hiển thị Summary Banner (Premium Styling)
        rec_color = "#10B981" if rec == "MUA" else ("#F59E0B" if rec == "HOLD" else "#EF4444")
        bg_color = "#F0FDF4" if rec == "MUA" else ("#FFFBEB" if rec == "HOLD" else "#FEF2F2")
        text_color = "#166534" if rec == "MUA" else ("#92400E" if rec == "HOLD" else "#991B1B")
        
        st.markdown(
            f"""
            <div style="background-color: {bg_color}; padding: 24px; border-radius: 12px; border-left: 8px solid {rec_color}; margin-bottom: 24px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05);">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span style="color: #64748B; font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">
                            {scenario_company.ticker} · {scenario_company.sector} · cập nhật thời gian thực
                        </span>
                        <h1 style="color: {text_color}; margin: 6px 0 0 0; font-size: 36px; font-weight: 800; font-family: 'Outfit', sans-serif; letter-spacing: -0.02em;">
                            {rec} · Giá MT {blended_fv:,.0f} VND
                        </h1>
                    </div>
                    <div style="text-align: right;">
                        <span style="color: #64748B; font-size: 13px; font-weight: 500;">Giá thị trường: {scenario_company.current_price:,.0f} VND</span>
                        <h2 style="color: {text_color}; margin: 6px 0 0 0; font-size: 32px; font-weight: 800; font-family: 'Outfit', sans-serif;">
                            Upside {upside:+.1f}%
                        </h2>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        tab1, tab2, tab3 = st.tabs([
            "📊 Báo cáo Tài chính Lịch sử & Dự phóng", 
            "⚙️ Giả định & Tham số Dự phóng", 
            "🏆 Kết quả Định giá & Quan điểm"
        ])
        
        with tab1:
            render_input_financials(company, blended_fv=blended_fv, upside=upside, rec=rec)
            
        with tab2:
            render_input_assumptions(company)
            
        with tab3:
            render_valuation_results(company, db_write)
    else:
        st.info("👈 Vui lòng chọn Ticker ở sidebar và nhấn **'Tải dữ liệu mặc định'** để bắt đầu phân tích định giá.", icon="ℹ️")

except Exception as e:
    st.error(f"Đã xảy ra lỗi hệ thống: {e}")
    import traceback
    st.code(traceback.format_exc())

finally:
    # Luôn đóng session DB đúng cách
    db_read.close()
    db_write.close()
