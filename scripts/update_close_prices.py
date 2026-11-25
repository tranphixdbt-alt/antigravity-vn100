"""Job `gia-cuoi-phien` (D121): tải giá, khối ngoại, tự doanh VN100 + VNINDEX ngay sau khi phiên đóng cửa.

Trước đây giá chỉ vào DB lúc 07:50 sáng hôm sau, nên từ chiều tới sáng web chậm một phiên. Job này dùng đúng
`daily_report.refresh_market` (FHSC trước, VCI dự phòng; cùng khóa với Quét VN100), bỏ bước kiểm cổ tức, không
gửi Discord, không định giá lại. Lượt 07:50 sáng hôm sau vẫn tải lại phiên này (đệm 5 ngày) và ghi trong báo cáo
sáng số mã đổi so với lượt này (`recheck`).

Lịch VPS: 15:45 thứ Hai–thứ Sáu (vn100-worker). Thoát mã 1 khi bị khóa (Quét VN100 đang chạy) hoặc không mã nào
cập nhật được giá, để scheduler báo lỗi lên Discord.

    python scripts/update_close_prices.py
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from valuation.services.daily_report import refresh_market


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    info = refresh_market(corporate_actions=False)
    updated = sum((info.get("price_sources") or {}).values())
    print(
        f"Giá cuối phiên: {updated}/{info['price_total']} mã cập nhật, nguồn {info.get('price_sources')},"
        f" khối ngoại {info.get('flow_updated', 0)} mã, lỗi {len(info['price_errors'])}."
    )
    print(json.dumps(info, ensure_ascii=False, default=str))
    if info["skipped"]:
        print(f"BỎ QUA: {info['skipped']}")
        return 1
    return 0 if updated else 1


if __name__ == "__main__":
    raise SystemExit(main())
