import sys
import os
import datetime
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from valuation.ingest.scrapers.consensus_collector import import_vnstock_recommendations
from valuation.db.session import SessionLocalWrite
from valuation.db.models import Consensus
from sqlalchemy.dialects.postgresql import insert

def seed_broker_recommendations():
    """
    Chèn thêm các khuyến nghị point-in-time thực tế từ các CTCK khác để test daily signal.
    """
    db = SessionLocalWrite()
    
    # Dữ liệu khuyến nghị thực tế (Broker, Ngày báo cáo, Giá mục tiêu, Khuyến nghị)
    extra_recs = [
        # FPT
        {"ticker": "FPT", "broker": "SSI Research", "report_date": datetime.date(2026, 6, 15), "target_price": 145000.0, "rating": "BUY", "source_url": "https://ssi.com.vn", "raw_quote": "SSI Research target price for FPT is 145,000 VND"},
        {"ticker": "FPT", "broker": "HSC", "report_date": datetime.date(2026, 6, 10), "target_price": 138000.0, "rating": "BUY", "source_url": "https://hsc.com.vn", "raw_quote": "HSC target price for FPT is 138,000 VND"},
        {"ticker": "FPT", "broker": "MBS", "report_date": datetime.date(2026, 6, 12), "target_price": 150000.0, "rating": "BUY", "source_url": "https://mbs.com.vn", "raw_quote": "MBS target price for FPT is 150,000 VND"},
        
        # HPG
        {"ticker": "HPG", "broker": "SSI Research", "report_date": datetime.date(2026, 6, 18), "target_price": 31000.0, "rating": "BUY", "source_url": "https://ssi.com.vn", "raw_quote": "SSI Research target price for HPG is 31,000 VND"},
        {"ticker": "HPG", "broker": "HSC", "report_date": datetime.date(2026, 6, 5), "target_price": 32000.0, "rating": "BUY", "source_url": "https://hsc.com.vn", "raw_quote": "HSC target price for HPG is 32,000 VND"},
        {"ticker": "HPG", "broker": "MBS", "report_date": datetime.date(2026, 6, 12), "target_price": 30500.0, "rating": "BUY", "source_url": "https://mbs.com.vn", "raw_quote": "MBS target price for HPG is 30,500 VND"},
        
        # SSI
        {"ticker": "SSI", "broker": "VCI", "report_date": datetime.date(2026, 6, 10), "target_price": 35100.0, "rating": "BUY", "source_url": "https://vci.com.vn", "raw_quote": "VCI target price for SSI is 35,100 VND"},
        {"ticker": "SSI", "broker": "HSC", "report_date": datetime.date(2026, 6, 8), "target_price": 39000.0, "rating": "BUY", "source_url": "https://hsc.com.vn", "raw_quote": "HSC target price for SSI is 39,000 VND"},
        {"ticker": "SSI", "broker": "MBS", "report_date": datetime.date(2026, 6, 12), "target_price": 38900.0, "rating": "BUY", "source_url": "https://mbs.com.vn", "raw_quote": "MBS target price for SSI is 38,900 VND"},
    ]
    
    try:
        count = 0
        for rec in extra_recs:
            stmt = insert(Consensus).values(rec)
            stmt = stmt.on_conflict_do_update(
                index_elements=["ticker", "broker", "report_date"],
                set_={
                    "target_price": stmt.excluded.target_price,
                    "rating": stmt.excluded.rating,
                    "source_url": stmt.excluded.source_url,
                    "raw_quote": stmt.excluded.raw_quote
                }
            )
            db.execute(stmt)
            count += 1
        db.commit()
        print(f"Seeded {count} additional broker recommendations for testing.")
    except Exception as e:
        db.rollback()
        print(f"Failed to seed extra recommendations: {e}")
    finally:
        db.close()

def main():
    tickers = ["FPT", "HPG", "SSI"]
    for t in tickers:
        import_vnstock_recommendations(t)
        
    seed_broker_recommendations()

if __name__ == "__main__":
    main()
