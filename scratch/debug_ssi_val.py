import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from valuation.db.session import SessionLocalRead
from valuation.engine.ttm_helper import (
    build_ssi_current_financials,
    get_latest_tpcp_10y,
    estimate_vcb_beta,
)
from valuation.engine.models.securities import SecuritiesValuationModel
from valuation.config import load_defaults

def main():
    db = SessionLocalRead()
    ticker = "SSI"
    
    current_financials = build_ssi_current_financials(db, ticker)
    config_defaults = load_defaults()
    erp_total = config_defaults.get("coe_convention", {}).get("erp_total", 0.082)
    rf_dynamic = get_latest_tpcp_10y(db)
    beta_dynamic = estimate_vcb_beta(db, ticker)
    
    coe = rf_dynamic + beta_dynamic * erp_total
    
    assumptions = {
        'cost_of_equity': coe,
        'long_term_growth': 0.04,
        'market_liquidity_vnd_billion': 18000.0,
        'brokerage_market_share': 0.095,
        'brokerage_margin': 0.0015,
        'margin_loans': 16000.0,
        'net_margin_rate': 0.055,
        'prop_trading_income': 1800.0,
        'opex_ratio': 0.35,
        'tax_rate': 0.20,
        'payout_ratio': 0.20,
        'weight_ri': 0.5,
        'drivers': {
            'brokerage_market_share': {'bump': 0.01},
            'net_margin_rate': {'bump': 0.005}
        }
    }
    
    print("=== SSI DEBUG VALUATION ===")
    print("current_financials:")
    for k, v in current_financials.items():
        print(f"  {k}: {v:,.2f}" if isinstance(v, (int, float)) else f"  {k}: {v}")
        
    print("COE parameters:")
    print(f"  rf: {rf_dynamic:.4f}")
    print(f"  beta: {beta_dynamic:.4f}")
    print(f"  erp: {erp_total:.4f}")
    print(f"  COE: {coe:.4f}")
    
    model = SecuritiesValuationModel(ticker, current_financials, assumptions)
    
    # In forecast_drivers
    fc = model.forecast_drivers()
    print("Forecast drivers:")
    print(f"  terminal_roe: {fc['terminal_roe']:.4%}")
    for f in fc['forecasts']:
        print(f"  Year {f['year']}: net_income={f['net_income']:,.2f}, book_value_start={f['book_value_start']:,.2f}")
        
    # In perform_valuation
    res = model.perform_valuation()
    print("Valuation results:")
    for k, v in res.items():
        print(f"  {k}: {v:,.2f}" if isinstance(v, (int, float)) else f"  {k}: {v}")
        
    db.close()

if __name__ == "__main__":
    main()
