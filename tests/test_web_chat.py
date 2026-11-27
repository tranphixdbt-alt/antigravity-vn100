"""Web hợp nhất, lát 7 (D120): góc chat AI "Hỏi Ếch" và các công cụ mới của nó.

Người dùng chốt 26/11/2026: góc chat dùng số liệu của chính web, học cách chia công cụ của TCBS. Các phép tính có ca
tính tay; DeepSeek và coin là giả; một test đọc DB thật của máy với mạng bị chặn.
"""

from __future__ import annotations

import datetime as dt
import json
import socket

import pandas as pd
import pytest

import valuation.services.assistant as a
from tests.test_web_auth import ORIGIN, client, coin_env
from tests.test_web_portfolio import vao
from valuation.db import web_user as wu
from valuation.services import web_chat
from valuation.services import web_chat_tools as t

U = frozenset({"FPT", "MBB", "VCB", "HPG", "VRE"})
CFG = {
    **a._cfg(),
    "max_calls": 3,
    "max_tickers": 5,
    "max_rows": 30,
    "max_sessions": 250,
    "breadth_max_sessions": 60,
    "foreign_max_sessions": 60,
    "cw_max_rows": 20,
}


# ---------- phép tính, tính tay ----------


def test_do_rong_tinh_tay():
    """A 10→11→11, B 20→19→21, C 5→trống→6. Phiên 2: A tăng, B giảm, C thiếu giá (bỏ).
    Phiên 3: A đứng, B tăng, C thiếu giá phiên trước (bỏ)."""
    closes = pd.DataFrame(
        {"A": [10, 11, 11], "B": [20, 19, 21], "C": [5, None, 6]},
        index=pd.to_datetime(["2026-11-20", "2026-11-23", "2026-11-24"]),
    )
    assert t.breadth_counts(closes, 5) == [
        {"ngay": "2026-11-23", "tang": 1, "giam": 1, "dung": 0},
        {"ngay": "2026-11-24", "tang": 1, "giam": 0, "dung": 1},
    ]
    assert t.breadth_counts(closes, 1) == [
        {"ngay": "2026-11-24", "tang": 1, "giam": 0, "dung": 1}
    ]
    assert t.breadth_counts(closes.iloc[:1], 5) == []


def test_dong_gop_vao_ro_tinh_tay():
    """A: giá 10→11, 100 cổ phiếu, vốn hóa đầu 1.000; B: 20→18, 50 cổ phiếu, vốn hóa đầu 1.000; C thiếu số cổ phiếu.
    Tỷ trọng 0,5 và 0,5; A +10% → +5 điểm %, B −10% → −5 điểm %; tổng 0, đúng bằng (1.100 + 900) ÷ 2.000 − 1.
    """
    first = pd.Series({"A": 10.0, "B": 20.0, "C": 7.0})
    last = pd.Series({"A": 11.0, "B": 18.0, "C": 8.0})
    df = t.contributions(first, last, {"A": 100.0, "B": 50.0})
    assert list(df["ma"]) == ["A", "B"]
    assert df["ty_trong"].tolist() == pytest.approx([0.5, 0.5])
    assert df["dong_gop"].tolist() == pytest.approx([5.0, -5.0])
    assert df["dong_gop"].sum() == pytest.approx(
        (11 * 100 + 18 * 50) / (10 * 100 + 20 * 50) * 100 - 100
    )


def test_ky_thuat_chuoi_tang_giam_deu():
    """Giá tăng đều 1..260: giá cuối trên cả 6 đường trung bình, RSI14 = 100 (không phiên nào giảm), cách đỉnh 1 năm 0%,
    cách đáy 1 năm (giá thấp nhất trong 250 phiên cuối là 11): 260 ÷ 11 − 1 = 2.263,6%. Giảm đều thì ngược lại.
    """
    tang = t.tech_summary(pd.Series(range(1, 261), dtype=float))
    assert tang["so_duong_gia_dang_tren"] == 6 and tang["so_duong_tinh_duoc"] == 6
    assert tang["rsi14"] == 100.0 and tang["cach_dinh_pct"] == 0.0
    assert tang["cach_day_pct"] == pytest.approx(2263.6, abs=0.05)
    assert tang["duong_trung_binh"]["5"] == 258  # (256 + 257 + 258 + 259 + 260) ÷ 5
    giam = t.tech_summary(pd.Series(range(260, 0, -1), dtype=float))
    assert (
        giam["so_duong_gia_dang_tren"] == 0
        and giam["rsi14"] == 0.0
        and giam["cach_day_pct"] == 0.0
    )
    ngan = t.tech_summary(pd.Series(range(1, 31), dtype=float))
    assert ngan["so_duong_tinh_duoc"] == 3  # 30 phiên chỉ tính được đường 5, 10, 20


