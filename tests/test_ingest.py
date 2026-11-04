import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from valuation.db.models import FinancialsQuarterly, PricesDaily, Ticker
from valuation.db.session import Base
from valuation.ingest import pipeline
from valuation.ingest.normalizer import normalize_daily_prices, unpivot_financials


def test_normalize_daily_prices():
    # Input mockup
    data = {
        "time": ["2026-01-01", "2026-01-02"],
        "open": [56.29, 55.0],
        "high": [57.0, 56.1],
        "low": [55.1, 54.0],
        "close": [56.29, 55.5],
        "volume": [1000, 2000],
    }
    df = pd.DataFrame(data)
    df_norm = normalize_daily_prices(df)

    assert df_norm.iloc[0]["open"] == 56290.0
    assert df_norm.iloc[0]["close"] == 56290.0
    assert df_norm.iloc[1]["high"] == 56100.0
    assert df_norm.iloc[1]["low"] == 54000.0
    assert df_norm.iloc[0]["volume"] == 1000  # volume ko doi
    assert "price_unit" in df_norm.columns
    assert df_norm.iloc[0]["price_unit"] == "VND"


def test_unpivot_financials():
    data = {
        "item": ["Tiền mặt", "Tài sản cố định"],
        "item_en": ["Cash", "Fixed Assets"],
        "item_id": ["cash", "fixed_assets"],
        "2024-Q1": [1000.0, 5000.0],
        "2023-Q4": [900.0, 4800.0],
    }
    df_wide = pd.DataFrame(data)

    df_long = unpivot_financials(df_wide, "BS")

    # Kì vọng: 2 dòng * 2 quý = 4 dòng
    assert len(df_long) == 4

    # Test cash quý 1/2024
    cash_2024q1 = df_long[
        (df_long["line_item"] == "cash")
        & (df_long["fiscal_year"] == 2024)
        & (df_long["fiscal_quarter"] == 1)
    ]
    assert len(cash_2024q1) == 1
    assert cash_2024q1.iloc[0]["value"] == 1000.0
    assert cash_2024q1.iloc[0]["statement"] == "BS"
    assert cash_2024q1.iloc[0]["is_consolidated"]
    assert not cash_2024q1.iloc[0]["is_restated"]


def test_missing_publication_date_is_python_none():
    frame = pd.DataFrame({"item_id": ["net_sales"], "2026-Q2": [100.0]})

    result = unpivot_financials(frame, "IS")

    assert result.iloc[0]["published_at"] is None


def test_legacy_duplicate_item_ids_are_preserved_with_distinct_keys():
    frame = pd.DataFrame(
        {
            "item": [
                "Tiền gửi và vay các Tổ chức tín dụng khác",
                "Tiền gửi của các tổ chức tín dụng khác",
                "Tài sản Có khác",
                "Tài sản Có khác",
            ],
            "item_en": [
                "Deposits and Loans from other credit institutions",
                "Deposits and Loans from other credit institutions",
                "Other assets",
                "Other assets",
            ],
            "item_id": [
                "deposits_and_loans_from_other_credit_institutions",
                "deposits_and_loans_from_other_credit_institutions",
                "other_assets",
                "other_assets",
            ],
            "2026-Q2": [372.0, 332.0, 67.0, 5.0],
        }
    )

    result = unpivot_financials(frame, "BS")

    assert len(result) == 4
    assert result["line_item"].is_unique
    assert sorted(result["value"].tolist()) == [5.0, 67.0, 332.0, 372.0]


def test_run_ingest_reports_partial_instead_of_false_success(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(pipeline, "SessionLocalWrite", factory)
    with factory() as db:
        db.add(Ticker(ticker="AAA", company_name="AAA", is_vn100=True))
        db.commit()

    prices = pd.DataFrame(
        {
            "time": ["2026-09-10"],
            "open": [10.0],
            "high": [10.0],
            "low": [10.0],
            "close": [10.0],
            "volume": [100],
        }
    )
    monkeypatch.setattr(
        pipeline.vnstock_client, "get_historical_prices", lambda *_: prices
    )
    monkeypatch.setattr(
        pipeline.vnstock_client,
        "get_financials",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("bad BCTC")),
    )

    result = pipeline.run_ingest(
        "AAA",
        data_types=["prices", "financials"],
        incremental=True,
        include_yearly=False,
        include_market_flows=False,
    )

    assert result["status"] == "PARTIAL"
    assert result["prices"]["status"] == "UPDATED"
    assert len(result["errors"]) == 3
    assert {entry["statement"] for entry in result["errors"]} == {"BS", "IS", "CF"}


