import datetime
import statistics
from typing import Dict, Any
from sqlalchemy.orm import Session
from valuation.db.models import Consensus

def get_consensus_stats(ticker: str, trade_date: datetime.date, db: Session) -> Dict[str, Any]:
    """
    Truy vấn các khuyến nghị trong consensus_history cho ticker,
    lọc điều kiện report_date <= trade_date và trong vòng 180 ngày gần nhất.
    Tính toán trung vị (Median), trung bình (Mean) và số lượng báo cáo.
    """
    start_date = trade_date - datetime.timedelta(days=180)
    records = db.query(Consensus).filter(
        Consensus.ticker == ticker,
        Consensus.report_date <= trade_date,
        Consensus.report_date >= start_date
    ).all()
    
    if not records:
        return {"median": None, "mean": None, "count": 0}
        
    prices = [float(r.target_price) for r in records if r.target_price is not None]
    if not prices:
        return {"median": None, "mean": None, "count": 0}
        
    median_val = statistics.median(prices)
    mean_val = sum(prices) / len(prices)
    
    return {
        "median": median_val,
        "mean": mean_val,
        "count": len(prices)
    }
