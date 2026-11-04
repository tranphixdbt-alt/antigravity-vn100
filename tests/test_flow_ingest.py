"""B1 flow_daily (D73): TB1–TB4, TB7. Không gọi mạng; DB là SQLite tạm."""

from __future__ import annotations

import datetime as dt
import importlib
import importlib.util
import logging
import math
import sys
from pathlib import Path
from types import ModuleType

import pandas as pd
import pytest
from sqlalchemy import create_engine, func, inspect, select

from valuation.config import settings
from valuation.db.flow_models import FlowMetaData, flow_daily
from valuation.ingest.flow_client import (
    FlowClient,
    FlowConfigError,
    FlowRateLimited,
    FlowSchemaError,
    to_flow_frame,
    validate_tickers,
)

ROOT = Path(__file__).resolve().parents[1]
TOL = 0.001
SETTLE = "17:30"


def _script(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


update = _script("update_flow_daily")
migrate_mod = _script("migrate_flow_daily")

# Fixture dựng tay theo VCI price_history(get_all=True) MCH 09/10/2026 (gọi thật 23/10, chỉ đọc).
MCH_0910_PRICE = {
    "trading_date": pd.Timestamp("2026-10-09"),
    "matched_volume": 805_122.0,
    "matched_value": 115_009_642_700.0,
    "deal_volume": 64_274_571.0,
    "deal_value": 9_641_185_650_000.0,
    "total_volume": 65_079_693.0,  # 805.122 + 64.274.571
    "total_value": 9_756_195_292_700.0,  # 115.009.642.700 + 9.641.185.650.000
    "fr_buy_volume_matched": 359_173.0,
    "fr_buy_value_matched": 51_257_259_000.0,
    "fr_sell_volume_matched": 26_100.0,
    "fr_sell_value_matched": 3_719_810_000.0,
    "fr_net_volume_matched": 333_073.0,  # 359.173 − 26.100
    "fr_net_value_matched": 47_537_449_000.0,  # 51.257.259.000 − 3.719.810.000
    "fr_buy_volume_deal": 0.0,
    "fr_buy_value_deal": 0.0,
    "fr_sell_volume_deal": 64_274_571.0,
    "fr_sell_value_deal": 9_641_185_650_000.0,
    "fr_net_volume_deal": -64_274_571.0,
    "fr_net_value_deal": -9_641_185_650_000.0,
    "fr_buy_volume_total": 359_173.0,
    "fr_buy_value_total": 51_257_259_000.0,
    "fr_sell_volume_total": 64_300_671.0,  # 26.100 + 64.274.571
    "fr_sell_value_total": 9_644_905_460_000.0,
    "fr_net_volume_total": -63_941_498.0,
    "fr_net_value_total": -9_593_648_201_000.0,  # 47.537.449.000 − 9.641.185.650.000
    "fr_total_room": 1_307_404_949.0,
    "fr_current_room": 1_097_598_310.0,
    "fr_owned_percentage": 0.16047563,
}
MCH_0910_PROP = {
    "trading_date": pd.Timestamp("2026-10-09"),
    "total_buy_trade_volume": 112_800.0,
    "total_buy_trade_value": 16_146_760_000.0,
    "total_sell_trade_volume": 527_700.0,
    "total_sell_trade_value": 75_336_310_000.0,
    "total_trade_net_volume": -414_900.0,
    "total_trade_net_value": -59_189_550_000.0,  # 16.146.760.000 − 75.336.310.000
    "total_match_buy_trade_volume": 112_800.0,
    "total_match_buy_trade_value": 16_146_760_000.0,
    "total_match_sell_trade_volume": 527_700.0,
    "total_match_sell_trade_value": 75_336_310_000.0,
    "total_match_trade_net_volume": -414_900.0,
    "total_match_trade_net_value": -59_189_550_000.0,
    "total_deal_buy_trade_volume": 0.0,
    "total_deal_buy_trade_value": 0.0,
    "total_deal_sell_trade_volume": 0.0,
    "total_deal_sell_trade_value": 0.0,
    "total_deal_trade_net_volume": 0.0,
    "total_deal_trade_net_value": 0.0,
}

CONTRACT_COLUMNS = {
    "ticker", "trade_date", "source", "matched_vol", "matched_val", "deal_vol", "deal_val",
    "fr_buy_match_vol", "fr_sell_match_vol", "fr_net_match_vol",
    "fr_buy_match_val", "fr_sell_match_val", "fr_net_match_val",
    "fr_buy_deal_vol", "fr_sell_deal_vol", "fr_net_deal_vol",
    "fr_buy_deal_val", "fr_sell_deal_val", "fr_net_deal_val",
    "fr_total_room", "fr_current_room", "fr_owned_pct",
    "prop_buy_match_vol", "prop_sell_match_vol", "prop_net_match_vol",
    "prop_buy_match_val", "prop_sell_match_val", "prop_net_match_val",
    "prop_buy_deal_vol", "prop_sell_deal_vol", "prop_net_deal_vol",
    "prop_buy_deal_val", "prop_sell_deal_val", "prop_net_deal_val",
    "fetched_at", "is_final", "batch_id", "quality_flags",
}  # fmt: skip


def _vn(hour: int) -> dt.datetime:
    """fetched_at lưu giờ VN không tz (hợp đồng flow_daily)."""
    return dt.datetime(2026, 10, 23, hour)  # noqa: DTZ001


def _price(*rows: dict) -> pd.DataFrame:
    return pd.DataFrame(list(rows) or [MCH_0910_PRICE])


def _prop(*rows: dict) -> pd.DataFrame:
    return pd.DataFrame(list(rows) or [MCH_0910_PROP])


def _day(row: dict, day: str) -> dict:
    return {**row, "trading_date": pd.Timestamp(day)}


# ---------- TB1: map đúng cột/đơn vị, đẳng thức total = khớp + thỏa thuận ----------


def test_tb1_mch_0910_matched_plus_deal_equals_total() -> None:
    r = to_flow_frame("MCH", _price(), _prop(), TOL).iloc[0]
    assert r.trade_date == dt.date(2026, 10, 9) and r.source == "VCI"
    assert r.deal_vol == 64_274_571
    assert round(r.fr_net_deal_val / 1e9, 2) == -9_641.19  # tỷ đồng
    assert round(r.fr_net_match_val / 1e9, 2) == 47.54
    total = r.fr_net_match_val + r.fr_net_deal_val
    assert (
        round(total / 1e9, 2) == -9_593.65
    )  # = prices_daily.foreign_net_val MCH 09/10
    assert total - MCH_0910_PRICE["fr_net_value_total"] == 0  # sai số 0
    assert r.fr_sell_match_vol + r.fr_sell_deal_vol == 64_300_671
    assert r.prop_net_match_val == -59_189_550_000 and r.prop_net_deal_val == 0
    assert r.fr_owned_pct == pytest.approx(0.16047563)
    assert r.quality_flags is None


def test_tb1_identity_break_flags_and_nan_stays_nan() -> None:
    broken = {
        **MCH_0910_PRICE,
        "fr_net_value_total": MCH_0910_PRICE["fr_net_value_total"] + 1e12,
    }
    nan_deal = _day({**MCH_0910_PRICE, "deal_value": float("nan")}, "2026-10-10")
    out = to_flow_frame("MCH", _price(broken, nan_deal), _prop(), TOL)
    assert out.iloc[0].quality_flags == "id:fr_net_value_total"
    second = out.iloc[1]
    assert math.isnan(second.deal_val)  # không thay NaN bằng 0, không gắn cờ đẳng thức
    assert second.quality_flags == "no_prop"  # thiếu tự doanh → NULL + cờ
    assert all(math.isnan(second[c]) for c in out.columns if c.startswith("prop_"))


# ---------- TB2: upsert idempotent, dòng đã chốt không bị ghi đè ----------


def _flow_engine(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'flow.db'}")
    FlowMetaData.create_all(engine)
    return engine


def _rows(engine) -> dict[dt.date, dict]:
    with engine.connect() as conn:
        return {
            r["trade_date"]: dict(r)
            for r in conn.execute(select(flow_daily)).mappings()
        }


def test_tb2_upsert_twice_no_duplicates_final_kept(tmp_path: Path, caplog) -> None:
    engine = _flow_engine(tmp_path)
    today = _day(MCH_0910_PRICE, "2026-10-23")
    frame = to_flow_frame(
        "MCH",
        _price(MCH_0910_PRICE, today),
        _prop(MCH_0910_PROP, _day(MCH_0910_PROP, "2026-10-23")),
        TOL,
    )
    t1600 = _vn(16)  # trước giờ chốt tự doanh 17:30

    with engine.begin() as conn:
        s1 = update.upsert_flow(conn, frame, t1600, "b1", SETTLE)
    with engine.begin() as conn:
        s2 = update.upsert_flow(conn, frame, t1600, "b2", SETTLE)
    rows = _rows(engine)
    assert (s1["inserted"], s1["updated"], s1["skipped_final"]) == (2, 0, 0)
    assert (s2["inserted"], s2["updated"], s2["skipped_final"], s2["mismatches"]) == (
        0,
        1,
        1,
        [],
    )
    assert len(rows) == 2
    assert (
        rows[dt.date(2026, 10, 9)]["is_final"] is True
    )  # ngày đã qua → final (như backfill)
    assert rows[dt.date(2026, 10, 23)]["is_final"] is False  # phiên hôm nay 16:00 → tạm

    changed = frame.copy()
    changed["fr_net_match_val"] += 1e9
    caplog.set_level(logging.WARNING, logger="update_flow_daily")
    with engine.begin() as conn:
        s3 = update.upsert_flow(conn, changed, _vn(18), "b3", SETTLE)
    rows = _rows(engine)
    assert len(rows) == 2
    final = rows[dt.date(2026, 10, 9)]
    assert final["fr_net_match_val"] == 47_537_449_000 and final["batch_id"] == "b1"
    assert s3["mismatches"] == [
        {
            "ticker": "MCH",
            "trade_date": "2026-10-09",
            "column": "fr_net_match_val",
            "final": 47_537_449_000.0,
            "new": 48_537_449_000.0,
        }
    ]
    assert "Lệch dòng đã chốt" in caplog.text and "fr_net_match_val" in caplog.text
    today_row = rows[dt.date(2026, 10, 23)]
    assert (
        today_row["fr_net_match_val"] == 48_537_449_000
        and today_row["is_final"] is True
    )
    assert today_row["batch_id"] == "b3"


def test_tb2_dry_run_writes_nothing(tmp_path: Path) -> None:
    engine = _flow_engine(tmp_path)
    frame = to_flow_frame("MCH", _price(), _prop(), TOL)
    with engine.begin() as conn:
        stats = update.upsert_flow(conn, frame, _vn(18), "b1", SETTLE, dry_run=True)
    with engine.connect() as conn:
        assert conn.execute(select(func.count()).select_from(flow_daily)).scalar() == 0
    assert stats["inserted"] == 1


# ---------- TB3: init_db không tạo bảng; migrate tạo sau backup, idempotent ----------


def test_tb3_init_db_skips_flow_daily_migrate_backs_up_first(tmp_path: Path) -> None:
    from valuation.db.session import init_db

    assert {c.name for c in flow_daily.columns} == CONTRACT_COLUMNS
    engine = create_engine(f"sqlite:///{tmp_path / 'app.db'}")
    init_db(engine)
    assert "prices_daily" in inspect(engine).get_table_names()
    assert not inspect(engine).has_table("flow_daily")

    backups = tmp_path / "backups"
    assert "SẼ TẠO" in migrate_mod.migrate(engine, backups, apply=False)
    assert not backups.exists() and not inspect(engine).has_table("flow_daily")

    migrate_mod.migrate(engine, backups, apply=True, now=_vn(18))
    files = list(backups.iterdir())
    assert [f.name for f in files] == ["app.pre_flow_daily_20261023_180000.db"]
    snapshot = inspect(create_engine(f"sqlite:///{files[0]}"))
    assert "prices_daily" in snapshot.get_table_names() and not snapshot.has_table(
        "flow_daily"
    )
    assert inspect(engine).has_table("flow_daily")

    assert "ĐÃ CÓ" in migrate_mod.migrate(engine, backups, apply=True)
    assert len(list(backups.iterdir())) == 1


def test_tb3_job_refuses_without_table(tmp_path: Path, monkeypatch) -> None:
    db = tmp_path / "app.db"
    from valuation.db.session import init_db

    init_db(create_engine(f"sqlite:///{db}"))
    monkeypatch.setattr(update.settings, "database_url_write", f"sqlite:///{db}")
    assert update.main(["--dry-run", "--tickers", "MCH"]) == 2


# ---------- TB4: thiếu cột → raise; whitelist mã ----------


@pytest.mark.parametrize(
    "drop", ["deal_volume", "fr_net_value_deal", "fr_total_room", "total_value"]
)
def test_tb4_missing_price_column_raises(drop: str) -> None:
    with pytest.raises(FlowSchemaError, match=drop):
        to_flow_frame("MCH", _price().drop(columns=[drop]), _prop(), TOL)


def test_tb4_missing_prop_column_and_duplicate_date_raise() -> None:
    with pytest.raises(FlowSchemaError, match="total_deal_trade_net_value"):
        to_flow_frame(
            "MCH", _price(), _prop().drop(columns=["total_deal_trade_net_value"]), TOL
        )
    with pytest.raises(FlowSchemaError, match="trùng"):
        to_flow_frame("MCH", _price(MCH_0910_PRICE, MCH_0910_PRICE), _prop(), TOL)


def test_tb4_ticker_whitelist() -> None:
    assert validate_tickers([" mch "], {"MCH"}) == ["MCH"]
    for bad in ["MCH;DROP", "MC", "../x", "AAA"]:
        with pytest.raises(ValueError):
            validate_tickers([bad], {"MCH"})


# ---------- TB7: log/stdout không lộ key, tên tài khoản, tier ----------

_SECRET = "FAKE-KEY-ONLY-FOR-TB7"
_BANNER = "Xin chào Nguyễn Văn Thử · gói Golden"


def _fake_vnstock_data(root: Path) -> None:
    pkg = root / "vnstock_data" / "explorer" / "vci"
    pkg.mkdir(parents=True)
    banner = f"print({_BANNER!r}); import sys, os; print(os.environ.get('VNSTOCK_API_KEY'), file=sys.stderr)\n"
    (root / "vnstock_data" / "__init__.py").write_text(banner, encoding="utf-8")
    (root / "vnstock_data" / "explorer" / "__init__.py").write_text(
        "", encoding="utf-8"
    )
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "const.py").write_text(
        '_VCI_COMPANY_URL = "https://iq.vietcap.com.vn/api/iq-insight-service/v1/company"\n',
        encoding="utf-8",
    )
    _price().to_pickle(root / "price.pkl")
    _prop().to_pickle(root / "prop.pkl")
    (pkg / "trading.py").write_text(
        "import logging, os, sys\n"
        "import pandas as pd\n"
        f"ROOT = {str(root)!r}\n"
        "class Trading:\n"
        "    def __init__(self, symbol):\n"
        "        self.symbol = symbol\n"
        "    def _leak(self):\n"
        f"        print({_BANNER!r}, os.environ['VNSTOCK_API_KEY'])\n"
        f"        print({_BANNER!r}, file=sys.stderr)\n"
        f"        logging.getLogger('vnai').warning({_BANNER!r} + os.environ['VNSTOCK_API_KEY'])\n"
        "    def price_history(self, **kw):\n"
        "        self._leak(); return pd.read_pickle(ROOT + '/price.pkl')\n"
        "    def prop_trade(self, **kw):\n"
        "        self._leak(); return pd.read_pickle(ROOT + '/prop.pkl')\n",
        encoding="utf-8",
    )


