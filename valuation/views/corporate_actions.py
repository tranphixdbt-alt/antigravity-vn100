"""Tab cổ tức, tăng vốn và quyền cổ đông."""
from __future__ import annotations

import datetime
from typing import Any, Dict

import pandas as pd
import streamlit as st

from valuation.analysis.corporate_actions import (
    analyze_corporate_action,
    analyze_historical_price_impact,
    assess_corporate_action,
    explain_historical_price_impact,
    explain_upcoming_action,
)
from valuation.config import load_defaults
from valuation.data_access.corporate_actions import load_corporate_actions
from valuation.db.models import PricesDaily
from valuation.ingest.corporate_actions import refresh_corporate_actions


_EVENT_LABELS = {
    "CASH_DIVIDEND": "Cổ tức tiền mặt",
    "STOCK_DIVIDEND": "Cổ tức cổ phiếu",
    "BONUS_SHARE": "Cổ phiếu thưởng",
    "RIGHTS_ISSUE": "Quyền mua",
    "ESOP": "ESOP/CBCNV",
    "PRIVATE_PLACEMENT": "Phát hành riêng lẻ",
    "SHARE_ISSUE": "Phát hành cổ phiếu",
    "ADDITIONAL_LISTING": "Niêm yết bổ sung",
    "SHARE_BUYBACK": "Mua lại cổ phiếu",
    "CONVERTIBLE": "Chuyển đổi",
    "MERGER": "Sáp nhập",
    "OTHER_CAPITAL_ACTION": "Sự kiện vốn khác",
}

_PRICE_IMPACT_TYPES = {
    "CASH_DIVIDEND",
    "STOCK_DIVIDEND",
    "BONUS_SHARE",
    "RIGHTS_ISSUE",
    "ESOP",
    "PRIVATE_PLACEMENT",
    "SHARE_ISSUE",
}


def _anchor(row: Any) -> Any:
    return (
        row.ex_right_date
        or row.record_date
        or row.payment_date
        or row.listing_date
        or row.announcement_date
    )


def _fmt_vnd(value: Any) -> str:
    return "-" if value is None else f"{float(value):,.0f}".replace(",", ".")


def _fmt_pct(value: Any) -> str:
    return "-" if value is None else f"{float(value):+.1f}%"


def _date_role(row: Any) -> str:
    if row.ex_right_date:
        return "Ngày GDKHQ"
    if row.record_date:
        return "Ngày chốt quyền"
    if row.payment_date:
        return "Ngày thanh toán"
    if row.listing_date:
        return "Ngày niêm yết"
    return "Ngày công bố"


def _benefit_summary(row: Any) -> str:
    ratio = float(row.exercise_ratio) if row.exercise_ratio is not None else None
    cash = (
        float(row.cash_amount_vnd_per_share)
        if row.cash_amount_vnd_per_share is not None
        else None
    )
    issue_price = float(row.issue_price_vnd) if row.issue_price_vnd is not None else None
    if row.event_type == "CASH_DIVIDEND" and cash is not None:
        return f"{_fmt_vnd(cash)} VND/cổ phiếu"
    if row.event_type in {"STOCK_DIVIDEND", "BONUS_SHARE"} and ratio is not None:
        return f"Thêm {ratio * 100:g} cổ phiếu/100 cổ phiếu"
    if row.event_type == "RIGHTS_ISSUE" and ratio is not None:
        text = f"Được mua {ratio * 100:g} cổ phiếu/100 cổ phiếu"
        return f"{text}, giá {_fmt_vnd(issue_price)} VND" if issue_price else text
    return "Chưa đủ thông tin"


