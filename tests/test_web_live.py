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
    assert a == b and goi == ["VNINDEX", "VN30"]  # lần hai lấy từ bộ nhớ, không gọi lại
    assert [x["ma"] for x in a["chi_so"]] == ["VNINDEX", "VN30"] and a["loi"] == []
    web_live.clear_cache()

    def hong(syms):
        raise web_live.LiveDataError("Vietcap trả lỗi 503")

    monkeypatch.setattr(web_live, "_board", hong)
    c = web_live.snapshot(now)
    assert c["chi_so"] and c["noi_bat"] is None
    assert c["loi"] == ["Bảng giá VN100: Vietcap trả lỗi 503"]
    web_live.clear_cache()


def test_trong_gio_lay_lien_tuc_ngoai_gio_chi_4h_8h(monkeypatch):
    """Người dùng 26/11/2026: trong giờ lấy giá liên tục; ngoài giờ chỉ lấy lúc 4 giờ, 8 giờ sáng để kiểm."""
    goi = []
    monkeypatch.setattr(
        web_live,
        "_chart",
        lambda ma: goi.append(ma)
        or _nen([("2026-11-25", 100.0), ("2026-11-26", 101.0)]),
    )
    monkeypatch.setattr(web_live, "_board", lambda syms: [_bg("AAA", 10000, 10100)])
    monkeypatch.setattr(web_live, "_vn100", lambda: ["AAA"])
    web_live.clear_cache()
    lan = lambda: len(goi) // 2  # mỗi lượt lấy gọi 2 chỉ số
    t = lambda d, h, m, s=0: dt.datetime(
        2026, 11, d, h, m, s, tzinfo=VN
    )  # 26/11/2026 thứ Năm, 28/11 thứ Bảy

    # trong giờ: nhớ 5 giây, trình duyệt hỏi lại sau 10 giây
    r = web_live.snapshot(t(26, 10, 0, 0))
    assert r["trong_gio"] is True and r["hoi_lai_giay"] == 10 and lan() == 1
    web_live.snapshot(t(26, 10, 0, 4))
    assert lan() == 1
    web_live.snapshot(t(26, 10, 0, 5))
    assert lan() == 2

    # 15:05 hết giờ: lấy một lượt giá đã chốt rồi giữ tới 4 giờ sáng hôm sau, dù có người xem lúc 20:08
    web_live.snapshot(t(26, 15, 4, 50))
    r = web_live.snapshot(t(26, 15, 6))
    assert lan() == 4 and r["trong_gio"] is False
    r = web_live.snapshot(t(26, 20, 8))
    assert lan() == 4
    # D128: ngoài giờ trình duyệt vẫn hỏi web 5 phút một lần để thấy DB có số mới (15:45, 17:45), nhưng lượt hỏi đó
    # không gọi Vietcap (lan() vẫn 4 ở trên); sát mốc 4 giờ thì hỏi đúng mốc: 03:58 → 04:00 là 120 giây, +5 giây
    assert r["hoi_lai_giay"] == 300
    assert web_live.snapshot(t(27, 3, 58))["hoi_lai_giay"] == 125 and lan() == 4
    web_live.snapshot(t(27, 4, 0, 1))
    assert lan() == 5
    web_live.snapshot(t(27, 7, 59))
    assert lan() == 5
    web_live.snapshot(t(27, 8, 0, 1))
    assert lan() == 6
    web_live.snapshot(t(27, 8, 30))
    assert lan() == 6
    # thứ Bảy: không có giờ giao dịch, chỉ 2 mốc kiểm
    assert web_live.in_live_hours(t(28, 10, 0)) is False
    assert web_live.next_mark(t(28, 10, 0)) == t(29, 4, 0)
    assert web_live.last_mark(t(28, 10, 0)) == t(28, 8, 0)
    # thứ Sáu 27/11 sau 8 giờ: mốc kế tiếp là lúc vào giờ 09:00
    assert web_live.next_mark(t(27, 8, 30)) == t(27, 9, 0)
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


# ---------- D128: phiên trên bảng giá của từng mã (nến hôm nay, khối ngoại trong phiên) ----------
def _bg_phien(ma, time, khop, mo=1, cao=1, thap=1, mua=0, ban=0, kl=0, gt=0):
    return {
        "listingInfo": {"symbol": ma, "refPrice": 43_500},
        "matchPrice": {
            "symbol": ma,
            "time": time,
            "matchPrice": khop,
            "openPrice": mo,
            "highest": cao,
            "lowest": thap,
            "accumulatedVolume": kl,
            "accumulatedValue": gt,
            "foreignBuyValue": mua,
            "foreignSellValue": ban,
        },
    }


