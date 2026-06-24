import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from valuation.db.session import SessionLocalWrite
from valuation.db.models import FinancialsQuarterly, PricesDaily
from valuation.ingest.pipeline import run_ingest

def main():
    db = SessionLocalWrite()
    
    tickers = ["FPT", "HPG", "SSI"]
    for t in tickers:
        print(f"\n=== CLEANING DATA FOR {t} ===")
        # 1. Xóa các bản ghi BCTC có source IS NULL (dữ liệu seed)
        deleted_fin = db.query(FinancialsQuarterly).filter(
            FinancialsQuarterly.ticker == t,
            FinancialsQuarterly.source.is_(None)
        ).delete()
        print(f"Deleted {deleted_fin} seed financial records for {t}")
        
        # 2. Xóa các giá trị mock/hardcode (nếu có) - ví dụ giá ngày 2026-06-20 được setup mock trong run_real_signals
        # Để đảm bảo an toàn, ta chỉ xóa giá trị mock nếu nó được chèn thủ công (ví dụ ngày 2026-06-20 có close=28000 hoặc 35000)
        # Thực ra, ta có thể xóa giá ngày 2026-06-20 đi để khi re-ingest hoặc chạy tín hiệu thật sẽ tự động cập nhật
        deleted_prices = db.query(PricesDaily).filter(
            PricesDaily.ticker == t,
            PricesDaily.trade_date == "2026-06-20"
        ).delete()
        print(f"Deleted {deleted_prices} mock prices for {t}")
        
    db.commit()
    db.close()
    
    # 3. Chạy lại ingest từ vnstock cho cả 3 mã
    for t in tickers:
        print(f"\n=== RE-INGESTING LIVE DATA FOR {t} ===")
        try:
            run_ingest(t, ["prices", "financials"])
            print(f"SUCCESSfully re-ingested live data for {t}!")
        except Exception as e:
            print(f"FAILED to re-ingest live data for {t}: {e}")

if __name__ == "__main__":
    main()
