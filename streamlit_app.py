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
# Ưu tiên .env ở thư mục chạy exe (cwd) trước, sau đó mới dùng .env đóng gói kèm
env_cwd = os.path.join(os.getcwd(), ".env")
env_bundled = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(env_cwd):
    load_dotenv(env_cwd)
else:
    load_dotenv(env_bundled)

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
    db_url_read = os.getenv("DATABASE_URL_READONLY") or "sqlite:///vn100.db"
    db_url_write = os.getenv("DATABASE_URL_WRITE") or "sqlite:///vn100.db"
    
    _pool_kwargs = dict(pool_pre_ping=True)
    if "sqlite" in db_url_read:
        _pool_kwargs["connect_args"] = {"check_same_thread": False}
    else:
        _pool_kwargs.update(dict(
            pool_recycle=1800,
            pool_size=5,
            max_overflow=5,
            pool_timeout=30,
        ))
    
    try:
        engine_read = create_engine(db_url_read, **_pool_kwargs)
        engine_write = create_engine(db_url_write, **_pool_kwargs)
        # Test connection
        with engine_read.connect() as conn:
            pass
    except Exception as e:
        # Fallback sang SQLite nếu PostgreSQL local không hoạt động
        sqlite_url = "sqlite:///vn100.db"
        engine_read = create_engine(sqlite_url, connect_args={"check_same_thread": False})
        engine_write = create_engine(sqlite_url, connect_args={"check_same_thread": False})

    # Tự động khởi tạo schema nếu dùng SQLite
    if "sqlite" in str(engine_write.url):
        from valuation.db.models import Base
        Base.metadata.create_all(bind=engine_write)

    return engine_read, engine_write

engine_read, engine_write = get_db_engines()
SessionRead = sessionmaker(bind=engine_read)
SessionWrite = sessionmaker(bind=engine_write)

