"""D95: job hằng ngày tải giá/khối ngoại/tự doanh từ FHSC (vnstock thế hệ 6, ~/.venv_6x) qua MỘT tiến trình,
app dùng lại kết quả; VCI là dự phòng. Không gọi mạng: tiến trình con và nguồn đều giả."""

import datetime as dt
import importlib.util
import json
import subprocess
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from valuation.ingest import fhsc_bridge
from valuation.ingest.market_client import market_client
from valuation.ingest.vnstock_client import vnstock_client

VN = ZoneInfo("Asia/Ho_Chi_Minh")
CFG = {
    "jobs": True,
    "python": "/bin/echo",  # chỉ cần tồn tại; tiến trình con bị thay bằng `run` giả
    "service_hours": ["06:00", "21:00"],
    "min_interval_sec": 1.4,
    "rate_limit_wait_sec": 30,
    "rate_limit_retries": 2,
    "timeout_sec": 60,
    "cache_ttl_sec": 1800,
}
DAY = dt.datetime(2026, 11, 13, 7, 50, tzinfo=VN)


def _load_fetch_script():
    spec = importlib.util.spec_from_file_location("fhsc_fetch", "scripts/fhsc_fetch.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_fetch_script_paces_retries_429_and_skips_flows_for_index():
    fetch = _load_fetch_script()
    calls, sleeps = [], []
    tick = iter(range(0, 1000, 1))  # đồng hồ giả: mỗi lần đọc +1 s

    class Asset:
        def __init__(self, name):
            self.name = name

        def ohlcv(self, start):
            calls.append((self.name, "prices", start))
            if self.name == "FPT" and sum(c[0] == "FPT" for c in calls) == 1:
                raise RuntimeError("Nguồn báo vượt giới hạn tần suất (429)")
            return pd.DataFrame({"time": [pd.Timestamp("2026-11-12 07:00", tz=VN)], "close": [49.55]})

        def foreign_flow(self, start):
            raise RuntimeError("DF000 Vui lòng thử lại sau")

    class Market:
        def equity(self, t):
            return Asset(t)

        def index(self, t):
            return Asset(t)

    req = {"starts": {"FPT": "2026-11-10", "VNINDEX": "2026-11-10"}, "kinds": ["prices", "foreign"],
           "min_interval_sec": 1.4, "rate_limit_wait_sec": 30, "rate_limit_retries": 2}
    out = list(fetch.fetch_all(req, Market, sleep=sleeps.append, clock=lambda: next(tick)))

    assert [(o["ticker"], o["kind"], "error" in o) for o in out] == [
        ("FPT", "prices", False), ("FPT", "foreign", True), ("VNINDEX", "prices", False)]  # chỉ số: không có dòng tiền
    assert 30 in sleeps  # 429 → chờ rồi thử lại, không bỏ mã
    assert all(0 < s <= 1.4 for s in sleeps if s != 30)  # giãn nhịp giữa các lời gọi
    assert out[0]["rows"][0]["close"] == 49.55


def _item(ticker, kind, rows, profile="v5"):
    return json.dumps({"ticker": ticker, "kind": kind, "profile": profile, "rows": rows})


def _fake_run(lines, code=0):
    def run(cmd, **kw):
        assert json.loads(kw["input"])["min_interval_sec"] == 1.4
        return subprocess.CompletedProcess(cmd, code, stdout="\n".join(lines), stderr="")

    return run


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.setattr(fhsc_bridge, "_cfg", lambda: CFG)
    # Đồng hồ cố định = giờ nạp bộ đệm (DAY): `cached` so TTL với _now(); để giờ thật thì test hỏng sau
    # DAY + cache_ttl_sec (đã hỏng từ 08:20 ngày 13/11/2026).
    monkeypatch.setattr(fhsc_bridge, "_now", lambda: DAY)
    monkeypatch.delenv("VN100_FHSC_JOBS", raising=False)  # conftest tắt FHSC cho mọi test khác
    fhsc_bridge.clear()
    yield
    fhsc_bridge.clear()


def test_prefetch_feeds_existing_clients_in_vci_shape(monkeypatch):
    prices = [{"time": "2026-11-11T07:00:00.000+07:00", "open": 51.0, "high": 51.1, "low": 50.2, "close": 50.9, "volume": 6533000},
              {"time": "2026-11-12T07:00:00.000+07:00", "open": 51.0, "high": 51.0, "low": 49.45, "close": 49.55, "volume": 17335200}]
    flow = [{"time": "2026-11-12T00:00:00.000+07:00", "buy_vol": 1.0, "buy_val": 2.0, "sell_vol": 3.0,
             "sell_val": 4.0, "net_vol": -2.0, "net_val": -2.0}]
    run = _fake_run([_item("FPT", "prices", prices), _item("FPT", "foreign", flow), _item("FPT", "prop", flow)])
    stats = fhsc_bridge.prefetch({"FPT": "2026-11-11"}, ["prices", "foreign", "prop"], now=DAY, run=run)
    assert stats == {"ok": 3, "errors": {}, "skipped": None}

    # vnstock_client/market_client lấy từ bộ đệm FHSC, không gọi VCI (vnstock 4 không bị import)
    df = vnstock_client.get_historical_prices("FPT", "2026-11-12")
    assert df["time"].tolist() == [pd.Timestamp("2026-11-12")] and df["close"].tolist() == [49.55]
    assert df.attrs["source"] == "fhsc" and df.attrs["price_unit"] == "thousand_VND"
    fo = market_client.fetch_foreign_flow("FPT", start="2026-11-11")
    assert fo["time"].tolist() == [dt.date(2026, 11, 12)] and fo.attrs["source"] == "fhsc"
    assert market_client.fetch_proprietary_flow("FPT", start="2026-11-11")["net_val"].tolist() == [-2.0]

    # Cần khoảng sớm hơn phần đã tải (vd tải lại toàn bộ khi giá điều chỉnh hồi tố) → không dùng bộ đệm
    assert fhsc_bridge.cached("FPT", "prices", "2026-01-01") is None


def test_prefetch_drops_flows_of_unfinished_session():
    # Lỗi 18/11/2026: vá lúc 12:40 ghi khối ngoại phiên 18/11 đang dở (FHSC trả số trong ngày) thành 98 dòng chỉ có
    # dòng tiền, tab money coi là phiên mới nhất. Phiên hôm nay chưa chốt → bỏ, lượt sáng hôm sau lấy (đệm 5 ngày).
    noon = DAY.replace(hour=12, minute=40)
    flow = [{"time": f"2026-11-{d}T00:00:00.000+07:00", "buy_vol": 1.0, "buy_val": 2.0, "sell_vol": 3.0,
             "sell_val": 4.0, "net_vol": -2.0, "net_val": -2.0} for d in (12, 13)]
    price = [{"time": "2026-11-13T07:00:00.000+07:00", "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}]
    run = _fake_run([_item("FPT", "foreign", flow), _item("FPT", "prop", flow), _item("FPT", "prices", price)])
    fhsc_bridge.prefetch({"FPT": "2026-11-12"}, ["foreign", "prop", "prices"], now=noon, run=run)
    for kind in ("foreign", "prop"):
        assert fhsc_bridge.cached("FPT", kind, "2026-11-12")["time"].tolist() == [dt.date(2026, 11, 12)]
    assert len(fhsc_bridge.cached("FPT", "prices", "2026-11-12")) == 1  # giá trong phiên giữ như trước (nút Tải mới)


def test_prefetch_guards_hours_unit_profile_and_ttl(monkeypatch):
    night = DAY.replace(hour=22)
    assert fhsc_bridge.prefetch({"FPT": "2026-11-11"}, ["prices"], now=night, run=_fake_run([]))["skipped"]

    row = [{"time": "2026-11-12T07:00:00.000+07:00", "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}]
    stats = fhsc_bridge.prefetch({"FPT": "2026-11-11"}, ["prices"], now=DAY,
                                 run=_fake_run([_item("FPT", "prices", row, profile="v6")]))
    assert stats["ok"] == 0 and "FPT/prices" in stats["errors"]  # hồ sơ khác v5 → không đoán đơn vị
    assert fhsc_bridge.cached("FPT", "prices", "2026-11-11") is None

    fhsc_bridge.prefetch({"FPT": "2026-11-11"}, ["prices"], now=DAY, run=_fake_run([_item("FPT", "prices", row)]))
    assert fhsc_bridge.cached("FPT", "prices", "2026-11-11") is not None
    monkeypatch.setattr(fhsc_bridge, "_now", lambda: DAY + dt.timedelta(seconds=CFG["cache_ttl_sec"] + 1))
    assert fhsc_bridge.cached("FPT", "prices", "2026-11-11") is None  # bộ đệm cũ không lọt sang lượt sau


def test_run_ingest_records_price_source(monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from valuation.db.models import Ticker
    from valuation.db.session import Base
    from valuation.ingest import pipeline

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(pipeline, "SessionLocalWrite", factory)
    with factory() as db:
        db.add(Ticker(ticker="FPT", company_name="FPT", is_vn100=True))
        db.commit()
    row = [{"time": "2026-11-12T07:00:00.000+07:00", "open": 51.0, "high": 51.0, "low": 49.45, "close": 49.55, "volume": 1}]
    fhsc_bridge.prefetch({"FPT": "2020-01-01"}, ["prices"], now=DAY, run=_fake_run([_item("FPT", "prices", row)]))

    res = pipeline.run_ingest("FPT", ["prices"], include_market_flows=False)
    assert res["prices"]["status"] == "UPDATED" and res["prices"]["source"] == "fhsc"
