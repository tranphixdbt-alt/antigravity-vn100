"""
Cấu hình hệ thống Valuation VN100.
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    database_url_readonly: str = os.getenv("DATABASE_URL_READONLY") or "postgresql://macos@localhost:5432/vn100"
    database_url_write: str = os.getenv("DATABASE_URL_WRITE") or "postgresql://macos@localhost:5432/vn100"
    vnstock_api_key: str = os.getenv("VNSTOCK_API_KEY") or ""
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY") or ""

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

def load_defaults() -> dict:
    """Tải cấu hình mặc định (bù đắp phần config bị mất do thao tác trước đó)."""
    return {
        "macro_sources": {
            "tpcp_10y_endpoint": ""
        },
        "rating_bands": [],
        "coe_convention": {},
        "ddm": {
            "power_dcf_weight": 0.6
        },
        "sector_pe": {},
        "proxy_valuation": {}
    }

def get_macro_allowed_domains() -> list:
    """Trả về danh sách các domain được phép lấy dữ liệu macro."""
    return ["vietcap.com.vn", "ssi.com.vn", "vndirect.com.vn", "sbv.gov.vn", "gso.gov.vn"]

def load_elasticities() -> dict:
    """Tải cấu hình độ co giãn (elasticity) để điều chỉnh mô hình vĩ mô."""
    return {
        "macro_overlay": {
            "enabled": True,
            "revenue_growth_to_gdp": {
                "default": 1.0,
                "banks": 1.5,
                "retail": 2.0
            },
            "credit_growth_to_system": {
                "default": 1.0,
                "banks": 1.2
            }
        }
    }

def get_macro_series_registry() -> dict:
    """Trả về danh sách các chỉ số vĩ mô hợp lệ."""
    return {
        "GDP_YOY": {},
        "CREDIT_GROWTH": {},
        "STEEL_HRC": {},
        "CPI_YOY": {}
    }

import pathlib
PROJECT_ROOT = pathlib.Path(__file__).parent.parent.resolve()

