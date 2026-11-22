"""Job nạp TPCP_10Y từ worldgovernmentbonds.com + báo Discord khi chuỗi cũ quá 21 ngày (D100).

Lịch VPS: 07:20 thứ Hai–thứ Sáu (vn100-worker), trước báo cáo sáng 07:50 và xếp hạng 08:00.

    python scripts/update_tpcp_10y.py            # chạy thật: ghi DB, báo Discord nếu cũ
    python scripts/update_tpcp_10y.py --dry-run  # chỉ tải + in điểm sẽ ghi; không ghi DB, không gửi Discord

Thoát mã 1 khi tải/parse/ghi lỗi (traceback nằm trong log job); vẫn kiểm tra tuổi và báo trước đó.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from valuation.db.session import SessionLocalWrite
from valuation.ingest.tpcp_wgb import run_tpcp_update


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="không ghi DB, không gửi Discord")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    db = SessionLocalWrite()
    try:
        result = run_tpcp_update(db, dry_run=args.dry_run)
    finally:
        db.close()

    pts = result["points"]
    span = f"{pts[0][0]}…{pts[-1][0]}" if pts else "không có"
    print(
        f"TPCP_10Y: điểm mới {len(pts)} ({span}), đã ghi {result['written']}"
        f"{' (dry-run)' if args.dry_run else ''}; mới nhất {result['last_date']}"
        f" = {result['last_value']}, cũ {result['age_days']} ngày."
    )
    if result["alert"]:
        if args.dry_run:
            state = "không gửi, dry-run"
        else:
            state = "đã gửi Discord" if result["alert_sent"] else "CHƯA gửi được Discord"
        print(f"CẢNH BÁO ({state}): {result['alert']}")
    print(json.dumps(result, ensure_ascii=False))
    return 1 if result["error"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