def test_session_bars_tinh_tay_fpt_27_11():
    """Số thật FPT phiên 27/11/2026 trên bảng giá Vietcap, khớp từng đồng với dòng job 15:45 ghi vào DB."""
    rows = [
        _bg_phien(
            "FPT", "2026-11-27T07:45:00.006Z", 44_600, 43_800, 45_300, 43_750,
            268_400_876_200, 86_508_778_250, 12_431_700, 554_623_000_000,
        ),
        _bg_phien("AAA", "2026-11-27T02:20:00Z", 0),  # chưa khớp lệnh: bỏ
        _bg_phien("BBB", "2026-11-26T20:00:00Z", 10_000, 0, 10_100, 9_900),  # 03:00 ngày 27/11 giờ VN; thiếu giá mở
        _bg_phien("CCC", "không phải ngày", 10_000),  # không đọc được giờ: bỏ, không đoán ngày
    ]  # fmt: skip
    bars = web_live.session_bars(rows, VN)
    assert set(bars) == {"FPT", "BBB"}
    f = bars["FPT"]
    assert f["ngay"] == dt.date(2026, 11, 27)  # 07:45 UTC = 14:45 giờ VN
    assert (f["mo"], f["cao"], f["thap"], f["gia"], f["kl"]) == (
        43_800, 45_300, 43_750, 44_600, 12_431_700
    )  # fmt: skip
    # tính tay: 268.400.876.200 − 86.508.778.250 = 181.892.097.950 đồng (DB 27/11: foreign_net_val 181.892.097.950)
    assert f["nn_rong"] == 181_892_097_950 and f["nen"] is True
    b = bars["BBB"]
    assert (
        b["ngay"] == dt.date(2026, 11, 27) and b["nen"] is False
    )  # không vẽ nến thiếu giá mở
    assert (
        b["nn_rong"] == 0
    )  # mua 0, bán 0 là số thật (không ai giao dịch), không phải thiếu


def test_foreign_summary_tinh_tay():
    d, cu = dt.date(2026, 11, 27), dt.date(2026, 11, 26)
    bars = {
        "AAA": {"ngay": d, "nn_rong": 5e9},
        "BBB": {"ngay": d, "nn_rong": -3e9},
        "CCC": {"ngay": d, "nn_rong": 2e9},
        "DDD": {"ngay": d, "nn_rong": None},  # thiếu số: không tính
        "EEE": {"ngay": cu, "nn_rong": 9e9},  # phiên cũ hơn: không tính
    }
    s = web_live.foreign_summary(bars, 1)
    # tính tay: 5 − 3 + 2 = 4 tỷ trên 3 mã; mua ròng nhiều nhất AAA, bán ròng nhiều nhất BBB
    assert s == {
        "ngay": d,
        "rong": 4e9,
        "so_ma": 3,
        "mua": [{"ma": "AAA", "rong": 5e9}],
        "ban": [{"ma": "BBB", "rong": -3e9}],
    }
    assert web_live.foreign_summary({}, 3) is None


def test_snapshot_co_khoi_ngoai_nhung_khong_gui_tung_ma(monkeypatch):
    monkeypatch.setattr(
        web_live,
        "_chart",
        lambda ma: _nen([("2026-11-26", 100.0), ("2026-11-27", 101.0)]),
    )
    rows = [
        _bg_phien("FPT", "2026-11-27T03:00:00Z", 44_600, 43_800, 45_000, 43_700, 3e9, 1e9),
        _bg_phien("HPG", "2026-11-27T03:00:00Z", 19_900, 19_800, 20_000, 19_700, 1e9, 2e9),
    ]  # fmt: skip
    for r in rows:
        r["listingInfo"]["refPrice"] = r["matchPrice"]["matchPrice"]
    monkeypatch.setattr(web_live, "_board", lambda syms: rows)
    monkeypatch.setattr(web_live, "_vn100", lambda: ["FPT", "HPG"])
    web_live.clear_cache()
    now = dt.datetime(2026, 11, 27, 10, 0, tzinfo=VN)
    s = web_live.snapshot(now)
    assert "phien" not in s  # 100 mã × 10 trường không gửi mỗi 10 giây
    kn = s["noi_bat"]["khoi_ngoai"]
    assert kn["rong"] == 1e9 and [x["ma"] for x in kn["mua"]] == ["FPT"]  # 2 − 1 tỷ
    bars, loi = web_live.session_data(now)
    assert set(bars) == {"FPT", "HPG"} and loi == []
    assert s["hoi_bieu_do_giay"] == 30
    web_live.clear_cache()
