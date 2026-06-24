from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import datetime
from valuation.db.session import get_read_db, get_write_db
from valuation.db.models import FinancialsQuarterly, PricesDaily, ValuationSensitivity, Ticker, ValuationOutput
from valuation.engine.consensus_helper import get_consensus_stats
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
    
    # Generic assumptions / special flows for FPT, HPG, SSI, DGC
    if ticker in ["FPT", "HPG", "SSI", "DGC"]:
        from valuation.engine.ttm_helper import (
            build_fpt_current_financials,
            build_hpg_current_financials,
            build_ssi_current_financials,
            build_dgc_current_financials,
            get_latest_tpcp_10y,
            estimate_vcb_beta,
        )
        from valuation.config import load_defaults
        import yaml
        
        # 1. Trích xuất financials thật từ DB
        if ticker == "FPT":
            current_financials = build_fpt_current_financials(db_read, ticker)
        elif ticker == "HPG":
            current_financials = build_hpg_current_financials(db_read, ticker)
        elif ticker == "DGC":
            current_financials = build_dgc_current_financials(db_read, ticker)
        else: # SSI
            current_financials = build_ssi_current_financials(db_read, ticker)
            
        current_financials['current_price'] = curr_price
        
        # 2. Xây dựng assumptions động từ nguyên tắc
        config_defaults = load_defaults()
        erp_total = config_defaults.get("coe_convention", {}).get("erp_total", 0.082)
        rf_dynamic = get_latest_tpcp_10y(db_read)
        beta_dynamic = estimate_vcb_beta(db_read, ticker)
        
        coe = rf_dynamic + beta_dynamic * erp_total
        # Sanity floor cho COE
        if coe < rf_dynamic + 0.05:
            raise ValueError("COE_TOO_LOW")
            
        # Tính WACC động cho phi tài chính
        wacc = None
        if ticker in ["FPT", "HPG", "DGC"]:
            E = float(current_financials['total_equity'])
            D = float(current_financials['total_debt'])
            tax_rate = 0.20 if ticker in ["HPG", "DGC"] else 0.10
            cod = rf_dynamic + 0.03
            if E + D > 0:
                wacc = coe * (E / (E + D)) + cod * (1 - tax_rate) * (D / (E + D))
            else:
                wacc = coe
            wacc = max(wacc, rf_dynamic + 0.03)
            
        # Thiết lập assumptions cho từng mã
        if ticker == "FPT":
            assumptions = {
                'cost_of_equity': coe,
                'wacc': wacc,
                'revenue_growth_1_to_3': 0.18,
                'revenue_growth_4_to_5': 0.15,
                'ebit_margin': 0.16,
                'tax_rate': 0.10,
                'reinvestment_rate': 0.35,
                'target_ev_ebitda': 13.0,
                'long_term_growth': 0.05,
                'weight_dcf': 0.5,
                'drivers': {
                    'revenue_growth_1_to_3': {'bump': 0.01},
                    'ebit_margin': {'bump': 0.01},
                    'wacc': {'bump': 0.005}
                }
            }
            model = DCFValuationModel(ticker, current_financials, assumptions)
        elif ticker == "HPG":
            assumptions = {
                'cost_of_equity': coe,
                'wacc': wacc,
                'revenue_growth_1_to_3': 0.12,
                'revenue_growth_4_to_5': 0.08,
                'ebit_margin': 0.11,
                'tax_rate': 0.20,
                'reinvestment_rate': 0.50,
                'target_ev_ebitda': 7.0,
                'long_term_growth': 0.03,
                'weight_dcf': 0.5,
                'drivers': {
                    'revenue_growth_1_to_3': {'bump': 0.01},
                    'ebit_margin': {'bump': 0.01},
                    'wacc': {'bump': 0.005}
                }
            }
            model = DCFValuationModel(ticker, current_financials, assumptions)
        elif ticker == "DGC":
            assumptions = {
                'cost_of_equity': coe,
                'wacc': wacc,
                'revenue_growth_1_to_3': 0.15,
                'revenue_growth_4_to_5': 0.10,
                'ebit_margin': 0.22,
                'tax_rate': 0.20,
                'reinvestment_rate': 0.35,
                'target_ev_ebitda': 8.0,
                'long_term_growth': 0.04,
                'weight_dcf': 0.5,
                'drivers': {
                    'revenue_growth_1_to_3': {'bump': 0.01},
                    'ebit_margin': {'bump': 0.01},
                    'wacc': {'bump': 0.005}
                }
            }
            model = DCFValuationModel(ticker, current_financials, assumptions)
        else: # SSI
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
            model = SecuritiesValuationModel(ticker, current_financials, assumptions)
            
        try:
            full_valuation = model.perform_valuation()
            val_result = model.calculate_greeks() 
            blended_fvps = float(val_result['base_fair_value'])
            greeks = {k: float(v) if v is not None else None for k, v in val_result['greeks'].items()}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
            
        # 3. Tầng 1 — Reverse Sanity
        net_income_ttm = float(current_financials['net_income'])
        total_equity = float(current_financials['total_equity'])
        shares = float(current_financials['shares_outstanding'])
        
        eps_ttm = net_income_ttm / shares if shares > 0 else 0.0
        bvps_ttm = total_equity / shares if shares > 0 else 0.0
        
        implied_pe = blended_fvps / eps_ttm if eps_ttm > 0 else None
        implied_pb = blended_fvps / bvps_ttm if bvps_ttm > 0 else None
        
        implied_ev_ebitda = None
        if ticker in ["FPT", "HPG"]:
            ebitda_ttm = float(current_financials['ebitda'])
            total_debt = float(current_financials['total_debt'])
            cash = float(current_financials['cash_and_equivalents'])
            
            implied_ev = blended_fvps * shares + total_debt - cash
            implied_ev_ebitda = implied_ev / ebitda_ttm if ebitda_ttm > 0 else None
            
        from valuation.config import PROJECT_ROOT
        benchmarks_path = PROJECT_ROOT / "config" / "valuation_benchmarks.yaml"
        benchmarks_config = {}
        if benchmarks_path.exists():
            with open(benchmarks_path, "r", encoding="utf-8") as f:
                benchmarks_config = yaml.safe_load(f).get("benchmarks", {}).get(ticker, {})
                
        # Gắn cờ Tầng 1
        flags = []
        if implied_pe is not None:
            if implied_pe < 4.0 or implied_pe > 50.0:
                flags.append("IMPLIED_PE_OUT_OF_BOUNDS_EXTREME")
            pe_bench = benchmarks_config.get("pe", {})
            if pe_bench:
                low = pe_bench.get("low")
                high = pe_bench.get("high")
                if low is not None and implied_pe < low:
                    flags.append("IMPLIED_PE_OUT_OF_BOUNDS")
                elif high is not None and implied_pe > high:
                    flags.append("IMPLIED_PE_OUT_OF_BOUNDS")
                    
        if implied_pb is not None:
            pb_bench = benchmarks_config.get("pb", {})
            if pb_bench:
                low = pb_bench.get("low")
                high = pb_bench.get("high")
                if low is not None and implied_pb < low:
                    flags.append("IMPLIED_PB_OUT_OF_BOUNDS")
                elif high is not None and implied_pb > high:
                    flags.append("IMPLIED_PB_OUT_OF_BOUNDS")
                    
        if implied_ev_ebitda is not None:
            ev_bench = benchmarks_config.get("ev_ebitda", {})
            if ev_bench:
                low = ev_bench.get("low")
                high = ev_bench.get("high")
                if low is not None and implied_ev_ebitda < low:
                    flags.append("IMPLIED_EV_EBITDA_OUT_OF_BOUNDS")
                elif high is not None and implied_ev_ebitda > high:
                    flags.append("IMPLIED_EV_EBITDA_OUT_OF_BOUNDS")
                    
        # 4. Tầng 2 — Consensus Check
        eval_date = latest_price.trade_date if latest_price else datetime.date.today()
        consensus_stats = get_consensus_stats(ticker, eval_date, db_read)
        consensus_median = consensus_stats["median"]
        consensus_mean = consensus_stats["mean"]
        consensus_count = consensus_stats["count"]
        
        deviation_pct = None
        if consensus_median is not None:
            deviation_pct = (blended_fvps - consensus_median) / consensus_median
            if abs(deviation_pct) > 0.25:
                flags.append("CONSENSUS_DEVIATION_HIGH")
                
        # QC Checks
        qc_result = run_qc_checks(
            ticker=ticker,
            sector_name=t.sector if t.sector else 'Unknown',
            financials=df_fin,
            market_cap=curr_price * shares
        )
        qc_flags = qc_result.get("flags", [])
        
        # Append các cờ của Tầng 1 và Tầng 2 vào qc_flags
        for flg in flags:
            if flg not in qc_flags:
                qc_flags.append(flg)
                
        if any(v is None for v in greeks.values()):
            if "SENSITIVITY_FAILED" not in qc_flags:
                qc_flags.append("SENSITIVITY_FAILED")
                
        # In bảng tổng hợp
        print(f"\n========================================================")
        print(f" BẢNG TỔNG HỢP KIỂM ĐỊNH ĐỊNH GIÁ (3 TẦNG) - {ticker}")
        print(f"========================================================")
        print(f"Giá thị trường hiện tại: {curr_price:,.0f} VND")
        print(f"Giá trị hợp lý (Base FV): {blended_fvps:,.0f} VND")
        print(f"P/E ngụ ý (Implied P/E): {f'{implied_pe:.2f}x' if implied_pe else 'N/A'}")
        print(f"P/B ngụ ý (Implied P/B): {f'{implied_pb:.2f}x' if implied_pb else 'N/A'}")
        print(f"EV/EBITDA ngụ ý: {f'{implied_ev_ebitda:.2f}x' if implied_ev_ebitda else 'N/A'}")
        if consensus_median is not None:
            print(f"Consensus trung vị: {consensus_median:,.0f} VND (lệch: {deviation_pct:+.2%})")
            print(f"Consensus trung bình: {consensus_mean:,.0f} VND (Số báo cáo: {consensus_count})")
        else:
            print(f"Consensus trung vị: N/A")
        print(f"Cảnh báo (Flags): {', '.join(qc_flags) if qc_flags else 'Không có (PASS)'}")
        print(f"========================================================\n")
        
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
            "qc": {
                **qc_result,
                "flags": qc_flags
            }
        }
        
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
        assumptions['brokerage_market_share'] = 0.10
        assumptions['net_margin_rate'] = 0.05
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