@st.cache_data(ttl=300)
def fetch_live_price_cached(ticker: str) -> float:
    """Lấy giá live từ vnstock với cache 5 phút để không bị lag UI"""
    from valuation.ingest.vnstock_client import vnstock_client
    try:
        return vnstock_client.get_live_price(ticker)
    except Exception:
        return 0.0

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
    
    # Auto Weekly Freshness Check Hook on Startup
    if "auto_weekly_check_done" not in st.session_state:
        from valuation.data_access.freshness_checker import check_data_freshness
        freshness_status = check_data_freshness(db_read, threshold_days=7)
        if freshness_status.is_stale:
            st.warning(
                f"🚨 **Phát hiện dữ liệu hệ thống cần làm mới (Giá: {freshness_status.days_since_price} ngày, Báo cáo CTCK: {freshness_status.days_since_consensus} ngày trước).** "
                f"Đang tự động khởi chạy tiến trình quét BCTC Quý/Năm, Báo cáo định giá CTCK và Giá thị trường mới nhất dưới nền...",
                icon="⚠️"
            )
            import threading
            from valuation.ingest.weekly_updater import run_weekly_auto_update
            def _auto_bg():
                bg_read = SessionRead()
                bg_write = SessionWrite()
                try:
                    run_weekly_auto_update(bg_read, bg_write)
                except Exception as e_bg:
                    logger.error(f"Lỗi chạy cập nhật ngầm: {e_bg}")
                finally:
                    bg_read.close()
                    bg_write.close()
            threading.Thread(target=_auto_bg, daemon=True).start()
            st.toast("🚀 Đã tự động kích hoạt tiến trình cập nhật BCTC & Báo cáo CTCK hàng tuần ngầm dưới nền!", icon="🔄")
        st.session_state["auto_weekly_check_done"] = True

    # Render sidebar
    render_select_ticker(db_read, db_write)
    
    # Render các tab chính
    if "company" in st.session_state:
        company = st.session_state["company"]
        
        # Cập nhật giá live liên tục mỗi lần rerun để tránh kẹt cache giá cũ
        # Gọi qua cache 5 phút để tránh bị lag UI (do call API vnstock quá nhiều)
        live_p = fetch_live_price_cached(company.ticker)
        if live_p == 0:
            from valuation.data_access.repo import get_latest_price
            live_p = get_latest_price(db_read, company.ticker, fetch_live=False)
            
        if live_p > 0:
            company.current_price = live_p
            st.session_state["company"] = company
        
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
            
        # Engine DUY NHẤT: dùng cùng lõi valuate() với CLI/batch/Sheets & tab Kết quả.
        # Base dùng projections trong session (có thể đã chỉnh tay); kịch bản khác forecast lại.
        from valuation.engine.valuate import valuate
        _proj = st.session_state.get("projections") if analyst_scenario == "Base" else scenario_projections
        # Vĩ mô cập nhật MỖI LẦN QUÉT: ưu tiên analyst chỉnh tay (session_state),
        # mặc định tự dựng từ macro_series trong DB (CPI/TPCP_10Y/POLICY_RATE).
        macro_env = st.session_state.get("macro_env")
        if macro_env is None:
            from valuation.models.macro_env import MacroEnvironment
            macro_env = MacroEnvironment.from_db(db_read)
        _res = valuate(scenario_company, projections=_proj, macro_env=macro_env)
        int_fv = _res["intrinsic_fv"]
        rel_fv = _res["relative_fv"]
        weight_intrinsic = _res["weight_intrinsic"]

        # Ghi đè chủ quan (chỉ khi analyst nhập > 0)
        pb_override = st.session_state.get("analyst_pb_override", 0.0)
        pe_override = st.session_state.get("analyst_pe_override", 0.0)
        has_override = (is_bank and pb_override > 0.0) or ((not is_bank) and pe_override > 0.0)
        if is_bank and pb_override > 0.0:
            eq_yr1 = scenario_projections[0]["total_equity"] if analyst_scenario != "Base" else st.session_state["projections"][0]["total_equity"]
            shares = scenario_company.shares_outstanding
            rel_fv = (pb_override * eq_yr1 / shares) * 1000.0 if shares > 0 else rel_fv
        elif (not is_bank) and pe_override > 0.0:
            target_projections = st.session_state["projections"] if analyst_scenario == "Base" else scenario_projections
            eps_yr1 = target_projections[0].get("net_income", 0.0) / scenario_company.shares_outstanding if scenario_company.shares_outstanding > 0 else 0.0
            rel_fv = pe_override * eps_yr1 * 1000.0

        # Bank: int/rel là 2 chân thực → blend (cho phép override). Phi tài chính: valuate
        # đã blend sẵn → dùng thẳng; chỉ blend lại khi có P/E override.
        # Tính toán Fair Value
        if is_bank or has_override:
            blended_fv, upside, _ = blend_intrinsic_relative(int_fv, rel_fv, weight_intrinsic, scenario_company.current_price)
            # Re-run Decision Engine if there are overrides
            from valuation.engine.decision_engine import InvestmentDecisionMaker
            from valuation.engine.sector_router import route as _route_fn
            plan = _route_fn(company.ticker) or {}
            decision_engine = InvestmentDecisionMaker(
                business_nature=plan.get("business_nature", "Unknown"),
                current_price=scenario_company.current_price,
                fair_value=blended_fv,
                governance=scenario_company.governance
            )
            decision = decision_engine.make_decision()
            rec = decision["recommendation"]
        else:
            blended_fv, upside, rec = _res["blended_fair_value_per_share"], _res["upside"], _res["recommendation"]
            decision = _res.get("decision", {})
        
        
        # Hiển thị các cảnh báo Model Integrity (nếu có)
        if scenario_company.warnings:
            st.warning("⚠️ **Cảnh báo tính toàn vẹn mô hình (Model Integrity):**")
            for warn in scenario_company.warnings:
                st.error(f"- {warn}")
                
        # 3. Hiển thị Summary Banner (Premium Styling)
        # NOT_RATED phải TRUNG TÍNH (xám), không tô đỏ: "chưa đủ cơ sở định giá"
        # hoàn toàn khác "khuyến nghị bán" — tô đỏ sẽ khiến người đọc hiểu nhầm
        # thành tín hiệu tiêu cực (D28).
        if rec == "NOT_RATED":
            rec_color, bg_color, text_color = "#64748B", "#F8FAFC", "#334155"
        elif rec == "BUY":
            rec_color, bg_color, text_color = "#10B981", "#F0FDF4", "#166534"
        elif rec in ["HOLD", "TRIM"]:
            rec_color, bg_color, text_color = "#F59E0B", "#FFFBEB", "#92400E"
        else:
            rec_color, bg_color, text_color = "#EF4444", "#FEF2F2", "#991B1B"
        
        # Với NOT_RATED, KHÔNG hiển thị giá mục tiêu và upside — đó chính là con
        # số hệ thống vừa tuyên bố là không đáng tin. Hiện nó ra rồi dán nhãn
        # "không định giá được" là tự mâu thuẫn, và người đọc sẽ nhớ con số.
        if rec == "NOT_RATED":
            _headline = "CHƯA ĐỦ CƠ SỞ ĐỊNH GIÁ"
            _right = ("<span style='color:#64748B;font-size:13px;font-weight:500;'>"
                      "Không công bố giá mục tiêu</span>")
        else:
            _headline = f"{rec} · Giá MT {blended_fv:,.0f} VND"
            _right = (f"<h2 style=\"color: {text_color}; margin: 6px 0 0 0; font-size: 32px; "
                      f"font-weight: 800; font-family: 'Outfit', sans-serif;\">"
                      f"Upside {upside:+.1f}%</h2>")

        st.markdown(
            f"""
            <div style="background-color: {bg_color}; padding: 24px; border-radius: 12px; border-left: 8px solid {rec_color}; margin-bottom: 24px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05);">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span style="color: #64748B; font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">
                            {scenario_company.ticker} · {scenario_company.sector} · cập nhật thời gian thực
                        </span>
                        <h1 style="color: {text_color}; margin: 6px 0 0 0; font-size: 36px; font-weight: 800; font-family: 'Outfit', sans-serif; letter-spacing: -0.02em;">
                            {_headline}
                        </h1>
                    </div>
                    <div style="text-align: right;">
                        <span style="color: #64748B; font-size: 13px; font-weight: 500;">Giá thị trường: {scenario_company.current_price:,.0f} VND</span>
                        {_right}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        if rec == "NOT_RATED":
            st.warning(
                "Mô hình **không đủ cơ sở** để định giá mã này (phương pháp proxy cho ra "
                "kết quả lệch phi lý so thị giá). Hệ thống cố ý **không công bố giá mục "
                "tiêu và không đưa khuyến nghị** thay vì đưa ra một con số không đáng tin. "
                "Xem cờ định giá bên dưới để biết cần bổ sung dữ liệu gì.",
                icon="🚫",
            )
        
        # Hard Gates & Governance Section
        violations = decision.get("hard_gates_violations", [])
        if violations:
            st.error("🚨 **HARD GATES BỊ VI PHẠM (Chỉ định: HARD REJECT)**")
            for v in violations:
                st.markdown(f"- {v}")
        else:
            st.success("✅ **Governance Check Passed** (Không phát hiện cờ rủi ro Hard Gates)")
            
        st.markdown(f"**Margin of Safety (MOS) Mục tiêu cho {decision.get('business_nature', 'Unknown')}:** {decision.get('target_mos', 0)*100:.0f}%")

        # Cờ định giá (giải thích TẠI SAO kết quả bất thường — vd Giá MT = 0,
        # upside -100% — thay vì để người dùng tưởng nhầm là lỗi hệ thống).
        from valuation.engine.flag_descriptions import describe_flags
        valuation_flags = describe_flags(_res.get("flags", []))
        if valuation_flags:
            st.markdown("**Cờ định giá (Valuation Flags):**")
            for vf in valuation_flags:
                text = f"`{vf['code']}` — {vf['message']}"
                if vf["level"] == "error":
                    st.error(text, icon="🚨")
                elif vf["level"] == "warning":
                    st.warning(text, icon="⚠️")
                else:
                    st.info(text, icon="ℹ️")


        from valuation.views.tradingview_chart import render_tradingview_widget

        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Báo cáo Tài chính Lịch sử & Dự phóng",
            "⚙️ Giả định & Tham số Dự phóng",
            "🏆 Kết quả Định giá & Quan điểm",
            "🏦 So sánh CTCK",
            "📈 Biểu đồ Kỹ thuật TradingView"
        ])

        with tab1:
            render_input_financials(company, blended_fv=blended_fv, upside=upside, rec=rec)

        with tab2:
            render_input_assumptions(company)

        with tab3:
            render_valuation_results(company, db_write)

        with tab4:
            from valuation.views.consensus_compare import render_consensus_compare
            render_consensus_compare(company, blended_fv, db_write)

        with tab5:
            st.subheader(f"📈 Biểu Đồ Kỹ Thuật & Công Cụ Vẽ TradingView ({company.ticker})")
            st.caption("💡 Sử dụng đầy đủ thanh công cụ phía bên trái biểu đồ để vẽ đường xu hướng (Trendline), Fibonacci, đo khoảng giá, vẽ hình khối, và chèn các chỉ báo kỹ thuật (RSI, MACD, MA, Volume).")
            render_tradingview_widget(company.ticker, height=680, key_prefix="chart_tab")
    else:
        st.info("👈 Vui lòng chọn Ticker ở sidebar và nhấn **'Tải dữ liệu mặc định'** để bắt đầu phân tích định giá.", icon="ℹ️")

except Exception as e:
    st.error(f"Đã xảy ra lỗi hệ thống: {e}")
    import traceback
    st.code(traceback.format_exc())
    with open("streamlit_crash.log", "w", encoding="utf-8") as f:
        f.write(traceback.format_exc())

finally:
    # Luôn đóng session DB đúng cách
    db_read.close()
    db_write.close()
