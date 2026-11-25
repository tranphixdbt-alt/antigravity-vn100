"""Báo Discord khi một job của vn100-worker thoát mã khác 0 (D121). `scheduler.py` gọi sau mỗi job lỗi.

Trước đây job lỗi chỉ để lại dòng "<tên> exit=1" trong nhật ký container, không ai biết (vd sao lưu web_user.db).
Tin báo chỉ có tên job, mã thoát, giờ và đường dẫn nhật ký: không chép nội dung nhật ký lên Discord (có thể lẫn
đường dẫn, mã lỗi của nguồn ngoài; luật bảo mật AGENTS.md mục 5).

    python scripts/notify_job_failure.py <tên job> <mã thoát>
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")  # tên job trong scheduler.JOBS


def message(name: str, code: int, now: datetime) -> str:
    if not _NAME.match(name):
        raise ValueError(f"tên job không hợp lệ: {name!r}")
    return (
        f"Job `{name}` trên vn100-worker lỗi (mã thoát {code}) lúc {now:%H:%M %d/%m/%Y}. "
        f"Xem nhật ký /app/logs/{name}.log trong container vn100-worker."
    )


def main() -> int:
    from valuation.output.discord_alerter import notify_discord

    name, code = sys.argv[1], int(sys.argv[2])
    resp = notify_discord(content=message(name, code, datetime.now().astimezone()))
    ok = resp is not None and getattr(resp, "status_code", 0) in (200, 204)
    print(f"báo lỗi job {name}: {'đã gửi' if ok else 'CHƯA gửi được'} Discord")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
