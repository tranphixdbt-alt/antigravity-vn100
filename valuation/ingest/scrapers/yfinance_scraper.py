import yfinance as yf
from sqlalchemy.orm import Session
from valuation.db.models import MacroSeries
from valuation.db.session import SessionLocalWrite

# Map of yfinance symbols to our internal indicator codes
YF_MAPPING = {
    "VND=X": "EXCHANGE_RATE", # USD/VND
    "HRC=F": "STEEL_HRC",     # US Midwest Hot-Rolled Coil Steel Futures
    "CL=F": "CRUDE_OIL"       # Crude Oil WTI Futures
}

def fetch_yfinance_macro(db: Session = None):
    close_db = False
    if db is None:
        db = SessionLocalWrite()
        close_db = True

    try:
        records = []
        for symbol, code in YF_MAPPING.items():
            ticker = yf.Ticker(symbol)
            # Fetch last 5 days to ensure we get a valid trading day
            hist = ticker.history(period="5d")
            if not hist.empty:
                latest = hist.iloc[-1]
                # hist.index is typically a datetime with timezone
                date_val = latest.name.date()
                val = float(latest["Close"])
                
                # Check if this exact date + code already exists to prevent duplicates
                exists = db.query(MacroSeries).filter_by(
                    indicator_code=code, 
                    date=date_val
                ).first()
                
                if not exists:
                    rec = MacroSeries(
                        indicator_code=code,
                        date=date_val,
                        value=val,
                        source="yfinance"
                    )
                    records.append(rec)
                    print(f"[{code}] Fetched value: {val} on {date_val}")
                else:
                    print(f"[{code}] Data already up-to-date for {date_val}")
            else:
                print(f"[{code}] Could not fetch data for symbol {symbol}")
                
        if records:
            db.add_all(records)
            db.commit()
            print(f"Saved {len(records)} records from yfinance.")
            
    except Exception as e:
        db.rollback()
        print(f"Error in yfinance scraper: {e}")
    finally:
        if close_db:
            db.close()

if __name__ == "__main__":
    fetch_yfinance_macro()
