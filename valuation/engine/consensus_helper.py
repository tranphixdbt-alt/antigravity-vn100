import datetime
import statistics
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from valuation.db.models import Consensus, ConsensusSynthesis

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


def get_synthesis(ticker: str, db: Session) -> Optional[Dict[str, Any]]:
    """Lấy bản AI tổng hợp đa-CTCK (điểm chung/riêng/mấu chốt) cho 1 mã.

    Trả None nếu chưa có. Dùng cho báo cáo/app hiển thị nhận định tổng hợp.
    """
    row = db.query(ConsensusSynthesis).filter(
        ConsensusSynthesis.ticker == ticker.upper()).one_or_none()
    if row is None:
        return None
    return {
        "ticker": row.ticker,
        "n_reports": row.n_reports,
        "brokers": row.brokers,
        "diem_chung": row.diem_chung or [],
        "diem_rieng": row.diem_rieng or [],
        "diem_mau_chot": row.diem_mau_chot or [],
        "doi_chieu_noi_bo": row.doi_chieu_noi_bo or "",
        "internal_fv": float(row.internal_fv) if row.internal_fv is not None else None,
        "consensus_median": float(row.consensus_median) if row.consensus_median is not None else None,
        "generated_at": row.generated_at,
    }
