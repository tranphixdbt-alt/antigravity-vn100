import sys
import os
from unittest.mock import MagicMock

class MockSt:
    def __init__(self):
        self.session_state = {}
        self.sidebar = MagicMock()
    def __getattr__(self, name):
        return MagicMock()

sys.modules['streamlit'] = MockSt()
import streamlit as st

import valuation.engine.batch as batch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

db_url = os.getenv("DATABASE_URL_READONLY") or "postgresql://readonly_user:readonly_pass@localhost:5432/vn100"
engine = create_engine(db_url)
Session = sessionmaker(bind=engine)
db = Session()

st.session_state["current_mode"] = "TTM"
st.session_state["company"] = batch.build_company_data(db, "HPG", mode="TTM")
st.session_state["macro_env"] = None
st.session_state["projections"] = None
st.session_state["analyst_scenario"] = "Base"

from valuation.views.results import render_valuation_results

print("Testing HPG rendering...")
try:
    render_valuation_results(st.session_state["company"], db)
    print("HPG rendered successfully without crashing.")
except Exception as e:
    import traceback
    traceback.print_exc()
