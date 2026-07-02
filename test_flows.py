import pandas as pd
from datetime import datetime, timedelta
from valuation.db.session import SessionLocalWrite
from valuation.db.models import PricesDaily
from valuation.ingest.pipeline import upsert_market_flows

def test_upsert():
    print("Testing upsert_market_flows...")
    ticker = "REE"
    today = datetime.now()
    dates = [today - timedelta(days=i) for i in range(5)]
    
    # Tạo mock data foreign flow
    df_foreign = pd.DataFrame({
        'time': dates,
        'buy_vol': [1000]*5,
        'buy_val': [50000]*5,
        'sell_vol': [500]*5,
        'sell_val': [25000]*5,
        'net_vol': [500]*5,
        'net_val': [11_000_000_000]*5 # 11 tỷ mỗi ngày -> 5 ngày 55 tỷ
    })
    
    # Tạo mock data prop flow
    df_prop = pd.DataFrame({
        'time': dates,
        'buy_vol': [2000]*5,
        'buy_val': [100000]*5,
        'sell_vol': [1000]*5,
        'sell_val': [50000]*5,
        'net_vol': [1000]*5,
        'net_val': [5_000_000_000]*5 # 5 tỷ mỗi ngày -> 5 ngày 25 tỷ
    })
    
    # Upsert
    upsert_market_flows(ticker, df_foreign, df_prop)
    print("Upsert completed.")
    
    # Validate in DB
    db = SessionLocalWrite()
    records = db.query(PricesDaily).filter(PricesDaily.ticker == ticker).limit(5).all()
    print(f"Found {len(records)} records for {ticker}")
    for r in records:
        print(f"Date: {r.trade_date}, F_Net_Val: {r.foreign_net_val}, P_Net_Val: {r.proprietary_net_val}")
    db.close()

    # Test scoring logic
    from valuation.engine.daily_signal import calculate_daily_signal
    res = calculate_daily_signal(ticker, force_override=True)
    print("Signal flags:", res.get('flags'))
    print("Confidence:", res.get('confidence'))

if __name__ == "__main__":
    test_upsert()
