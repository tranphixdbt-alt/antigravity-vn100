"""Job `ban-tin-vi-mo` (D122): viết lại bản tin vĩ mô AI trên trang Hôm nay của btinvest.vn.

Trước D122 bản tin chỉ được viết lại khi có người bấm nút trong app Streamlit cũ; web hợp nhất chỉ đọc bản đã lưu, nên
bản tin đứng ở 19/11/2026 suốt một tuần. Job này gọi đúng hàm của nút đó (`get_macro_bulletin_cached(force=True)`):
đọc tin cafef, chỉ gọi AI khi tin đổi so với lần trước (so mã băm), nên không tốn lượt AI khi tin chưa đổi.

Lịch VPS: 07:30 thứ Hai–thứ Sáu (sau vi-mo-vn 07:25 để bản tin dùng số vĩ mô mới nhất, trước báo cáo sáng 07:50).

    python scripts/refresh_macro_bulletin.py

In một dòng JSON (trạng thái, giờ viết). Thoát mã 1 khi không viết được và bản lưu không được gia hạn (lỗi tin hoặc AI),
để nhật ký worker ghi exit=1 và job báo lỗi lên Discord.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from valuation.data_access import macro_news as mn


def _state() -> dict:
    try:
        return json.loads(mn._MACRO_CACHE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def main() -> int:
    before = _state()
    started = time.time()
    text = mn.get_macro_bulletin_cached(force=True)
    after = _state()
    if after.get("ts", 0) >= started:
        status = "viet_moi"
    elif after.get("checked_at", 0) >= started:
        status = "tin_khong_doi"
    else:
        status = "loi"
    out = {
        "trang_thai": status,
        "viet_luc": (
            time.strftime("%Y-%m-%d %H:%M", time.localtime(after.get("ts", 0)))
            if after.get("ts")
            else None
        ),
        "truoc_do": (
            time.strftime("%Y-%m-%d %H:%M", time.localtime(before["ts"]))
            if before.get("ts")
            else None
        ),
        "so_ky_tu": len(text or ""),
    }
    if status == "loi":
        out["loi"] = (text or "")[:200]
    print(json.dumps(out, ensure_ascii=False))
    return 1 if status == "loi" else 0


if __name__ == "__main__":
    raise SystemExit(main())
