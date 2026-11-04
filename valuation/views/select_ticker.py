"""
Select ticker view — Chọn cổ phiếu và chế độ năm gốc định giá (TTM/FY).
"""

import re

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from valuation.data_access.repo import build_company_data
from valuation.db.models import Ticker
from valuation.views.device import is_phone

_UI_HANDLED_EXCEPTIONS = (
    SQLAlchemyError,
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
    KeyError,
    AttributeError,
    ImportError,
)


def _format_run_option(run) -> str:
    created_at = run.created_at
    created_label = (
        created_at.strftime("%d/%m %H:%M")
        if created_at is not None
        else "không rõ thời gian"
    )
    analyst = run.analyst or "Analyst"
    return f"Vòng {run.id} - {analyst} ({created_label})"


@st.cache_data(ttl=30, show_spinner=False)
def _data_coverage() -> str:
    """Độ phủ dữ liệu THẬT trong DB (gồm cả cập nhật bằng CLI/lịch), không chỉ job UI."""
    from sqlalchemy import text

    from valuation.db.session import SessionLocalRead

    db = SessionLocalRead()
    try:
        price = db.execute(text(
            "select max(m), sum(m = (select max(trade_date) from prices_daily where ticker <> 'VNINDEX')), count(*) "
            "from (select max(trade_date) m from prices_daily where ticker <> 'VNINDEX' group by ticker)"
        )).one()
        fin = db.execute(text(
            "with q as (select ticker, max(fiscal_year * 10 + fiscal_quarter) k from financials_quarterly "
            "where fiscal_quarter > 0 group by ticker) select max(k), sum(k = (select max(k) from q)), count(*) from q"
        )).one()
    finally:
        db.close()
    price_day = "/".join(reversed(str(price[0])[:10].split("-")))
    return (
        f"Giá mới nhất {price_day}: {price[1]}/{price[2]} mã đã cập nhật · "
        f"BCTC quý {fin[0] % 10}/{fin[0] // 10}: {fin[1]}/{fin[2]} mã"
    )


@st.fragment(run_every="5s")
def _data_update_progress() -> None:
    from valuation.services.data_update_job import job_status

    s = job_status()
    state = s.get("status")
    if state in ("QUEUED", "RUNNING"):
        done, total = s.get("completed", 0), s.get("total") or 0
        st.progress(done / max(1, total), text=f"Quét VN100: {done}/{total or '?'} mã · {s.get('message', '')}")
        st.session_state["data_update_waiting"] = True
    elif st.session_state.pop("data_update_waiting", False):
        _data_coverage.clear()
        st.rerun()  # vừa xong → nạp lại trang với dữ liệu mới
    elif state == "DONE":
        st.caption(
            f"Đợt quét gần nhất xong {s['finished_at'][:16].replace('T', ' ')}: "
            f"{s['success']} đủ · {s['partial']} một phần · {s['failed']} lỗi / {s['total']} mã"
            + (f" · {s['message'].rsplit(' · ', 1)[-1]}" if "flow_exit" in s else "")
        )
    elif state in ("FAILED", "INTERRUPTED"):
        st.warning(s["message"])
    st.caption(_data_coverage())


def load_macro_bulletin(force: bool = False):
    # Đọc bản lưu; chỉ nút làm mới được phép gọi AI khi nguồn thay đổi.
    from valuation.data_access.macro_news import get_macro_bulletin_cached

    return get_macro_bulletin_cached(force=force)


_LEGAL_FORM = re.compile(
    r"(Tổng\s+)?Công\s+ty\s+Cổ\s+phần|Thương\s+mại\s+Cổ\s+phần|\bCTCP\b", re.IGNORECASE
)


def short_company_name(ticker: str, name: str | None) -> str:
    """Bỏ loại hình pháp lý (Công ty Cổ phần, TMCP, CTCP) cho danh sách gọn; trùng mã → rỗng."""
    short = re.sub(r"\s{2,}", " ", _LEGAL_FORM.sub("", name or "")).strip(" -–")
    return "" if short.upper() == ticker else short


