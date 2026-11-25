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
    # D100 (22/11/2026): nạp TPCP_10Y từ worldgovernmentbonds.com (Chromium headless, ~10 s) + báo Discord khi
    # chuỗi cũ > 21 ngày. Đứng đầu danh sách để khi chạy bù vẫn xong trước báo cáo sáng và xếp hạng (rf mới nhất).
    ("tpcp-10y", range(0, 5), "07:20", ["python", "scripts/update_tpcp_10y.py"]),
    # D101 (22/11/2026): lưu mua/bán chủ động FHSC (~100 lời gọi ≈ 3 phút). FHSC chỉ giữ ~61 phiên → phải chạy mỗi ngày.
    ("active-flow", range(0, 5), "07:35", ["python", "scripts/update_active_flow.py"]),
    ("daily-report", range(0, 5), "07:50", ["python", "scripts/daily_report.py"]),
    # D97: flow-daily (khớp/thỏa thuận tách, VCI qua vnstock_data) tắt — gói bị khóa từ 10/11/2026, job lỗi mỗi ngày.
    # Khối ngoại/tự doanh gộp giờ lấy từ FHSC trong daily-report. Bật lại khi có nguồn tách khớp/thỏa thuận.
    # ("flow-daily", range(0, 5), "08:30", ["python", "scripts/update_flow_daily.py"]),
    ("weekly-digest", [6], "18:00", ["python", "scripts/weekly_learning_digest.py"]),
    # Người dùng quyết 21/11/2026: 08:00 thứ Hai và thứ Năm tự cập nhật dữ liệu ("Quét VN100": giá + BCTC + khuyến nghị CTCK)
    # rồi xếp hạng/định giá lại (có một lượt AI). Trước đó hai việc này chỉ chạy khi bấm trên giao diện (lần cuối 13/11 và 27/10).
    # Vòng lặp chạy lần lượt theo thứ tự danh sách, nên cập nhật dữ liệu xong mới tới xếp hạng (~30 phút + ~50 phút).
    # Bản sao trong repo: deploy/docker/scheduler.py (đồng bộ 22/11/2026, D100) — sửa ở đây thì chép sang đó.
    ("data-update", [0, 3], "08:00", ["python", "-m", "valuation.services.data_update_job"]),
    ("ranking", [0, 3], "08:00", ["python", "scripts/update_vn100_ranking.py"]),
    # D112 (25/11/2026): sao lưu tệp dữ liệu người dùng của web hợp nhất btinvest.vn (/data/web_user/web_user.db: tài
    # khoản, lệnh, mức giá) mỗi ngày, giữ 14 bản ở /data/web_user/sao_luu/. Cùng ổ với tệp gốc: chống xóa nhầm và hỏng
    # tệp, KHÔNG chống mất cả ổ. 23:00 không trùng job nào; ô giờ nằm sát nửa đêm nên chỉ chạy bù được tới 23:59.
    # Job lỗi: dòng "web-user-backup exit=1" trong nhật ký worker, lý do ở /app/logs/web-user-backup.log.
    ("web-user-backup", range(0, 7), "23:00", ["python", "scripts/backup_web_user_db.py"]),
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
    assert due(dt.datetime(2026, 11, 23, 8, 4), [0, 3], "08:00", None)  # thứ Hai 08:00: cập nhật dữ liệu + xếp hạng
    assert due(dt.datetime(2026, 11, 26, 9, 30), [0, 3], "08:00", None)  # thứ Năm, chạy bù trong 3 giờ
    assert not due(dt.datetime(2026, 11, 24, 8, 0), [0, 3], "08:00", None)  # thứ Ba không chạy
    assert due(dt.datetime(2026, 11, 23, 7, 20), range(0, 5), "07:20", None)  # TPCP_10Y thứ Hai 07:20
    assert not due(dt.datetime(2026, 11, 28, 7, 20), range(0, 5), "07:20", None)  # thứ Bảy không nạp TPCP_10Y
    assert due(dt.datetime(2026, 11, 28, 23, 0), range(0, 7), "23:00", None)  # sao lưu web_user.db chạy cả thứ Bảy
    assert not due(dt.datetime(2026, 11, 28, 23, 30), range(0, 7), "23:00", "2026-11-28")  # hôm nay đã sao lưu
    assert not due(dt.datetime(2026, 11, 29, 0, 30), range(0, 7), "23:00", None)  # qua nửa đêm: không chạy bù
    names = [name for name, *_ in JOBS]
    assert len(names) == len(set(names)), "tên job trùng nhau thì hai job dùng chung một dòng trạng thái"
    print("selftest OK")


if __name__ == "__main__":
    _selftest() if "--selftest" in sys.argv else main()
