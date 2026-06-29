"""
Select ticker view — Chọn cổ phiếu và chế độ năm gốc định giá (TTM/FY).
"""
import streamlit as st
from sqlalchemy.orm import Session
from valuation.db.models import Ticker
from valuation.data_access.repo import build_company_data

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
    
    # Nút bấm để load dữ liệu
    if st.sidebar.button("Tải dữ liệu mặc định", use_container_width=True) or "company" not in st.session_state or st.session_state.get("current_ticker") != ticker or st.session_state.get("current_mode") != mode:
        with st.spinner(f"Đang tải dữ liệu cho {ticker}..."):
            try:
                company = build_company_data(db_read, ticker, mode=mode)
                st.session_state["company"] = company
                st.session_state["current_ticker"] = ticker
                st.session_state["current_mode"] = mode
                st.session_state["analyst_assumptions"] = None  # Reset assumptions của analyst
                st.toast(f"Đã tải thành công dữ liệu {ticker} ({mode})!", icon="✅")
            except Exception as e:
                st.error(f"Lỗi khi tải dữ liệu: {e}")
                
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
                run_options = [
                    f"Vòng {r.id} - {r.analyst} ({r.created_at.strftime('%d/%m %H:%M')})"
                    for r in past_runs
                ]
                selected_run_option = st.sidebar.selectbox(
                    "Chọn kịch bản cũ để nạp:",
                    run_options,
                    key="select_past_run"
                )
                
                if st.sidebar.button("Nạp kịch bản này", use_container_width=True):
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

