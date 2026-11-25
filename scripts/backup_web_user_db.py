"""Job sao lưu tệp dữ liệu người dùng của web hợp nhất (lát 6, mục 14 của docs/PLAN_WEB_HOP_NHAT.md).

Lịch VPS: mỗi ngày trong vn100-worker. Chạy lại trong ngày chỉ thay bản của hôm nay, không tạo bản thứ hai.

    python scripts/backup_web_user_db.py

Thoát mã 1 khi không sao lưu được (lý do nằm trong nhật ký của job); không in nội dung dữ liệu, chỉ in số dòng.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from valuation.services import web_backup


def main() -> int:
    try:
        result = web_backup.backup()
    except web_backup.BackupError as exc:
        print(f"Sao lưu web_user.db LỖI: {exc}")
        return 1
    rows = ", ".join(f"{table} {count}" for table, count in result.rows.items())
    removed = f"; xóa bản cũ: {', '.join(result.removed)}" if result.removed else ""
    print(f"Sao lưu web_user.db: {result.path} ({rows}){removed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
