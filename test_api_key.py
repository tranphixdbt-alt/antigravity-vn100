import vnstock
vnstock.change_api_key('vnstock_18f09cd1b725946b19c537a7c4b23983')

try:
    from vnstock_data.market.market_client import Market
    m = Market()
    df = m.foreign_trade(symbol='REE')
    print("foreign_trade success:")
    print(df.head())
except Exception as e:
    print("Error:", e)
    
try:
    print("Trying via vnstock.api...")
    import vnstock_data
    print("vnstock_data available:", dir(vnstock_data))
except Exception as e:
    print("No vnstock_data:", e)

