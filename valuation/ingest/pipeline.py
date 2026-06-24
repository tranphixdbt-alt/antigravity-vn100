import logging
import pandas as pd
from datetime import datetime
from sqlalchemy.dialects.postgresql import insert
from valuation.db.session import SessionLocalWrite
from valuation.db.models import PricesDaily, FinancialsQuarterly, BackfillStatus, Ticker
from valuation.ingest.vnstock_client import vnstock_client
from valuation.ingest.normalizer import normalize_daily_prices, unpivot_financials

logger = logging.getLogger(__name__)

def upsert_prices(df: pd.DataFrame, ticker: str):
    if df.empty:
        return
    
    # Chuẩn bị records
    records = []
    for _, row in df.iterrows():
        records.append({
            'ticker': ticker,
            'trade_date': row['time'].date() if isinstance(row['time'], pd.Timestamp) else pd.to_datetime(row['time']).date(),
            'open': row.get('open'),
            'high': row.get('high'),
            'low': row.get('low'),
            'close': row.get('close'),
            'volume': row.get('volume'),
            'price_unit': row.get('price_unit', 'VND')
        })
    
    db = SessionLocalWrite()
    try:
        stmt = insert(PricesDaily).values(records)
        update_dict = {
            c.name: c for c in stmt.excluded 
            if c.name not in ['ticker', 'trade_date']
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=['ticker', 'trade_date'],
            set_=update_dict
        )
        db.execute(stmt)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error upserting prices for {ticker}: {e}")
        raise e
    finally:
        db.close()

def upsert_financials(df: pd.DataFrame, ticker: str):
    if df.empty:
        return
        
    records = []
    for _, row in df.iterrows():
        val = row.get('value')
        if pd.isna(val):
            val = None
        elif isinstance(val, (int, float)):
            val = float(val)
            
        records.append({
            'ticker': ticker,
            'fiscal_year': int(row['fiscal_year']),
            'fiscal_quarter': int(row['fiscal_quarter']),
            'is_consolidated': bool(row['is_consolidated']),
            'is_restated': bool(row['is_restated']),
            'statement': str(row['statement']),
            'line_item': str(row['line_item']),
            'value': val,
            'currency': str(row.get('currency', 'VND')),
            'source': 'vnstock'
        })
        
    db = SessionLocalWrite()
    try:
        # Chia nhỏ để tránh lỗi quá tải tham số của PostgreSQL
        batch_size = 500
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            stmt = insert(FinancialsQuarterly).values(batch)
            update_dict = {
                c.name: c for c in stmt.excluded 
                if c.name not in ['ticker', 'fiscal_year', 'fiscal_quarter', 'is_consolidated', 'is_restated', 'statement', 'line_item']
            }
            stmt = stmt.on_conflict_do_update(
                index_elements=['ticker', 'fiscal_year', 'fiscal_quarter', 'is_consolidated', 'is_restated', 'statement', 'line_item'],
                set_=update_dict
            )
            db.execute(stmt)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error upserting financials for {ticker}: {e}")
        raise e
    finally:
        db.close()

def update_backfill_status(ticker: str, status: str, last_price_date=None, last_financial_period=None):
    db = SessionLocalWrite()
    try:
        stmt = insert(BackfillStatus).values(
            ticker=ticker,
            status=status,
            last_price_date=last_price_date,
            last_financial_period=last_financial_period
        )
        update_dict = {
            'status': stmt.excluded.status,
            'updated_at': datetime.now()
        }
        if last_price_date:
            update_dict['last_price_date'] = stmt.excluded.last_price_date
        if last_financial_period:
            update_dict['last_financial_period'] = stmt.excluded.last_financial_period
            
        stmt = stmt.on_conflict_do_update(
            index_elements=['ticker'],
            set_=update_dict
        )
        db.execute(stmt)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating status for {ticker}: {e}")
    finally:
        db.close()

def run_ingest(ticker: str, data_types: list):
    """
    Orchestrator hàm lấy dữ liệu, chuẩn hóa và lưu DB.
    data_types: ['prices', 'financials']
    """
    # 1. Đảm bảo ticker tồn tại (để foreign key ko báo lỗi)
    db = SessionLocalWrite()
    try:
        if not db.query(Ticker).filter(Ticker.ticker == ticker).first():
            overview = vnstock_client.get_company_overview(ticker)
            if not overview.empty:
                info = overview.iloc[0]
                db.execute(insert(Ticker).values(
                    ticker=ticker,
                    company_name=info.get('organ_name', ''),
                    exchange='',
                    sector=info.get('sector', ''),
                    industry=info.get('icb_code_lv4', ''),
                    is_vn100=True
                ).on_conflict_do_nothing())
                db.commit()
    finally:
        db.close()

    status = "SUCCESS"
    last_price = None
    last_fin = None

    try:
        if 'prices' in data_types:
            df_prices = vnstock_client.get_historical_prices(ticker, '2020-01-01')
            df_norm = normalize_daily_prices(df_prices)
            upsert_prices(df_norm, ticker)
            if not df_prices.empty:
                last_price = pd.to_datetime(df_prices.iloc[-1]['time']).date()

        if 'financials' in data_types:
            for stmt_type in ['BS', 'IS', 'CF']:
                df_fin = vnstock_client.get_financials(ticker, stmt_type)
                df_long = unpivot_financials(df_fin, stmt_type)
                upsert_financials(df_long, ticker)
                if not df_long.empty and not last_fin:
                    last_fin = f"{df_long['fiscal_year'].max()}-Q{df_long[df_long['fiscal_year']==df_long['fiscal_year'].max()]['fiscal_quarter'].max()}"

    except Exception as e:
        logger.error(f"Ingest failed for {ticker}: {e}")
        status = "FAILED"
        raise e
    finally:
        update_backfill_status(ticker, status, last_price, last_fin)