def test_cung_nganh_hang_va_cong_cong_bo():
    rows = [
        {
            "ticker": "A",
            "sector": "X",
            "metrics": {"roe": 0.2, "revenue_cagr": 0.1},
            "upside_pct": 12.0,
            "blockers": [],
        },
        {
            "ticker": "B",
            "sector": "X",
            "metrics": {"roe": 0.3, "revenue_cagr": 0.05},
            "upside_pct": 40.0,
            "blockers": ["x"],
        },
        {
            "ticker": "C",
            "sector": "Y",
            "metrics": {"roe": 0.5},
            "upside_pct": 5.0,
            "blockers": [],
        },
    ]
    d = t.peer_table(rows, "A")
    assert (
        d["so_ma_cung_nganh"] == 2
        and d["hang_roe"] == 2
        and d["hang_tang_truong_doanh_thu"] == 1
    )
    by = {r["ma"]: r for r in d["cac_ma"]}
    assert by["A"]["roe_pct"] == 20.0 and by["A"]["upside_pct"] == 12.0
    assert by["B"]["upside_pct"] is None  # chưa qua cổng công bố: không đưa upside
    # cột trống ở cả ngành (nợ xấu ngoài ngân hàng, điểm hồ sơ chưa có) bỏ hẳn; upside trống vẫn giữ vì nghĩa là chưa công bố
    assert (
        "no_xau_pct" not in by["A"]
        and "diem_tich_san" not in by["A"]
        and "upside_pct" in by["B"]
    )
    assert "error" in t.peer_table(rows, "Z")


def test_ma_gan_nut_mo():
    calls = [("valuate", {"tickers": ["FPT", "MBB"]}), ("peers", {"ticker": "VCB"})]
    assert web_chat.linked_tickers(calls, "HPG và FPT tăng; XYZ không có", U, 6) == [
        "FPT",
        "MBB",
        "VCB",
        "HPG",
    ]
    assert web_chat.linked_tickers(calls, "HPG", U, 2) == ["FPT", "MBB"]


def test_lam_sach_cau_hoi():
    assert (
        web_chat.clean_question("  Thị trường\n\thôm nay\x00 thế nào? ", 300)
        == "Thị trường hôm nay thế nào?"
    )
    for xau in ("", "   ", 123, "a" * 301):
        with pytest.raises(web_chat.ChatError) as e:
            web_chat.clean_question(xau, 300)
        assert e.value.status == 422


def _khoi_ngoai() -> pd.DataFrame:
    d = [dt.date(2026, 11, x) for x in (19, 20, 23, 25)]
    rows = [
        # FPT 23/11 là số thật Vietcap (đồng); 20/11 thiếu số khối ngoại (NaN), không được coi là 0
        ("FPT", d[0], 100e9, 300e9, -200e9, -4e6),
        ("FPT", d[1], None, None, None, None),
        ("FPT", d[2], 225151047950.0, 200121286500.0, 25029761450.0, 519010.0),
        ("FPT", d[3], 110e9, 110e9, 0.0, 0.0),
        ("VCB", d[2], 50e9, 20e9, 30e9, 5e5),
        ("VCB", d[3], 10e9, 5e9, 5e9, 1e5),
        ("HPG", d[3], 1e9, 41e9, -40e9, -1e6),
    ]
    return pd.DataFrame(
        rows, columns=["ma", "ngay", "mua", "ban", "rong", "rong_kl"]
    ).astype({c: float for c in ("mua", "ban", "rong", "rong_kl")})


