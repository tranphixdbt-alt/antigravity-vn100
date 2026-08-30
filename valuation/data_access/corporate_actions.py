"""Đọc sự kiện doanh nghiệp theo thời điểm, không rò dữ liệu công bố tương lai."""
from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from valuation.analysis.corporate_actions import (
    analyze_corporate_action,
    analyze_historical_price_impact,
    assess_corporate_action,
    explain_historical_price_impact,
    explain_upcoming_action,
)
from valuation.config import load_defaults
from valuation.db.models import CorporateAction, CorporateActionSync, PricesDaily


_PRICE_IMPACT_TYPES = {
    "CASH_DIVIDEND",
    "STOCK_DIVIDEND",
    "BONUS_SHARE",
    "RIGHTS_ISSUE",
    "ESOP",
    "PRIVATE_PLACEMENT",
    "SHARE_ISSUE",
}


def should_refresh_corporate_actions(
    db: Session,
    ticker: str,
    *,
    now: Optional[datetime.datetime] = None,
    ttl_hours: int = 24,
    error_retry_minutes: int = 30,
) -> bool:
    now = now or datetime.datetime.now()
    sync = db.get(CorporateActionSync, (ticker.upper(), "VCI"))
    if sync is None or sync.last_checked_at is None:
        return True
    checked = sync.last_checked_at
    if checked.tzinfo is not None and now.tzinfo is None:
        checked = checked.replace(tzinfo=None)
    if sync.status != "OK":
        return now - checked >= datetime.timedelta(minutes=error_retry_minutes)
    return now - checked >= datetime.timedelta(hours=ttl_hours)


def _event_anchor(row: CorporateAction) -> Optional[datetime.date]:
    return (
        row.ex_right_date
        or row.record_date
        or row.payment_date
        or row.listing_date
        or row.announcement_date
    )


def load_corporate_actions(
    db: Session,
    ticker: str,
    *,
    as_of_date: Optional[datetime.date] = None,
    history_years: int = 5,
    future_days: int = 365,
) -> List[CorporateAction]:
    """Chỉ dùng sự kiện đã được công bố tính đến `as_of_date`."""
    as_of = as_of_date or datetime.date.today()
    window_start = as_of - datetime.timedelta(days=history_years * 366)
    window_end = as_of + datetime.timedelta(days=future_days)
    rows = (
        db.query(CorporateAction)
        .filter(
            CorporateAction.ticker == ticker.upper(),
            CorporateAction.announcement_date.is_not(None),
            CorporateAction.announcement_date <= as_of,
        )
        .all()
    )
    rows = [row for row in rows if (anchor := _event_anchor(row)) and window_start <= anchor <= window_end]
    source_rank = {"OFFICIAL": 0, "AGGREGATOR": 1}
    rows.sort(
        key=lambda row: (
            _event_anchor(row) or datetime.date.min,
            -source_rank.get(row.source_tier, 9),
        ),
        reverse=True,
    )
    return rows


