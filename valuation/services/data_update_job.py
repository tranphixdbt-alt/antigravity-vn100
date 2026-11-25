"""Job nền "Quét VN100": cập nhật giá + BCTC + khuyến nghị CTCK, rồi dòng tiền (flow_daily), có tiến độ.

Cùng mẫu với job xếp hạng (investment_job): tiến trình Python riêng, trạng thái ghi
ra status.json sau MỖI mã, khóa OS chống chạy trùng. Trước đây nút chỉ bật một
thread daemon rồi hiện toast — không biết đang tới đâu, bấm lại là chạy trùng.

  python -m valuation.services.data_update_job   # worker (UI tự khởi chạy)
"""
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from valuation.services.ranking_store import ROOT, exclusive_lock, read_json, write_json

STORE = ROOT / ".data_update"
_ACTIVE = ("QUEUED", "RUNNING")


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def job_status(store: Path = STORE) -> dict:
    """Trạng thái hiện tại; RUNNING mà khóa worker đang trống = worker đã chết."""
    status = read_json(store / "status.json", {}) or {}
    if status.get("status") in _ACTIVE:
        try:
            with exclusive_lock(store / "worker.lock"):
                age = (datetime.now().astimezone() - datetime.fromisoformat(status["updated_at"])).total_seconds()
                if status["status"] == "RUNNING" or age > 60:
                    return {**status, "status": "INTERRUPTED",
                            "message": f"Đợt quét dừng giữa chừng ở {status.get('completed', 0)}/{status.get('total', '?')} mã. Có thể quét lại."}
        except BlockingIOError:
            pass  # worker đang giữ khóa → thực sự đang chạy
    return status


def start_job(store: Path = STORE) -> bool:
    """Khởi chạy worker; False nếu một đợt khác đang chạy."""
    try:
        with exclusive_lock(store / "launch.lock"):
            if job_status(store).get("status") in _ACTIVE:
                return False
            write_json(store / "status.json", {"status": "QUEUED", "message": "Đang khởi động",
                                               "completed": 0, "total": 0, "started_at": _now(), "updated_at": _now()})
            # Phiên riêng: tắt/khởi động lại app (Ctrl-C, đóng terminal) không giết đợt quét.
            subprocess.Popen([sys.executable, "-m", "valuation.services.data_update_job"], cwd=ROOT,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            return True
    except BlockingIOError:
        return False


def main(store: Path = STORE) -> None:
    from valuation.db.session import SessionLocalRead, SessionLocalWrite
    from valuation.ingest.weekly_updater import run_weekly_auto_update

    with exclusive_lock(store / "worker.lock"):
        started = (read_json(store / "status.json", {}) or {}).get("started_at", _now())

        def progress(idx: int, total: int, msg: str) -> None:
            # idx là mã ĐANG xử lý → đã xong idx−1 mã; idx=0 = bước chung trước mã đầu (vd tải trước FHSC, D95).
            write_json(store / "status.json", {"status": "RUNNING", "message": msg, "completed": max(0, idx - 1),
                                               "total": total, "started_at": started, "updated_at": _now()})

        db_read, db_write = SessionLocalRead(), SessionLocalWrite()
        try:
            result = run_weekly_auto_update(db_read, db_write, progress_callback=progress)
            # D121: bỏ lời gọi job flow_daily (khớp/thỏa thuận tách qua vnstock_data, đã khóa từ 10/11/2026 và tắt
            # ở lịch sáng từ D97). Khối ngoại/tự doanh gộp đã vào prices_daily qua FHSC ngay trong đợt quét này.
            write_json(store / "status.json", {
                "status": "DONE", "message": result["message"],
                "completed": result["total"],
                "total": result["total"], "started_at": started, "updated_at": _now(), "finished_at": _now(),
                "success": result["success_count"], "partial": result["partial_count"], "failed": result["fail_count"],
                "missing": result.get("missing", {}), "missing_summary": result.get("missing_summary", {}),
            })
        except Exception as exc:  # báo lỗi lên UI thay vì chết im lặng
            last = read_json(store / "status.json", {}) or {}
            write_json(store / "status.json", {**last, "status": "FAILED", "updated_at": _now(),
                                               "message": f"Lỗi: {type(exc).__name__}: {str(exc)[:200]}"})
            raise
        finally:
            db_read.close()
            db_write.close()


def retry_missing(store: Path = STORE, run=None, sleep=None, pause_s: float = 3.0, today: str | None = None) -> dict:
    """Quét bù (D121): tải lại ĐÚNG phần còn thiếu của các mã trong đợt Quét VN100 cùng ngày.

    Đợt quét 08:00 trên VPS hay bị nguồn VCI trả 418/quá giờ chờ (23/11/2026: 45/100 mã chỉ lấy được một phần).
    Buổi tối thử lại riêng những mã đó, giãn nhịp. Ghi DB như đợt quét (upsert BCTC DO NOTHING, giá coalesce) nên
    chạy lại vô hại. Kết quả ở `retry.json`; status.json của đợt quét giữ nguyên để còn đối chiếu.
    """
    import time

    from valuation.ingest.pipeline import run_ingest
    from valuation.ingest.weekly_updater import missing_parts

    run = run or run_ingest
    sleep = sleep or time.sleep
    today = today or _now()[:10]
    status = read_json(store / "status.json", {}) or {}
    missing: dict[str, list[str]] = status.get("missing") or {}
    out: dict = {"ran_at": _now(), "scan_finished_at": status.get("finished_at"), "tried": {}, "still_missing": {}}
    if status.get("status") != "DONE" or not str(status.get("finished_at", "")).startswith(today) or not missing:
        out["skipped"] = "không có đợt Quét VN100 xong hôm nay với mã thiếu"
        write_json(store / "retry.json", out)
        return out
    with exclusive_lock(store / "worker.lock"):
        for ticker, parts in sorted(missing.items()):
            types = (["prices"] if any(p in ("giá", "dòng tiền") for p in parts) else []) + (
                ["financials"] if any(p.startswith("BCTC") for p in parts) else []
            )
            if not types:
                continue
            res = run(ticker, types, include_yearly=any(p.endswith("năm") for p in parts))
            out["tried"][ticker] = types
            left = missing_parts(res.get("errors") or [])
            if left:
                out["still_missing"][ticker] = left
            sleep(pause_s)
    write_json(store / "retry.json", out)
    return out


if __name__ == "__main__":
    main()
