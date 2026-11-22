"""Tạo bảng active_flow_daily (D101, W0 docs/PLAN_WYCKOFF_FLOW.md) sau khi backup SQLite. Mặc định chỉ in việc sẽ làm.

~/.venv/bin/python scripts/migrate_active_flow.py                               # dry-run
~/.venv/bin/python scripts/migrate_active_flow.py --apply                       # backup vào ./backups rồi tạo bảng
python scripts/migrate_active_flow.py --apply --backup-dir /data                # VPS: backup nằm trong volume
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from migrate_flow_daily import backup_sqlite
from sqlalchemy import Engine, inspect

from valuation.config import PROJECT_ROOT, settings
from valuation.db.flow_models import (
    FlowMetaData,
    active_flow_daily,
    open_flow_engine,
)

BACKUP_DIR = PROJECT_ROOT / "backups"


def migrate(
    engine: Engine, backup_dir: Path, apply: bool, now: dt.datetime | None = None
) -> str:
    """Idempotent: có bảng → không làm gì; chưa có → (apply) backup rồi CREATE. Không đụng bảng khác."""
    name = active_flow_daily.name
    if inspect(engine).has_table(name):
        return f"{name}: ĐÃ CÓ, không làm gì"
    if engine.dialect.name != "sqlite":
        raise RuntimeError(
            "Chỉ hỗ trợ SQLite portable; Postgres: pg_dump rồi tạo bảng thủ công"
        )
    src = Path(engine.url.database or "")
    if not apply:
        return f"{name}: SẼ TẠO trong {src} (backup trước vào {backup_dir}); thêm --apply để chạy"
    backup = backup_sqlite(
        src, backup_dir, now or dt.datetime.now().astimezone(), tag=name
    )
    FlowMetaData.create_all(engine, tables=[active_flow_daily])
    return f"{name}: ĐÃ TẠO. Backup: {backup}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--apply", action="store_true", help="Backup rồi tạo bảng")
    parser.add_argument(
        "--backup-dir", type=Path, default=BACKUP_DIR, help="Thư mục đặt bản backup"
    )
    args = parser.parse_args()
    engine = open_flow_engine(settings.database_url_write)
    print(migrate(engine, args.backup_dir, apply=args.apply))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
