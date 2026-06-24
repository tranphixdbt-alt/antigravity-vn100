import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from valuation.ingest.pipeline import run_ingest

def ingest_dgc():
    ticker = "DGC"
    print(f"Starting data ingestion for {ticker} from vnstock API...")
    try:
        run_ingest(ticker, ["prices", "financials"])
        print(f"Successfully ingested all historical prices and financial reports for {ticker}!")
    except Exception as e:
        print(f"Failed to ingest data for {ticker}: {e}")

if __name__ == "__main__":
    ingest_dgc()
