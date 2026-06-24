import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from valuation.db.session import SessionLocalRead, SessionLocalWrite
from valuation.api.routes.valuation import revalue_ticker

def run_test():
    db_read = SessionLocalRead()
    db_write = SessionLocalWrite()
    ticker = "DGC"
    print(f"Running valuation for {ticker}...")
    try:
        res = revalue_ticker(ticker, db_read=db_read, db_write=db_write)
        print("\n--- API Response Metadata ---")
        print(f"Ticker: {res['ticker']}")
        print(f"Current Price: {res['current_price']:,.0f} VND")
        print(f"Blended Fair Value: {res['valuation']['blended_fair_value_per_share']:,.0f} VND")
        print(f"DCF Fair Value: {res['valuation']['dcf_fvps']:,.0f} VND")
        print(f"Multiple Fair Value: {res['valuation']['multiples_fvps']:,.0f} VND")
        print(f"Greeks: {res['greeks']}")
        print(f"QC Flags: {res['qc']['flags']}")
        print("Valuation run completed successfully!")
    except Exception as e:
        print(f"Valuation failed: {e}")
    finally:
        db_read.close()
        db_write.close()

if __name__ == "__main__":
    run_test()
