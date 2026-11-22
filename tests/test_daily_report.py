from datetime import date

from valuation.services.daily_report import (
    build_message,
    changes,
    previous_report,
    session_moves,
)
from valuation.services.ranking_store import write_json

CFG = {
    "top_n": 5,
    "price_move_pct": 5,
    "snapshot_stale_days": 14,
    "price_stale_days": 4,
    "max_lines": 10,
}


def _state(
    picks, notes, moves, price_date="2026-10-19", completed="2026-10-13T09:50:00+07:00"
):
    return {
        "date": "2026-10-20",
        "price_date": price_date,
        "snapshot": {"run_id": "R1", "completed_at": completed},
        "max_per_sector": 2,
        "picks": [
            {
                "ticker": t,
                "price": 100.0,
                "fair_value": 150.0,
                "upside": 50.0,
                "sector": "X",
            }
            for t in picks
        ],
        "notes": notes,
        "moves": moves,
        "macro_lines": [],
    }


def test_session_moves_hand_calculated():
    d1, d2, d0 = date(2026, 10, 16), date(2026, 10, 19), date(2026, 10, 15)
    rows = [
        ("AAA", d2, 105.0),
        ("AAA", d1, 100.0),  # +5,00% (thứ tự lộn xộn vẫn đúng)
        ("BBB", d1, 50.0),
        ("BBB", d2, 46.5),  # 46,5/50 − 1 = −7,00%
        ("CCC", d0, 10.0),
        ("CCC", d1, 11.0),  # không giao dịch phiên 19/10 → bỏ
        ("DDD", d2, 20.0),  # chỉ 1 phiên → bỏ
    ]
    assert session_moves(rows, d2) == {"AAA": 5.0, "BBB": -7.0}


def test_changes_entered_left_notes_movers():
    prev = _state(
        ["A", "B", "C"], {"A": "", "B": "", "C": ""}, {}, price_date="2026-10-16"
    )
    cur = _state(
        ["B", "C", "D"],
        {"A": "", "B": "", "C": "Lỗi dữ liệu: NOT_RATED"},
        {"A": 6.2, "B": -5.0, "C": 4.99},
    )
    chg = changes(prev, cur, 5)
    assert chg["entered"] == ["D"] and chg["left"] == ["A"]
    assert chg["notes"] == [("C", "", "Lỗi dữ liệu: NOT_RATED")]
    assert chg["movers"] == [("A", 6.2), ("B", -5.0)]  # |−5,0| ≥ 5 tính; 4,99 không


def test_changes_no_new_session_hides_movers_and_first_report():
    prev = _state(["A"], {"A": ""}, {"A": 9.0})
    cur = _state(["A"], {"A": ""}, {"A": 9.0})
    chg = changes(prev, cur, 5)
    assert chg["new_session"] is False and chg["movers"] == []
    assert changes(None, cur, 5) is None


def test_build_message_format_and_stale_warnings():
    state = _state(["FPT"], {"FPT": ""}, {}, completed="2026-09-29T09:00:00+07:00")
    state["picks"] = [
        {
            "ticker": "FPT",
            "price": 57100.0,
            "fair_value": 87848.0,
            "upside": 53.85,
            "sector": "Công nghệ",
        }
    ]
    msg = build_message(
        state,
        None,
        {
            "skipped": None,
            "price_errors": ["XYZ: FAILED"],
            "macro_errors": [],
            "price_total": 102,
        },
        CFG,
        date(2026, 10, 20),
    )
    picks, diff, ca, _ = (f["value"] for f in msg["fields"])
    assert picks == "**FPT** 57.100 → FV 87.848 (+53,9%) · Công nghệ"
    assert ca.startswith("Không có mã nào")
    assert diff == "Chưa có báo cáo trước để so sánh."
    assert "21 ngày trước" in msg["embed_desc"]  # 29/09 → 20/10 > 14 ngày
    assert "1/102 mã không cập nhật được giá: XYZ" in msg["embed_desc"]
    assert "R1" in msg["footer"]


def test_build_message_marks_rescaled_fair_value_d99():
    # TCB: FV đợt 27/10 41.121 (thang giá trước thưởng 50%) × 0,6666 = 27.410; giá 20.600 → +33,1%.
    state = _state(["TCB"], {"TCB": ""}, {})
    state["picks"] = [
        {
            "ticker": "TCB",
            "price": 20600.0,
            "fair_value": 27409.99,
            "upside": 33.06,
            "sector": "Ngân hàng",
            "fv_scale": 0.6666,
        },
        # Báo cáo cũ (trước D99) không có khóa fv_scale → không ghi chú.
        {"ticker": "FPT", "price": 45700.0, "fair_value": 90960.0, "upside": 99.04, "sector": "Công nghệ"},
    ]
    msg = build_message(state, None, None, CFG, date(2026, 10, 20))
    picks = msg["fields"][0]["value"].split("\n")
    assert picks[0] == (
        "**TCB** 20.600 → FV 27.410 (+33,1%) · Ngân hàng · FV quy đổi ×0,667 do cổ tức/chia tách"
    )
    assert picks[1] == "**FPT** 45.700 → FV 90.960 (+99,0%) · Công nghệ"


def test_previous_report_skips_today(tmp_path):
    for day in ("2026-10-16", "2026-10-19", "2026-10-20"):
        write_json(tmp_path / "history" / f"{day}.json", {"date": day})
    assert previous_report(date(2026, 10, 20), tmp_path) == {"date": "2026-10-19"}
    assert previous_report(date(2026, 10, 16), tmp_path) is None


