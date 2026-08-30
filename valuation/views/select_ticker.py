"""
Select ticker view — Chọn cổ phiếu và chế độ năm gốc định giá (TTM/FY).
"""
import streamlit as st
from sqlalchemy.orm import Session
from valuation.db.models import Ticker
from valuation.data_access.repo import build_company_data


def _format_run_option(run) -> str:
    created_at = run.created_at
    created_label = (
        created_at.strftime("%d/%m %H:%M")
        if created_at is not None
        else "không rõ thời gian"
    )
    analyst = run.analyst or "Analyst"
    return f"Vòng {run.id} - {analyst} ({created_label})"


def load_macro_bulletin(force: bool = False):
    # Cache ra FILE với TTL 7 giờ (tồn tại qua các lần restart app) → không tốn token
    # gọi lại AI nếu trong 7 giờ đã có báo cáo.
    from valuation.data_access.macro_news import get_macro_bulletin_cached
    return get_macro_bulletin_cached(force=force)

def render_select_ticker(db_read: Session, db_write: Session = None):
    """
    Render giao diện chọn Ticker và chế độ định giá.
    """
    st.sidebar.header("🔍 Cấu hình Ticker")
    
    # Lấy danh sách VN100 tickers
    tickers_list = (
        db_read.query(Ticker.ticker, Ticker.company_name)
        .filter(Ticker.is_vn100 == True)
        .order_by(Ticker.ticker.asc())
        .all()
    )
    
    options = [f"{t[0]} - {t[1]}" for t in tickers_list]
    if not options:
        options = ["VCB - Vietcombank", "HPG - Hòa Phát", "FPT - FPT", "DGC - Hóa chất Đức Giang", "SSI - SSI"]
        
    selected_option = st.sidebar.selectbox("Chọn Ticker định giá:", options)
    ticker = selected_option.split(" - ")[0]
    
    # Toggle chọn chế độ TTM hoặc FY
    base_year_mode = st.sidebar.radio(
        "Năm gốc định giá (Base Year):",
        ["TTM (4 quý gần nhất)", "FY (Năm tài chính gần nhất)"],
        index=0
    )
    mode = "TTM" if "TTM" in base_year_mode else "FY"

    st.sidebar.markdown("---")
    
    # --- Bảng tin Vĩ mô (Macro News) ---
    with st.sidebar.expander("📰 Bản tin Vĩ mô & Nhận định", expanded=True):
        # Nút này BUỘC tạo mới (bỏ qua mốc 7 giờ) — chỉ khi user chủ động bấm.
        if st.button("🔄 Làm mới tin tức", width="stretch"):
            with st.spinner("AI đang tổng hợp tin..."):
                load_macro_bulletin(force=True)
            st.rerun()

        # Render bình thường: đọc bản lưu (không tốn token nếu còn trong 7 giờ).
        from valuation.data_access.macro_news import get_macro_cache_age_hours
        _age = get_macro_cache_age_hours()
        if _age is None:
            # Chưa có bản tin nào → tạo lần đầu
            with st.spinner("AI đang tổng hợp tin..."):
                macro_text = load_macro_bulletin()
        else:
            macro_text = load_macro_bulletin()
            st.caption(f"🕒 Cập nhật {_age:.1f} giờ trước (tự làm mới sau 7 giờ)")
        st.markdown(macro_text)

    # --- Nâng cấp Vĩ mô ---
    st.sidebar.markdown("---")
    st.sidebar.header("🌍 Môi trường Vĩ mô")
    macro_inflation = st.sidebar.number_input("Lạm phát mục tiêu (%)", min_value=0.0, max_value=20.0, value=3.0, step=0.5) / 100.0
    macro_sbv = st.sidebar.selectbox("Chính sách SBV", ["Neutral", "Accommodative", "Tightening"])
    
    # Update MacroEnvironment in session state
    from valuation.models.macro_env import MacroEnvironment
    st.session_state["macro_env"] = MacroEnvironment(inflation_rate=macro_inflation, sbv_stance=macro_sbv)
    
    # --- Nút cập nhật dữ liệu ---
    st.sidebar.markdown("---")
    st.sidebar.header("🔄 Cập nhật Dữ liệu & BCTC Hàng tuần")

    # Kiểm tra độ tươi dữ liệu
    from valuation.data_access.freshness_checker import check_data_freshness
    freshness = check_data_freshness(db_read)
    if freshness.is_stale:
        st.sidebar.error(f"🔴 Dữ liệu đã cũ (Cập nhật {freshness.days_since_price} ngày trước)", icon="⚠️")
    else:
        st.sidebar.success(f"🟢 Dữ liệu mới nhất (Cập nhật {freshness.days_since_price} ngày trước)", icon="✅")

    col1, col2 = st.sidebar.columns(2)
    if col1.button(f"Tải mới {ticker}", width="stretch", help="Kéo dữ liệu giá, BCTC và báo cáo khuyến nghị CTCK mới nhất cho mã này."):
        with st.spinner(f"Đang tải dữ liệu mới cho {ticker}..."):
            from valuation.ingest.pipeline import run_ingest
            from valuation.ingest.weekly_updater import _CONSENSUS_SOURCES
            try:
                run_ingest(ticker, data_types=['prices', 'financials'], incremental=True)
                # Dùng chung danh sách nguồn với quét hàng tuần (D24) để nút này
                # và nút quét VN100 không bao giờ lệch nhau về nguồn dữ liệu.
                for _src_name, _importer in _CONSENSUS_SOURCES:
                    try:
                        _importer(ticker)
                    except Exception as e_broker:
                        st.sidebar.warning(f"Không lấy được báo cáo CTCK ({_src_name}) cho {ticker}: {e_broker}")
                # Xóa cache để bắt buộc tải lại
                if "company" in st.session_state:
                    del st.session_state["company"]
                st.toast(f"Đã cập nhật dữ liệu {ticker} thành công!", icon="✅")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Lỗi khi cập nhật {ticker}: {e}")

    if col2.button("Quét VN100 Hàng Tuần", width="stretch", help="Tự động kiểm tra BCTC & Báo cáo định giá CTCK mới nhất cho toàn bộ rổ VN100"):
        import threading
        from valuation.db.session import SessionLocalRead, SessionLocalWrite
        from valuation.ingest.weekly_updater import run_weekly_auto_update
        def _bg_update():
            bg_read = SessionLocalRead()
            bg_write = SessionLocalWrite()
            try:
                run_weekly_auto_update(bg_read, bg_write)
            finally:
                bg_read.close()
                bg_write.close()
        threading.Thread(target=_bg_update, daemon=True).start()
        st.toast("🚀 Đã khởi chạy tiến trình quét tự động BCTC & Báo cáo định giá CTCK cho VN100 ngầm dưới nền!", icon="✅")

    st.sidebar.markdown("<br>", unsafe_allow_html=True)

    # Nút bấm để load dữ liệu vào màn hình
    if st.sidebar.button("📊 TẢI DỮ LIỆU ĐỊNH GIÁ", width="stretch", type="primary") or "company" not in st.session_state or st.session_state.get("current_ticker") != ticker or st.session_state.get("current_mode") != mode:
        with st.spinner(f"Đang phân tích dữ liệu {ticker}..."):
            try:
                company = build_company_data(db_read, ticker, mode=mode)
                st.session_state["company"] = company
                st.session_state["current_ticker"] = ticker
                st.session_state["current_mode"] = mode
                st.session_state["analyst_assumptions"] = None  # Reset assumptions của analyst
                st.toast(f"Đã nạp xong mô hình định giá {ticker} ({mode})!", icon="✅")
            except Exception as e:
                st.sidebar.error(f"Lỗi khi nạp dữ liệu: {e}")
                
    if "company" in st.session_state:
        comp = st.session_state["company"]
        st.sidebar.info(
            f"**Doanh nghiệp:** {comp.name}\n\n"
            f"**Ngành:** {comp.sector}\n\n"
            f"**Giá hiện tại:** {comp.current_price:,.0f} VND\n\n"
            f"**CP lưu hành:** {comp.shares_outstanding:,.2f} triệu cp"
        )
        
        # Nạp kịch bản đã lưu từ DB (Việc 5)
        from valuation.db.models import ValuationRun
        try:
            db_to_query = db_write if db_write is not None else db_read
            past_runs = db_to_query.query(ValuationRun).filter(
                ValuationRun.ticker == comp.ticker
            ).order_by(ValuationRun.created_at.desc()).limit(10).all()
            
            if past_runs:
                st.sidebar.markdown("---")
                st.sidebar.subheader("💾 Nạp kịch bản cũ")
                run_options = [_format_run_option(r) for r in past_runs]
                selected_run_option = st.sidebar.selectbox(
                    "Chọn kịch bản cũ để nạp:",
                    run_options,
                    key="select_past_run"
                )
                
                if st.sidebar.button("Nạp kịch bản này", width="stretch"):
                    run_id = int(selected_run_option.split(" - ")[0].replace("Vòng ", ""))
                    run = next((r for r in past_runs if r.id == run_id), None)
                    
                    if run and run.assumptions_json:
                        # Khôi phục assumptions của company bằng cách gán từng key
                        for k, v in run.assumptions_json.items():
                            if hasattr(comp.assumptions, k):
                                setattr(comp.assumptions, k, v)
                        
                        # Khôi phục session states
                        st.session_state["analyst_scenario"] = run.scenario
                        st.session_state["analyst_pb_override"] = run.assumptions_json.get("pb_override", 0.0)
                        st.session_state["analyst_pe_override"] = run.assumptions_json.get("pe_override", 0.0)
                        st.session_state["analyst_confidence"] = run.assumptions_json.get("confidence_level", "Trung bình")
                        st.session_state["analyst_notes"] = run.notes or ""
                        
                        # Buộc reset projections để hệ thống sinh lại từ kịch bản mới
                        if "projections" in st.session_state:
                            del st.session_state["projections"]
                            
                        st.toast(f"Đã nạp kịch bản Vòng {run.id}!", icon="📥")
                        st.rerun()
        except Exception as ex:
            st.sidebar.error(f"Lỗi khi load danh sách kịch bản: {ex}")
