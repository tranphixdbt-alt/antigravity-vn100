"""
Freshness Checker Module — Kiểm tra độ tươi của dữ liệu BCTC, Giá và Báo cáo CTCK trong DB.
"""
from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from valuation.db.models import PricesDaily, Consensus, FinancialsQuarterly


@dataclass
class DataFreshnessStatus:
    is_stale: bool
    days_since_price: int
    days_since_consensus: int
    last_price_date: Optional[date]
    last_consensus_date: Optional[date]
    latest_financial_year: Optional[int]
    latest_financial_quarter: Optional[int]


def check_data_freshness(db: Session, threshold_days: int = 7) -> DataFreshnessStatus:
    """
    Kiểm tra độ tươi của dữ liệu trong hệ thống:
    - Ngày cập nhật giá thị trường gần nhất trong DB.
    - Ngày báo cáo khuyến nghị CTCK gần nhất trong DB.
    - Kỳ BCTC gần nhất.
    Trả về DataFreshnessStatus với `is_stale = True` nếu dữ liệu cũ hơn threshold_days (mặc định 7 ngày).
    """
    today = datetime.now().date()

    # 1. Lấy ngày giá thị trường mới nhất
    max_price_date = db.query(func.max(PricesDaily.trade_date)).scalar()
    
    # 2. Lấy ngày báo cáo CTCK mới nhất
    max_consensus_date = db.query(func.max(Consensus.report_date)).scalar()

    # 3. Lấy kỳ BCTC mới nhất
    latest_fin = db.query(
        func.max(FinancialsQuarterly.fiscal_year),
        func.max(FinancialsQuarterly.fiscal_quarter)
    ).first()
    
    latest_year = latest_fin[0] if latest_fin else None
    latest_quarter = latest_fin[1] if latest_fin else None

    # Tính khoảng cách số ngày
    days_price = (today - max_price_date).days if max_price_date else 999
    days_consensus = (today - max_consensus_date).days if max_consensus_date else 999

    # Dữ liệu bị coi là cũ nếu giá hoặc báo cáo CTCK chưa được cập nhật > threshold_days
    is_stale = (days_price >= threshold_days) or (days_consensus >= threshold_days)

    return DataFreshnessStatus(
        is_stale=is_stale,
        days_since_price=days_price,
        days_since_consensus=days_consensus,
        last_price_date=max_price_date,
        last_consensus_date=max_consensus_date,
        latest_financial_year=latest_year,
        latest_financial_quarter=latest_quarter
    )
