from valuation.db.session import SessionLocalRead
from valuation.data_access.repo import build_company_data
db = SessionLocalRead()
company = build_company_data(db, 'FPT')
for bs in company.historical_bs:
    diff = abs(bs.total_assets - bs.total_liabilities_and_equity)
    if diff > 0.05:
        print(f"Year {bs.year}: diff = {diff}")