def test_khoi_ngoai_mot_ma_tinh_tay():
    out = t.foreign_ticker_table(
        _khoi_ngoai(), "FPT", 3
    )  # 3 phiên cuối của rổ: 20, 23, 25/11
    assert out["so_phien"] == 3 and out["phien_thieu"] == ["2026-11-20"]
    assert [x["ngay"] for x in out["phien"]] == ["2026-11-23", "2026-11-25"]
    # 225.151.047.950 đ = 225,15 tỷ; ròng 25.029.761.450 đ = 25,03 tỷ
    assert out["phien"][0] == {
        "ngay": "2026-11-23",
        "mua_ty": 225.15,
        "ban_ty": 200.12,
        "rong_ty": 25.03,
        "rong_cp": 519010,
    }
    # tổng ròng = 25,03 + 0 = 25,03 tỷ; 1 phiên mua ròng, phiên ròng 0 không tính mua hay bán
    assert out["tong_rong_ty"] == 25.03 and (
        out["phien_mua_rong"],
        out["phien_ban_rong"],
    ) == (1, 0)
    assert (
        t.foreign_ticker_table(_khoi_ngoai(), "MBB", 3)["tong_rong_ty"] is None
    )  # không có số: không bịa 0


def test_khoi_ngoai_xep_hang_tinh_tay():
    out = t.foreign_rank(_khoi_ngoai(), 2, 5)  # 23/11 và 25/11
    assert (out["tu_ngay"], out["den_ngay"], out["so_phien"]) == (
        "2026-11-23",
        "2026-11-25",
        2,
    )
    # VCB 30 + 5 = 35 tỷ; FPT 25,03 + 0; HPG −40; cả rổ 35 + 25,03 − 40 = 20,03
    assert out["mua_rong_nhieu_nhat"] == [
        {"ma": "VCB", "rong_ty": 35.0},
        {"ma": "FPT", "rong_ty": 25.03},
    ]
    assert out["ban_rong_nhieu_nhat"] == [{"ma": "HPG", "rong_ty": -40.0}]
    assert out["ro_rong_ty"] == 20.03 and out["phien_thieu_khoi_ngoai"] == []
    # 3 phiên: 20/11 chỉ FPT có dòng và dòng đó thiếu số (0% < 50%) → ghi phiên thiếu
    assert t.foreign_rank(_khoi_ngoai(), 3, 5)["phien_thieu_khoi_ngoai"] == [
        "2026-11-20"
    ]


def test_kiem_tham_so_cong_cu_khoi_ngoai():
    plan = {
        "calls": [
            {"tool": "foreign_flow", "args": {"ticker": "fpt", "sessions": 999}},
            {"tool": "foreign_top", "args": {"top": 999}},
            {"tool": "foreign_flow", "args": {"ticker": "ZZZ"}},
        ]
    }
    calls, _ = a.validate(plan, U, CFG, t.WEB_TOOLS)
    assert calls == [
        ("foreign_flow", {"ticker": "FPT", "sessions": 60}),
        ("foreign_top", {"sessions": 5, "top": 30}),
    ]


def _cw(ma, cs, nhom, dat_re, don_bay):
    return {
        "ma": ma,
        "cs": cs,
        "nhom": nhom,
        "dat_re": dat_re,
        "don_bay": don_bay,
        "kl": 1000,
        "tcph": "X",
        "con_ngay": 81,
    }


CW_DATA = {
    "co": True,
    "lan_quet": "14:02 27/11/2026",
    "cu": None,
    "tong": 4,
    "nhom": [
        {"ma": "NÊN XEM XÉT", "ten": "Nên xem xét", "so": 2},
        {"ma": "BỎ QUA", "ten": "Bỏ qua", "so": 2},
    ],
    "cw": [
        # dòng đầu là số thật CVRE2609 lúc quét 27/11/2026: giá mua 800, giá hợp lý 1.068 → rẻ 25,1%
        _cw("CVRE2609", "VRE", "NÊN XEM XÉT", -25.1, 8.1),
        _cw("CVRE2610", "VRE", "BỎ QUA", 12.0, 5.0),
        _cw("CFPT2601", "FPT", "NÊN XEM XÉT", -3.0, 9.5),
        _cw("CHPG2602", "HPG", "BỎ QUA", None, 4.0),
    ],
}


