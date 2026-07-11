import pandas as pd
from vnstock.api.listing import Listing
from vnstock.api.quote import Quote
from vnstock.api.financial import Finance
from vnstock.api.company import Company

class VnstockClient:
    """Wrapper cho vnstock 4.0.4 để lấy dữ liệu với cấu hình source='VCI'"""
    
    def __init__(self):
        self.source = 'VCI'
    
    def get_company_overview(self, symbol: str) -> pd.DataFrame:
        """Lấy thông tin tổng quan công ty"""
        company = Company(source=self.source, symbol=symbol)
        return company.overview()
    
    def get_financials(self, symbol: str, statement_type: str = "BS", period: str = "quarter") -> pd.DataFrame:
        """
        Lấy báo cáo tài chính
        statement_type: 'BS' (Balance Sheet), 'IS' (Income Statement), 'CF' (Cash Flow)
        period: 'quarter' hoặc 'year'
        """
        finance = Finance(source=self.source, symbol=symbol, period=period, get_all=True)
        if statement_type == "BS":
            return finance.balance_sheet()
        elif statement_type == "IS":
            return finance.income_statement()
        elif statement_type == "CF":
            return finance.cash_flow()
        else:
            raise ValueError(f"Unknown statement_type: {statement_type}")

    def get_historical_prices(self, symbol: str, start_date: str) -> pd.DataFrame:
        """Lấy giá lịch sử từ ngày start_date (YYYY-MM-DD)"""
        quote = Quote(source=self.source, symbol=symbol)
        return quote.history(start=start_date)
        
    def get_live_price(self, symbol: str) -> float:
        """Lấy giá thị trường hiện tại (real-time/intraday)"""
        try:
            import datetime
            from vnstock.api.quote import Quote
            # Lấy 7 ngày gần nhất để đảm bảo có dữ liệu
            start_date = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
            df = Quote(source=self.source, symbol=symbol).history(start=start_date)
            if not df.empty and 'close' in df.columns:
                close_val = df.iloc[-1]['close']
                return float(close_val) * 1000.0
        except Exception as e:
            pass
        return 0.0
    
    def get_vn100_symbols(self) -> pd.Series:
        """Lấy danh sách mã VN100"""
        listing = Listing(source=self.source)
        return listing.symbols_by_group('VN100')

vnstock_client = VnstockClient()
