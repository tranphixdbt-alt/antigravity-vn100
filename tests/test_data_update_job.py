"""Job "Quét VN100": tiến độ ghi ra status.json từng mã, kết thúc DONE, worker chết → INTERRUPTED."""
import json
from datetime import datetime

from valuation.ingest import weekly_updater
from valuation.services import data_update_job as job


def test_worker_writes_progress_then_done(tmp_path, monkeypatch):
    seen = []

    def fake_update(db_read, db_write, progress_callback=None, max_tickers=None):
        for i, t in enumerate(["AAA", "BBB", "CCC"], start=1):
            progress_callback(i, 3, f"Đang cập nhật {t} ({i}/3)...")
            seen.append(json.loads((tmp_path / "status.json").read_text(encoding="utf-8")))
        return {"total": 3, "success_count": 2, "partial_count": 1, "fail_count": 0, "message": "xong",
                "missing": {"CCC": ["BCTC IS quý"]}, "missing_summary": {"BCTC IS quý": 1}}

    monkeypatch.setattr(weekly_updater, "run_weekly_auto_update", fake_update)
    job.main(store=tmp_path)

    assert [s["completed"] for s in seen] == [0, 1, 2]  # đang xử lý mã thứ i → đã xong i−1
    assert all(s["status"] == "RUNNING" and s["total"] == 3 for s in seen)
    final = job.job_status(tmp_path)
    assert final["status"] == "DONE" and final["completed"] == 3
    assert (final["success"], final["partial"], final["failed"]) == (2, 1, 0)
    # D121: không gọi job flow_daily đã tắt nữa; status ghi rõ mã nào thiếu phần nào để quét bù
    assert "flow_exit" not in final and final["message"] == "xong"
    assert final["missing"] == {"CCC": ["BCTC IS quý"]} and final["missing_summary"] == {"BCTC IS quý": 1}


def test_prefetch_step_before_first_ticker_reports_zero_not_negative(tmp_path, monkeypatch):
    # Lỗi 13/11: bước tải trước FHSC (D95) gọi progress_callback(0, …) → completed −1 → st.progress(−0,01)
    # báo StreamlitAPIException mỗi 5 giây ở thanh bên suốt ~7 phút tải trước.
    seen = []

    def fake_update(db_read, db_write, progress_callback=None, max_tickers=None):
        progress_callback(0, 100, "Đang tải trước giá & dòng tiền từ FHSC...")
        seen.append(json.loads((tmp_path / "status.json").read_text(encoding="utf-8")))
        return {"total": 100, "success_count": 100, "partial_count": 0, "fail_count": 0, "message": "xong"}

    monkeypatch.setattr(weekly_updater, "run_weekly_auto_update", fake_update)
    job.main(store=tmp_path)
    assert seen[0]["completed"] == 0 and seen[0]["total"] == 100


def test_running_status_without_worker_is_reported_interrupted(tmp_path):
    (tmp_path / "status.json").write_text(json.dumps({
        "status": "RUNNING", "completed": 40, "total": 100,
        "updated_at": datetime.now().astimezone().isoformat(),
    }), encoding="utf-8")
    s = job.job_status(tmp_path)
    assert s["status"] == "INTERRUPTED"
    assert "40/100" in s["message"]


def test_missing_parts_and_summary_d121():
    errors = [
        {"component": "financials", "statement": "IS", "period": "quarter", "message": "418"},
        {"component": "financials", "statement": "IS", "period": "quarter", "message": "lặp"},
        {"component": "financials", "statement": "BS", "period": "year", "message": "timeout"},
        {"component": "market_flows", "message": "x"},
    ]
    assert weekly_updater.missing_parts(errors) == ["BCTC IS quý", "BCTC BS năm", "dòng tiền"]
    summary = weekly_updater.summarize_missing({"A": ["BCTC IS quý"], "B": ["BCTC IS quý", "giá"]})
    assert summary == {"BCTC IS quý": 2, "giá": 1} and next(iter(summary)) == "BCTC IS quý"
