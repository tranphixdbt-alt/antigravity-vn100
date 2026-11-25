"""Job `kiem-du-lieu` (D121): báo Discord khi giá hoặc vĩ mô trên DB cũ hơn mức cho phép. Chỉ đọc DB.

Lịch VPS: 08:20 (sau báo cáo sáng) và 16:10 (sau job gia-cuoi-phien) thứ Hai–thứ Sáu.

    python scripts/check_data_freshness.py            # kiểm + gửi Discord nếu có vấn đề
    python scripts/check_data_freshness.py --dry-run  # chỉ in, không gửi

Thoát mã 1 khi có vấn đề mà KHÔNG gửi được Discord (để nhật ký worker ghi exit=1).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from valuation.db.session import SessionLocalRead
from valuation.ingest.session_guard import now_vn
from valuation.services.freshness_alert import run_check


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="không gửi Discord")
    args = parser.parse_args()
    db = SessionLocalRead()
    try:
        result = run_check(db, now_vn(), dry_run=args.dry_run)
    finally:
        db.close()
    print(json.dumps(result, ensure_ascii=False))
    if result["message"] and not args.dry_run and not result["sent"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
