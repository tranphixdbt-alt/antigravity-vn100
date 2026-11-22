"""Test nạp TPCP_10Y từ worldgovernmentbonds.com (D100) — OFFLINE, DB SQLite trong bộ nhớ.

Số trong mẫu lấy từ chuỗi thật của WGB (bond-historical-data/vietnam/10-years, đọc 22/11/2026):
19/11 = 4,568; 20/11 = 4,568; cuối tuần 21–22/11 lặp 4,568.
"""
import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from valuation.db.models import Base, MacroSeries
from valuation.ingest import tpcp_wgb as w
from valuation.ingest.macro_store import MacroPoint, upsert_macro_series

D = datetime.date
CFG = w.WgbConfig(
    url="https://www.worldgovernmentbonds.com/bond-historical-data/vietnam/10-years/",
    lookback_days=45,
    min_pct=0.5,
    max_pct=15.0,
    alert_after_days=21,
    page_timeout_sec=60,
)


def _q(day: str, val: float) -> dict:
    return {"CLOSE_VAL": val, "DATA_VAL": day, "TIME_VAL": f"{day} 15:15:10", "EXTRA_1": "0", "EXTRA_2": "0"}


# Dạng WGB trả: dict khóa "1".."n"
RAW = {
    "1": _q("2026-11-18", 4.572),
    "2": _q("2026-11-19", 4.568),
    "3": _q("2026-11-20", 4.568),
    "4": _q("2026-11-21", 4.568),  # thứ Bảy
    "5": _q("2026-11-22", 4.568),  # Chủ nhật
    "6": _q("2026-11-23", 4.561),  # thứ Hai
    "7": _q("2026-11-24", 4.555),  # thứ Ba
    "8": _q("2026-11-25", 4.550),  # thứ Tư = hôm nay trong test → chưa chốt, không ghi
}
TODAY = D(2026, 11, 25)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _seed_investing(db) -> None:
    """Như DB VPS: 18–20/11 nạp tay từ investing.com (18/11 = 4,571%, WGB ghi 4,572% → không được ghi đè)."""
    upsert_macro_series(
        [
            MacroPoint("TPCP_10Y", D(2026, 11, 18), 0.04571, "investing.com"),
            MacroPoint("TPCP_10Y", D(2026, 11, 19), 0.04568, "investing.com"),
            MacroPoint("TPCP_10Y", D(2026, 11, 20), 0.04568, "investing.com"),
        ],
        db,
    )


def _rows(db):
    return (
        db.query(MacroSeries.date, MacroSeries.value, MacroSeries.source)
        .filter(MacroSeries.indicator_code == "TPCP_10Y")
        .order_by(MacroSeries.date)
        .all()
    )


# ---------------- parse ----------------
def test_parse_sorts_and_reads_percent():
    rev = dict(reversed(list(RAW.items())))
    out = w.parse_wgb_quotes(rev)
    assert out[0] == (D(2026, 11, 18), 4.572)
    assert out[-1] == (D(2026, 11, 25), 4.550)
    assert [d for d, _ in out] == sorted(d for d, _ in out)
    assert w.parse_wgb_quotes(list(RAW.values())) == w.parse_wgb_quotes(RAW)  # dạng list cũng nhận


@pytest.mark.parametrize(
    "bad",
    [
        {"1": {"DATA_VAL": "2026-11-20"}},  # thiếu CLOSE_VAL
        {"1": {"CLOSE_VAL": 4.5, "DATA_VAL": "20/11/2026"}},  # ngày sai dạng
        {"1": {"CLOSE_VAL": None, "DATA_VAL": "2026-11-20"}},  # số rỗng
        {"1": {"CLOSE_VAL": "n.a.", "DATA_VAL": "2026-11-20"}},  # chữ
        {},  # rỗng
        "html thay vì JSON",
    ],
)
def test_parse_rejects_malformed(bad):
    with pytest.raises((ValueError, TypeError)):
        w.parse_wgb_quotes(bad)


# ---------------- chọn điểm ----------------
HAVE_18_20 = {D(2026, 11, 18), D(2026, 11, 19), D(2026, 11, 20)}


def test_select_only_missing_weekdays_before_today():
    """Tính tay: DB có 18–20/11, hôm nay 25/11 → chỉ 23/11 (T2) và 24/11 (T3).
    Bỏ 18–20/11 (đã có), 21–22/11 (cuối tuần), 25/11 (hôm nay). 4,561% → 0,04561."""
    pts = w.select_new_points(w.parse_wgb_quotes(RAW), HAVE_18_20, TODAY, CFG)
    assert [(p.date, p.value) for p in pts] == [(D(2026, 11, 23), 0.04561), (D(2026, 11, 24), 0.04555)]
    assert all(p.indicator_code == "TPCP_10Y" and p.source == "worldgovernmentbonds.com" for p in pts)


def test_select_fills_gap_without_touching_existing():
    """DB có 18/11 và 20/11 nhưng thiếu 19/11 (job lỡ) → lấp 19/11 = 4,568% → 0,04568; 18, 20 giữ nguyên."""
    pts = w.select_new_points(w.parse_wgb_quotes(RAW), {D(2026, 11, 18), D(2026, 11, 20)}, TODAY, CFG)
    assert [(p.date, p.value) for p in pts] == [
        (D(2026, 11, 19), 0.04568),
        (D(2026, 11, 23), 0.04561),
        (D(2026, 11, 24), 0.04555),
    ]


