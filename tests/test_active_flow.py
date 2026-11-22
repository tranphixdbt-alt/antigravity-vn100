"""W0 (D101, docs/PLAN_WYCKOFF_FLOW.md): lưu mua/bán chủ động FHSC hằng ngày vào bảng active_flow_daily.

FHSC `Market().equity(mã).active_flow()` chỉ trả ~61 phiên gần nhất (đo 22/11/2026: VCB 24/08 → 20/11, tham số
`start` không kéo dài được) → phải lưu mỗi ngày, dữ liệu quá 61 phiên không lấy lại được.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import sqlite3
from zoneinfo import ZoneInfo

import pandas as pd
from sqlalchemy import create_engine, func, inspect, select

from valuation.db.flow_models import FlowMetaData, active_flow_daily
from valuation.ingest import active_flow as af

VN = ZoneInfo("Asia/Ho_Chi_Minh")
NOW = dt.datetime(2026, 11, 23, 7, 35, tzinfo=VN)
FETCHED = NOW.replace(tzinfo=None)


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, f"scripts/{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _engine():
    eng = create_engine("sqlite:///:memory:")
    FlowMetaData.create_all(eng, tables=[active_flow_daily])
    return eng


def _frame(rows: list[tuple[str, float | None, float | None]]) -> pd.DataFrame:
    # Dạng fhsc_bridge.cached trả về cho dòng tiền: `time` là date (đã bỏ múi giờ), cột như FHSC.
    return pd.DataFrame(
        {
            "time": [dt.date.fromisoformat(d) for d, _, _ in rows],
            "active_buy_volume": [b for _, b, _ in rows],
            "active_sell_volume": [s for _, _, s in rows],
            "active_buy_percent": [None] * len(rows),
        }
    )


def test_fetch_script_requests_active_flow_and_skips_indexes():
    fetch = _load_script("fhsc_fetch")
    assert fetch.METHODS["active"] == "active_flow"
    calls = []

    class Asset:
        def __init__(self, name):
            self.name = name

        def active_flow(self, start):
            calls.append((self.name, start))
            return pd.DataFrame(
                {
                    "time": [pd.Timestamp("2026-11-20 07:00", tz=VN)],
                    "active_buy_volume": [6827840],
                    "active_sell_volume": [5787170],
                }
            )

    class Market:
        def equity(self, t):
            return Asset(t)

        def index(self, t):
            return Asset(t)

    req = {"starts": {"VCB": "2026-07-25", "VNINDEX": "2026-07-25"}, "kinds": ["active"],
           "min_interval_sec": 0, "rate_limit_wait_sec": 0, "rate_limit_retries": 0}  # fmt: skip
    out = list(fetch.fetch_all(req, Market, sleep=lambda s: None, clock=lambda: 0.0))
    assert calls == [("VCB", "2026-07-25")]  # chỉ số không có mua/bán chủ động
    assert out[0]["rows"][0]["active_buy_volume"] == 6827840


def test_normalize_hand_checked_and_drops_bad_rows():
    # VCB 20/11/2026 (số thật FHSC): mua chủ động 6.827.840 cp, bán chủ động 5.787.170 cp.
    df = _frame(
        [
            ("2026-11-19", 7868187, 8017485),
            ("2026-11-20", 6827840, 5787170),
            ("2026-11-18", None, 11040332),  # thiếu số → bỏ (không coi là 0)
            ("2026-11-17", -5, 10),  # âm → bỏ
            ("2026-11-16", 0, 0),  # cả hai bằng 0 → không có số, bỏ
        ]
    )
    rows, dropped = af.normalize(df, "VCB", FETCHED)
    assert dropped == 3
    assert rows == [
        {"ticker": "VCB", "trade_date": dt.date(2026, 11, 19), "source": "fhsc",
         "active_buy_vol": 7868187.0, "active_sell_vol": 8017485.0, "fetched_at": FETCHED},
        {"ticker": "VCB", "trade_date": dt.date(2026, 11, 20), "source": "fhsc",
         "active_buy_vol": 6827840.0, "active_sell_vol": 5787170.0, "fetched_at": FETCHED},
    ]  # fmt: skip
    # Tính tay: delta chủ động 20/11 = 6.827.840 − 5.787.170 = +1.040.670 cp
    assert rows[1]["active_buy_vol"] - rows[1]["active_sell_vol"] == 1040670


def test_normalize_duplicate_dates_keep_last():
    rows, dropped = af.normalize(
        _frame([("2026-11-20", 1, 2), ("2026-11-20", 3, 4)]), "VCB", FETCHED
    )
    assert dropped == 1 and [
        (r["active_buy_vol"], r["active_sell_vol"]) for r in rows
    ] == [(3.0, 4.0)]


def test_store_idempotent_keeps_existing_and_logs_mismatch():
    eng = _engine()
    rows, _ = af.normalize(
        _frame([("2026-11-19", 10, 20), ("2026-11-20", 30, 40)]), "VCB", FETCHED
    )
    first = af.store(eng, rows)
    second = af.store(eng, rows)
    assert (first["inserted"], first["unchanged"]) == (2, 0)
    assert (second["inserted"], second["unchanged"], second["mismatches"]) == (
        2 - 2,
        2,
        [],
    )
    with eng.connect() as c:
        assert (
            c.execute(select(func.count()).select_from(active_flow_daily)).scalar() == 2
        )

    # Nguồn đổi số của phiên đã lưu → GIỮ bản đã lưu (như flow_daily đã chốt), ghi vào mismatches
    changed, _ = af.normalize(
        _frame([("2026-11-20", 31, 40), ("2026-11-21", 5, 6)]), "VCB", FETCHED
    )
    third = af.store(eng, changed)
    assert third["inserted"] == 1 and third["mismatches"] == [("VCB", "2026-11-20")]
    with eng.connect() as c:
        kept = c.execute(
            select(active_flow_daily.c.active_buy_vol).where(
                active_flow_daily.c.trade_date == dt.date(2026, 11, 20)
            )
        ).scalar()
    assert kept == 30.0


def test_collect_end_to_end_with_fake_bridge():
    eng = _engine()
    seen = {}

    def prefetch(starts, kinds, now):
        seen.update(starts=starts, kinds=kinds, now=now)
        return {"ok": 1, "errors": {"BBB/active": "DF000"}, "skipped": None}

    frames = {"AAA": _frame([("2026-11-20", 100, 50)])}
    stats = af.collect(
        eng, ["AAA", "BBB"], NOW, "2026-07-26",
        prefetch=prefetch, cached=lambda t, kind, start: frames.get(t),
    )  # fmt: skip
    assert seen["kinds"] == ["active"] and seen["starts"] == {
        "AAA": "2026-07-26",
        "BBB": "2026-07-26",
    }
    assert (
        stats["inserted"] == 1
        and stats["missing"] == ["BBB"]
        and stats["errors"] == {"BBB/active": "DF000"}
    )
    assert stats["tickers_ok"] == 1 and stats["latest_date"] == "2026-11-20"


def test_collect_reports_skip_outside_fhsc_hours():
    stats = af.collect(
        _engine(), ["AAA"], NOW, "2026-07-26",
        prefetch=lambda s, k, now: {"ok": 0, "errors": {}, "skipped": "ngoài giờ phục vụ FHSC 06:00–21:00"},
        cached=lambda *a: None,
    )  # fmt: skip
    assert stats["skipped"].startswith("ngoài giờ") and stats["inserted"] == 0


def test_migrate_dry_run_then_apply_with_backup(tmp_path):
    mig = _load_script("migrate_active_flow")
    db = tmp_path / "vn100_full.db"
    with sqlite3.connect(db) as c:
        c.execute("create table prices_daily (ticker text)")
    eng = create_engine(f"sqlite:///{db}")
    backups = tmp_path / "backups"

    assert "SẼ TẠO" in mig.migrate(eng, backups, apply=False)
    assert not inspect(eng).has_table("active_flow_daily") and not backups.exists()

    msg = mig.migrate(eng, backups, apply=True, now=NOW)
    assert "ĐÃ TẠO" in msg and inspect(create_engine(f"sqlite:///{db}")).has_table(
        "active_flow_daily"
    )
    files = list(backups.iterdir())
    assert len(files) == 1 and "pre_active_flow_daily" in files[0].name
    assert "ĐÃ CÓ" in mig.migrate(
        eng, backups, apply=True, now=NOW
    )  # chạy lại: không làm gì
