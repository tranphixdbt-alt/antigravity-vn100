import json
from valuation.db.session import SessionLocalRead
from valuation.db.models import FinancialsQuarterly

db = SessionLocalRead()
row = db.query(FinancialsQuarterly).filter(FinancialsQuarterly.ticker == 'FPT', FinancialsQuarterly.fiscal_year == 2023).first()
if row:
    print(json.dumps(list(row.data.keys()), indent=2))
else:
    print("Not found")
