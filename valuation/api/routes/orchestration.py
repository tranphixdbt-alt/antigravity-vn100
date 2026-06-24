from fastapi import APIRouter, HTTPException, Depends
from typing import List
from pydantic import BaseModel
from sqlalchemy.orm import Session
import logging
import datetime

from valuation.db.session import get_write_db
from valuation.engine.daily_signal import calculate_batch_signals
from valuation.output.gsheets_exporter import export_daily_signals_to_gsheets
from valuation.output.discord_alerter import send_daily_alerts

router = APIRouter()
logger = logging.getLogger(__name__)

class RunDailyRequest(BaseModel):
    tickers: List[str]
    trade_date: str = None # Format YYYY-MM-DD
    force_override: bool = False

@router.post("/run-daily", summary="Chạy Daily Signal toàn bộ thị trường & Cập nhật Output")
def run_daily_pipeline(request: RunDailyRequest, db: Session = Depends(get_write_db)):
    """
    Endpoint duy nhất dành cho n8n để kích hoạt toàn bộ luồng xử lý cuối ngày:
    1. Tính toán Daily Signal cho rổ mã cung cấp.
    2. Đẩy kết quả vào Google Sheets (Two-Way Model).
    3. Phân tích kết quả và bắn cảnh báo Discord nếu cần.
    """
    try:
        trade_date = None
        if request.trade_date:
            trade_date = datetime.date.fromisoformat(request.trade_date)
            
        logger.info(f"Starting daily pipeline for {len(request.tickers)} tickers on {trade_date or 'LATEST'}")
        
        # Step 1: Calculate signals
        signals_res = calculate_batch_signals(
            tickers=request.tickers, 
            trade_date=trade_date,
            force_override=request.force_override,
            db=db
        )
        
        # Determine the effective trade_date for export
        effective_dates = []
        if isinstance(signals_res, dict):
            signals_values = signals_res.values()
        elif isinstance(signals_res, list):
            signals_values = signals_res
        else:
            signals_values = []
            
        for s in signals_values:
            if isinstance(s, dict) and 'trade_date' in s:
                effective_dates.append(datetime.date.fromisoformat(s['trade_date']))
                
        export_date = max(effective_dates) if effective_dates else (trade_date or datetime.date.today())
        
        # Step 2: Export to Google Sheets
        sheets_res = export_daily_signals_to_gsheets(trade_date=export_date, db=db)
        
        # Step 3: Discord Alerts
        discord_res = send_daily_alerts(trade_date=export_date, db=db)
        
        return {
            "status": "success",
            "pipeline_summary": {
                "signals_processed": len(signals_res),
                "google_sheets_sync": sheets_res,
                "discord_alerts": discord_res
            }
        }
        
    except Exception as e:
        logger.error(f"Daily pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
