"""D121: báo Discord khi dữ liệu cũ, báo job lỗi, quét bù mã thiếu. Không gọi mạng."""

import datetime as dt
import importlib.util
import json
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from valuation.db.models import MacroSeries, PricesDaily, Ticker
from valuation.db.session import Base
from valuation.services import data_update_job
from valuation.services import freshness_alert as fa

VN = ZoneInfo("Asia/Ho_Chi_Minh")
CFG = fa.FreshnessConfig(
    close="15:00",
    after_close_check="16:00",
    max_lag_weekdays=1,
    min_tickers=2,
    macro_max_age_days={"CPI_YOY": 50, "GDP_YOY": 125},
    macro_alert_weekdays=(0,),
)


def test_expected_session_and_weekday_lag():
    wed_morning = dt.datetime(2026, 11, 25, 8, 20, tzinfo=VN)
    assert fa.expected_session(wed_morning, "16:00") == dt.date(2026, 11, 24)
    assert fa.expected_session(
        wed_morning.replace(hour=16, minute=10), "16:00"
    ) == dt.date(2026, 11, 25)
    mon_morning = dt.datetime(2026, 11, 23, 8, 20, tzinfo=VN)
    assert fa.expected_session(mon_morning, "16:00") == dt.date(
        2026, 11, 20
    )  # bỏ thứ Bảy, Chủ nhật
    sat = dt.datetime(2026, 11, 28, 18, 0, tzinfo=VN)
    assert fa.expected_session(sat, "16:00") == dt.date(2026, 11, 27)
    # tính tay: 20/11 (T6) → 25/11 (T4) là 23, 24, 25 = 3 ngày làm việc; qua cuối tuần không tính
    assert fa.weekday_lag(dt.date(2026, 11, 20), dt.date(2026, 11, 25)) == 3
    assert fa.weekday_lag(dt.date(2026, 11, 25), dt.date(2026, 11, 25)) == 0


def test_price_problems_tolerates_one_holiday_but_not_two_days():
    universe = {"AAA", "BBB", "CCC"}
    # 25/11 08:20: DB có 23/11, ngày 24/11 sàn nghỉ → chậm 1 ngày, chịu được
    morning = dt.datetime(2026, 11, 25, 8, 20, tzinfo=VN)
    assert (
        fa.price_problems(dt.date(2026, 11, 23), universe, universe, morning, CFG) == []
    )
    # 25/11 16:10 mà vẫn 23/11 → chậm 2 ngày làm việc → báo
    msg = fa.price_problems(
        dt.date(2026, 11, 23),
        universe,
        universe,
        morning.replace(hour=16, minute=10),
        CFG,
    )
    assert msg and "chậm 2 ngày làm việc" in msg[0] and "nghỉ lễ" in msg[0]
    # dòng lạc của một mã (MCH 25/11): phiên mới nhất chỉ 1/3 mã → báo thiếu mã
    lone = fa.price_problems(dt.date(2026, 11, 25), {"AAA"}, universe, morning, CFG)
    assert lone == ["Phiên 25/11/2026 chỉ 1/3 mã VN100 có giá; thiếu: BBB, CCC."]
    assert fa.price_problems(None, set(), universe, morning, CFG) == [
        "Chưa có giá nào của rổ VN100 trong DB."
    ]


def test_macro_problems_by_period_age():
    today = dt.date(2026, 11, 26)
    latest = {"CPI_YOY": dt.date(2026, 9, 30), "GDP_YOY": dt.date(2026, 9, 30)}
    out = fa.macro_problems(latest, today, CFG)
    assert out == [
        "CPI_YOY: kỳ mới nhất 30/09/2026, cũ 57 ngày (ngưỡng 50)."
    ]  # 30/9 → 26/11 = 57 ngày (tính tay)
    assert fa.macro_problems({"CPI_YOY": dt.date(2026, 10, 31)}, today, CFG) == [
        "GDP_YOY: chưa có số nào."
    ]


@pytest.fixture
def mem_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add_all(
        [Ticker(ticker=t, company_name=t, is_vn100=True) for t in ("AAA", "BBB")]
    )
    db.add_all(
        [
            PricesDaily(ticker="AAA", trade_date=dt.date(2026, 11, 20), close=1.0),
            PricesDaily(ticker="BBB", trade_date=dt.date(2026, 11, 20), close=1.0),
            MacroSeries(
                indicator_code="CPI_YOY",
                date=dt.date(2026, 9, 30),
                value=0.0508,
                source="nso.gov.vn",
            ),
            MacroSeries(
                indicator_code="GDP_YOY",
                date=dt.date(2026, 9, 30),
                value=0.0995,
                source="nso.gov.vn",
            ),
        ]
    )
    db.commit()
    yield db
    db.close()


