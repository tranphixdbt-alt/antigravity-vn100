"""Web hợp nhất, lát 7 (D116): nút sinh báo cáo AI bản ngắn trên tờ mã.

Người dùng chốt 25/11/2026: mọi tài khoản đã duyệt bấm được, 5 lượt sinh mới mỗi tài khoản mỗi ngày, báo cáo
khoảng 500 từ. Coin, DeepSeek và gói dữ liệu đều giả (trừ một test đọc DB thật của máy, mạng bị chặn).
"""

from __future__ import annotations

import datetime as dt
import json
import socket
from types import SimpleNamespace
from typing import ClassVar

import pytest

from tests.test_web_auth import ORIGIN, client, coin_env
from tests.test_web_portfolio import vao
from valuation.config import settings
from valuation.db import web_user as wu
from valuation.report import verified_summary as vs
from valuation.services import web_ai_report as w
from valuation.services import web_valuation

PHAN = {
    "ket_luan": "VRE rẻ hơn giá trị hợp lý nhưng dòng tiền chưa xác nhận.",
    "tong_quan": "Công ty cho thuê trung tâm thương mại.",
    "nhan_dinh": "Định giá thấp hơn trung vị công ty chứng khoán.",
    "rui_ro": ["Rủi ro một.", "Rủi ro hai.", "Rủi ro ba."],
}


@pytest.fixture
def env(tmp_path, monkeypatch):
    yield from coin_env(tmp_path, monkeypatch)


