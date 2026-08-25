import os
import sys
import time
import json
import logging

sys.path.append(os.getcwd())
from valuation.ingest.pipeline import run_ingest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_ingest_all():
    print("--- Bắt đầu tải dữ liệu mới cho danh mục VN100 ---")
    with open('valuation/config/routing.json', 'r', encoding='utf-8') as f:
        routing_data = json.load(f)
        
    tickers = list(routing_data.keys())
    success_count = 0
    
    for i, ticker in enumerate(tickers):
        print(f"[{i+1}/{len(tickers)}] Đang cập nhật dữ liệu cho {ticker}...")
        try:
            run_ingest(ticker, data_types=['prices', 'financials'], incremental=True)
            success_count += 1
            time.sleep(1.5)  # Tránh rate limit của API vnstock
        except Exception as e:
            logger.error(f"Lỗi cập nhật {ticker}: {e}")
            
    print(f"--- Hoàn tất tải dữ liệu. Thành công: {success_count}/{len(tickers)} ---")

if __name__ == "__main__":
    run_ingest_all()
