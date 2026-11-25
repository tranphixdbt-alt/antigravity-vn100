"""D121: không ghi số của phiên đang giao dịch (lỗi MCH 25/11/2026: đóng cửa 133.000 ghi lúc giữa phiên, phiên thật
đóng 130.000). Không gọi mạng: nguồn giá giả, DB SQLite trong bộ nhớ."""

import datetime as dt
from zoneinfo import ZoneInfo

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from valuation.db.models import PricesDaily, Ticker
from valuation.db.session import Base
from valuation.ingest import pipeline, session_guard

VN = ZoneInfo("Asia/Ho_Chi_Minh")
WED = dt.datetime(2026, 11, 25, 10, 5, tzinfo=VN)  # thứ Tư, giữa phiên


def test_unfinished_session_date_switches_at_close():
    assert session_guard.unfinished_session_date(WED) == dt.date(2026, 11, 25)
    assert session_guard.unfinished_session_date(
        WED.replace(hour=14, minute=59)
    ) == dt.date(2026, 11, 25)
    assert session_guard.unfinished_session_date(WED.replace(hour=15, minute=0)) is None
    assert (
        session_guard.unfinished_session_date(WED.replace(hour=15, minute=45)) is None
    )
    # đồng hồ UTC vẫn quy về giờ VN: 03:05 UTC = 10:05 VN
    assert session_guard.unfinished_session_date(
        WED.astimezone(dt.timezone.utc)
    ) == dt.date(2026, 11, 25)


def test_drop_unfinished_session_handles_timestamp_date_and_string():
    df = pd.DataFrame(
        {
            "time": [pd.Timestamp("2026-11-24"), pd.Timestamp("2026-11-25")],
            "close": [1.0, 2.0],
        }
    )
    assert session_guard.drop_unfinished_session(df, WED)["close"].tolist() == [1.0]
    flows = pd.DataFrame(
        {"time": [dt.date(2026, 11, 24), dt.date(2026, 11, 25)], "net_val": [1.0, 2.0]}
    )
    assert session_guard.drop_unfinished_session(flows, WED)["net_val"].tolist() == [
        1.0
    ]
    text = pd.DataFrame({"time": ["2026-11-24", "2026-11-25"], "v": [1, 2]})
    assert session_guard.drop_unfinished_session(text, WED)["v"].tolist() == [1]
    after = WED.replace(hour=15, minute=45)
    assert (
        session_guard.drop_unfinished_session(df, after) is df
    )  # sau giờ đóng phiên: giữ nguyên
    assert session_guard.drop_unfinished_session(pd.DataFrame(), WED).empty


@pytest.fixture
def mem_db(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(pipeline, "SessionLocalWrite", factory)
    with factory() as db:
        db.add(Ticker(ticker="MCH", company_name="MCH", is_vn100=True))
        db.commit()
    return factory


def _fake_source(monkeypatch, rows):
    def prices(ticker, start, *a, **k):
        df = pd.DataFrame(rows)
        df.attrs.update(source="vci", price_unit="thousand_VND")
        return df

    monkeypatch.setattr(pipeline.vnstock_client, "get_historical_prices", prices)
    monkeypatch.setattr(pipeline, "_overlap_was_readjusted", lambda t, df: False)


def test_run_ingest_mid_session_does_not_write_today(monkeypatch, mem_db):
    # Tái hiện 25/11/2026 10:05: nguồn trả cả nến phiên đang chạy của MCH → trước D121 bị ghi thành "phiên mới nhất".
    monkeypatch.setattr(session_guard, "now_vn", lambda: WED)
    _fake_source(
        monkeypatch,
        [
            {
                "time": pd.Timestamp("2026-11-23"),
                "open": 132.0,
                "high": 133.7,
                "low": 130.4,
                "close": 132.8,
                "volume": 226560,
            },
            {
                "time": pd.Timestamp("2026-11-25"),
                "open": 132.8,
                "high": 133.1,
                "low": 132.5,
                "close": 133.0,
                "volume": 22200,
            },
        ],
    )
    res = pipeline.run_ingest("MCH", ["prices"], include_market_flows=False)
    assert (
        res["prices"]["status"] == "UPDATED"
        and res["prices"]["last_date"] == "2026-11-23"
    )
    with mem_db() as db:
        dates = [
            r[0]
            for r in db.query(PricesDaily.trade_date)
            .filter_by(ticker="MCH")
            .order_by(PricesDaily.trade_date)
        ]
    assert dates == [dt.date(2026, 11, 23)]


def test_run_ingest_after_close_writes_today(monkeypatch, mem_db):
    monkeypatch.setattr(
        session_guard, "now_vn", lambda: WED.replace(hour=15, minute=45)
    )
    _fake_source(
        monkeypatch,
        [
            {
                "time": pd.Timestamp("2026-11-23"),
                "open": 132.0,
                "high": 133.7,
                "low": 130.4,
                "close": 132.8,
                "volume": 226560,
            },
            {
                "time": pd.Timestamp("2026-11-25"),
                "open": 132.8,
                "high": 133.1,
                "low": 129.8,
                "close": 130.0,
                "volume": 472904,
            },
        ],
    )
    res = pipeline.run_ingest("MCH", ["prices"], include_market_flows=False)
    assert res["prices"]["last_date"] == "2026-11-25"
    with mem_db() as db:
        close = (
            db.query(PricesDaily.close)
            .filter_by(ticker="MCH", trade_date=dt.date(2026, 11, 25))
            .scalar()
        )
    assert close == 130000.0  # nghìn đồng × 1000, số đóng cửa thật


def test_run_ingest_only_today_mid_session_is_reported_not_written(monkeypatch, mem_db):
    monkeypatch.setattr(session_guard, "now_vn", lambda: WED)
    _fake_source(
        monkeypatch,
        [
            {
                "time": pd.Timestamp("2026-11-25"),
                "open": 1.0,
                "high": 1.0,
                "low": 1.0,
                "close": 1.0,
                "volume": 1,
            },
        ],
    )
    res = pipeline.run_ingest("MCH", ["prices"], include_market_flows=False)
    assert res["prices"]["status"] == "FAILED" and "chưa chốt" in res["prices"]["error"]