def test_tb7_logs_have_no_key_account_or_tier(
    tmp_path: Path, monkeypatch, caplog, capsys
) -> None:
    saved = {k: v for k, v in sys.modules.items() if k.split(".")[0] == "vnstock_data"}
    _fake_vnstock_data(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(settings, "vnstock_api_key", _SECRET)
    monkeypatch.delenv("VNSTOCK_API_KEY", raising=False)
    for name in saved:
        del sys.modules[name]
    importlib.invalidate_caches()
    caplog.set_level(logging.DEBUG)
    sleeps: list[float] = []
    try:
        client = FlowClient(
            {
                "source": "VCI",
                "allowed_domains": ["iq.vietcap.com.vn"],
                "max_calls_per_minute": 20,
            },
            sleep=sleeps.append,
            clock=lambda: 0.0,
        )
        frame = client.fetch("MCH", dt.date(2026, 10, 9), dt.date(2026, 10, 9))
        assert frame.iloc[0].fr_net_deal_val == -9_641_185_650_000
        assert sleeps == [3.0]  # 20 lượt/phút → cách nhau 3 giây
    finally:
        for name in [k for k in sys.modules if k.split(".")[0] == "vnstock_data"]:
            del sys.modules[name]
        sys.modules.update(saved)
    out, err = capsys.readouterr()
    for text in (out, err, caplog.text):
        assert _SECRET not in text
        assert "Nguyễn Văn Thử" not in text and "Golden" not in text


def test_tb7_domain_outside_allowlist_refused(tmp_path: Path, monkeypatch) -> None:
    saved = {k: v for k, v in sys.modules.items() if k.split(".")[0] == "vnstock_data"}
    _fake_vnstock_data(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    for name in saved:
        del sys.modules[name]
    importlib.invalidate_caches()
    try:
        client = FlowClient(
            {
                "source": "VCI",
                "allowed_domains": ["trading.vietcap.com.vn"],
                "max_calls_per_minute": 20,
            }
        )
        with pytest.raises(FlowConfigError, match="allowlist"):
            client.fetch("MCH", dt.date(2026, 10, 9), dt.date(2026, 10, 9))
        # trong job: lỗi cấu hình dừng ngay ở mã đầu (không lặp 100 mã), mã thoát riêng
        status = update.run(
            _flow_engine(tmp_path), client, ["MCH", "FPT"], *_SPAN, dry_run=False
        )
        assert status["fatal_kind"] == "FlowConfigError" and status["errors"] == []
        assert status["fatal"].startswith("MCH:") and update.exit_code(status) == 6
    finally:
        for name in [k for k in sys.modules if k.split(".")[0] == "vnstock_data"]:
            del sys.modules[name]
        sys.modules.update(saved)


# ---------- rà soát B1: hạn mức, nguồn rỗng, is_final, status ----------
_SPAN = (dt.date(2026, 10, 9), dt.date(2026, 10, 9), SETTLE, "b1")


class _Client:
    """Client giả: fetch trả lần lượt kết quả trong `out` (DataFrame hoặc exception)."""

    def __init__(self, *out):
        self.out, self.calls = list(out), 0

    def fetch(self, ticker, start, end):
        self.calls += 1
        x = self.out.pop(0) if len(self.out) > 1 else self.out[0]
        if isinstance(x, BaseException):
            raise x
        return x


def test_tb7_library_sys_exit_hides_tier_and_stops_job(tmp_path: Path, capsys) -> None:
    # vnai CleanErrorContext: in banner rồi sys.exit("Rate limit exceeded. … Gói hiện tại: …")
    def fn() -> pd.DataFrame:
        print(_BANNER)
        raise SystemExit(f"Rate limit exceeded. {_BANNER} Process terminated.")

    client = FlowClient(
        {"source": "VCI", "allowed_domains": [], "max_calls_per_minute": 60},
        sleep=lambda _: None,
    )
    with pytest.raises(FlowRateLimited) as info:
        client._call(fn)
    assert "Golden" not in str(info.value) and info.value.__suppress_context__

    client.fetch = lambda *a: client._call(fn)  # type: ignore[method-assign]
    saved: list[dict] = []
    status = update.run(
        _flow_engine(tmp_path), client, ["MCH", "FPT"], *_SPAN, False, save=saved.append
    )
    assert status["fatal_kind"] == "FlowRateLimited" and update.exit_code(status) == 5
    assert saved == [status] and "Golden" not in str(status)
    out, err = capsys.readouterr()
    assert "Golden" not in out + err and "Nguyễn Văn Thử" not in out + err


def test_tb8_empty_source_is_error_not_success(tmp_path: Path) -> None:
    engine = _flow_engine(tmp_path)
    empty = pd.DataFrame(columns=["ticker", "trade_date", "quality_flags"])
    status = update.run(engine, _Client(empty), ["MCH", "FPT"], *_SPAN, False)
    assert [e["ticker"] for e in status["errors"]] == ["MCH", "FPT"]
    assert status["fatal_kind"] == "FlowSchemaError" and update.exit_code(status) == 4

    # Chỉ có tự doanh, thiếu giá → lỗi (exit 1), dòng vẫn ghi nhưng KHÔNG chốt.
    prop_only = to_flow_frame("MCH", None, _prop(), TOL)
    status = update.run(engine, _Client(prop_only), ["MCH"], *_SPAN, False)
    assert status["errors"] == [
        {"ticker": "MCH", "error": "VCI trả price_history rỗng (chỉ có tự doanh)"}
    ]
    assert update.exit_code(status) == 1
    assert _rows(engine)[dt.date(2026, 10, 9)]["is_final"] is False


def test_tb2_missing_prop_group_not_final_and_filled_later(tmp_path: Path) -> None:
    engine = _flow_engine(tmp_path)
    no_prop = to_flow_frame("MCH", _price(), None, TOL)
    with engine.begin() as conn:
        update.upsert_flow(conn, no_prop, _vn(18), "b1", SETTLE)
    row = _rows(engine)[dt.date(2026, 10, 9)]
    assert row["quality_flags"] == "no_prop" and row["is_final"] is False
    with engine.begin() as conn:
        s = update.upsert_flow(
            conn, to_flow_frame("MCH", _price(), _prop(), TOL), _vn(19), "b2", SETTLE
        )
    row = _rows(engine)[dt.date(2026, 10, 9)]
    assert (s["updated"], s["skipped_final"]) == (1, 0)
    assert row["prop_net_match_val"] == -59_189_550_000 and row["is_final"] is True


def test_status_saved_when_job_aborted(tmp_path: Path) -> None:
    saved: list[dict] = []
    with pytest.raises(KeyboardInterrupt):
        update.run(
            _flow_engine(tmp_path), _Client(KeyboardInterrupt()), ["MCH"], *_SPAN, False,
            save=saved.append,
        )  # fmt: skip
    assert (
        saved[0]["fatal"] == "bị dừng: KeyboardInterrupt" and "finished_at" in saved[0]
    )


def test_transient_ticker_error_retried_once(tmp_path: Path) -> None:
    # vnai beam/quota.py: `import threading` cục bộ → UnboundLocalError ở lượt đồng bộ (~50 lời gọi/lần);
    # bộ đếm đã reset trước khi lỗi nên gọi lại ngay là qua. Timeout mạng cũng thử lại 1 lần.
    engine = _flow_engine(tmp_path)
    frame = to_flow_frame("MCH", _price(), _prop(), TOL)
    bug = UnboundLocalError("cannot access local variable 'threading'")
    client = _Client(bug, frame)
    status = update.run(engine, client, ["MCH"], *_SPAN, False)
    assert client.calls == 2 and status["errors"] == [] and status["inserted"] == 1

    # Lỗi cả 2 lần → ghi lỗi, chạy tiếp mã sau.
    client = _Client(ConnectionError("timeout"), ConnectionError("timeout"), frame)
    status = update.run(engine, client, ["MCH", "FPT"], *_SPAN, False)
    assert [e["ticker"] for e in status["errors"]] == ["MCH"] and client.calls == 3


def test_rate_limit_waits_then_retries_same_ticker(tmp_path: Path) -> None:
    # D93 (người dùng chọn 04/11): lượt 18:11 ngày 04/11 vượt hạn mức ngay ở mã đầu (ACB) và mất trọn
    # ngày dữ liệu → giờ chờ rồi thử lại chính mã đó; hết số lần mới dừng cả job như D73.
    engine = _flow_engine(tmp_path)
    frame = to_flow_frame("MCH", _price(), _prop(), TOL)
    limited = FlowRateLimited("vượt hạn mức")
    waits: list[float] = []
    retry = {"rate_limit_wait": 65, "rate_limit_retries": 2, "sleep": waits.append}
    client = _Client(limited, limited, frame)
    status = update.run(engine, client, ["MCH"], *_SPAN, False, **retry)
    assert waits == [65, 65] and client.calls == 3
    assert status["fatal"] is None and status["inserted"] == 1

    waits.clear()
    client = _Client(limited)
    status = update.run(engine, client, ["MCH", "FPT"], *_SPAN, False, **retry)
    assert waits == [65, 65] and client.calls == 3
    assert status["fatal_kind"] == "FlowRateLimited" and update.exit_code(status) == 5