def test_chung_quyen_loc_va_xep():
    out = t.cw_table(CW_DATA, "VRE", None, None, 10)
    assert [r["ma"] for r in out["cw"]] == ["CVRE2609", "CVRE2610"] and out[
        "so_dong_khop_loc"
    ] == 2
    assert (
        out["so_theo_nhom"] == {"Nên xem xét": 2, "Bỏ qua": 2}
        and out["lan_quet"] == "14:02 27/11/2026"
    )
    # rẻ nhất trước; mã thiếu số đắt/rẻ bị bỏ khỏi phép xếp
    assert [r["ma"] for r in t.cw_table(CW_DATA, None, None, "re", 10)["cw"]] == [
        "CVRE2609",
        "CFPT2601",
        "CVRE2610",
    ]
    assert [
        r["ma"] for r in t.cw_table(CW_DATA, None, "nen_xem_xet", "don_bay", 1)["cw"]
    ] == ["CFPT2601"]
    assert t.cw_table({"co": False}, None, None, None, 5) == {
        "error": "Chưa có lần quét chứng quyền nào"
    }
    assert t.cw_table(
        {"error": "Dịch vụ chứng quyền: không kết nối được"}, None, None, None, 5
    )["error"].startswith("Dịch vụ")


def test_etf_mot_quy_va_dem_dat():
    data = {
        "co": True,
        "luc": "lúc 15:10 26/11/2026",
        "so_quy": 2,
        "nguong": {"lai_rong": 0.5},
        "chiet_khau": {
            "dong": [
                {"Mã": "FUEVFVND", "Đạt": True, "Chiết khấu mua được %": 1.2},
                {"Mã": "FUEPHVNS", "Đạt": False, "Chiết khấu mua được %": 0.49},
            ]
        },
        "chi_so": {"dong": [{"Mã": "VNINDEX", "Giá": 1629.68, "1T %": -7.59}]},
    }
    out = t.etf_table(data, None, 10)
    assert out["so_quy_dat_nguong"] == 1 and [r["Mã"] for r in out["quy"]] == [
        "FUEVFVND",
        "FUEPHVNS",
    ]
    assert out["chi_so"][0]["Giá"] == 1629.68
    assert [r["Mã"] for r in t.etf_table(data, "FUEPHVNS", 10)["quy"]] == ["FUEPHVNS"]
    assert "error" in t.etf_table(data, "ZZZZ", 10)


def test_kiem_tham_so_cong_cu_chung_quyen_etf():
    plan = {
        "calls": [
            {
                "tool": "cw_list",
                "args": {"underlying": "vre", "group": "xau", "sort": "re", "top": 999},
            },
            {"tool": "cw_detail", "args": {"code": "cvre2609; drop"}},
            {"tool": "etf", "args": {"code": "fuevfvnd"}},
        ]
    }
    calls, notes = a.validate(plan, U, CFG, t.WEB_TOOLS)
    assert calls == [
        ("cw_list", {"underlying": "VRE", "group": None, "sort": "re", "top": 20}),
        ("etf", {"code": "FUEVFVND", "top": 10}),
    ] and any("chứng quyền không hợp lệ" in n for n in notes)
    calls, _ = a.validate(
        {
            "calls": [
                {"tool": "cw_detail", "args": {"code": "CVRE2609"}},
                {"tool": "futures"},
            ]
        },
        U,
        CFG,
        t.WEB_TOOLS,
    )
    assert calls == [("cw_detail", {"code": "CVRE2609"}), ("futures", {})]