def test_select_respects_lookback_when_db_empty():
    """DB trống, lookback 3 ngày từ 25/11 → từ 22/11: chỉ 23/11, 24/11."""
    cfg = w.WgbConfig(**{**CFG.__dict__, "lookback_days": 3})
    pts = w.select_new_points(w.parse_wgb_quotes(RAW), set(), TODAY, cfg)
    assert [p.date for p in pts] == [D(2026, 11, 23), D(2026, 11, 24)]


def test_select_rejects_out_of_range_value():
    raw = {"1": _q("2026-11-23", 45.61)}  # nhầm đơn vị (×10) → phải dừng, không ghi
    with pytest.raises(ValueError, match="ngoài khoảng"):
        w.select_new_points(w.parse_wgb_quotes(raw), HAVE_18_20, TODAY, CFG)


# ---------------- cảnh báo ----------------
def test_alert_threshold_hand_calc():
    """Điểm cuối 20/11: 11/12 cũ 21 ngày → chưa báo; 12/12 cũ 22 ngày → báo.
    Cờ chặn khi > 30 ngày → ngày chặn đầu tiên 20/11 + 31 = 21/12/2026."""
    last = D(2026, 11, 20)
    assert w.stale_alert_message(last, 0.04568, D(2026, 12, 11), 21) is None
    msg = w.stale_alert_message(last, 0.04568, D(2026, 12, 12), 21)
    assert msg is not None
    assert "cũ 22 ngày" in msg and "20/11/2026" in msg and "4.568%" in msg
    assert "sẽ bị chặn" in msg and "21/12/2026" in msg
    blocked = w.stale_alert_message(last, 0.04568, D(2026, 12, 21), 21)
    assert "ĐANG chặn" in blocked


def test_alert_when_series_empty_and_carries_error():
    msg = w.stale_alert_message(None, None, TODAY, 21, fetch_error="TimeoutError: x")
    assert "chưa có điểm" in msg and "TimeoutError" in msg


# ---------------- chạy cả job trên DB ----------------
def test_run_writes_then_rerun_is_idempotent(db):
    _seed_investing(db)
    sent: list[str] = []
    r1 = w.run_tpcp_update(db, TODAY, fetcher=lambda u: RAW, notifier=lambda m: sent.append(m) or True, cfg=CFG)
    assert r1["written"] == 2 and r1["error"] is None and r1["alert"] is None
    r2 = w.run_tpcp_update(db, TODAY, fetcher=lambda u: RAW, notifier=lambda m: sent.append(m) or True, cfg=CFG)
    assert r2["written"] == 0 and r2["points"] == []
    rows = _rows(db)
    assert len(rows) == 5  # 18–20/11 (investing) + 23/11 + 24/11
    assert rows[0][2] == "investing.com" and float(rows[0][1]) == pytest.approx(0.04571)  # không ghi đè
    assert rows[-1][2] == "worldgovernmentbonds.com" and float(rows[-1][1]) == pytest.approx(0.04555)
    assert r2["last_date"] == "2026-11-24" and r2["age_days"] == 1
    assert sent == []


def test_run_dry_run_writes_nothing(db):
    _seed_investing(db)
    r = w.run_tpcp_update(db, TODAY, fetcher=lambda u: RAW, notifier=lambda m: True, cfg=CFG, dry_run=True)
    assert len(r["points"]) == 2 and r["written"] == 0
    assert len(_rows(db)) == 3


def test_run_fetch_error_still_alerts_when_stale(db):
    _seed_investing(db)
    sent: list[str] = []

    def boom(url):
        raise TimeoutError("trang không render")

    r = w.run_tpcp_update(db, D(2026, 12, 14), fetcher=boom, notifier=lambda m: sent.append(m) or True, cfg=CFG)
    assert r["error"].startswith("TimeoutError") and r["written"] == 0
    assert r["alert_sent"] is True and len(sent) == 1
    assert "cũ 24 ngày" in sent[0] and "TimeoutError" in sent[0]


def test_run_fetch_error_fresh_data_no_alert(db):
    _seed_investing(db)
    sent: list[str] = []

    def boom(url):
        raise TimeoutError("x")

    r = w.run_tpcp_update(db, TODAY, fetcher=boom, notifier=lambda m: sent.append(m) or True, cfg=CFG)
    assert r["error"] is not None and r["alert"] is None and sent == []


def test_run_rejects_host_outside_allowlist(db):
    called: list[str] = []
    cfg = w.WgbConfig(**{**CFG.__dict__, "url": "https://evil.example.com/x"})
    r = w.run_tpcp_update(db, TODAY, fetcher=lambda u: called.append(u) or RAW, notifier=lambda m: True, cfg=cfg)
    assert called == [] and "allowed_domains" in r["error"]


def test_short_error_one_line_and_capped():
    exc = RuntimeError("BrowserType.launch: Executable doesn't exist\n╔══╗\n║ playwright install ║\n╚══╝")
    assert w.short_error(exc) == "RuntimeError: BrowserType.launch: Executable doesn't exist"
    long = w.short_error(ValueError("x" * 1000), max_len=50)
    assert len(long) == 50 and long.endswith("…")
    assert w.short_error(TimeoutError()) == "TimeoutError"


def test_request_filter_blocks_third_party():
    allowed = {"www.worldgovernmentbonds.com", "worldgovernmentbonds.com"}
    assert w.request_allowed("https://www.worldgovernmentbonds.com/wp-json/common/v1/historical", allowed)
    assert not w.request_allowed("https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js", allowed)
    assert not w.request_allowed("data:image/png;base64,xx", allowed)


def test_config_loads_from_defaults():
    cfg = w.load_wgb_config()
    assert cfg.alert_after_days == 21 and cfg.min_pct < 4.568 < cfg.max_pct
    assert "worldgovernmentbonds.com" in cfg.url