def _claim_auto_refresh(state, ticker: str) -> bool:
    """True đúng một lần cho mỗi mã trong phiên: mở/đổi mã thì tự tải mới (người dùng yêu cầu 30/10).
    Đánh dấu TRƯỚC khi tải để lỗi mạng không gây vòng lặp tải lại mỗi lần rerun."""
    done = state.setdefault("auto_refreshed_tickers", set())
    if ticker in done:
        return False
    done.add(ticker)
    return True


def render_select_ticker(db_read: Session, db_write: Session = None):
    """
    Render giao diện chọn Ticker và chế độ định giá.
    """
    # --- Chọn mã: dòng đầu sidebar, không tiêu đề (gõ để tìm) ---
    tickers_list = (
        db_read.query(Ticker.ticker, Ticker.company_name)
        .filter(Ticker.is_vn100)
        .order_by(Ticker.ticker.asc())
        .all()
    )
    names = {t: short_company_name(t, n) for t, n in tickers_list} or {
        "VCB": "Vietcombank",
        "HPG": "Hòa Phát",
        "FPT": "",
        "DGC": "Hóa chất Đức Giang",
        "SSI": "",
    }

    import os

    last_ticker_file = os.path.join(os.path.dirname(__file__), ".last_ticker.txt")
    default_ticker = "ACB"
    if os.path.exists(last_ticker_file):
        with open(last_ticker_file, "r", encoding="utf-8") as f:
            default_ticker = f.read().strip()

    options = list(names)
    ticker = st.sidebar.selectbox(
        "Mã đang phân tích",
        options,
        index=options.index(default_ticker) if default_ticker in options else 0,
        format_func=lambda t: f"{t} – {names[t]}" if names[t] else t,
        label_visibility="collapsed",
    )

    if ticker != default_ticker:
        with open(last_ticker_file, "w", encoding="utf-8") as f:
            f.write(ticker)
    # Hồ sơ mã đang mở hiện ngay dưới ô chọn; nội dung điền sau khi mô hình nạp xong (cuối hàm).
    profile_slot = st.sidebar.empty()

    # --- Nhìn 5 giây (D51) + khung chỉ số vĩ mô (D50): chỉ đọc DB ---
    from valuation.views.macro_panel import render_macro_panel
    from valuation.views.market_overview import render_market_overview

    render_market_overview(db_read)
    st.sidebar.markdown("---")
    render_macro_panel(db_read)
    st.sidebar.markdown("---")

    # --- Bảng tin Vĩ mô (Macro News) ---
    with st.sidebar.expander("Tin vĩ mô 24h (AI tóm tắt)", expanded=not is_phone()):
        # Chỉ kiểm tra nguồn/AI khi người dùng chủ động bấm.
        if st.button("Làm mới tin tức", width="stretch"):
            with st.spinner("AI đang tổng hợp tin..."):
                load_macro_bulletin(force=True)
            st.rerun()

        # Render bình thường không tải nguồn hoặc gọi AI.
        from valuation.data_access.macro_news import get_macro_cache_age_hours

        _age = get_macro_cache_age_hours()
        if _age is None:
            macro_text = load_macro_bulletin()
        else:
            macro_text = load_macro_bulletin()
            st.caption(f"Cập nhật {_age:.1f} giờ trước · Bản đã lưu")
        from valuation.data_access.macro_news import split_news_tags

        # Ẩn dòng TAGS máy đọc (nhãn hiện ở Tổng quan thị trường) và mục cũ dài.
        st.markdown(split_news_tags(macro_text, set())[0])

    # --- Nâng cấp Vĩ mô ---
    st.sidebar.markdown("---")
    st.sidebar.header("Môi trường vĩ mô")
    # Mặc định = dữ liệu thật trong DB (CPI mới nhất, xu hướng lãi suất điều hành);
    # trước đây cứng 3% và ghi đè mọi nơi → cùng một mã ra MOS khác nhau tùy màn hình.
    from valuation.models.macro_env import MacroEnvironment

    _db_macro = MacroEnvironment.from_db(db_read)
    _sbv_options = ["Neutral", "Easing", "Tightening"]
    macro_inflation = (
        st.sidebar.number_input(
            "Lạm phát (%) — mặc định CPI mới nhất",
            min_value=0.0, max_value=20.0,
            value=round(_db_macro.inflation_rate * 100.0, 2), step=0.5,
        )
        / 100.0
    )
    macro_sbv = st.sidebar.selectbox(
        "Chính sách SBV", _sbv_options,
        index=_sbv_options.index(_db_macro.sbv_stance) if _db_macro.sbv_stance in _sbv_options else 0,
    )

    st.session_state["macro_env"] = MacroEnvironment(
        inflation_rate=macro_inflation,
        sbv_stance=macro_sbv,
        risk_free_rate=_db_macro.risk_free_rate,
    )

    # --- Nút cập nhật dữ liệu ---
    st.sidebar.markdown("---")
    st.sidebar.header("Dữ liệu & cập nhật")

    base_year_mode = st.sidebar.radio(
        "Mốc dữ liệu định giá",
        ["TTM (4 quý)", "FY (năm gần nhất)"],
        index=0,
        horizontal=True,
    )
    mode = "TTM" if "TTM" in base_year_mode else "FY"

    # Giữ kết quả lượt cập nhật gần nhất của mã đang mở (không pop): một lượt tải lại
    # trang bất kỳ (vd thanh tiến độ quét VN100) từng làm mất thông báo ngay lập tức.
    last_ingest_notice = st.session_state.get("last_ingest_notice")
    if last_ingest_notice and last_ingest_notice.get("ticker") == ticker:
        notice_method = getattr(st.sidebar, last_ingest_notice["level"])
        notice_method(last_ingest_notice["message"])
        for detail in last_ingest_notice.get("details", []):
            st.sidebar.caption(f"- {detail}")

    # Kiểm tra độ tươi dữ liệu
    from valuation.data_access.freshness_checker import (
        check_data_freshness,
        describe_data_freshness,
    )

    freshness = check_data_freshness(db_read, ticker=ticker)
    freshness_headline, freshness_details = describe_data_freshness(freshness)
    if freshness.is_stale:
        st.sidebar.error(
            f"{freshness_headline}. {freshness_details}",
            icon=":material/warning:",
        )
    else:
        st.sidebar.success(
            f"{freshness_headline}. {freshness_details}",
            icon=":material/check_circle:",
        )

    col1, col2 = st.sidebar.columns(2)
    clicked = col1.button(
        f"Tải mới {ticker}",
        width="stretch",
        help="Kéo giá, dòng tiền, BCTC và báo cáo khuyến nghị CTCK mới nhất cho mã này. "
        "Mở hoặc đổi sang mã này sẽ tự tải bản nhẹ một lần (BCTC chỉ khi có quý mới).",
    )
    auto = _claim_auto_refresh(st.session_state, ticker)
    if clicked or auto:
        with st.sidebar.status(f"Đang tải dữ liệu mới cho {ticker}...", expanded=True) as _st_status:
            from concurrent.futures import ThreadPoolExecutor
            from datetime import datetime
            from zoneinfo import ZoneInfo

            from valuation.db.models import FinancialsQuarterly
            from valuation.ingest.pipeline import financials_due, run_ingest
            from valuation.ingest.weekly_updater import _CONSENSUS_SOURCES

            try:
                has_financial_history = (
                    db_read.query(FinancialsQuarterly.ticker)
                    .filter(FinancialsQuarterly.ticker == ticker)
                    .first()
                    is not None
                )
                latest_q = (
                    db_read.query(FinancialsQuarterly.fiscal_year, FinancialsQuarterly.fiscal_quarter)
                    .filter(FinancialsQuarterly.ticker == ticker, FinancialsQuarterly.fiscal_quarter > 0)
                    .order_by(FinancialsQuarterly.fiscal_year.desc(), FinancialsQuarterly.fiscal_quarter.desc())
                    .first()
                )
                # D92: tự tải khi mở mã chỉ kéo BCTC khi DB chưa có quý gần nhất đã kết thúc; bấm nút thì kéo đủ.
                today = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()
                with_financials = clicked or financials_due(latest_q, today)
                # Dùng chung danh sách nguồn với quét hàng tuần (D24) để nút này
                # và nút quét VN100 không bao giờ lệch nhau về nguồn dữ liệu.
                _st_status.write(
                    "Đang tải song song: giá & dòng tiền"
                    + (", BCTC" if with_financials else "")
                    + " (vnstock) và báo cáo CTCK ("
                    + ", ".join(name for name, _ in _CONSENSUS_SOURCES)
                    + ")..."
                )
                broker_errors = []
                broker_rows = 0
                with ThreadPoolExecutor(max_workers=1 + len(_CONSENSUS_SOURCES)) as pool:
                    ingest_future = pool.submit(
                        run_ingest,
                        ticker,
                        data_types=["prices", "financials"] if with_financials else ["prices"],
                        incremental=True,
                        include_yearly=not has_financial_history,
                        parallel=True,
                    )
                    broker_futures = [
                        (_src_name, pool.submit(_importer, ticker))
                        for _src_name, _importer in _CONSENSUS_SOURCES
                    ]
                    for _src_name, _future in broker_futures:
                        try:
                            broker_rows += len(_future.result() or [])
                        except _UI_HANDLED_EXCEPTIONS as e_broker:
                            broker_errors.append(f"CTCK {_src_name}: {e_broker}")
                    ingest_result = ingest_future.result()

                updated_statements = [
                    statement
                    for statement, periods in ingest_result["financials"].items()
                    if periods["quarter"]["status"] == "UPDATED"
                ]
                failed_statements = [
                    statement
                    for statement, periods in ingest_result["financials"].items()
                    if periods["quarter"]["status"] == "FAILED"
                ]
                details = []
                if ingest_result["prices"]["status"] == "UPDATED":
                    details.append(
                        "Giá đã cập nhật đến "
                        + ingest_result["prices"].get("last_date", "kỳ mới nhất")
                    )
                if updated_statements:
                    details.append("BCTC đã cập nhật: " + ", ".join(updated_statements))
                if failed_statements:
                    details.append(
                        "BCTC chưa cập nhật: " + ", ".join(failed_statements)
                    )
                if not with_financials:
                    details.append(
                        f"BCTC đã có quý {latest_q[0]}-Q{latest_q[1]}, chưa tới kỳ quý mới — "
                        "bỏ qua khi tự tải; bấm Tải mới để kéo lại."
                    )
                if broker_rows:
                    details.append(
                        f"Đã đọc {broker_rows} báo cáo CTCK; bản trùng được cập nhật, "
                        "không nhân đôi."
                    )
                elif not broker_errors:
                    details.append("Nguồn CTCK chưa công bố báo cáo mới cho mã này.")
                details.extend(broker_errors)

                status = ingest_result["status"]
                if status == "SUCCESS" and not broker_errors:
                    notice = {
                        "ticker": ticker,
                        "level": "success",
                        "message": f"Đã hoàn tất lượt cập nhật {ticker}.",
                        "details": details,
                    }
                elif status == "FAILED":
                    notice = {
                        "ticker": ticker,
                        "level": "error",
                        "message": f"Không cập nhật được dữ liệu {ticker}.",
                        "details": details
                        + [error["message"] for error in ingest_result["errors"][:3]],
                    }
                else:
                    notice = {
                        "ticker": ticker,
                        "level": "warning",
                        "message": f"{ticker} chỉ cập nhật được một phần dữ liệu.",
                        "details": details,
                    }

                # Xóa mô hình cũ để lần rerun đọc lại dữ liệu vừa ghi.
                if "company" in st.session_state:
                    del st.session_state["company"]
                db_read.expire_all()
                st.session_state["last_ingest_notice"] = notice
                st.rerun()
            except _UI_HANDLED_EXCEPTIONS as e:
                st.sidebar.error(f"Lỗi khi cập nhật {ticker}: {e}")

    if col2.button(
        "Quét VN100 hàng tuần",
        width="stretch",
        help="Tự động kiểm tra BCTC & Báo cáo định giá CTCK mới nhất cho toàn bộ rổ VN100",
    ):
        from valuation.services.data_update_job import start_job

        if start_job():
            st.session_state["data_update_waiting"] = True
            st.toast("Đã bắt đầu quét VN100; tiến độ hiển thị ngay bên dưới.", icon=":material/check_circle:")
        else:
            st.toast("Một đợt quét đang chạy; không tạo thêm đợt mới.", icon=":material/info:")

    with st.sidebar:
        _data_update_progress()

    st.sidebar.markdown("<br>", unsafe_allow_html=True)

    # Nút bấm để load dữ liệu vào màn hình
    if (
        st.sidebar.button(
            "Nạp lại mô hình đã lưu",
            width="stretch",
            type="primary",
            help="Đọc lại dữ liệu đã có trong máy; không gọi API và không tải dữ liệu mới.",
        )
        or "company" not in st.session_state
        or st.session_state.get("current_ticker") != ticker
        or st.session_state.get("current_mode") != mode
    ):
        with st.spinner(f"Đang phân tích dữ liệu {ticker}..."):
            try:
                company = build_company_data(db_read, ticker, mode=mode)
                st.session_state["company"] = company
                st.session_state["current_ticker"] = ticker
                st.session_state["current_mode"] = mode
                st.session_state["analyst_assumptions"] = (
                    None  # Reset assumptions của analyst
                )
                st.toast(f"Đã nạp xong mô hình định giá {ticker} ({mode})!", icon=":material/check_circle:")
            except _UI_HANDLED_EXCEPTIONS as e:
                st.sidebar.error(f"Lỗi khi nạp dữ liệu: {e}")

    if "company" in st.session_state:
        comp = st.session_state["company"]
        # Thông tin tra cứu, không phải thông báo → chữ thường, không đóng khung callout xanh.
        profile_slot.markdown(
            f"**{comp.name}**  \n"
            f"{comp.sector} · {comp.current_price:,.0f} VND  \n"
            f"{comp.shares_outstanding:,.2f} triệu cp lưu hành"
        )

        # Nạp kịch bản đã lưu từ DB (Việc 5)
        from valuation.db.models import ValuationRun

        try:
            db_to_query = db_write if db_write is not None else db_read
            past_runs = (
                db_to_query.query(ValuationRun)
                .filter(ValuationRun.ticker == comp.ticker)
                .order_by(ValuationRun.created_at.desc())
                .limit(10)
                .all()
            )

            if past_runs:
                st.sidebar.markdown("---")
                st.sidebar.subheader("Nạp kịch bản cũ")
                run_options = [_format_run_option(r) for r in past_runs]
                selected_run_option = st.sidebar.selectbox(
                    "Chọn kịch bản cũ để nạp:", run_options, key="select_past_run"
                )

                if st.sidebar.button("Nạp kịch bản này", width="stretch"):
                    run_id = int(
                        selected_run_option.split(" - ")[0].replace("Vòng ", "")
                    )
                    run = next((r for r in past_runs if r.id == run_id), None)

                    if run and run.assumptions_json:
                        # Khôi phục assumptions của company bằng cách gán từng key
                        for k, v in run.assumptions_json.items():
                            if hasattr(comp.assumptions, k):
                                setattr(comp.assumptions, k, v)

                        # Khôi phục session states
                        st.session_state["analyst_scenario"] = run.scenario
                        st.session_state["analyst_pb_override"] = (
                            run.assumptions_json.get("pb_override", 0.0)
                        )
                        st.session_state["analyst_pe_override"] = (
                            run.assumptions_json.get("pe_override", 0.0)
                        )
                        st.session_state["analyst_confidence"] = (
                            run.assumptions_json.get("confidence_level", "Trung bình")
                        )
                        st.session_state["analyst_notes"] = run.notes or ""

                        # Buộc reset projections để hệ thống sinh lại từ kịch bản mới
                        if "projections" in st.session_state:
                            del st.session_state["projections"]

                        st.toast(f"Đã nạp kịch bản Vòng {run.id}!", icon=":material/download:")
                        st.rerun()
        except _UI_HANDLED_EXCEPTIONS as ex:
            st.sidebar.error(f"Lỗi khi load danh sách kịch bản: {ex}")
