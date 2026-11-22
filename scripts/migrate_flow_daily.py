"""Tạo bảng flow_daily (B1, D73) sau khi backup SQLite. Mặc định chỉ in việc sẽ làm.

~/.venv/bin/python scripts/migrate_flow_daily.py            # dry-run
~/.venv/bin/python scripts/migrate_flow_daily.py --apply    # backup rồi tạo bảng
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import Engine, inspect

from valuation.config import PROJECT_ROOT, settings
from valuation.db.flow_models import (
    FlowMetaData,
    flow_daily,
    open_flow_engine,
)

BACKUP_DIR = PROJECT_ROOT / "backups"


def backup_sqlite(
    src: Path, backup_dir: Path, now: dt.datetime, tag: str = "flow_daily"
) -> Path:
    """Sao lưu bằng sqlite3 backup API (ảnh nhất quán kể cả khi app đang mở DB)."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    dst = backup_dir / f"{src.stem}.pre_{tag}_{now:%Y%m%d_%H%M%S}{src.suffix}"
    if dst.exists():
        raise FileExistsError(f"Backup đã tồn tại: {dst}")
    with contextlib.closing(sqlite3.connect(src)) as s, contextlib.closing(
        sqlite3.connect(dst)
    ) as d:
        s.backup(d)
    if dst.stat().st_size == 0:
        raise RuntimeError(f"Backup rỗng: {dst}")
    # ảnh hỏng chỉ lộ ra lúc cần rollback → kiểm ngay (như ensure_portable_db._validate_sqlite)
    with contextlib.closing(sqlite3.connect(dst)) as d:
        check = d.execute("PRAGMA integrity_check").fetchone()[0]
    if check != "ok":
        raise RuntimeError(f"Backup hỏng ({check}): {dst}")
    return dst


def migrate(
    engine: Engine, backup_dir: Path, apply: bool, now: dt.datetime | None = None
) -> str:
    """Idempotent: có bảng → không làm gì; chưa có → (apply) backup rồi CREATE."""
    if inspect(engine).has_table(flow_daily.name):
        return "flow_daily: ĐÃ CÓ, không làm gì"
    if engine.dialect.name != "sqlite":
        raise RuntimeError(
            "Chỉ hỗ trợ SQLite portable; Postgres: pg_dump rồi tạo bảng thủ công"
        )
    src = Path(engine.url.database or "")
    if not apply:
        return f"flow_daily: SẼ TẠO trong {src} (backup trước vào {backup_dir}); thêm --apply để chạy"
    backup = backup_sqlite(src, backup_dir, now or dt.datetime.now().astimezone())
    FlowMetaData.create_all(engine, tables=[flow_daily])
    return f"flow_daily: ĐÃ TẠO. Backup: {backup}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run", action="store_true", help="Chỉ in việc sẽ làm (mặc định)"
    )
    mode.add_argument("--apply", action="store_true", help="Backup rồi tạo bảng")
    args = parser.parse_args()
    engine = open_flow_engine(settings.database_url_write)
    print(migrate(engine, BACKUP_DIR, apply=args.apply))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
