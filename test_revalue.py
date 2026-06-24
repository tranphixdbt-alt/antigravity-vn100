from valuation.db.session import SessionLocalRead, SessionLocalWrite
from valuation.api.routes.valuation import revalue_ticker
from fastapi.encoders import jsonable_encoder
import json

db_read = SessionLocalRead()
db_write = SessionLocalWrite()

try:
    res = revalue_ticker("VCB", db_read=db_read, db_write=db_write)
    print("Success:")
    print(json.dumps(jsonable_encoder(res), indent=2))
except Exception as e:
    print(f"Exception: {e}")
finally:
    db_read.close()
    db_write.close()