def test_build_message_lists_upcoming_corporate_actions_and_errors():
    state = _state(["FPT"], {"FPT": ""}, {}, completed="2026-10-27T09:00:00+07:00")
    state["picks"] = []
    state["upcoming_ca"] = [
        {"ticker": "TCB", "date": "2026-10-29", "role": "Ngày GDKHQ", "title": "Cổ tức bằng cổ phiếu 50%"}
    ]
    info = {"skipped": None, "price_errors": [], "macro_errors": [], "price_total": 101,
            "corporate_actions": {"checked": 100, "inserted": 1, "updated": 3, "errors": ["GAS: timeout"]}}
    msg = build_message(state, None, info, CFG, date(2026, 10, 28))
    ca = msg["fields"][2]["value"]
    assert ca == "**TCB** 29/10/2026 · Ngày GDKHQ: Cổ tức bằng cổ phiếu 50%"
    assert "1/100 mã chưa kiểm tra được cổ tức/quyền mua: GAS" in msg["embed_desc"]


def test_refresh_all_corporate_actions_retry_and_pause(monkeypatch):
    import valuation.ingest.corporate_actions as ca_mod
    from valuation.services import daily_report as dr

    calls = []

    def fake_refresh(db, ticker, force=False):
        # Như hàm thật: không force mà mã vừa kiểm tra (OK < 24h, lỗi < 30 phút) → FRESH, không gọi VCI.
        if ticker == "SEEN" or (not force and ticker in calls):
            return {"status": "FRESH", "checked": False, "inserted": 0, "updated": 0}
        calls.append(ticker)
        if ticker == "BAD":
            return {"status": "ERROR", "error": "HTTPSConnectionPool"}
        if ticker == "FLAKY" and calls.count("FLAKY") == 1:
            return {"status": "ERROR", "error": "timeout"}
        return {"status": "OK", "inserted": 1, "updated": 0}

    monkeypatch.setattr(ca_mod, "refresh_corporate_actions", fake_refresh)
    sleeps = []
    out = dr.refresh_all_corporate_actions(["AAA", "SEEN", "FLAKY", "BAD"], 1.0, sleep=sleeps.append)
    # FLAKY lỗi lần đầu → thử lại (force) thành công; BAD lỗi cả 2 lần → liệt kê, không dừng;
    # SEEN đã kiểm tra trong 24h (FRESH) → không phải lỗi.
    assert calls == ["AAA", "FLAKY", "FLAKY", "BAD", "BAD"]
    assert out == {"checked": 4, "inserted": 2, "updated": 0, "errors": ["BAD: HTTPSConnectionPool"]}
    assert sleeps == [1.0, 1.0, 5.0, 1.0, 5.0]  # nghỉ giữa các mã, 5× khi thử lại, không nghỉ sau mã cuối


def _fake_refresh(monkeypatch, tmp_path, skipped):
    """refresh_market với DB/nguồn giả; trả (info, các lời gọi run_ingest)."""
    import valuation.db.session as session_mod
    import valuation.ingest.fhsc_bridge as fhsc_mod
    import valuation.ingest.fred_fetcher as fred_mod
    import valuation.ingest.macro_fetcher as macro_mod
    import valuation.ingest.pipeline as pipeline_mod
    import valuation.services.daily_report as dr

    class _Q:
        def filter(self, *_):
            return self

        def order_by(self, *_):
            return iter([("AAA",)])

    class _S:
        def query(self, *_):
            return _Q()

        def close(self):
            pass

    calls, kinds = [], []
    monkeypatch.setattr(dr, "DATA_LOCK", tmp_path / "worker.lock")
    monkeypatch.setattr(dr, "_cfg", lambda: {"corporate_actions_refresh": False})
    monkeypatch.setattr(session_mod, "SessionLocalRead", _S)
    monkeypatch.setattr(session_mod, "SessionLocalWrite", _S)
    monkeypatch.setattr(fred_mod, "fetch_fred", lambda db: None)
    monkeypatch.setattr(macro_mod, "fetch_market_macro", lambda db: None)
    monkeypatch.setattr(
        pipeline_mod, "_incremental_price_start", lambda t: "2026-11-11"
    )
    monkeypatch.setattr(
        fhsc_mod,
        "prefetch",
        lambda starts, k: kinds.extend(k)
        or {"ok": 1, "errors": {}, "skipped": skipped},
    )

    def fake_ingest(t, types, include_yearly, include_market_flows):
        calls.append((t, include_market_flows))
        out = {"prices": {"status": "UPDATED", "source": "fhsc"}}
        if include_market_flows:
            out["market_flows"] = {"status": "UPDATED", "foreign_rows": 5}
        return out

    monkeypatch.setattr(pipeline_mod, "run_ingest", fake_ingest)
    return dr.refresh_market(), calls, kinds


def test_refresh_market_pulls_fhsc_flows_except_index(monkeypatch, tmp_path):
    info, calls, kinds = _fake_refresh(monkeypatch, tmp_path, skipped=None)
    assert kinds == ["prices", "foreign", "prop"]
    assert calls == [("AAA", True), ("VNINDEX", False)]  # chỉ số không có khối ngoại
    assert info["flow_updated"] == 1 and info["price_errors"] == []


def test_refresh_market_skips_flows_outside_fhsc_hours(monkeypatch, tmp_path):
    # ngoài giờ FHSC: không gọi nguồn dự phòng vnstock_data (đã khóa) cho dòng tiền
    info, calls, _ = _fake_refresh(
        monkeypatch, tmp_path, skipped="ngoài giờ phục vụ FHSC"
    )
    assert calls == [("AAA", False), ("VNINDEX", False)]
    assert "flow_updated" not in info
