import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from valuation.db.session import SessionLocalRead, SessionLocalWrite
from valuation.api.routes.valuation import revalue_ticker

def test_revalue_run():
    db_read = SessionLocalRead()
    db_write = SessionLocalWrite()
    
    tickers = ["FPT", "HPG", "SSI"]
    for t in tickers:
        print(f"\n==========================================")
        print(f" RUNNING REVALUATION FOR {t}")
        print(f"==========================================")
        try:
            res = revalue_ticker(t, db_read=db_read, db_write=db_write)
            print("SUCCESS!")
            # In ra các cờ Flags
            print(f"Base Fair Value: {res['valuation'].get('blended_fair_value_per_share', res['valuation'].get('base_fair_value')):,.0f} VND")
            print(f"Implied Metrics:")
            # Tìm implied PE, PB
            # Trong response trả về, QC có kết quả
            qc = res.get("qc", {})
            print(f"  Flags: {qc.get('flags', [])}")
        except Exception as e:
            print(f"Error revaluing {t}: {e}")
            
    db_read.close()
    db_write.close()

if __name__ == "__main__":
    test_revalue_run()
