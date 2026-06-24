import pandas as pd
from valuation.ingest.normalizer import normalize_daily_prices, unpivot_financials

def test_normalize_daily_prices():
    # Input mockup
    data = {
        'time': ['2026-01-01', '2026-01-02'],
        'open': [56.29, 55.0],
        'high': [57.0, 56.1],
        'low': [55.1, 54.0],
        'close': [56.29, 55.5],
        'volume': [1000, 2000]
    }
    df = pd.DataFrame(data)
    df_norm = normalize_daily_prices(df)
    
    assert df_norm.iloc[0]['open'] == 56290.0
    assert df_norm.iloc[0]['close'] == 56290.0
    assert df_norm.iloc[1]['high'] == 56100.0
    assert df_norm.iloc[1]['low'] == 54000.0
    assert df_norm.iloc[0]['volume'] == 1000  # volume ko doi
    assert 'price_unit' in df_norm.columns
    assert df_norm.iloc[0]['price_unit'] == 'VND'

def test_unpivot_financials():
    data = {
        'item': ['Tiền mặt', 'Tài sản cố định'],
        'item_en': ['Cash', 'Fixed Assets'],
        'item_id': ['cash', 'fixed_assets'],
        '2024-Q1': [1000.0, 5000.0],
        '2023-Q4': [900.0, 4800.0]
    }
    df_wide = pd.DataFrame(data)
    
    df_long = unpivot_financials(df_wide, "BS")
    
    # Kì vọng: 2 dòng * 2 quý = 4 dòng
    assert len(df_long) == 4
    
    # Test cash quý 1/2024
    cash_2024q1 = df_long[(df_long['line_item'] == 'cash') & 
                          (df_long['fiscal_year'] == 2024) & 
                          (df_long['fiscal_quarter'] == 1)]
    assert len(cash_2024q1) == 1
    assert cash_2024q1.iloc[0]['value'] == 1000.0
    assert cash_2024q1.iloc[0]['statement'] == 'BS'
    assert cash_2024q1.iloc[0]['is_consolidated'] == True
    assert cash_2024q1.iloc[0]['is_restated'] == False
