import logging
import datetime
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
from sqlalchemy.orm import Session
from valuation.db.models import DailySignal, Ticker
from valuation.db.session import SessionLocalRead
from valuation.config import settings

logger = logging.getLogger(__name__)

def export_daily_signals_to_gsheets(trade_date: datetime.date = None, db: Session = None):
    """
    Xuất bảng DailySignal trong ngày ra Google Sheets.
    Cấu hình credentials nằm trong file service_account.json
    """
    if not settings.google_service_account_json or not settings.google_sheet_master_id:
        logger.warning("Google Sheets config missing. Skipping export.")
        return {"status": "skipped", "reason": "Missing GS config"}
        
    close_db = False
    if db is None:
        db = SessionLocalRead()
        close_db = True
        
    if trade_date is None:
        trade_date = datetime.date.today()
        
    try:
        # Fetch data
        signals = db.query(DailySignal).filter(DailySignal.trade_date == trade_date).all()
        if not signals:
            logger.info("No daily signals found for export.")
            return {"status": "success", "exported_rows": 0}
            
        data = []
        for s in signals:
            ticker_obj = db.query(Ticker).filter(Ticker.ticker == s.ticker).first()
            sector = ticker_obj.sector if ticker_obj else "Unknown"
            
            data.append({
                "Mã CK": s.ticker,
                "Ngành": sector,
                "Ngày GD": s.trade_date.isoformat(),
                "Thị giá": float(s.close_price) if s.close_price else None,
                "FV Nhịp Nhanh": float(s.fair_value_fast) if s.fair_value_fast else None,
                "Upside (%)": float(s.upside) * 100 if s.upside else None,
                "Margin of Safety (%)": float(s.margin_of_safety) * 100 if s.margin_of_safety else None,
                "Điểm Conviction (0-100)": float(s.conviction_score) if s.conviction_score else None,
                "Cờ Cảnh Báo": ", ".join(s.flags) if s.flags else "OK"
            })
            
        df = pd.DataFrame(data)
        
        # Sort by Conviction Score desc
        df = df.sort_values(by="Điểm Conviction (0-100)", ascending=False)
        
        # Authenticate and Push
        gc = gspread.service_account(filename=settings.google_service_account_json)
        sh = gc.open_by_key(settings.google_sheet_master_id)
        
        try:
            worksheet = sh.worksheet("Daily_Screener")
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sh.add_worksheet(title="Daily_Screener", rows="100", cols="20")
            
        # Clear old data and insert new
        worksheet.clear()
        set_with_dataframe(worksheet, df)
        
        logger.info(f"Successfully exported {len(df)} rows to Google Sheets.")
        return {"status": "success", "exported_rows": len(df)}
        
    except Exception as e:
        logger.error(f"Failed to export to Google Sheets: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        if close_db:
            db.close()
