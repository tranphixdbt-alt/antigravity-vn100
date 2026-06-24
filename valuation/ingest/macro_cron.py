from valuation.db.session import SessionLocalWrite
from valuation.ingest.scrapers.yfinance_scraper import fetch_yfinance_macro
# from valuation.ingest.scrapers.llm_extractor import extract_macro_from_text

def run_macro_ingestion_pipeline():
    """
    Chạy tất cả các scraper để cập nhật dữ liệu vĩ mô.
    Có thể được schedule bằng cronjob trên server (ví dụ chạy lúc 5PM mỗi ngày).
    """
    print("Starting Macro Ingestion Pipeline...")
    
    db = SessionLocalWrite()
    try:
        # 1. Fetch yfinance data (FX, Commodities)
        print("\n--- Fetching global data from yfinance ---")
        fetch_yfinance_macro(db)
        
        # 2. Fetch domestic data via Scraping + LLM (Placeholder logic)
        print("\n--- Fetching domestic data via LLM (if applicable) ---")
        # Logic to scrape domestic sites and pass to extract_macro_from_text would go here.
        # Example:
        # text = scrape_sbv_news()
        # data = extract_macro_from_text(text, "Lãi suất liên ngân hàng")
        # if data.get('value'):
        #     # Save to db...
        print("LLM domestic scraper placeholder executed.")
        
    finally:
        db.close()
        
    print("\nMacro Ingestion Pipeline Completed.")

if __name__ == "__main__":
    run_macro_ingestion_pipeline()