def render_corporate_actions(
    company: Any,
    db: Any,
    *,
    refresh_result: Dict[str, Any] | None = None,
) -> None:
    cfg = (load_defaults().get("corporate_actions") or {}).copy()
    today = datetime.date.today()
    rows = load_corporate_actions(
        db,
        company.ticker,
        as_of_date=today,
        history_years=int(cfg.get("history_years", 5)),
        future_days=int(cfg.get("future_days", 365)),
    )

    st.header(f"Cổ tức, tăng vốn & quyền cổ đông ({company.ticker})")
    if st.button(
        "Làm mới",
        icon=":material/refresh:",
        help="Bỏ qua cache 24 giờ và kiểm tra nguồn sự kiện ngay.",
    ):
        with st.spinner("Đang kiểm tra công bố mới..."):
            refresh_corporate_actions(db, company.ticker, force=True)
        st.rerun()
    if refresh_result and refresh_result.get("status") == "BACKGROUND":
        st.caption(
            "Đang kiểm tra công bố mới trong nền; dữ liệu đã lưu vẫn được hiển thị ngay."
        )
    elif refresh_result and refresh_result.get("status") == "ERROR":
        st.warning(f"Chưa kiểm tra được nguồn mới: {refresh_result.get('error')}")
    elif refresh_result and refresh_result.get("checked"):
        changed = int(refresh_result.get("inserted") or 0) + int(
            refresh_result.get("updated") or 0
        )
        if changed:
            st.success(f"Đã nhận {changed} sự kiện mới hoặc được điều chỉnh.")
        else:
            st.info("Nguồn không có sự kiện mới; dữ liệu lịch sử không bị ghi lại.")
    else:
        st.caption("Dữ liệu đang trong thời hạn cache; không phát sinh lượt tải mới.")

    if not rows:
        st.info("Chưa có sự kiện vốn hoặc quyền cổ đông trong cửa sổ theo dõi.")
        return

    upcoming_rows = [row for row in rows if _anchor(row) and _anchor(row) > today]
    historical_rows = [row for row in rows if _anchor(row) and _anchor(row) <= today]
    nearest = min((_anchor(row) for row in upcoming_rows), default=None)
    days_to_nearest = (nearest - today).days if nearest else None

    metric_a, metric_b, metric_c = st.columns(3)
    metric_a.metric("Sắp tới (12 tháng)", len(upcoming_rows))
    metric_b.metric(
        "Gần nhất",
        f"{days_to_nearest} ngày" if days_to_nearest is not None else "Chưa có",
    )
    metric_c.metric("Lịch sử", len(historical_rows))

    with st.expander("Hiểu nhanh các con số trong phần này"):
        st.markdown(
            """
- **Giá trong ngày chia quyền**: giá trước sự kiện và giá khi cổ tức hoặc quyền mua đã được tách ra.
- **Bạn nhận thêm**: tiền mặt, cổ phiếu mới hoặc quyền được mua cổ phiếu.
- **Tổng tài sản sau khi cộng quyền lợi**: ước tính bạn thực sự tăng hay giảm bao nhiêu sau khi cộng phần nhận thêm.
- **Sau khoảng 1 tuần/1 tháng**: giá tăng hay giảm tiếp so với ngày chia quyền. Đây chỉ là diễn biến giá, không khẳng định sự kiện là nguyên nhân duy nhất.
- **Lợi nhuận trên mỗi cổ phiếu (EPS)**: phần lợi nhuận tương ứng với một cổ phiếu. Khi số cổ phiếu tăng nhanh hơn lợi nhuận, phần này sẽ giảm.
            """
        )

    st.subheader("Sự kiện đã công bố trong 12 tháng tới")
    st.caption(
        "Chỉ hiển thị sự kiện đã có công bố và ngày thực hiện. Hệ thống không tự dự đoán sự kiện chưa có nghị quyết."
    )
    if not upcoming_rows:
        st.info(
            "Hiện chưa có sự kiện cổ tức, quyền mua hoặc tăng vốn nào trong 12 tháng tới "
            "đã được nguồn dữ liệu công bố. Điều này không có nghĩa doanh nghiệp chắc chắn sẽ không phát sinh sự kiện mới."
        )
    else:
        for row in sorted(upcoming_rows, key=_anchor):
            ratio = float(row.exercise_ratio) if row.exercise_ratio is not None else None
            cash = (
                float(row.cash_amount_vnd_per_share)
                if row.cash_amount_vnd_per_share is not None
                else None
            )
            issue_price = (
                float(row.issue_price_vnd)
                if row.issue_price_vnd is not None
                else None
            )
            analysis = analyze_corporate_action(
                event_type=row.event_type,
                current_price_vnd=company.current_price,
                shares_outstanding=company.shares_outstanding * 1_000_000.0,
                exercise_ratio=ratio,
                cash_amount_vnd_per_share=cash,
                issue_price_vnd=issue_price,
            )
            assessment = assess_corporate_action(
                event_type=row.event_type,
                analysis=analysis,
                attractive_dividend_yield_pct=float(
                    cfg.get("attractive_dividend_yield_pct", 5.0)
                ),
                dilution_warning_pct=float(cfg.get("dilution_warning_pct", 10.0)),
            )
            explanation = explain_upcoming_action(
                event_type=row.event_type,
                holding_shares=int(cfg.get("example_holding_shares", 1_000)),
                current_price_vnd=company.current_price,
                exercise_ratio=ratio,
                cash_amount_vnd_per_share=cash,
                issue_price_vnd=issue_price,
                analysis=analysis,
            )
            label = _EVENT_LABELS.get(row.event_type, row.event_type)
            anchor = _anchor(row)
            with st.container(border=True):
                st.markdown(f"#### {label}: {row.title}")
                st.caption(
                    f"{_date_role(row)} {anchor.strftime('%d/%m/%Y')} · "
                    f"Nguồn {row.source_site} ({row.source_tier})"
                )
                first_row = st.columns(2)
                first_row[0].metric(
                    "Tỷ lệ",
                    f"{ratio * 100:.1f}%" if ratio is not None else "Chưa có",
                )
                first_row[1].metric(
                    "Giá dự kiến sau khi chia",
                    (
                        f"{_fmt_vnd(analysis['theoretical_ex_price_vnd'])} VND"
                        if analysis.get("theoretical_ex_price_vnd") is not None
                        else "Chưa tính được"
                    ),
                )
                second_row = st.columns(2)
                second_row[0].metric(
                    "Tiền trên mỗi cổ phiếu",
                    f"{_fmt_vnd(cash)} VND" if cash is not None else "Không có",
                )
                second_row[1].metric(
                    "EPS có thể giảm",
                    (
                        f"{abs(float(analysis['eps_dilution_pct_before_new_profit'])):.1f}%"
                        if analysis.get("eps_dilution_pct_before_new_profit") is not None
                        else "Không áp dụng"
                    ),
                )
                left, right = st.columns(2)
                with left:
                    st.markdown("**Nếu bạn đang giữ 1.000 cổ phiếu**")
                    st.write(explanation["what_you_receive"])
                    st.markdown("**Giá có thể điều chỉnh thế nào?**")
                    st.write(explanation["price_effect"])
                with right:
                    st.markdown("**Điều cần theo dõi**")
                    st.write(explanation["watch_for"])
                    st.markdown("**Kết luận dễ hiểu**")
                    st.write(explanation["simple_verdict"])
                if assessment["verdict"] in {"CẦN THẬN TRỌNG", "THIẾU DỮ LIỆU"}:
                    st.warning(f"{assessment['verdict']}: {assessment['reason']}")
                else:
                    st.info(f"{assessment['verdict']}: {assessment['reason']}")
                if row.source_url:
                    st.link_button(
                        "Mở công bố nguồn",
                        row.source_url,
                        icon=":material/open_in_new:",
                    )
                elif row.source_tier != "OFFICIAL":
                    st.caption(
                        "Nguồn tổng hợp; cần đối chiếu VSDC/HOSE/HNX/IR trước quyết định đầu tư."
                    )

    st.subheader("Sau những lần chia cổ tức hoặc tăng vốn, bạn lãi hay lỗ?")
    st.caption(
        "Trong ngày chia quyền, giá cổ phiếu thường tự giảm vì bạn được nhận tiền, "
        "cổ phiếu mới hoặc quyền mua. Vì vậy, bảng dưới cộng phần bạn nhận thêm để "
        "ước tính tổng tài sản tăng hay giảm. Giá vẫn có thể bị ảnh hưởng bởi các tin khác."
    )
    price_rows = (
        db.query(PricesDaily.trade_date, PricesDaily.close)
        .filter(PricesDaily.ticker == company.ticker)
        .order_by(PricesDaily.trade_date)
        .all()
    )
    prices = [
        {"date": item.trade_date, "close": float(item.close)}
        for item in price_rows
        if item.close is not None
    ]
    max_history = int(cfg.get("historical_impact_max_events", 12))
    impact_items = []
    for row in historical_rows:
        if row.event_type not in _PRICE_IMPACT_TYPES:
            continue
        ratio = float(row.exercise_ratio) if row.exercise_ratio is not None else None
        cash = (
            float(row.cash_amount_vnd_per_share)
            if row.cash_amount_vnd_per_share is not None
            else None
        )
        issue_price = (
            float(row.issue_price_vnd) if row.issue_price_vnd is not None else None
        )
        impact = analyze_historical_price_impact(
            prices=prices,
            event_date=_anchor(row),
            event_type=row.event_type,
            exercise_ratio=ratio,
            cash_amount_vnd_per_share=cash,
            issue_price_vnd=issue_price,
            short_sessions=int(cfg.get("price_impact_short_sessions", 5)),
            long_sessions=int(cfg.get("price_impact_long_sessions", 20)),
        )
        story = explain_historical_price_impact(
            event_type=row.event_type,
            impact=impact,
            reaction_materiality_pct=float(
                cfg.get("reaction_materiality_pct", 2.0)
            ),
        )
        impact_items.append((row, impact, story))
        if len(impact_items) >= max_history:
            break

    available_items = [item for item in impact_items if item[1].get("available")]
    if not available_items:
        st.info("Chưa đủ dữ liệu giá trước và sau sự kiện để đo tác động lịch sử.")
    else:
        table_rows = []
        for row, impact, story in available_items:
            table_rows.append(
                {
                    "Ngày": _anchor(row),
                    "Sự kiện": _EVENT_LABELS.get(row.event_type, row.event_type),
                    "Giá trong ngày chia quyền": (
                        f"{_fmt_vnd(impact.get('price_before_vnd'))} → "
                        f"{_fmt_vnd(impact.get('price_event_vnd'))} "
                        f"({_fmt_pct(impact.get('raw_event_return_pct'))})"
                    ),
                    "Bạn nhận thêm": _benefit_summary(row),
                    "Tổng tài sản sau khi cộng quyền lợi": _fmt_pct(
                        impact.get("shareholder_wealth_change_pct")
                    ),
                    "Giá sau khoảng 1 tuần": _fmt_pct(
                        impact.get("return_after_5_sessions_pct")
                    ),
                    "Giá sau khoảng 1 tháng": _fmt_pct(
                        impact.get("return_after_20_sessions_pct")
                    ),
                    "Nói ngắn gọn": story["reaction_label"],
                }
            )
        st.dataframe(
            pd.DataFrame(table_rows),
            width="stretch",
            hide_index=True,
            column_config={"Ngày": st.column_config.DateColumn(format="DD/MM/YYYY")},
        )
        st.markdown("**Xem giải thích bằng lời**")
        for index, (row, impact, story) in enumerate(available_items):
            label = _EVENT_LABELS.get(row.event_type, row.event_type)
            with st.expander(
                f"{label} · {_anchor(row).strftime('%d/%m/%Y')} · {story['reaction_label']}",
                expanded=index == 0,
            ):
                st.write(story["price_explanation"])
                st.write(story["wealth_explanation"])
                st.write(story["follow_through"])
                if impact.get("data_warning"):
                    st.caption(impact["data_warning"])

    implementation_rows = [
        row for row in historical_rows if row.event_type == "ADDITIONAL_LISTING"
    ]
    if implementation_rows:
        with st.expander("Các mốc niêm yết bổ sung đã hoàn tất"):
            st.caption(
                "Các mốc này là bước thực hiện sau phát hành/chia cổ phiếu; không tính "
                "thêm một lần pha loãng để tránh đánh giá trùng."
            )
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Ngày": _anchor(row),
                            "Nội dung": row.title,
                            "Nguồn": f"{row.source_site} ({row.source_tier})",
                        }
                        for row in implementation_rows
                    ]
                ),
                width="stretch",
                hide_index=True,
                column_config={
                    "Ngày": st.column_config.DateColumn(format="DD/MM/YYYY")
                },
            )
