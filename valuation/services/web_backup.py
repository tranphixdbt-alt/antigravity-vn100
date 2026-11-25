"""Sao lưu tệp dữ liệu người dùng của web hợp nhất (lát 6, mục 14 của docs/PLAN_WEB_HOP_NHAT.md).

`web_user.db` giữ tài khoản, lệnh và mức giá của cả đội, không dựng lại được từ nguồn nào khác. Mỗi ngày
chép một bản nhất quán bằng cơ chế sao lưu của SQLite (chép được cả khi web đang ghi), kiểm bản chép rồi
mới đặt vào chỗ, và chỉ giữ số bản gần nhất ghi ở `web.backup.keep`.

Bản sao lưu nằm cùng ổ với tệp gốc: chống được xóa nhầm và hỏng tệp, KHÔNG chống được mất cả ổ.
"""

from __future__ import annotations

import datetime as dt
import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from valuation.config import load_defaults, settings
from valuation.db.web_user import UserBase, sqlite_file

_NAME = re.compile(r"web_user-(\d{8})\.db")


class BackupError(Exception):
    """Không sao lưu được; câu báo ghi rõ lý do để hiện trong nhật ký của job."""


@dataclass(frozen=True)
class BackupResult:
    path: Path  # bản sao lưu của hôm nay
    rows: dict[str, int]  # số dòng từng bảng trong bản sao lưu
    removed: list[str]  # tên các bản cũ đã xóa vì vượt số bản giữ lại


def _cfg() -> dict[str, Any]:
    return load_defaults()["web"]["backup"]


def _verify(conn: sqlite3.Connection) -> str:
    """`ok` nếu bản chép lành lặn; ngược lại là câu báo lỗi của SQLite."""
    return str(conn.execute("PRAGMA integrity_check").fetchone()[0])


def _count_rows(conn: sqlite3.Connection) -> dict[str, int]:
    """Số dòng từng bảng người dùng có trong bản chép (tên bảng lấy từ schema của ứng dụng, không từ ngoài)."""
    present = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    return {
        table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in sorted(UserBase.metadata.tables)
        if table in present
    }


def _prune(folder: Path, keep: int) -> list[str]:
    """Xóa các bản cũ hơn `keep` bản gần nhất. Chỉ đụng tệp đúng mẫu tên `web_user-YYYYMMDD.db`."""
    dated = sorted(
        (p for p in folder.iterdir() if p.is_file() and _NAME.fullmatch(p.name)),
        key=lambda p: p.name,
        reverse=True,
    )
    removed = [p.name for p in dated[keep:]]
    for path in dated[keep:]:
        path.unlink()
    return sorted(removed)


def backup(today: dt.date | None = None) -> BackupResult:
    """Chép `web_user.db` thành bản của hôm nay rồi dọn bản cũ. Chạy lại trong ngày thì thay bản hôm nay."""
    cfg = _cfg()
    keep = int(cfg["keep"])
    if keep < 1:
        raise BackupError("Cấu hình web.backup.keep phải từ 1 trở lên.")
    source = sqlite_file(settings.web_user_db_url)
    if source is None:
        raise BackupError(
            "WEB_USER_DB_URL không phải tệp SQLite; script này chỉ sao lưu tệp SQLite."
        )
    if not source.is_file():
        raise BackupError(f"Chưa có tệp dữ liệu người dùng ở {source}.")
    folder = source.parent / cfg["dir_name"]
    folder.mkdir(parents=True, exist_ok=True)
    day = (today or dt.datetime.now().astimezone().date()).strftime("%Y%m%d")
    target = folder / f"web_user-{day}.db"
    temp = folder / f"web_user-{day}.db.tmp"
    temp.unlink(missing_ok=True)

    # mở tệp gốc ở chế độ chỉ đọc: job sao lưu không bao giờ ghi vào dữ liệu người dùng
    src = sqlite3.connect(f"{source.resolve().as_uri()}?mode=ro", uri=True)
    try:
        dst = sqlite3.connect(temp)
        try:
            src.backup(dst)
            check = _verify(dst)
            rows = _count_rows(dst) if check == "ok" else {}
        finally:
            dst.close()
    finally:
        src.close()
    if check != "ok":
        temp.unlink(missing_ok=True)
        raise BackupError(
            f"Bản chép không qua được kiểm tra của SQLite ({check}); giữ nguyên các bản cũ."
        )
    os.replace(temp, target)
    return BackupResult(path=target, rows=rows, removed=_prune(folder, keep))
