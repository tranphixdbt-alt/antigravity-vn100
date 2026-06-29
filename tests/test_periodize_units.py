"""
Unit test for data_access periodize & units.
"""
import pytest
import pandas as pd
from valuation.data_access.units import to_billion_vnd, from_billion_vnd
from valuation.data_access.periodize import periodize_quarters_to_annual, is_stock_item

def test_units_conversion():
    assert to_billion_vnd(1_000_000_000) == 1.0
    assert to_billion_vnd(500_000_000) == 0.5
    assert to_billion_vnd(None) == 0.0
    
    assert from_billion_vnd(1.5) == 1_500_000_000.0
    assert from_billion_vnd(0.0) == 0.0
    assert from_billion_vnd(None) == 0.0

def test_is_stock_item():
    # Các khoản mục CĐKT (Stock)
    assert is_stock_item("Tổng tài sản") is True
    assert is_stock_item("Vốn chủ sở hữu") is True
    assert is_stock_item("Cho vay khách hàng") is True
    assert is_stock_item("total_assets") is True
    assert is_stock_item("owners_equity") is True
    
    # Các khoản mục KQKD/LCTT (Flow)
    assert is_stock_item("Doanh thu thuần") is False
    assert is_stock_item("Lợi nhuận sau thuế") is False
    assert is_stock_item("net_sales") is False
    assert is_stock_item("net_income") is False

def test_periodize_quarters_to_annual():
    # Tạo DataFrame giả lập dữ liệu quý
    data = [
        # Doanh thu thuần (Flow) - TTM phải bằng sum các quý = 1000
        {"fiscal_year": 2024, "fiscal_quarter": 1, "line_item": "Doanh thu thuần", "value": 200.0},
        {"fiscal_year": 2024, "fiscal_quarter": 2, "line_item": "Doanh thu thuần", "value": 250.0},
        {"fiscal_year": 2024, "fiscal_quarter": 3, "line_item": "Doanh thu thuần", "value": 300.0},
        {"fiscal_year": 2024, "fiscal_quarter": 4, "line_item": "Doanh thu thuần", "value": 250.0},
        
        # Vốn chủ sở hữu (Stock) - TTM phải bằng giá trị quý cuối cùng (Q4) = 520
        {"fiscal_year": 2024, "fiscal_quarter": 1, "line_item": "Vốn chủ sở hữu", "value": 500.0},
        {"fiscal_year": 2024, "fiscal_quarter": 2, "line_item": "Vốn chủ sở hữu", "value": 510.0},
        {"fiscal_year": 2024, "fiscal_quarter": 3, "line_item": "Vốn chủ sở hữu", "value": 515.0},
        {"fiscal_year": 2024, "fiscal_quarter": 4, "line_item": "Vốn chủ sở hữu", "value": 520.0},
    ]
    df = pd.DataFrame(data)
    
    # Chạy TTM
    result_ttm = periodize_quarters_to_annual(df, 2024, mode="TTM", latest_quarter=4)
    
    assert result_ttm["Doanh thu thuần"] == 1000.0
    assert result_ttm["Vốn chủ sở hữu"] == 520.0
    
    # Chạy FY
    result_fy = periodize_quarters_to_annual(df, 2024, mode="FY")
    assert result_fy["Doanh thu thuần"] == 1000.0
    assert result_fy["Vốn chủ sở hữu"] == 520.0
