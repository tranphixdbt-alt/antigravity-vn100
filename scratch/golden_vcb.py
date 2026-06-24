import sys
from valuation.db.session import SessionLocalWrite
from valuation.api.routes.valuation import revalue_ticker

db = SessionLocalWrite()
try:
    res = revalue_ticker("VCB", db, db)
    print("Golden Test VCB Result:")
    print("Base FV:", res["valuation"]["blended_fair_value_per_share"])
    print("RI FV:", res["valuation"]["ri_fvps"])
    print("PB FV:", res["valuation"]["pb_fvps"])
except Exception as e:
    print("Error:", e)
finally:
    db.close()