@pytest.fixture
def ai(tmp_path, monkeypatch):
    """Gói dữ liệu và DeepSeek giả. `state["dau_vao"]` là dấu vân tay gói dữ liệu; đổi nó = dữ liệu đã đổi."""
    state: dict = {"dau_vao": "fp-1", "goi": 0, "loi": None}
    monkeypatch.setattr(vs, "_REPORT_CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(web_valuation, "known", lambda db, ma: ma in ("VRE", "HPG"))

    def build_inputs(db, ma):
        return {
            "payload": {"ticker": ma},
            "fingerprint": state["dau_vao"],
            "model": "deepseek-v4-flash",
            "nguon": {
                "gia": 24250.0,
                "gia_tri_hop_ly": 31852.0,
                "gia_den": "2026-11-23",
            },
        }

    def call_model(payload, model):
        if state["loi"]:
            raise state["loi"]
        state["goi"] += 1
        return {
            "phan": dict(PHAN),
            "mo_hinh": model,
            "token_vao": 9000,
            "token_ra": 900,
        }

    monkeypatch.setattr(w, "build_inputs", build_inputs)
    monkeypatch.setattr(w, "call_model", call_model)
    return state


def utc(*parts: int) -> dt.datetime:
    """Mốc UTC không kèm múi giờ, đúng kiểu cột `luc` của web_audit."""
    return dt.datetime(*parts, tzinfo=dt.timezone.utc).replace(tzinfo=None)


def sinh(c, ma="VRE", headers=ORIGIN):
    return c.post(f"/api/co-phieu/{ma}/bao-cao-ai", json={}, headers=headers)


def dong_bao_cao(env) -> list[tuple[int | None, str, str]]:
    with env["db"]() as db:
        return [
            (a.user_id, a.viec, a.doi_tuong)
            for a in db.query(wu.WebAudit)
            .filter(wu.WebAudit.viec == w.VIEC)
            .order_by(wu.WebAudit.id)
        ]


def test_chua_sinh_thi_chua_co_ban_va_con_du_luot(env, ai):
    d = vao(env, "t-an").get("/api/co-phieu/VRE/bao-cao-ai").json()
    assert d == {
        "ma": "VRE",
        "bao_cao": None,
        "con_lai": 5,
        "gioi_han": 5,
        "so_tu": 500,
    }


def test_sinh_moi_luu_ban_dung_chung_va_tru_mot_luot(env, ai, tmp_path):
    an = vao(env, "t-an")
    r = sinh(an)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["dung_lai"] is False and d["con_lai"] == 4 and ai["goi"] == 1
    bc = d["bao_cao"]
    assert bc["van_ban"] == w.to_markdown("VRE", PHAN)
    assert (
        bc["mo_hinh"] == "deepseek-v4-flash" and bc["nguon"]["gia_den"] == "2026-11-23"
    )
    assert (
        "dau_vao" not in bc and "token_vao" not in bc
    )  # chỉ để truy vết trong tệp, không đưa ra giao diện
    saved = json.loads(
        (tmp_path / "cache" / "ban_ngan" / "VRE.json").read_text(encoding="utf-8")
    )
    assert (
        saved["dau_vao"] == "fp-1"
        and saved["token_ra"] == 900
        and saved["phien_ban"] == w.PROMPT_VERSION
    )
    an_id = an.get("/api/toi").json()["id"]
    assert dong_bao_cao(env) == [(an_id, "bao_cao_ai", "co_phieu:VRE")]
    # người khác thấy cùng bản đó, lượt của họ vẫn đủ 5
    sep = client("t-sep").get("/api/co-phieu/VRE/bao-cao-ai").json()
    assert sep["bao_cao"]["van_ban"] == bc["van_ban"] and sep["con_lai"] == 5


def test_du_lieu_khong_doi_thi_dung_lai_khong_tru_luot(env, ai):
    an = vao(env, "t-an")
    assert sinh(an).json()["con_lai"] == 4
    d = sinh(an).json()
    assert d["dung_lai"] is True and d["con_lai"] == 4 and ai["goi"] == 1
    ai["dau_vao"] = "fp-2"  # dữ liệu đổi: sinh mới, trừ lượt
    d = sinh(an).json()
    assert d["dung_lai"] is False and d["con_lai"] == 3 and ai["goi"] == 2


def test_het_5_luot_thi_bao_429_va_khong_goi_ai(env, ai):
    """Tính tay: hạn mức 5, mỗi lần dữ liệu khác nhau nên mỗi lần trừ 1: còn 4, 3, 2, 1, 0; lần thứ 6 bị chặn."""
    an = vao(env, "t-an")
    con = []
    for i in range(5):
        ai["dau_vao"] = f"fp-{i}"
        r = sinh(an, "VRE" if i % 2 else "HPG")
        assert r.status_code == 200
        con.append(r.json()["con_lai"])
    assert con == [4, 3, 2, 1, 0]
    ai["dau_vao"] = "fp-6"
    r = sinh(an)
    assert r.status_code == 429 and "hết 5 lượt" in r.json()["detail"]
    assert ai["goi"] == 5 and len(dong_bao_cao(env)) == 5
    assert an.get("/api/co-phieu/VRE/bao-cao-ai").json()["con_lai"] == 0
    # hạn mức tính theo từng tài khoản
    assert sinh(client("t-sep")).json()["con_lai"] == 4


def test_qua_0_gio_viet_nam_thi_co_lai_luot(env):
    """Tính tay: 23:59 giờ VN ngày 25/11 là 16:59 UTC; 00:00 giờ VN ngày 26/11 là 17:00 UTC ngày 25/11."""
    with env["db"]() as db:
        u = wu.WebUser(
            coin_user_id="u-x",
            trang_thai=wu.DA_DUYET,
            vai=wu.VAI_NHAN_VIEN,
            tao_luc=wu.now_utc(),
        )
        db.add(u)
        db.commit()
        dem = utc(2026, 11, 25, 16, 59)
        for phut in range(5):
            db.add(
                wu.WebAudit(
                    luc=dem.replace(second=phut),
                    user_id=u.id,
                    viec=w.VIEC,
                    doi_tuong="co_phieu:VRE",
                )
            )
        # một dòng của ngày hôm trước (23:00 giờ VN ngày 24/11) và một dòng việc khác: không tính
        db.add(
            wu.WebAudit(
                luc=utc(2026, 11, 24, 16, 0),
                user_id=u.id,
                viec=w.VIEC,
                doi_tuong="co_phieu:VRE",
            )
        )
        db.add(
            wu.WebAudit(luc=dem, user_id=u.id, viec="duyet", doi_tuong="web_users:1")
        )
        db.commit()
        assert w.used_today(db, u.id, utc(2026, 11, 25, 16, 59, 30)) == 5
        assert w.remaining(db, u.id, utc(2026, 11, 25, 16, 59, 30)) == 0
        assert w.used_today(db, u.id, utc(2026, 11, 25, 17, 0)) == 0
        assert w.remaining(db, u.id, utc(2026, 11, 25, 17, 0)) == 5
        # 08:00 giờ VN ngày 25/11 (01:00 UTC) cùng ngày VN với 23:59: vẫn là 5
        assert w.used_today(db, u.id, utc(2026, 11, 25, 1, 0)) == 5
        # 23:30 giờ VN ngày 24/11 (16:30 UTC): chỉ dòng 23:00 ngày 24, không lẫn 5 dòng của ngày sau
        assert w.used_today(db, u.id, utc(2026, 11, 24, 16, 30)) == 1


def test_ai_loi_thi_khong_tru_luot_va_khong_luu(env, ai, tmp_path):
    an = vao(env, "t-an")
    ai["loi"] = w.AiReportError(
        502, "Chưa sinh được báo cáo: lỗi kết nối. Lượt này không bị tính."
    )
    r = sinh(an)
    assert r.status_code == 502 and "không bị tính" in r.json()["detail"]
    assert (
        dong_bao_cao(env) == []
        and not (tmp_path / "cache" / "ban_ngan" / "VRE.json").exists()
    )
    assert an.get("/api/co-phieu/VRE/bao-cao-ai").json()["con_lai"] == 5


def test_chi_tai_khoan_da_duyet_gui_tu_chinh_trang(env, ai):
    assert sinh(client()).status_code == 401
    cho = vao(env, "t-an", duyet=False)
    assert (
        sinh(cho).status_code == 403
        and cho.get("/api/co-phieu/VRE/bao-cao-ai").status_code == 403
    )
    an = vao(env, "t-an")
    assert (
        sinh(an, headers={}).status_code == 403
    )  # trang lạ không tự bấm hộ được (thiếu Origin)
    assert ai["goi"] == 0 and dong_bao_cao(env) == []


def test_ma_la_bi_tu_choi(env, ai):
    an = vao(env, "t-an")
    assert sinh(an, "ZZZ").status_code == 404
    assert sinh(an, "AB").status_code == 422
    assert ai["goi"] == 0


def test_dang_viet_thi_lan_bam_thu_hai_bi_chan(env, ai):
    an = vao(env, "t-an")
    lock = w._user_lock(an.get("/api/toi").json()["id"])
    assert lock.acquire(blocking=False)
    try:
        r = sinh(an)
    finally:
        lock.release()
    assert r.status_code == 409 and ai["goi"] == 0


def test_tep_hong_thi_coi_nhu_chua_co(env, ai, tmp_path):
    p = tmp_path / "cache" / "ban_ngan" / "VRE.json"
    p.parent.mkdir(parents=True)
    p.write_text("{hỏng", encoding="utf-8")
    assert (
        vao(env, "t-an").get("/api/co-phieu/VRE/bao-cao-ai").json()["bao_cao"] is None
    )


def test_van_ban_va_dem_tu_tinh_tay():
    phan = {
        "ket_luan": "A b.",
        "tong_quan": "C d e.",
        "nhan_dinh": "F.",
        "rui_ro": ["G h.", "I."],
    }
    text = w.to_markdown("VRE", phan)
    assert text == (
        "**A b.**\n\n#### Tổng quan công ty\nC d e.\n\n#### Nhận định về VRE\nF.\n\n"
        "#### Rủi ro cần theo dõi\n- G h.\n- I.\n"
    )
    # đếm từ bỏ dấu đề mục và gạch đầu dòng: thân bài A b C d e F G h I = 9; ba đề mục "Tổng quan công ty" 4,
    # "Nhận định về VRE" 4, "Rủi ro cần theo dõi" 5 = 13; tổng 22
    assert w.word_count(text) == 22


class _FakeOpenAI:
    """Thay openai.OpenAI: ghi lại tham số lời gọi, trả nội dung và lý do kết thúc đặt sẵn."""

    last: ClassVar[dict] = {}
    content = json.dumps(PHAN, ensure_ascii=False)
    finish = "stop"

    def __init__(self, **kwargs):
        _FakeOpenAI.last = {"client": kwargs}
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        _FakeOpenAI.last["call"] = kwargs
        choice = SimpleNamespace(
            finish_reason=_FakeOpenAI.finish,
            message=SimpleNamespace(content=_FakeOpenAI.content),
        )
        usage = SimpleNamespace(prompt_tokens=100, completion_tokens=50)
        return SimpleNamespace(choices=[choice], usage=usage, model="deepseek-v4-flash")


@pytest.fixture
def fake_openai(monkeypatch):
    import openai

    monkeypatch.setattr(openai, "OpenAI", _FakeOpenAI)
    monkeypatch.setattr(settings, "deepseek_api_key", "khoa-thu")
    _FakeOpenAI.content, _FakeOpenAI.finish = (
        json.dumps(PHAN, ensure_ascii=False),
        "stop",
    )
    return _FakeOpenAI


def test_goi_deepseek_dung_mot_lan_voi_goi_du_lieu(fake_openai):
    payload = {"ticker": "VRE", "target_price_vnd": None, "recommendation": "NOT_RATED"}
    out = w.call_model(payload, "deepseek-v4-flash")
    assert out["phan"] == PHAN and out["token_vao"] == 100 and out["token_ra"] == 50
    call = fake_openai.last["call"]
    assert call["max_tokens"] == 2500 and call["response_format"] == {
        "type": "json_object"
    }
    assert (
        fake_openai.last["client"]["max_retries"] == 0
    )  # một lần bấm = đúng một lời gọi
    noi_dung = call["messages"][1]["content"]
    assert (
        json.dumps(payload, ensure_ascii=False) in noi_dung
        and "khoảng 500 từ" in noi_dung
    )
    assert (
        "KHÔNG nêu giá trị hợp lý, giá mục tiêu" in noi_dung and "TRUNG VỊ" in noi_dung
    )


def test_deepseek_tra_loi_hong_thi_bao_loi(fake_openai, monkeypatch):
    fake_openai.finish = "length"
    with pytest.raises(w.AiReportError) as e:
        w.call_model({"ticker": "VRE"}, "m")
    assert e.value.status == 502 and "bị cắt" in e.value.detail
    fake_openai.finish, fake_openai.content = "stop", json.dumps({**PHAN, "rui_ro": []})
    with pytest.raises(w.AiReportError):
        w.call_model({"ticker": "VRE"}, "m")
    fake_openai.content = "không phải JSON"
    with pytest.raises(w.AiReportError):
        w.call_model({"ticker": "VRE"}, "m")
    monkeypatch.setattr(settings, "deepseek_api_key", "")
    with pytest.raises(w.AiReportError) as e:
        w.call_model({"ticker": "VRE"}, "m")
    assert e.value.status == 503


def test_phan_tram_tinh_san_tinh_tay():
    """Tính tay: thị giá 24.250, trung vị CTCK 33.200: 33.200 ÷ 24.250 − 1 = 36,907% → 36,9.
    Giá trị hợp lý 31.852: 31.852 ÷ 24.250 − 1 = 31,348% → 31,3. Chưa công bố (trống) thì không tính.
    """
    p = {
        "current_price_vnd": 24250,
        "target_price_vnd": 31852,
        "consensus_ctck": {"consensus_median_vnd": 33200},
    }
    d = w._derived(p)
    assert (
        d["trung_vi_ctck_so_voi_thi_gia_pct"] == 36.9
        and d["gia_tri_hop_ly_mo_hinh_so_voi_thi_gia_pct"] == 31.3
    )
    d = w._derived({**p, "target_price_vnd": None, "consensus_ctck": {}})
    assert (
        d["gia_tri_hop_ly_mo_hinh_so_voi_thi_gia_pct"] is None
        and d["trung_vi_ctck_so_voi_thi_gia_pct"] is None
    )


def test_goi_du_lieu_that_ap_cong_cong_bo(monkeypatch):
    """DB thật của máy, mạng bị chặn: gói dữ liệu có phần dòng tiền, dấu vân tay ổn định, và kết quả chưa được
    công bố thì AI không thấy giá mục tiêu của mô hình (như bản dài của web cũ)."""
    from valuation.db.models import Ticker
    from valuation.db.session import SessionLocalRead

    def blocked(*a, **k):
        raise OSError("mạng bị chặn trong test")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    db = SessionLocalRead()
    try:
        if db.query(Ticker).filter(Ticker.ticker == "VRE").first() is None:
            pytest.skip("DB của máy không có VRE")
        a = w.build_inputs(db, "VRE")
        b = w.build_inputs(db, "VRE")
        result = web_valuation._bundle(db, "VRE")["result"]
    finally:
        db.close()
    p = a["payload"]
    assert a["fingerprint"] == b["fingerprint"]
    assert p["ticker"] == "VRE" and p["dong_tien_web"]["available"] is True
    assert a["nguon"]["gia_tri_hop_ly"] == pytest.approx(
        result["blended_fair_value_per_share"]
    )
    if not result.get("publication_allowed", True):
        assert (
            p["recommendation"] == "NOT_RATED"
            and p["target_price_vnd"] is None
            and p["upside_pct"] is None
        )
        # gói CTCK của bản dài chép giá trị hợp lý của mô hình: bản ngắn phải bỏ ra khi chưa công bố
        assert (p.get("consensus_ctck") or {}).get("internal_target_vnd") is None
        assert p["tinh_san"]["gia_tri_hop_ly_mo_hinh_so_voi_thi_gia_pct"] is None
    else:
        assert p["target_price_vnd"] == pytest.approx(
            result["blended_fair_value_per_share"]
        )
