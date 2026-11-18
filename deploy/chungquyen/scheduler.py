"""Lịch chạy app chứng quyền trên VPS — thay 4 lịch launchd vn.cw-scanner.* của Mac (cai_lich_quet.sh).

Chạy trong container chungquyen-worker, thư mục làm việc /app (git clone cw_scanner, dữ liệu nằm cạnh code).
Mỗi job một tiến trình riêng (quét 14:00 chạy lâu không chặn lượt kiểm 5 phút); job đang chạy thì không chạy chồng.
Nhật ký gộp vào /app/log.txt như launchd (StandardOutPath).
"""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path

# (tên, lịch, lệnh). Lịch: ("lich", các thứ 0 = thứ 2 … 4 = thứ 6, "HH:MM") hoặc ("moi", số giây)
JOBS = [
    ("quet", ("lich", range(0, 5), "14:00"), ["bash", "chay_quet_tu_dong.sh"]),
    ("etf", ("lich", range(0, 5), "09:40"), ["bash", "chay_etf_tu_dong.sh"]),
    ("danh-muc", ("moi", 300), ["bash", "kiem_tra_danh_muc.sh"]),
    ("chiet-khau", ("moi", 300), ["bash", "kiem_tra_chiet_khau.sh"]),
]
CATCH_UP = dt.timedelta(hours=3)  # VPS khởi động lại trễ: chạy bù lịch giờ cố định trong 3 giờ (launchd chạy bù khi máy thức)
APP = Path("/app")
STATE = APP / "ket_qua" / ".lich_vps.json"  # ket_qua/ nằm trong .gitignore: không mất khi deploy kéo code mới


def due_lich(now: dt.datetime, days, hhmm: str, last_run: str | None) -> bool:
    h, m = map(int, hhmm.split(":"))
    slot = now.replace(hour=h, minute=m, second=0, microsecond=0)
    return now.weekday() in days and slot <= now < slot + CATCH_UP and last_run != slot.date().isoformat()


def due_moi(now_s: float, every: int, last_s: float | None) -> bool:
    return last_s is None or now_s - last_s >= every


def main() -> None:
    STATE.parent.mkdir(exist_ok=True)
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    last_interval: dict[str, float] = {}
    running: dict[str, subprocess.Popen] = {}
    print(f"scheduler chứng quyền bắt đầu, trạng thái: {state}", flush=True)
    while True:
        now = dt.datetime.now()
        for name, proc in list(running.items()):
            if (code := proc.poll()) is not None:
                print(f"{now:%Y-%m-%d %H:%M} {name} exit={code}", flush=True)
                del running[name]
        for name, (kind, *spec), cmd in JOBS:
            if name in running:
                continue
            if kind == "lich":
                if not due_lich(now, spec[0], spec[1], state.get(name)):
                    continue
                state[name] = now.date().isoformat()
                STATE.write_text(json.dumps(state))
            elif due_moi(time.monotonic(), spec[0], last_interval.get(name)):
                last_interval[name] = time.monotonic()
            else:
                continue
            log = (APP / "log.txt").open("a", encoding="utf-8")
            running[name] = subprocess.Popen(cmd, cwd=APP, stdout=log, stderr=subprocess.STDOUT)
            log.close()  # tiến trình con giữ bản sao của file nhật ký
        time.sleep(15)


def _selftest() -> None:
    mon = dt.datetime(2026, 11, 16, 14, 0)  # thứ 2
    days = range(0, 5)
    assert due_lich(mon, days, "14:00", None)
    assert not due_lich(mon.replace(minute=59, hour=13), days, "14:00", None)
    assert not due_lich(mon, days, "14:00", "2026-11-16")
    assert due_lich(mon.replace(hour=16, minute=59), days, "14:00", "2026-11-13")  # chạy bù trong 3 giờ
    assert not due_lich(mon.replace(hour=17), days, "14:00", None)
    assert not due_lich(dt.datetime(2026, 11, 15, 14, 0), days, "14:00", None)  # chủ nhật
    assert due_moi(1000.0, 300, None) and due_moi(1300.0, 300, 1000.0) and not due_moi(1299.0, 300, 1000.0)
    print("selftest OK")


if __name__ == "__main__":
    _selftest() if "--selftest" in sys.argv else main()