def test_bo_cong_cu_web_khong_doi_bot_discord():
    plan = {
        "calls": [
            {"tool": "breadth", "args": {"sessions": 999}},
            {"tool": "index_movers", "args": {"sessions": 20, "top": 999}},
            {"tool": "technical", "args": {"ticker": "hpg"}},
        ]
    }
    calls, _ = a.validate(plan, U, CFG, t.WEB_TOOLS)
    assert calls == [
        ("breadth", {"sessions": 60}),
        ("index_movers", {"sessions": 20, "top": 30}),
        ("technical", {"ticker": "HPG"}),
    ]
    calls, _ = a.validate(
        {
            "calls": [
                {"tool": "peers", "args": {"ticker": "ZZZ"}},
                {"tool": "market_today"},
            ]
        },
        U,
        CFG,
        t.WEB_TOOLS,
    )
    assert calls == [("market_today", {})]
    # bot Discord vẫn chỉ có bộ công cụ cũ
    calls, notes = a.validate(plan, U, CFG)
    assert calls == [] and any("breadth" in n for n in notes)
    assert set(t.WEB_TOOLS) - set(a.TOOLS) == {
        "market_today",
        "breadth",
        "index_movers",
        "technical",
        "foreign_flow",
        "foreign_top",
        "cw_list",
        "cw_detail",
        "etf",
        "futures",
        "alerts",
        "peers",
    }


# ---------- dịch vụ và đường API ----------


@pytest.fixture
def env(tmp_path, monkeypatch):
    yield from coin_env(tmp_path, monkeypatch)


@pytest.fixture
def ai(monkeypatch):
    """Trợ lý giả: ghi lại câu hỏi và bộ công cụ nhận được; `state` đặt kết quả hoặc lỗi cho lần gọi kế tiếp."""
    state: dict = {"goi": [], "loi": None, "kq": None}

    def ask(text, tools=None, answer_system=None):
        state["goi"].append({"text": text, "tools": tools, "system": answer_system})
        if state["loi"]:
            raise state["loi"]
        return state["kq"] or {
            "answer": "VRE tăng nhẹ, FPT giảm.",
            "sources": "**VRE** giá 24.250 · ⛔ chưa công bố FV",
            "calls": [("valuate", {"tickers": ["VRE"]})],
            "notes": [],
        }

    monkeypatch.setattr(web_chat.assistant, "ask", ask)
    monkeypatch.setattr(web_chat.assistant, "vn100", lambda: U)
    return state


def hoi(c, cau="Thị trường hôm nay thế nào?", headers=ORIGIN):
    return c.post("/api/hoi-ai", json={"cau_hoi": cau}, headers=headers)


def dong_hoi(env):
    with env["db"]() as db:
        return [
            (x.user_id, x.viec, x.chi_tiet)
            for x in db.query(wu.WebAudit).filter(wu.WebAudit.viec == "hoi_ai")
        ]


def test_trang_thai_va_tra_loi_tru_mot_luot(env, ai):
    an = vao(env, "t-an")
    s = an.get("/api/hoi-ai").json()
    assert (
        s["con_lai"] == 20
        and s["gioi_han"] == 20
        and len(s["goi_y"]) == 8
        and s["toi_da_ky_tu"] == 300
    )
    r = hoi(an)
    assert r.status_code == 200, r.text
    d = r.json()
    assert (
        d["tra_loi"] == "VRE tăng nhẹ, FPT giảm."
        and d["con_lai"] == 19
        and d["ngoai_pham_vi"] is False
    )
    assert d["ma"] == ["VRE", "FPT"] and d["cong_cu"] == ["valuate"]
    assert "⛔" not in d["nguon"] and "chưa công bố FV" in d["nguon"]
    assert (
        ai["goi"][0]["tools"] is t.WEB_TOOLS
        and ai["goi"][0]["system"] == web_chat.ANSWER_SYSTEM
    )
    ((_, viec, chi_tiet),) = dong_hoi(env)
    assert viec == "hoi_ai" and json.loads(chi_tiet) == {
        "cong_cu": ["valuate"],
        "do_dai": 27,
    }
    assert "Thị trường" not in chi_tiet  # không lưu câu hỏi


