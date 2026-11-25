"""Job `vi-mo-vn` (D121): nạp CPI, bán lẻ, GDP Việt Nam từ báo cáo kinh tế – xã hội của Cục Thống kê (nso.gov.vn).

Lịch VPS: 07:25 thứ Hai–thứ Sáu (vn100-worker), trước báo cáo sáng. Chỉ thêm kỳ chưa có; kỳ đã có mà Cục Thống kê
sửa số thì in ra (không ghi đè). Báo chuỗi cũ do job kiem-du-lieu lo.

    python scripts/update_vn_macro.py            # chạy thật: ghi DB
    python scripts/update_vn_macro.py --dry-run  # chỉ đọc nguồn + in điểm sẽ ghi

Thoát mã 1 khi tải/đọc lỗi (scheduler báo Discord).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from valuation.db.session import SessionLocalWrite
from valuation.ingest.nso_reports import run_nso_update


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="không ghi DB")
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    db = SessionLocalWrite()
    try:
        result = run_nso_update(db, dry_run=args.dry_run)
    finally:
        db.close()
    print(
        f"Vĩ mô VN (nso.gov.vn): đọc {len(result['read'])} bài, thấy {len(result['found'])} điểm, "
        f"kỳ mới {len(result['points'])}, đã ghi {result['written']}{' (dry-run)' if args.dry_run else ''}."
    )
    for r in result["revisions"]:
        print(
            f"SỐ ĐÃ SỬA (không ghi đè): {r['code']} {r['date']}: DB {r['db']} → Cục Thống kê {r['nso']}"
        )
    print(json.dumps(result, ensure_ascii=False))
    return 1 if result["error"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
