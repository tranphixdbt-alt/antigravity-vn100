import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
MAPPING_FILE = PROJECT_ROOT / "config" / "sector_mapping.yaml"

def load_mapping():
    if MAPPING_FILE.exists():
        with open(MAPPING_FILE, "r", encoding="utf-8") as f:
            return yaml.safe_load(f).get("mapping", {})
    return {}

_mapping = load_mapping()

def get_valuation_model_for_sector(sector_name: str) -> str:
    return _mapping.get(sector_name, "non_financial")
