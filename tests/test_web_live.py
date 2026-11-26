"""Giá trong phiên cho trang Hôm nay (D122): VN-Index, VN30, mã VN100 tăng giảm mạnh nhất. Không gọi mạng."""

from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from valuation.db.models import PricesDaily, Ticker
from valuation.db.session import Base
from valuation.services import web_live
from valuation.views import market_overview as mo

VN = ZoneInfo("Asia/Ho_Chi_Minh")


@pytest.fixture
def mem_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add_all(
        [Ticker(ticker="AAA", company_name="AAA", is_vn100=True)]
        + [Ticker(ticker="VNINDEX", company_name="VNINDEX", is_vn100=False)]
    )
    db.commit()
    yield db
    db.close()


def test_load_market_data_bo_phien_chua_chot(mem_db):
    """Tái hiện lỗi 26/11/2026: thẻ VN-Index ghi "giá đến 25/11" nhưng hiện điểm giữa phiên 26/11."""
    mem_db.add_all(
        [
            PricesDaily(
                ticker="VNINDEX", trade_date=dt.date(2026, 11, 25), close=1687.45
            ),
            PricesDaily(
                ticker="VNINDEX", trade_date=dt.date(2026, 11, 26), close=1677.93
            ),
            PricesDaily(ticker="AAA", trade_date=dt.date(2026, 11, 25), close=10.0),
        ]
    )
    mem_db.commit()
    cfg = {"history_days": 30, "min_coverage": 0.5}
    vni, *_ = mo.load_market_data(
        mem_db, cfg, dt.datetime(2026, 11, 26, 10, 50, tzinfo=VN)
    )
    assert vni.index.max().date() == dt.date(2026, 11, 25) and vni.iloc[-1] == 1687.45
    # sau giờ đóng phiên dòng 26/11 là số đã chốt, được tính
    vni, *_ = mo.load_market_data(
        mem_db, cfg, dt.datetime(2026, 11, 26, 16, 10, tzinfo=VN)
    )
    assert vni.index.max().date() == dt.date(2026, 11, 26)


def _nen(ngay_gia: list[tuple[str, float]]) -> list[dict]:
    t = [
        str(
            int(
                dt.datetime.fromisoformat(d).replace(tzinfo=dt.timezone.utc).timestamp()
            )
        )
        for d, _ in ngay_gia
    ]
    return [{"t": t, "c": [g for _, g in ngay_gia]}]


def test_index_row_tinh_tay():
    # 26/11 10:50: nến hôm nay 1.661,41, phiên trước 1.687,45 → −26,04 điểm, −1,543% (tính tay)
    now = dt.datetime(2026, 11, 26, 10, 50, tzinfo=VN)
    row = web_live.index_row(
        "VNINDEX", _nen([("2026-11-25", 1687.45), ("2026-11-26", 1661.41)]), now
    )
    assert row["ngay"] == dt.date(2026, 11, 26) and row["diem"] == 1661.41
    assert row["thay_doi"] == pytest.approx(-26.04)
    assert row["ty_le"] == pytest.approx(1661.41 / 1687.45 - 1)
    assert row["trong_phien"] is True
    # 07:30 sáng hôm sau, chưa có nến mới: hiện phiên đóng gần nhất, không phải "trong phiên"
    row = web_live.index_row(
        "VN30",
        _nen([("2026-11-25", 1778.58), ("2026-11-26", 1755.93)]),
        now.replace(day=27, hour=7, minute=30),
    )
    assert row["ngay"] == dt.date(2026, 11, 26) and row["trong_phien"] is False
    with pytest.raises(web_live.LiveDataError):
        web_live.index_row("VN30", [], now)


def _bg(ma, tham_chieu, khop, tran=0, san=0):
    return {
        "listingInfo": {
            "symbol": ma,
            "refPrice": tham_chieu,
            "ceiling": tran,
            "floor": san,
        },
        "matchPrice": {"matchPrice": khop, "accumulatedVolume": 100},
    }


