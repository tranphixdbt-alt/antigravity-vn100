import pandas as pd
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

try:
    from vnstock_data import Market
    HAS_VNSTOCK_DATA = True
except ImportError:
    HAS_VNSTOCK_DATA = False
    logger.warning("Thư viện 'vnstock_data' chưa được cài đặt. Đang sử dụng chế độ MOCK (giả lập dữ liệu) cho dòng tiền.")

class MarketFlowClient:
    """
    Client sử dụng vnstock_data (Sponsor) để lấy dữ liệu dòng tiền khối ngoại và tự doanh.
    Nếu chưa cài đặt vnstock_data, sẽ trả về dữ liệu rỗng hoặc giả lập.
    """
    def __init__(self):
        if HAS_VNSTOCK_DATA:
            self.mkt = Market()
        else:
            self.mkt = None

    def fetch_foreign_flow(self, ticker: str, start: str, end: str = None) -> pd.DataFrame:
        """
        Lấy dữ liệu mua bán ròng khối ngoại.
        Trả về DataFrame với các cột: time, buy_vol, buy_val, sell_vol, sell_val, net_vol, net_val.
        """
        if not HAS_VNSTOCK_DATA:
            logger.info(f"[MOCK] Lấy dữ liệu khối ngoại cho {ticker} từ {start}")
            # Trả về DF rỗng với cấu trúc chuẩn
            return pd.DataFrame(columns=['time', 'buy_vol', 'buy_val', 'sell_vol', 'sell_val', 'net_vol', 'net_val'])
            
        try:
            # Tham khảo schema từ docs
            df = self.mkt.equity(ticker).foreign_flow(start=start, end=end, interval='1D')
            if df is not None and not df.empty:
                df['time'] = pd.to_datetime(df['time']).dt.date
            return df
        except Exception as e:
            logger.error(f"Lỗi khi lấy foreign_flow cho {ticker}: {e}")
            return pd.DataFrame()

    def fetch_proprietary_flow(self, ticker: str, start: str, end: str = None) -> pd.DataFrame:
        """
        Lấy dữ liệu mua bán ròng tự doanh.
        Trả về DataFrame với các cột: time, buy_vol, buy_val, sell_vol, sell_val, net_vol, net_val.
        """
        if not HAS_VNSTOCK_DATA:
            logger.info(f"[MOCK] Lấy dữ liệu tự doanh cho {ticker} từ {start}")
            return pd.DataFrame(columns=['time', 'buy_vol', 'buy_val', 'sell_vol', 'sell_val', 'net_vol', 'net_val'])
            
        try:
            df = self.mkt.equity(ticker).proprietary_flow(start=start, end=end, interval='1D')
            if df is not None and not df.empty:
                df['time'] = pd.to_datetime(df['time']).dt.date
            return df
        except Exception as e:
            logger.error(f"Lỗi khi lấy proprietary_flow cho {ticker}: {e}")
            return pd.DataFrame()

market_client = MarketFlowClient()