def test_cau_ngoai_pham_vi_va_loi_khong_tinh_luot(env, ai):
    an = vao(env, "t-an")
    ai["kq"] = {"answer": "Chưa hỗ trợ", "sources": "", "calls": [], "notes": []}
    d = hoi(an, "viết code cho tôi").json()
    assert d["ngoai_pham_vi"] is True and d["con_lai"] == 20
    ai["kq"], ai["loi"] = None, RuntimeError("⚠️ Lỗi kết nối tới DeepSeek: khóa ...")
    r = hoi(an)
    assert (
        r.status_code == 502
        and "không bị tính" in r.json()["detail"]
        and "khóa" not in r.json()["detail"]
    )
    ai["loi"], ai["kq"] = None, {
        "answer": "⚠️ Lỗi khi gọi DeepSeek API",
        "sources": "",
        "calls": [("macro", {})],
        "notes": [],
    }
    assert hoi(an).status_code == 502
    assert dong_hoi(env) == [] and an.get("/api/hoi-ai").json()["con_lai"] == 20


def test_het_20_cau_thi_bao_429_khong_goi_ai(env, ai):
    an = vao(env, "t-an")
    uid = an.get("/api/toi").json()["id"]
    with env["db"]() as db:
        for i in range(20):
            db.add(
                wu.WebAudit(
                    luc=wu.now_utc() - dt.timedelta(seconds=i),
                    user_id=uid,
                    viec="hoi_ai",
                    doi_tuong="hoi_ai",
                )
            )
        db.commit()
    r = hoi(an)
    assert r.status_code == 429 and "20 câu" in r.json()["detail"] and ai["goi"] == []
    assert hoi(client("t-sep")).status_code == 200  # hạn mức theo từng tài khoản


def test_chan_quyen_va_cau_hoi_xau(env, ai):
    assert hoi(client()).status_code == 401
    cho = vao(env, "t-an", duyet=False)
    assert hoi(cho).status_code == 403 and cho.get("/api/hoi-ai").status_code == 403
    an = vao(env, "t-an")
    assert hoi(an, headers={}).status_code == 403  # thiếu Origin
    assert hoi(an, "a" * 301).status_code == 422
    assert hoi(an, "   ").status_code == 422
    lock = web_chat._user_lock(an.get("/api/toi").json()["id"])
    assert lock.acquire(blocking=False)
    try:
        assert hoi(an).status_code == 409
    finally:
        lock.release()
    assert ai["goi"] == []


def test_cong_cu_tren_db_that():
    """DB thật của máy, mạng bị chặn: các công cụ chạy được và số khớp nhau."""
    from valuation.db.models import Ticker
    from valuation.db.session import SessionLocalRead

    db = SessionLocalRead()
    try:
        if db.query(Ticker).filter(Ticker.ticker == "VRE").first() is None:
            pytest.skip("DB của máy không có VRE")
    finally:
        db.close()

    def blocked(*args, **kwargs):
        raise OSError("mạng bị chặn trong test")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(socket.socket, "connect", blocked)
        mp.setattr(socket, "create_connection", blocked)
        b = t.tool_breadth(5)
        m = t.tool_index_movers(20, 3)
        k = t.tool_technical("VRE")
        p = t.tool_peers("VRE")
        h = t.tool_market_today()
        f = t.tool_foreign_flow("VRE", 10)
        r = t.tool_foreign_top(5, 3)
    assert b["so_phien"] == 5 and all(
        x["tang"] + x["giam"] + x["dung"] <= 100 for x in b["phien"]
    )
    assert len(m["keo_len"]) == 3 and m["so_ma_tinh"] > 50
    assert (
        m["keo_len"][0]["dong_gop_diem_pct"] >= m["keo_xuong"][0]["dong_gop_diem_pct"]
    )
    assert (
        k["ticker"] == "VRE"
        and 0 <= k["so_duong_gia_dang_tren"] <= k["so_duong_tinh_duoc"] <= 6
    )
    assert p["ma"] == "VRE" and p["so_ma_cung_nganh"] >= 1
    assert h["nhan_thi_truong"] and len(h["bon_tru_cot"]) == 4
    assert (
        f["ma"] == "VRE"
        and f["so_phien"] == 10
        and len(f["phien"]) + len(f["phien_thieu"]) == 10
    )
    assert r["so_phien"] == 5 and len(r["mua_rong_nhieu_nhat"]) <= 3