def test_movers_tinh_tay_va_bo_ma_chua_khop():
    rows = [
        _bg("AAA", 10000, 10500),  # +5%
        _bg("BBB", 20000, 19000),  # −5%
        _bg("CCC", 30000, 30000),  # đứng giá
        _bg("DDD", 40000, 0),  # chưa khớp lệnh: không tính
        _bg("EEE", 10000, 10700, tran=10700, san=9300),  # trần +7%
    ]
    out = web_live.movers(rows, top_n=2)
    assert [r["ma"] for r in out["tang"]] == ["EEE", "AAA"]
    assert (
        out["tang"][0]["ty_le"] == pytest.approx(0.07)
        and out["tang"][0]["tran"] is True
    )
    assert [r["ma"] for r in out["giam"]] == ["BBB"]
    assert out["giam"][0]["ty_le"] == pytest.approx(-0.05)
    assert out["do_rong"] == {"tang": 2, "giam": 1, "dung": 1, "chua_khop": 1}


def test_snapshot_nho_va_bao_loi_ro(monkeypatch):
    goi = []

    def fake_chart(ma):
        goi.append(ma)
        return _nen([("2026-11-25", 100.0), ("2026-11-26", 101.0)])

    monkeypatch.setattr(web_live, "_chart", fake_chart)
    monkeypatch.setattr(web_live, "_board", lambda syms: [_bg("AAA", 10000, 10100)])
    monkeypatch.setattr(web_live, "_vn100", lambda: ["AAA"])
    web_live.clear_cache()
    now = dt.datetime(2026, 11, 26, 10, 50, tzinfo=VN)
    a = web_live.snapshot(now)
    b = web_live.snapshot(now)
    assert a is b and goi == ["VNINDEX", "VN30"]  # lần hai lấy từ bộ nhớ, không gọi lại
    assert [x["ma"] for x in a["chi_so"]] == ["VNINDEX", "VN30"] and a["loi"] == []
    web_live.clear_cache()

    def hong(syms):
        raise web_live.LiveDataError("Vietcap trả lỗi 503")

    monkeypatch.setattr(web_live, "_board", hong)
    c = web_live.snapshot(now)
    assert c["chi_so"] and c["noi_bat"] is None
    assert c["loi"] == ["Bảng giá VN100: Vietcap trả lỗi 503"]
    web_live.clear_cache()


def _script():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "refresh_macro_bulletin", "scripts/refresh_macro_bulletin.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_job_ban_tin_vi_mo_bao_dung_trang_thai(tmp_path, monkeypatch, capsys):
    """Job D122: viết mới → 0; tin không đổi (gia hạn) → 0; lỗi tin/AI, bản lưu không đổi → 1."""
    import json as _json

    from valuation.data_access import macro_news as mn

    f = tmp_path / "cache.json"
    f.write_text(_json.dumps({"ts": 1.0, "text": "cũ"}), encoding="utf-8")
    monkeypatch.setattr(mn, "_MACRO_CACHE_FILE", f)
    mod = _script()

    def viet(force):
        f.write_text(_json.dumps({"ts": 9e12, "text": "mới"}), encoding="utf-8")
        return "mới"

    monkeypatch.setattr(mn, "get_macro_bulletin_cached", viet)
    assert mod.main() == 0 and '"viet_moi"' in capsys.readouterr().out

    def giu(force):
        f.write_text(
            _json.dumps({"ts": 1.0, "checked_at": 9e12, "text": "cũ"}), encoding="utf-8"
        )
        return "cũ"

    monkeypatch.setattr(mn, "get_macro_bulletin_cached", giu)
    assert mod.main() == 0 and '"tin_khong_doi"' in capsys.readouterr().out
    f.write_text(_json.dumps({"ts": 1.0, "text": "cũ"}), encoding="utf-8")
    monkeypatch.setattr(
        mn, "get_macro_bulletin_cached", lambda force: "⚠️ Không thể lấy được bản tin"
    )
    assert mod.main() == 1 and '"loi"' in capsys.readouterr().out
