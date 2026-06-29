import pandas as pd
import re

def normalize_daily_prices(df: pd.DataFrame) -> pd.DataFrame:
    """
    Chuẩn hóa giá daily từ vnstock.
    vnstock trả giá ở đơn vị nghìn VND (ví dụ: 56.29 = 56,290 VND).
    Hàm này nhân các cột giá với 1000 để chuẩn hóa về VND tuyệt đối, khớp với BCTC.
    """
    if df.empty:
        return df
    
    # Các cột cần nhân x1000
    price_cols = ['open', 'high', 'low', 'close']
    
    # Tạo bản sao để tránh DtypeWarning hoặc SettingWithCopyWarning
    df_norm = df.copy()
    
    for col in price_cols:
        if col in df_norm.columns:
            df_norm[col] = df_norm[col] * 1000.0
            
    # Thêm cột price_unit để rõ ràng
    df_norm['price_unit'] = 'VND'
    
    return df_norm

def unpivot_financials(df_wide: pd.DataFrame, statement_type: str) -> pd.DataFrame:
    """
    Unpivot (melt) BCTC từ dạng wide (quý làm cột) sang dạng long.
    df_wide có các cột như: 'item', 'item_en', 'item_id', '2024-Q1', '2023-Q4'...
    Đầu ra sẽ có: 'line_item', 'fiscal_year', 'fiscal_quarter', 'value', 'statement'.
    """
    if df_wide.empty:
        return pd.DataFrame()
    
    id_vars = ['item_id']
    
    # Tìm các cột là quý (format: YYYY-QX) hoặc năm (format: YYYY)
    value_vars = [c for c in df_wide.columns if re.match(r'^\d{4}(-Q\d)?$', str(c))]
    
    df_long = df_wide.melt(id_vars=id_vars, value_vars=value_vars, 
                           var_name='period', value_name='value')
    
    # Đổi tên 'item_id' thành 'line_item'
    df_long = df_long.rename(columns={'item_id': 'line_item'})
    
    # Loại bỏ giá trị NA
    df_long = df_long.dropna(subset=['value'])
    
    # Parse period -> fiscal_year, fiscal_quarter
    df_long['fiscal_year'] = df_long['period'].str[:4].astype(int)
    
    def parse_quarter(p):
        if '-Q' in p:
            return int(p[-1])
        return 0  # 0 indicates Full Year data
        
    df_long['fiscal_quarter'] = df_long['period'].apply(parse_quarter)
    
    df_long['statement'] = statement_type
    df_long['is_consolidated'] = True # Ưu tiên lấy hợp nhất từ vnstock
    df_long['is_restated'] = False # Hiện vnstock không tách bạch
    df_long['currency'] = 'VND'
    
    # Chỉ giữ các cột cần thiết
    cols_to_keep = ['fiscal_year', 'fiscal_quarter', 'is_consolidated', 
                    'is_restated', 'statement', 'line_item', 'value', 'currency']
    
    df_long = df_long[cols_to_keep]
    # Bỏ các dòng trùng lặp dựa trên khóa chính
    df_long = df_long.drop_duplicates(
        subset=['fiscal_year', 'fiscal_quarter', 'is_consolidated', 'is_restated', 'statement', 'line_item'],
        keep='last'
    )
    
    return df_long.reset_index(drop=True)
