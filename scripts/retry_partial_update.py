"""Job `quet-bu` (D121): tối thứ Hai và thứ Năm, tải lại phần còn thiếu của các mã trong đợt Quét VN100 08:00.

Đọc `.data_update/status.json` (mục `missing`, mã nào thiếu phần nào), gọi lại đúng phần đó, ghi kết quả ở
`.data_update/retry.json`. Thoát mã 1 khi vẫn còn mã thiếu, để scheduler báo lên Discord.

    python scripts/retry_partial_update.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from valuation.config import load_defaults
from valuation.services.data_update_job import retry_missing


def main() -> int:
    pause = float(load_defaults()["data_update"]["retry_pause_sec"])
    out = retry_missing(pause_s=pause)
    print(json.dumps(out, ensure_ascii=False))
    if out.get("skipped"):
        print(f"BỎ QUA: {out['skipped']}")
        return 0
    print(
        f"Quét bù: thử {len(out['tried'])} mã, còn thiếu {len(out['still_missing'])} mã."
    )
    return 1 if out["still_missing"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