def corporate_actions_context(
    db: Session,
    *,
    ticker: str,
    current_price_vnd: float,
    shares_outstanding: float,
    as_of_date: Optional[datetime.date] = None,
) -> Dict[str, Any]:
    cfg = (load_defaults().get("corporate_actions") or {}).copy()
    rows = load_corporate_actions(
        db,
        ticker,
        as_of_date=as_of_date,
        history_years=int(cfg.get("history_years", 5)),
        future_days=int(cfg.get("future_days", 365)),
    )
    max_events = int(cfg.get("max_events_ai", 12))
    as_of = as_of_date or datetime.date.today()
    price_rows = (
        db.query(PricesDaily.trade_date, PricesDaily.close)
        .filter(PricesDaily.ticker == ticker.upper())
        .order_by(PricesDaily.trade_date)
        .all()
    )
    prices = [
        {"date": row.trade_date, "close": float(row.close)}
        for row in price_rows
        if row.close is not None
    ]
    events: List[Dict[str, Any]] = []
    for row in rows[:max_events]:
        analysis = analyze_corporate_action(
            event_type=row.event_type,
            current_price_vnd=current_price_vnd,
            shares_outstanding=shares_outstanding,
            exercise_ratio=float(row.exercise_ratio) if row.exercise_ratio is not None else None,
            cash_amount_vnd_per_share=(
                float(row.cash_amount_vnd_per_share)
                if row.cash_amount_vnd_per_share is not None
                else None
            ),
            issue_price_vnd=float(row.issue_price_vnd) if row.issue_price_vnd is not None else None,
        )
        assessment = assess_corporate_action(
            event_type=row.event_type,
            analysis=analysis,
            attractive_dividend_yield_pct=float(
                cfg.get("attractive_dividend_yield_pct", 5.0)
            ),
            dilution_warning_pct=float(cfg.get("dilution_warning_pct", 10.0)),
        )
        anchor = _event_anchor(row)
        time_status = "UPCOMING" if anchor and anchor > as_of else "HISTORICAL"
        historical_price_impact = None
        if anchor and anchor <= as_of and row.event_type in _PRICE_IMPACT_TYPES:
            historical_price_impact = analyze_historical_price_impact(
                prices=prices,
                event_date=anchor,
                event_type=row.event_type,
                exercise_ratio=(
                    float(row.exercise_ratio)
                    if row.exercise_ratio is not None
                    else None
                ),
                cash_amount_vnd_per_share=(
                    float(row.cash_amount_vnd_per_share)
                    if row.cash_amount_vnd_per_share is not None
                    else None
                ),
                issue_price_vnd=(
                    float(row.issue_price_vnd)
                    if row.issue_price_vnd is not None
                    else None
                ),
                short_sessions=int(cfg.get("price_impact_short_sessions", 5)),
                long_sessions=int(cfg.get("price_impact_long_sessions", 20)),
            )
        historical_explanation = None
        if historical_price_impact and historical_price_impact.get("available"):
            historical_explanation = explain_historical_price_impact(
                event_type=row.event_type,
                impact=historical_price_impact,
                reaction_materiality_pct=float(
                    cfg.get("reaction_materiality_pct", 2.0)
                ),
            )
        upcoming_explanation = None
        if time_status == "UPCOMING":
            upcoming_explanation = explain_upcoming_action(
                event_type=row.event_type,
                holding_shares=int(cfg.get("example_holding_shares", 1_000)),
                current_price_vnd=current_price_vnd,
                exercise_ratio=(
                    float(row.exercise_ratio)
                    if row.exercise_ratio is not None
                    else None
                ),
                cash_amount_vnd_per_share=(
                    float(row.cash_amount_vnd_per_share)
                    if row.cash_amount_vnd_per_share is not None
                    else None
                ),
                issue_price_vnd=(
                    float(row.issue_price_vnd)
                    if row.issue_price_vnd is not None
                    else None
                ),
                analysis=analysis,
            )
        events.append(
            {
                "event_type": row.event_type,
                "title": row.title,
                "announcement_date": row.announcement_date.isoformat() if row.announcement_date else None,
                "effective_date": anchor.isoformat() if anchor else None,
                "time_status": time_status,
                "exercise_ratio": float(row.exercise_ratio) if row.exercise_ratio is not None else None,
                "cash_amount_vnd_per_share": (
                    float(row.cash_amount_vnd_per_share)
                    if row.cash_amount_vnd_per_share is not None
                    else None
                ),
                "issue_price_vnd": float(row.issue_price_vnd) if row.issue_price_vnd is not None else None,
                "shares_after": float(row.shares_after) if row.shares_after is not None else None,
                "source_site": row.source_site,
                "source_tier": row.source_tier,
                "source_url": row.source_url,
                "analysis": analysis,
                "assessment": assessment,
                "historical_price_impact": historical_price_impact,
                "historical_explanation": historical_explanation,
                "upcoming_explanation": upcoming_explanation,
            }
        )
    sync = db.get(CorporateActionSync, (ticker.upper(), "VCI"))
    return {
        "available": bool(events),
        "as_of_date": as_of.isoformat(),
        "n_events": len(events),
        "events": events,
        "last_checked_at": sync.last_checked_at.isoformat() if sync and sync.last_checked_at else None,
        "source_warning": (
            "VCI là nguồn tổng hợp. Sự kiện chưa có nguồn OFFICIAL cần đối chiếu VSDC/HOSE/HNX/IR trước quyết định."
        ),
    }