def test_run_check_sends_one_message_and_macro_only_on_monday(mem_db):
    sent = []
    wed = dt.datetime(2026, 11, 25, 16, 10, tzinfo=VN)
    res = fa.run_check(mem_db, wed, notifier=lambda m: sent.append(m) or True, cfg=CFG)
    assert res["latest_price"] == "2026-11-20" and res["tickers_on_latest"] == 2
    assert res["macro_checked"] is False and res["sent"] is True and len(sent) == 1
    assert sent[0].startswith(
        "Dữ liệu btinvest.vn cần xem:\n- Giá: Giá mới nhất trong DB là phiên 20/11/2026"
    )
    mon = dt.datetime(2026, 11, 30, 8, 20, tzinfo=VN)
    res = fa.run_check(mem_db, mon, notifier=lambda m: True, cfg=CFG, dry_run=True)
    assert res["macro_checked"] and res["macro_problems"] == [
        "CPI_YOY: kỳ mới nhất 30/09/2026, cũ 61 ngày (ngưỡng 50)."
    ]
    assert res["sent"] is False  # dry-run không gửi


def test_run_check_quiet_when_fresh(mem_db):
    mem_db.add_all(
        [
            PricesDaily(ticker=t, trade_date=dt.date(2026, 11, 25), close=1.0)
            for t in ("AAA", "BBB")
        ]
    )
    mem_db.commit()
    res = fa.run_check(
        mem_db,
        dt.datetime(2026, 11, 26, 8, 20, tzinfo=VN),
        notifier=lambda m: 1 / 0,
        cfg=CFG,
    )
    assert res["message"] is None and res["sent"] is False


def test_job_failure_message_has_no_log_content_and_validates_name():
    spec = importlib.util.spec_from_file_location(
        "notify_job_failure", "scripts/notify_job_failure.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    msg = mod.message("web-user-backup", 1, dt.datetime(2026, 11, 26, 23, 0, tzinfo=VN))
    assert msg == (
        "Job `web-user-backup` trên vn100-worker lỗi (mã thoát 1) lúc 23:00 26/11/2026. "
        "Xem nhật ký /app/logs/web-user-backup.log trong container vn100-worker."
    )
    with pytest.raises(ValueError):
        mod.message("x; rm -rf /", 1, dt.datetime(2026, 11, 26, tzinfo=VN))


def _status(tmp_path, **kw):
    base = {
        "status": "DONE",
        "finished_at": "2026-11-23T10:01:57+07:00",
        "missing": {"TMP": ["BCTC BS quý", "BCTC IS năm"], "VNM": ["giá"], "XYZ": []},
    }
    (tmp_path / "status.json").write_text(json.dumps({**base, **kw}), encoding="utf-8")


def test_retry_missing_calls_only_missing_parts(tmp_path):
    _status(tmp_path)
    calls = []

    def fake_run(t, types, include_yearly):
        calls.append((t, types, include_yearly))
        return {
            "errors": (
                [{"component": "financials", "statement": "BS", "period": "quarter"}]
                if t == "TMP"
                else []
            )
        }

    out = data_update_job.retry_missing(
        tmp_path, run=fake_run, sleep=lambda s: None, today="2026-11-23"
    )
    assert calls == [("TMP", ["financials"], True), ("VNM", ["prices"], False)]
    assert out["still_missing"] == {"TMP": ["BCTC BS quý"]}
    assert json.loads((tmp_path / "retry.json").read_text(encoding="utf-8"))[
        "tried"
    ] == {"TMP": ["financials"], "VNM": ["prices"]}


def test_retry_missing_skips_when_scan_not_today_or_not_done(tmp_path):
    _status(tmp_path)
    out = data_update_job.retry_missing(
        tmp_path, run=lambda *a, **k: 1 / 0, today="2026-11-24"
    )
    assert out["skipped"] and out["tried"] == {}
    _status(tmp_path, status="RUNNING")
    assert data_update_job.retry_missing(
        tmp_path, run=lambda *a, **k: 1 / 0, today="2026-11-23"
    )["skipped"]
