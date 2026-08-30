import yaml
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULTS_FILE = PROJECT_ROOT / "config" / "defaults.yaml"

def load_defaults() -> dict:
    if DEFAULTS_FILE.exists():
        with open(DEFAULTS_FILE, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}

_defaults = load_defaults()


ELASTICITIES_FILE = PROJECT_ROOT / "config" / "elasticities.yaml"


def load_elasticities() -> dict:
    """Đọc config macro overlay (elasticities.yaml)."""
    if ELASTICITIES_FILE.exists():
        with open(ELASTICITIES_FILE, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def get_macro_series_registry() -> dict:
    """Registry các series_code vĩ mô được phép ghi vào macro_series."""
    return _defaults.get("macro_series_registry", {})


def get_macro_allowed_domains() -> list[str]:
    """Allowlist domain mà scraper macro được phép gọi (Bảo mật mục 5)."""
    return list(_defaults.get("macro_sources", {}).get("allowed_domains", []))


def get_macro_source_config() -> dict:
    """Cấu hình chung cho scraper macro (timeout, user-agent, allowlist)."""
    return _defaults.get("macro_sources", {})


class Settings(BaseSettings):
    vnstock_api_key: str = Field(default="")
    database_url_readonly: str = Field(default="sqlite:///vn100_full.db")
    database_url_write: str = Field(default="sqlite:///vn100_full.db")
    google_service_account_json: str = Field(default="")
    google_sheet_master_id: str = Field(default="")
    google_drive_folder_id: str = Field(default="")
    discord_webhook_url: str = Field(default="")
    recompute_webhook_token: str = Field(default="")
    deepseek_api_key: str = Field(default="")
    discord_bot_token: str = Field(default="")
    
    erp_vn: float = Field(default=_defaults.get("erp_vn", 8.5))
    
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
