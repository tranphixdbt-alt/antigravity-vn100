"""Hộp thư vòng học: lưu file Claude-cloud gửi qua Discord webhook vào knowledge/ (docs/PLAN_LEARNING_LOOP.md).

Connector Google Drive của routine đọc được nhưng KHÔNG ghi được file → routine gửi đề xuất + LEARNINGS.md
qua webhook kèm nhãn MARKER; bot Discord gọi `save_learning_attachment` để lưu. Thư mục dự án nằm trên Google
Drive nên file tự đồng bộ cho lần duyệt tuần sau đọc lại.
"""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

from valuation.config import PROJECT_ROOT

MARKER = "[VN100-LEARNING]"
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"
MAX_BYTES = 200_000
_PROPOSAL = re.compile(r"^\d{4}-W\d{2}\.md$")


def save_learning_attachment(filename: str, data: bytes, root: Path | None = None) -> Path | None:
    """Chỉ nhận `<năm>-W<tuần>.md` (→ proposals/) và `LEARNINGS.md`; văn bản UTF-8 ≤ MAX_BYTES.
    Tên khác/nhị phân/quá lớn → None (không ghi). Bản cũ được giữ lại trước khi ghi đè."""
    root = root or KNOWLEDGE_DIR
    if len(data) > MAX_BYTES:
        return None
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%d_%H%M%S")
    if _PROPOSAL.fullmatch(filename):
        path = root / "proposals" / filename
        backup = path.with_name(f"{path.stem}.{stamp}.prev.md")
    elif filename == "LEARNINGS.md":
        path = root / "LEARNINGS.md"
        backup = root / "learnings_history" / f"LEARNINGS_{stamp}.md"
    else:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup.parent.mkdir(parents=True, exist_ok=True)
        path.replace(backup)
    path.write_text(text, encoding="utf-8")
    return path
