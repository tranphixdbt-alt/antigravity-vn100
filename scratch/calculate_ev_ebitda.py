import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from sqlalchemy import text
from valuation.db.session import engine_read, SessionLocalRead
from valuation.engine.ttm_helper import get_shares_outstanding

def calculate_ev_ebitda_percentiles(ticker):
    conn = engine_read.connect()
    
    # 1. Lấy giá lịch sử
    query_prices = text("SELECT trade_date, close FROM prices_daily WHERE ticker = :ticker ORDER BY trade_date")
    df_prices = pd.read_sql(query_prices, conn, params={"ticker": ticker})
    if df_prices.empty:
        print(f"No price data for {ticker}")
        conn.close()
        return
        
    # 2. Lấy BCTC lịch sử
    query_fin = text("""
        SELECT fiscal_year, fiscal_quarter, line_item, value 
        FROM financials_quarterly 
        WHERE ticker = :ticker 
        ORDER BY fiscal_year, fiscal_quarter
    """)
    df_fin = pd.read_sql(query_fin, conn, params={"ticker": ticker})
    if df_fin.empty:
        print(f"No financial data for {ticker}")
        conn.close()
        return
        
    try:
        db = SessionLocalRead()
        shares = get_shares_outstanding(db, ticker)
        db.close()
    except Exception as e:
        print(f"Error getting shares: {e}")
        conn.close()
        return
        
    periods = df_fin[['fiscal_year', 'fiscal_quarter']].drop_duplicates().values
    
    quarterly_metrics = []
    for yr, q in periods:
        if q == 0: continue
        
        # 4 quý gần nhất
        sub_quarters = []
        cyr, cq = yr, q
        for _ in range(4):
            sub_quarters.append((cyr, cq))
            cq -= 1
            if cq == 0:
                cq = 4
                cyr -= 1
                
        # Tổng hợp EBITDA TTM
        ebitda_vals = []
        for syr, sq in sub_quarters:
            # ebitda
            val_eb = df_fin[(df_fin['fiscal_year'] == syr) & (df_fin['fiscal_quarter'] == sq) & 
                            (df_fin['line_item'].str.lower() == 'ebitda')]['value']
            if not val_eb.empty:
                ebitda_vals.append(float(val_eb.iloc[0]))
            else:
                # EBIT + D&A fallback
                op_val = df_fin[(df_fin['fiscal_year'] == syr) & (df_fin['fiscal_quarter'] == sq) & 
                                (df_fin['line_item'].str.contains('operating_profit_loss|Lợi nhuận từ hoạt động kinh doanh', case=False, na=False))]['value']
                depr_val = df_fin[(df_fin['fiscal_year'] == syr) & (df_fin['fiscal_quarter'] == sq) & 
                                 (df_fin['line_item'].str.contains('depreciation_and_amortization|Khấu hao', case=False, na=False))]['value']
                op = float(op_val.iloc[0]) if not op_val.empty else 0.0
                depr = float(depr_val.iloc[0]) if not depr_val.empty else 0.0
                if op > 0 or depr > 0:
                    ebitda_vals.append(op + depr)
                else:
                    # fallback net income * 1.2
                    ni_val = df_fin[(df_fin['fiscal_year'] == syr) & (df_fin['fiscal_quarter'] == sq) & 
                                    (df_fin['line_item'].str.contains('net_profit_loss_after_tax|Lợi nhuận sau thuế', case=False, na=False))]['value']
                    if not ni_val.empty:
                        ebitda_vals.append(float(ni_val.iloc[0]) * 1.2)
                        
        if len(ebitda_vals) < 4:
            continue
            
        ebitda_ttm = sum(ebitda_vals)
        
        # Debt và Cash tại quý này
        cash_val = df_fin[(df_fin['fiscal_year'] == yr) & (df_fin['fiscal_quarter'] == q) & 
                          (df_fin['line_item'].str.contains('cash_and_cash_equivalents|Tiền và các khoản tương đương tiền', case=False, na=False))]['value']
        
        # HPG: thêm short_term_financial_investments
        st_invest_val = df_fin[(df_fin['fiscal_year'] == yr) & (df_fin['fiscal_quarter'] == q) & 
                               (df_fin['line_item'].str.contains('short_term_financial_investments|Đầu tư tài chính ngắn hạn', case=False, na=False))]['value']
        
        st_borrow = df_fin[(df_fin['fiscal_year'] == yr) & (df_fin['fiscal_quarter'] == q) & 
                           (df_fin['line_item'].str.contains('short_term_borrowings|Vay ngắn hạn', case=False, na=False))]['value']
        lt_borrow = df_fin[(df_fin['fiscal_year'] == yr) & (df_fin['fiscal_quarter'] == q) & 
                           (df_fin['line_item'].str.contains('long_term_borrowings|Vay dài hạn', case=False, na=False))]['value']
                           
        cash = float(cash_val.iloc[0]) if not cash_val.empty else 0.0
        if ticker == "HPG" and not st_invest_val.empty:
            cash += float(st_invest_val.iloc[0])
            
        debt = (float(st_borrow.iloc[0]) if not st_borrow.empty else 0.0) + (float(lt_borrow.iloc[0]) if not lt_borrow.empty else 0.0)
        
        # Ngày kết thúc quý (xấp xỉ)
        if q == 1: end_date = pd.Timestamp(f"{yr}-03-31")
        elif q == 2: end_date = pd.Timestamp(f"{yr}-06-30")
        elif q == 3: end_date = pd.Timestamp(f"{yr}-09-30")
        else: end_date = pd.Timestamp(f"{yr}-12-31")
        
        quarterly_metrics.append({
            "end_date": end_date,
            "ebitda_ttm": ebitda_ttm,
            "cash": cash,
            "debt": debt
        })
        
    df_metrics = pd.DataFrame(quarterly_metrics)
    if df_metrics.empty:
        print(f"No metric data for {ticker}")
        conn.close()
        return
        
    df_metrics = df_metrics.sort_values("end_date")
    
    ev_ebitda_list = []
    df_prices['trade_date'] = pd.to_datetime(df_prices['trade_date'])
    for _, row in df_prices.iterrows():
        t_date = row['trade_date']
        close = float(row['close'])
        
        past_metrics = df_metrics[df_metrics['end_date'] <= t_date]
        if past_metrics.empty:
            metric = df_metrics.iloc[0]
        else:
            metric = past_metrics.iloc[-1]
            
        ebitda_ttm = metric['ebitda_ttm']
        cash = metric['cash']
        debt = metric['debt']
        
        # EV = close * shares + debt - cash
        ev = close * shares + debt - cash
        if ebitda_ttm > 0 and ev > 0:
            ev_ebitda_list.append(ev / ebitda_ttm)
            
    if ev_ebitda_list:
        ev_10 = np.percentile(ev_ebitda_list, 10)
        ev_90 = np.percentile(ev_ebitda_list, 90)
        print(f"Ticker: {ticker} | EV/EBITDA: 10% = {ev_10:.2f}x, 90% = {ev_90:.2f}x")
    else:
        print(f"Ticker: {ticker} | EV/EBITDA: N/A")
        
    conn.close()

if __name__ == "__main__":
    for ticker in ["FPT", "HPG"]:
        calculate_ev_ebitda_percentiles(ticker)
