import os
import sys

# Đảm bảo đường dẫn project đúng
sys.path.append(os.getcwd())

from valuation.db.session import SessionLocalWrite
from valuation.engine.valuate import valuate
from valuation.data_access.repo import build_company_data
from valuation.models.macro_env import MacroEnvironment

def test_valuation(ticker, macro_env=None):
    db = SessionLocalWrite()
    try:
        company = build_company_data(db, ticker, mode="TTM")
        res = valuate(company, macro_env=macro_env)
        print(f"--- {ticker} Valuation (Stressed: {macro_env.is_macro_stressed if macro_env else False}) ---")
        print(f"Fair Value: {res['blended_fair_value_per_share']:.0f}")
        print(f"Recommendation: {res['recommendation']}")
        if res.get('decision'):
            print(f"Target MOS: {res['decision']['target_mos'] * 100:.1f}%")
            print(f"Hard Gates: {res['decision']['hard_gates_violations']}")
        print(f"Upside: {res['upside'] * 100:.2f}%")
        print()
    finally:
        db.close()

if __name__ == "__main__":
    normal_env = MacroEnvironment(inflation_rate=0.03, sbv_stance="Neutral")
    stressed_env = MacroEnvironment(inflation_rate=0.06, sbv_stance="Tightening")

    test_valuation("FPT", normal_env)
    test_valuation("FPT", stressed_env)

    test_valuation("HPG", normal_env)
    test_valuation("HPG", stressed_env)