def test_financial_upsert_is_idempotent_and_does_not_overwrite_history(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    monkeypatch.setattr(pipeline, "SessionLocalWrite", session_factory)
    db = session_factory()
    db.add(Ticker(ticker="AAA", company_name="AAA", is_vn100=True))
    db.commit()
    db.close()

    base = {
        "fiscal_year": 2026,
        "fiscal_quarter": 1,
        "is_consolidated": True,
        "is_restated": False,
        "statement": "BS",
        "line_item": "total_assets",
        "currency": "VND",
    }
    pipeline.upsert_financials(pd.DataFrame([{**base, "value": 100.0}]), "AAA")
    pipeline.upsert_financials(pd.DataFrame([{**base, "value": 200.0}]), "AAA")

    db = session_factory()
    rows = db.query(FinancialsQuarterly).all()
    assert len(rows) == 1
    assert float(rows[0].value) == 100.0
    db.close()


def test_incremental_prices_refetch_full_history_after_retroactive_adjustment(monkeypatch):
    # vnstock trả giá ĐÃ điều chỉnh hồi tố. Sau một đợt thưởng 66,9% (PVD 07/2026),
    # đoạn chồng lấn tải incremental lệch với DB → phải tải lại toàn bộ, nếu không
    # lịch sử cũ giữ giá chưa điều chỉnh và chuỗi gãy −40% trong một phiên.
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(pipeline, "SessionLocalWrite", factory)
    with factory() as db:
        db.add(Ticker(ticker="AAA", company_name="AAA", is_vn100=True))
        for d in ("2026-06-01", "2026-07-01", "2026-07-02"):
            db.add(PricesDaily(ticker="AAA", trade_date=pd.Timestamp(d).date(), close=30000))
        db.commit()

    factor = 1.669
    full = pd.DataFrame(
        {
            "time": ["2026-06-01", "2026-07-01", "2026-07-02", "2026-07-15"],
            "open": [30.0 / factor] * 3 + [18.1],
            "high": [30.0 / factor] * 3 + [18.1],
            "low": [30.0 / factor] * 3 + [18.1],
            "close": [30.0 / factor] * 3 + [18.1],
            "volume": [100] * 4,
        }
    )
    calls = []

    def fake_history(_ticker, start):
        calls.append(start)
        return full[pd.to_datetime(full["time"]) >= pd.Timestamp(start)].reset_index(drop=True)

    monkeypatch.setattr(pipeline.vnstock_client, "get_historical_prices", fake_history)

    result = pipeline.run_ingest(
        "AAA", data_types=["prices"], incremental=True, include_market_flows=False
    )

    assert result["prices"]["full_refresh"] is True
    assert min(calls) <= "2026-06-01"
    with factory() as db:
        closes = [
            float(c)
            for (c,) in db.query(PricesDaily.close)
            .filter(PricesDaily.ticker == "AAA")
            .order_by(PricesDaily.trade_date)
        ]
    assert closes[0] == pytest.approx(30000 / factor)
    assert all(abs(b / a - 1) < 0.07 for a, b in zip(closes, closes[1:]))


def test_incremental_prices_skip_full_refetch_when_overlap_unchanged(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(pipeline, "SessionLocalWrite", factory)
    with factory() as db:
        db.add(Ticker(ticker="AAA", company_name="AAA", is_vn100=True))
        db.add(PricesDaily(ticker="AAA", trade_date=pd.Timestamp("2026-07-02").date(), close=30000))
        db.commit()
    calls = []

    def fake_history(_ticker, start):
        calls.append(start)
        return pd.DataFrame(
            {"time": ["2026-07-02", "2026-07-03"], "open": [30.0, 30.2], "high": [30.0, 30.2],
             "low": [30.0, 30.2], "close": [30.0, 30.2], "volume": [100, 100]}
        )

    monkeypatch.setattr(pipeline.vnstock_client, "get_historical_prices", fake_history)
    result = pipeline.run_ingest(
        "AAA", data_types=["prices"], incremental=True, include_market_flows=False
    )
    assert len(calls) == 1
    assert result["prices"]["full_refresh"] is False


def test_run_ingest_new_subsidiary_is_not_added_to_vn100(monkeypatch):
    """Công ty con niêm yết ingest cho SOTP (is_vn100=False) không được lọt vào rổ VN100."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(pipeline, "SessionLocalWrite", factory)
    monkeypatch.setattr(
        pipeline.vnstock_client,
        "get_company_overview",
        lambda _t: pd.DataFrame([{"organ_name": "Sub", "sector": "Utilities"}]),
    )
    prices = pd.DataFrame(
        {"time": ["2026-10-19"], "open": [10.0], "high": [10.0], "low": [10.0], "close": [10.0], "volume": [1]}
    )
    monkeypatch.setattr(pipeline.vnstock_client, "get_historical_prices", lambda *_: prices)

    kwargs = {"data_types": ["prices"], "include_yearly": False, "include_market_flows": False, "is_vn100": False}
    assert pipeline.run_ingest("SUB", **kwargs)["status"] == "SUCCESS"
    assert pipeline.run_ingest("SUB", **kwargs)["status"] == "SUCCESS"  # chạy lại: không nhân đôi
    with factory() as db:
        assert db.get(Ticker, "SUB").is_vn100 is False
        assert db.query(PricesDaily).filter(PricesDaily.ticker == "SUB").count() == 1


def test_weekly_update_refreshes_sotp_subsidiaries_outside_vn100(monkeypatch):
    """Công ty con SOTP ngoài VN100 được làm mới hàng tuần với is_vn100=False; mã VN100 không bị chạy hai lần."""
    import valuation.config as cfg_mod
    from valuation.ingest import weekly_updater

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        db.add(Ticker(ticker="HOLD", company_name="HOLD", is_vn100=True))
        db.add(Ticker(ticker="LIST", company_name="LIST", is_vn100=True))
        db.commit()
    calls = []

    def fake_ingest(ticker, data_types, **kw):
        calls.append((ticker, kw.get("is_vn100", True)))
        return {"status": "SUCCESS", "prices": {"status": "UPDATED"}, "errors": []}

    monkeypatch.setattr(weekly_updater, "run_ingest", fake_ingest)
    monkeypatch.setattr(weekly_updater, "_CONSENSUS_SOURCES", ())
    monkeypatch.setattr(weekly_updater.time, "sleep", lambda _s: None)
    holdings = {"holders": {"HOLD": {"holdings": [{"ticker": "LIST"}, {"ticker": "sub"}]}}}
    monkeypatch.setattr(cfg_mod, "load_sotp_holdings", lambda: holdings)

    with factory() as db:
        out = weekly_updater.run_weekly_auto_update(db)
    assert out["sotp_subs"] == {"SUB": "SUCCESS"}
    assert ("SUB", False) in calls
    assert [t for t, _ in calls].count("LIST") == 1


def test_latest_ended_quarter_and_financials_due():
    # Tính tay: 04/11/2026 → quý vừa kết thúc là Q3/2026; tháng 1–3 → Q4 năm trước.
    import datetime as dt

    assert pipeline.latest_ended_quarter(dt.date(2026, 11, 4)) == (2026, 3)
    assert pipeline.latest_ended_quarter(dt.date(2026, 3, 31)) == (2025, 4)
    assert pipeline.latest_ended_quarter(dt.date(2026, 4, 1)) == (2026, 1)
    assert pipeline.latest_ended_quarter(dt.date(2027, 1, 15)) == (2026, 4)
    today = dt.date(2026, 11, 4)
    assert pipeline.financials_due(None, today) is True  # chưa có BCTC nào
    assert pipeline.financials_due((2026, 2), today) is True  # thiếu Q3/2026 → kéo
    assert pipeline.financials_due((2026, 3), today) is False  # đã có quý mới nhất → bỏ qua


def test_run_ingest_parallel_fetches_concurrently_with_same_result(monkeypatch):
    # D92: nút "Tải mới"/tự tải khi mở mã gọi mạng cùng lúc; ghi DB vẫn tuần tự nên kết quả
    # phải y hệt chạy tuần tự (đợt quét VN100 vẫn dùng parallel=False).
    import threading
    import time

    lock = threading.Lock()
    inflight = {"now": 0, "max": 0}

    def slow(frame):
        def fetch(*_args, **_kwargs):
            with lock:
                inflight["now"] += 1
                inflight["max"] = max(inflight["max"], inflight["now"])
            time.sleep(0.1)
            with lock:
                inflight["now"] -= 1
            return frame.copy()

        return fetch

    prices = pd.DataFrame(
        {
            "time": ["2026-09-10"],
            "open": [10.0],
            "high": [10.0],
            "low": [10.0],
            "close": [10.0],
            "volume": [100],
        }
    )
    fin = pd.DataFrame(
        {"item": ["Tiền mặt"], "item_en": ["Cash"], "item_id": ["cash"], "2026-Q3": [1000.0]}
    )
    flow = pd.DataFrame(
        {
            "time": [pd.Timestamp("2026-09-10").date()],
            "buy_vol": [1.0],
            "buy_val": [10.0],
            "sell_vol": [0.0],
            "sell_val": [0.0],
            "net_vol": [1.0],
            "net_val": [10.0],
        }
    )
    monkeypatch.setattr(pipeline.vnstock_client, "get_historical_prices", slow(prices))
    monkeypatch.setattr(pipeline.vnstock_client, "get_financials", slow(fin))
    monkeypatch.setattr(pipeline.market_client, "fetch_foreign_flow", slow(flow))
    monkeypatch.setattr(pipeline.market_client, "fetch_proprietary_flow", slow(flow))

    out = {}
    for parallel in (False, True):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        factory = sessionmaker(bind=engine)
        monkeypatch.setattr(pipeline, "SessionLocalWrite", factory)
        with factory() as db:
            db.add(Ticker(ticker="AAA", company_name="AAA", is_vn100=True))
            db.commit()
        inflight["max"] = 0
        result = pipeline.run_ingest(
            "AAA",
            data_types=["prices", "financials"],
            incremental=True,
            include_yearly=True,
            parallel=parallel,
        )
        with factory() as db:
            stored = (
                db.query(PricesDaily.close, PricesDaily.foreign_net_val).one(),
                db.query(FinancialsQuarterly).count(),
            )
        out[parallel] = (result, inflight["max"], stored)

    (seq, seq_max, seq_db), (par, par_max, par_db) = out[False], out[True]
    assert seq_max == 1 and par_max >= 2
    assert par == seq and par["status"] == "SUCCESS"
    assert par_db == seq_db and par_db[1] > 0
