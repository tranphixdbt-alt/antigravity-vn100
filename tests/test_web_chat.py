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
        and len(s["goi_y"]) == 6
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
