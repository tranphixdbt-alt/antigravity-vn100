import yaml
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

PROJECT_ROOT = Path(__file__).parent.parent
DEFAULTS_FILE = PROJECT_ROOT / "config" / "defaults.yaml"

def load_defaults() -> dict:
    if DEFAULTS_FILE.exists():
        with open(DEFAULTS_FILE, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}

_defaults = load_defaults()

class Settings(BaseSettings):
    vnstock_api_key: str = Field(default="")
    database_url_readonly: str = Field(...)
    database_url_write: str = Field(...)
    google_service_account_json: str = Field(default="")
    google_sheet_master_id: str = Field(default="")
    google_drive_folder_id: str = Field(default="")
    discord_webhook_url: str = Field(default="")
    recompute_webhook_token: str = Field(default="")
    deepseek_api_key: str = Field(default="")
    
    erp_vn: float = Field(default=_defaults.get("erp_vn", 8.5))
    
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
