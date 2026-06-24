import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from valuation.db.session import SessionLocalWrite
from valuation.db.models import FinancialsQuarterly, PricesDaily

def main():
    db = SessionLocalWrite()
    for tk in ["FPT", "HPG", "SSI"]:
        print(f"\n=== {tk} SOURCE CHECK ===")
        # Đếm số dòng BCTC
        cnt_all = db.query(FinancialsQuarterly).filter(FinancialsQuarterly.ticker == tk).count()
        cnt_vnstock = db.query(FinancialsQuarterly).filter(FinancialsQuarterly.ticker == tk, FinancialsQuarterly.source == 'vnstock').count()
        cnt_null = db.query(FinancialsQuarterly).filter(FinancialsQuarterly.ticker == tk, FinancialsQuarterly.source.is_(None)).count()
        cnt_other = db.query(FinancialsQuarterly).filter(
            FinancialsQuarterly.ticker == tk, 
            FinancialsQuarterly.source.isnot(None), 
            FinancialsQuarterly.source != 'vnstock'
        ).count()
        print(f"Total Financials: {cnt_all}")
        print(f"  vnstock source: {cnt_vnstock}")
        print(f"  NULL source (likely seed): {cnt_null}")
        print(f"  other source: {cnt_other}")
        
        # Xem một số record không phải vnstock
        non_vn = db.query(FinancialsQuarterly).filter(
            FinancialsQuarterly.ticker == tk, 
            FinancialsQuarterly.source.is_(None)
        ).limit(10).all()
        for r in non_vn:
            print(f"    {r.line_item} | Q{r.fiscal_quarter}/{r.fiscal_year} | {r.value:,.0f} | source: {r.source}")
            
    db.close()

if __name__ == "__main__":
    main()
