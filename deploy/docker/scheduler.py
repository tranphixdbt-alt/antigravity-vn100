"""Lịch chạy job VN100 trong container vn100-worker (thay launchd của máy Mac). Chỉ dùng thư viện chuẩn.

Mỗi 30 giây: job nào đã tới giờ hẹn (giờ VN, TZ của container) mà hôm nay chưa chạy thì chạy, lần lượt từng job.
Khởi động muộn (deploy, mất điện) vẫn chạy bù nếu chưa quá CATCH_UP sau giờ hẹn. Ngày chạy cuối của từng job
lưu ở /data/scheduler_state.json (volume) nên deploy lại không chạy trùng; ghi TRƯỚC khi chạy để job lỗi không
bị gọi lại liên tục trong ngày.

    python /opt/vn100/scheduler.py             # chạy lịch
    python /opt/vn100/scheduler.py --selftest  # tự kiểm tra hàm `due`
"""
from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path

# (tên, các thứ trong tuần: 0 = thứ 2 … 6 = chủ nhật, giờ hẹn, lệnh chạy trong /app) — giống launchd trên Mac
JOBS = [
    ("daily-report", range(0, 5), "07:50", ["python", "scripts/daily_report.py"]),
    ("flow-daily", range(0, 5), "08:30", ["python", "scripts/update_flow_daily.py"]),  # D88: đầu phiên
    ("weekly-digest", [6], "18:00", ["python", "scripts/weekly_learning_digest.py"]),
]
CATCH_UP = dt.timedelta(hours=3)
STATE = Path("/data/scheduler_state.json")
LOGS = Path("/app/logs")


def due(now: dt.datetime, days, hhmm: str, last_run: str | None) -> bool:
    h, m = map(int, hhmm.split(":"))
    slot = now.replace(hour=h, minute=m, second=0, microsecond=0)
    return now.weekday() in days and slot <= now < slot + CATCH_UP and last_run != slot.date().isoformat()


def main() -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    print(f"scheduler bắt đầu, trạng thái: {state}", flush=True)
    while True:
        now = dt.datetime.now()
        for name, days, hhmm, cmd in JOBS:
            if not due(now, days, hhmm, state.get(name)):
                continue
            state[name] = now.date().isoformat()
            STATE.write_text(json.dumps(state))
            with (LOGS / f"{name}.log").open("a", encoding="utf-8") as log:
                log.write(f"\n=== {now:%Y-%m-%d %H:%M} scheduler ===\n")
                log.flush()
                code = subprocess.run(cmd, cwd="/app", stdout=log, stderr=subprocess.STDOUT).returncode
            print(f"{now:%Y-%m-%d %H:%M} {name} exit={code}", flush=True)
        time.sleep(30)


def _selftest() -> None:
    mon = dt.datetime(2026, 11, 16, 7, 50)  # thứ 2
    days = range(0, 5)
    assert due(mon, days, "07:50", None)
    assert not due(mon.replace(minute=49), days, "07:50", None)  # chưa tới giờ
    assert not due(mon, days, "07:50", "2026-11-16")  # hôm nay đã chạy
    assert due(mon.replace(hour=10, minute=49), days, "07:50", "2026-11-13")  # chạy bù trong 3 giờ
    assert not due(mon.replace(hour=10, minute=50), days, "07:50", None)  # quá 3 giờ: bỏ, chờ ngày sau
    assert not due(dt.datetime(2026, 11, 15, 7, 50), days, "07:50", None)  # chủ nhật không có báo cáo sáng
    assert due(dt.datetime(2026, 11, 15, 18, 5), [6], "18:00", None)  # tóm tắt tuần chủ nhật
    print("selftest OK")


if __name__ == "__main__":
    _selftest() if "--selftest" in sys.argv else main()
