from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from valuation.db.session import get_read_db, get_write_db
from valuation.db.models import FinancialsQuarterly, PricesDaily, ValuationSensitivity, Ticker, ValuationOutput
from valuation.engine.models.bank_vcb import VCBValuationModel
from valuation.engine.models.dcf import DCFValuationModel
from valuation.engine.models.rnav import RNAVValuationModel
from valuation.engine.models.securities import SecuritiesValuationModel
from valuation.engine.models.sotp import SOTPValuationModel
from valuation.quality.bank_metrics import _get_val
import pandas as pd
from valuation.quality.scores import run_qc_checks

router = APIRouter(prefix="/valuation", tags=["valuation"])

@router.post("/revalue/{ticker}")
def revalue_ticker(ticker: str, db_read: Session = Depends(get_read_db), db_write: Session = Depends(get_write_db)):
    # 1. Verify ticker
    t = db_read.query(Ticker).filter(Ticker.ticker == ticker).first()
    if not t:
        raise HTTPException(status_code=404, detail="Ticker not found")
        
    # 2. Get financials (simplification: get all and convert to pandas)
    fin_records = db_read.query(FinancialsQuarterly).filter(FinancialsQuarterly.ticker == ticker).all()
    # Temporarily bypassed for pilot testing without data
    # if not fin_records:
    #     raise HTTPException(status_code=404, detail="No financials found")
        
    fin_data = [{
        "fiscal_year": r.fiscal_year,
        "fiscal_quarter": r.fiscal_quarter,
        "line_item": r.line_item,
        "value": r.value
    } for r in fin_records]
    
    df_fin = pd.DataFrame(fin_data, columns=["fiscal_year", "fiscal_quarter", "line_item", "value"])
    
    # 3. Get latest price
    latest_price = db_read.query(PricesDaily).filter(PricesDaily.ticker == ticker).order_by(PricesDaily.trade_date.desc()).first()
    curr_price = float(latest_price.close) if latest_price else 0.0
    
    # Get latest year data
    latest_year = df_fin['fiscal_year'].max() if not df_fin.empty else 0
    curr_period = (latest_year, 0) # Use annual if available, or just the latest year's metrics
    
    # Check if annual exists, if not maybe sum quarters? For now, assume data has annual (quarter=0) or we just pick latest Q for BS
    if not df_fin.empty:
        sub_df = df_fin[df_fin['fiscal_year'] == latest_year]
        if 0 in sub_df['fiscal_quarter'].values:
            curr_period = (latest_year, 0)
        else:
            latest_q = sub_df['fiscal_quarter'].max()
            curr_period = (latest_year, latest_q)
        
    # Build current_financials dict (Mocking some missing mapping fields for G2)
    current_financials = {
        'total_equity': _get_val(df_fin, ["Vốn chủ sở hữu"], curr_period),
        'total_assets': _get_val(df_fin, ["Tổng tài sản"], curr_period),
        'customer_loans': _get_val(df_fin, ["Cho vay khách hàng"], curr_period),
        'customer_deposits': _get_val(df_fin, ["Tiền gửi của khách hàng", "Tiền gửi theo loại hình"], curr_period),
        'net_income': _get_val(df_fin, ["Lợi nhuận sau thuế"], curr_period),
        'total_revenue': _get_val(df_fin, ["Doanh thu thuần", "Thu nhập lãi thuần"], curr_period), # Basic fallback
        'total_debt': _get_val(df_fin, ["Vay và nợ thuê tài chính"], curr_period),
        'cash_and_equivalents': _get_val(df_fin, ["Tiền và các khoản tương đương tiền"], curr_period),
        'shares_outstanding': 1.0e9, # Placeholder
        'current_price': curr_price
    }
    
    # Routing Logic (Factory)
    if ticker == "VCB":
        # --- Dùng TTM Helper lấy dữ liệu thật từ DB ---
        from valuation.engine.ttm_helper import (
            build_vcb_current_financials,
            build_vcb_assumptions_from_history,
        )
        current_financials = build_vcb_current_financials(db_read, ticker)
        current_financials['current_price'] = curr_price

        assumptions = build_vcb_assumptions_from_history(db_read, ticker)

        model = VCBValuationModel(current_financials, assumptions)
        try:
            full_valuation = model.blend_valuation()
            blended_fvps = float(full_valuation['blended_fair_value_per_share'])
            greeks = {k: float(v) if v is not None else None for k, v in model.calculate_greeks()['greeks'].items()}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        
        # QC Checks
        qc_result = run_qc_checks(
            ticker=ticker,
            sector_name=t.sector if t.sector else 'Unknown',
            financials=df_fin,
            market_cap=curr_price * current_financials['shares_outstanding']
        )
        qc_flags = qc_result.get("flags", [])
        
        if any(v is None for v in greeks.values()):
            if "SENSITIVITY_FAILED" not in qc_flags:
                qc_flags.append("SENSITIVITY_FAILED")
        
        from valuation.analysis.macro_radar import capture_macro_snapshot
        macro_snap = capture_macro_snapshot(t.sector if t.sector else 'Unknown', db_read)

        # Save to DB
        out_record = ValuationOutput(
            ticker=ticker,
            blended_fair_value_per_share=blended_fvps,
            flags=qc_flags,
            macro_snapshot=macro_snap
        )
        db_write.add(out_record)
        db_write.commit()
        db_write.refresh(out_record)
        
        for d, dfv in greeks.items():
            db_write.add(ValuationSensitivity(
                ticker=ticker, assumption_version=out_record.id, driver_code=d, dFV_ddriver=dfv
            ))
        db_write.commit()
        
        return {"ticker": ticker, "current_price": curr_price, "valuation": full_valuation, "greeks": greeks, "qc": qc_result}
    
    # Generic assumptions for others
    assumptions = {
        'cost_of_equity': 0.13,
        'wacc': 0.11,
        'long_term_growth': 0.05,
        'drivers': {
            'revenue_growth_1_to_3': {'bump': 0.01},
            'ebit_margin': {'bump': 0.01},
            'wacc': {'bump': 0.005}
        }
    }
    
    if ticker in ["FPT", "HPG", "VNM", "GAS"]:
        model = DCFValuationModel(ticker, current_financials, assumptions)
    elif ticker == "VHM":
        model = RNAVValuationModel(ticker, current_financials, assumptions)
    elif ticker == "SSI":
        assumptions['drivers'] = {'brokerage_market_share': {'bump': 0.01}, 'net_margin_rate': {'bump': 0.005}}
        model = SecuritiesValuationModel(ticker, current_financials, assumptions)
    elif ticker == "MSN":
        assumptions['drivers'] = {'wcm_target_ev_sales': {'bump': 0.1}, 'mch_target_ev_ebitda': {'bump': 1.0}}
        model = SOTPValuationModel(ticker, current_financials, assumptions)
    else:
        raise HTTPException(status_code=400, detail=f"No valuation model implemented for ticker {ticker}")
        
    try:
        full_valuation = model.perform_valuation()
        val_result = model.calculate_greeks() 
        blended_fvps = float(val_result['base_fair_value'])
        greeks = {k: float(v) if v is not None else None for k, v in val_result['greeks'].items()}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    # QC Checks
    qc_result = run_qc_checks(
        ticker=ticker,
        sector_name=t.sector if t.sector else 'Unknown',
        financials=df_fin,
        market_cap=curr_price * current_financials['shares_outstanding']
    )
    qc_flags = qc_result.get("flags", [])
    
    if any(v is None for v in greeks.values()):
        if "SENSITIVITY_FAILED" not in qc_flags:
            qc_flags.append("SENSITIVITY_FAILED")
    
    from valuation.analysis.macro_radar import capture_macro_snapshot
    macro_snap = capture_macro_snapshot(t.sector if t.sector else 'Unknown', db_read)

    # Save to DB
    out_record = ValuationOutput(
        ticker=ticker,
        blended_fair_value_per_share=blended_fvps,
        fair_value_bull=float(full_valuation['bull_fair_value']) if full_valuation.get('bull_fair_value') is not None else None,
        fair_value_bear=float(full_valuation['bear_fair_value']) if full_valuation.get('bear_fair_value') is not None else None,
        flags=qc_flags,
        macro_snapshot=macro_snap
    )
    db_write.add(out_record)
    db_write.commit()
    db_write.refresh(out_record)
    
    for d, dfv in greeks.items():
        db_write.add(ValuationSensitivity(
            ticker=ticker, assumption_version=out_record.id, driver_code=d, dFV_ddriver=dfv
        ))
    db_write.commit()
        
    return {
        "ticker": ticker,
        "current_price": curr_price,
        "valuation": full_valuation,
        "greeks": greeks,
        "qc": qc_result
    }
