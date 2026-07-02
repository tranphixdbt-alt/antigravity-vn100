import sys
import os
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(".env")
db_url = os.getenv("DATABASE_URL_READONLY") or "postgresql://readonly_user:readonly_pass@localhost:5432/vn100"
engine = create_engine(db_url)
Session = sessionmaker(bind=engine)
session = Session()

from valuation.data_access.repo import build_company_data
from valuation.engine.sensitivity import run_valuation_engine

company = build_company_data(session, "FPT", mode="TTM")
intrinsic_fv, relative_fv = run_valuation_engine(company)
print(f"run_valuation_engine output: Intrinsic FV: {intrinsic_fv}, Relative FV: {relative_fv}")
