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
import traceback

import valuation.engine.batch as batch
from valuation.db.database import get_db_engines, get_db_read, get_db_write

db = get_db_read()

st.session_state["current_mode"] = "TTM"
try:
    st.session_state["company"] = batch.build_company_data(db, "HPG", mode="TTM")
except Exception as e:
    print("Error in build_company_data:")
    traceback.print_exc()

st.session_state["macro_env"] = None
st.session_state["projections"] = None
st.session_state["analyst_scenario"] = "Base"

from valuation.views.results import render_valuation_results
print("Testing render_valuation_results...")
try:
    render_valuation_results(st.session_state["company"], db)
    print("Success")
except Exception as e:
    print("Error in render:")
    traceback.print_exc()
