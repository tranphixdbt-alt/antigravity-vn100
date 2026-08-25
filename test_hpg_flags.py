import valuation.engine.batch as batch
from valuation.engine.valuate import valuate
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

db_url = os.getenv("DATABASE_URL_READONLY") or "postgresql://readonly_user:readonly_pass@localhost:5432/vn100"
engine = create_engine(db_url)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

comp = batch.build_company_data(db, "HPG", mode="TTM")
res = valuate(comp)

print("FLAGS:", res.get("flags", []))
print("HARD GATES:", res.get("decision", {}).get("hard_gates_violations", []))
