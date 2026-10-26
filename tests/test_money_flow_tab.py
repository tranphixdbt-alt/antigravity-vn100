"""T16 — tab "Dòng tiền ngành" (D73, docs/PLAN_SECTOR_FLOW.md §8).

AppTest CHỈ render render_money_flow trên SQLite tạm dựng tay, chặn socket. Fixture 4 mã × 30 phiên
(GTGD = close × 10 triệu cp), số tính tay:
- FPT (Công nghệ): close 9.600, H/L 10.500/9.500 → MFM = (100 − 900)/1.000 = −0,8; ngoại −3 tỷ/phiên
  → R_F = −60 / (20 × 96) = −3,125% → Dấu hiệu xả.
- VCB (Ngân hàng): close 10.400 → MFM +0,8; ngoại +3 tỷ → +2,88% → Dấu hiệu gom.
- BID, CTG (Ngân hàng): close 10.000 → CMF 0; ngoại 0 và +1 tỷ (+1%) → Trung tính.
- Tổng 20 phiên = −60 + 60 + 0 + 20 = +20 tỷ. Ngân hàng: F = 80 tỷ, GTGD = 20 × 304 tỷ → +1,3%.
- Upside FPT = 12.000 / 9.600 − 1 = +25,0%.
"""

from __future__ import annotations

import ast
import datetime as dt
import socket
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from valuation.analysis.investment_ranking import load_ranking_config
from valuation.db.models import Base, PricesDaily, Ticker

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = {"vnstock", "vnstock_data", "vnii", "vnai"}
BN = 1e9
VOL = 1e7
# mã: (giá đóng cửa, ngoại ròng/phiên VND)
FIX = {"FPT": (9_600.0, -3 * BN), "VCB": (10_400.0, 3 * BN), "BID": (10_000.0, 0.0)}
FIX["CTG"] = (10_000.0, 1 * BN)


def _sessions(n: int = 30) -> pd.DatetimeIndex:
    today = dt.datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()
    return pd.bdate_range(end=today - dt.timedelta(days=1), periods=n)


def _make_db(path: Path, *, flow_daily: bool = False) -> str:
    url = f"sqlite:///{path}"
    eng = create_engine(url)
    Base.metadata.create_all(eng)
    db = sessionmaker(bind=eng)()
    for t in FIX:
        db.add(Ticker(ticker=t, is_vn100=True))
    for d in _sessions():
        for t, (close, f) in FIX.items():
            db.add(
                PricesDaily(
                    ticker=t,
                    trade_date=d.date(),
                    open=close,
                    high=10_500.0,
                    low=9_500.0,
                    close=close,
                    volume=int(VOL),
                    foreign_buy_val=max(f, 0.0),
                    foreign_sell_val=max(-f, 0.0),
                    foreign_net_val=f,
                    foreign_buy_vol=max(f, 0.0) / close,
                    foreign_sell_vol=max(-f, 0.0) / close,
                )
            )
    db.commit()
    db.close()
    if flow_daily:
        from valuation.db.flow_models import FlowMetaData
        from valuation.db.flow_models import flow_daily as fd

        FlowMetaData.create_all(eng)
        last = _sessions()[-1]
        with eng.begin() as c:
            c.execute(
                fd.insert().values(
                    ticker="FPT",
                    trade_date=last.date(),
                    source="VCI",
                    matched_val=96 * BN,
                    deal_vol=0.0,
                    deal_val=0.0,
                    fr_net_match_val=-3 * BN,
                    fr_net_deal_val=0.0,
                    fetched_at=dt.datetime.combine(last.date(), dt.time(18, 0)),
                    is_final=True,
                    batch_id="test",
                )
            )
    eng.dispose()
    return url


def _app() -> None:
    import os

    import streamlit as st
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from valuation.views.money_flow import render_money_flow

    db = sessionmaker(bind=create_engine(os.environ["MF_TEST_DB"]))()
    try:
        render_money_flow(db, st.session_state.get("sidebar_ticker"))
    finally:
        db.close()


@pytest.fixture
def run_tab(tmp_path, monkeypatch):
    """Trả hàm dựng AppTest; chặn mạng; snapshot xếp hạng giả (FPT FV 12.000)."""
    import streamlit as st
    from streamlit.testing.v1 import AppTest

    import valuation.views.money_flow as view

    def blocked(*a, **k):
        raise OSError("mạng bị chặn trong test")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    snap = {
        "run_id": "T16",
        "completed_at": "2026-10-20T10:00:00+07:00",
        "config": load_ranking_config(),
        "rows": [{"ticker": "FPT", "fair_value": 12_000.0, "flags": []}],
    }
    monkeypatch.setattr(view, "latest_snapshot", lambda: snap)
    st.cache_data.clear()

    def make(sidebar: str | None = "FPT", **kw) -> AppTest:
        monkeypatch.setenv("MF_TEST_DB", _make_db(tmp_path / "t16.db", **kw))
        at = AppTest.from_function(_app, default_timeout=60)
        at.session_state["sidebar_ticker"] = sidebar
        return at

    return make


def _text(at) -> str:
    parts = [m.value for m in at.markdown] + [c.value for c in at.caption]
    return "\n".join(parts)


def test_t16_status_conclusion_disclaimer_map_and_card(run_tab):
    at = run_tab("FPT")
    before = set(sys.modules)
    at.run()
    assert not at.exception, at.exception
    leaked = {
        m
        for m in set(sys.modules) - before
        if m.split(".")[0] in FORBIDDEN or m.startswith("valuation.ingest")
    }
    assert leaked == set()

    caps = [c.value for c in at.caption]
    status = next(c for c in caps if c.startswith("Giá đến"))
    assert "ngoại 4/4 mã" in status and "Loại thỏa thuận" in status
    assert "0 phiên thủng" in status and "nguồn prices_daily" in status
    assert "cấu hình money_flow #" in status and "(D73)" in status
    md = [m.value for m in at.markdown]
    assert (
        "**20 phiên, loại thỏa thuận: ngoại mua ròng 20,0 tỷ · mua mạnh Ngân hàng · "
        "không ngành nào bán ròng · dấu hiệu: 1 gom, 1 xả**"
    ) in md
    assert any(
        c.startswith("Mô tả dữ liệu quá khứ, không phải khuyến nghị") for c in caps
    )

    sector = at.dataframe[0].value
    bank = sector[sector["Ngành"] == "Ngân hàng"].iloc[0]
    assert bank["Ngoại 20p"] == "▲ +80,0 tỷ · +1,3%"
    assert bank["Gom / xả"] == "1 ▲ · 0 ▼ / 3"
    assert "ít mã" in sector.set_index("Ngành").at["Công nghệ", "Cờ"]

    assert at.selectbox(key="flow_ticker").value == "FPT"
    text = _text(at)
    assert ":red[▼ Dấu hiệu xả] · giá đi ngang (+0,0%)" in text
    assert "Ngoại ▼ −3,1% GTGD, 20/20 phiên bán ròng" in text
    assert "Giá-KL ▼ CMF20 −0,80" in text
    assert "Upside mô hình (phụ): +25,0%" in text

    lst = at.dataframe[-1].value
    assert list(lst["Mã"]) == ["BID", "CTG", "FPT", "VCB"]
    assert lst.set_index("Mã").at["FPT", "Ngoại (tỷ)"] == pytest.approx(-60.0)


def test_t16_select_and_sidebar_sync_and_reject_non_vn100(run_tab):
    at = run_tab("ZZZ")
    at.run()
    assert not at.exception
    assert any("ZZZ không thuộc VN100" in c.value for c in at.caption)
    assert at.selectbox(key="flow_ticker").value == "BID"

    at.selectbox(key="flow_ticker").set_value("VCB").run()
    assert ":green[▲ Dấu hiệu gom]" in _text(at)

    at.session_state["sidebar_ticker"] = "FPT"  # mã sidebar đổi → ô tra mã đổi theo
    at.run()
    assert at.selectbox(key="flow_ticker").value == "FPT"
    assert ":red[▼ Dấu hiệu xả]" in _text(at)

    at.selectbox(key="flow_ticker").set_value(
        "CTG"
    ).run()  # sidebar không đổi → giữ lựa chọn
    assert at.selectbox(key="flow_ticker").value == "CTG"


def test_t16_gom_mode_detail_toggle_and_filters(run_tab):
    at = run_tab("FPT")
    at.run()
    at.radio(key="flow_mode").set_value("Gồm").run()
    assert not at.exception
    status = next(c.value for c in at.caption if c.value.startswith("Giá đến"))
    assert "Gồm thỏa thuận" in status
    sector = at.dataframe[0].value
    assert sector.set_index("Ngành").at["Ngân hàng", "Ngoại 20p"] == "▲ +80,0 tỷ"
    assert "R_F (%)" not in at.dataframe[-1].value.columns

    at.selectbox(key="flow_sector").set_value("Ngân hàng").run()
    assert list(at.dataframe[-1].value["Mã"]) == ["BID", "CTG", "VCB"]
    at.selectbox(key="flow_label").set_value("Dấu hiệu gom").run()
    assert list(at.dataframe[-1].value["Mã"]) == ["VCB"]

    at.toggle(key="flow_detail").set_value(True).run()
    assert not at.exception, at.exception
    text = _text(at)
    assert "Bảng phiếu FPT" in text and "Huy hiệu sự kiện" in text
    assert not any(e.label == "Đọc thế nào?" for e in at.expander)  # hướng dẫn đã chuyển vào dấu (?)
    assert [t.label for t in at.tabs][-3:] == ["Biểu đồ", "Bảng phiếu", "Phiên thỏa thuận"]


def test_t16_flow_daily_source_shown_when_table_exists(run_tab):
    at = run_tab("FPT", flow_daily=True)
    at.run()
    assert not at.exception, at.exception
    status = next(c.value for c in at.caption if c.value.startswith("Giá đến"))
    assert "nguồn flow_daily 1 mã + prices_daily" in status


def test_t16_lessons_and_position_calculator(run_tab):
    at = run_tab("FPT")
    at.run()
    caps = [c.value for c in at.caption]
    assert sum(c.startswith("Ví dụ từ dữ liệu:") for c in caps) == 10
    assert "Ví dụ từ dữ liệu: 50.000.000 × 2% / (50.000 − 45.000) = 200 cp." in caps
    for k, v in {
        "flow_calc_cap": 100_000_000.0,
        "flow_calc_risk": 1.0,
        "flow_calc_entry": 20_000.0,
        "flow_calc_stop": 17_000.0,
    }.items():
        at.number_input(key=k).set_value(v)
    at.run()
    # 100.000.000 × 1% / 3.000 = 333,3 → làm tròn xuống lô 100 = 300 cp
    assert any("**300 cp**" in s.value for s in at.success)
    at.number_input(key="flow_calc_stop").set_value(21_000.0).run()
    assert any("Giá stop phải thấp hơn giá vào" in e.value for e in at.error)


# ---------- test tĩnh ----------
def _imports(path: Path) -> set[str]:
    out: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            out |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module)
    return out


@pytest.mark.parametrize(
    "rel",
    [
        "valuation/views/money_flow.py",
        "valuation/views/money_flow_lessons.py",
        "valuation/analysis/money_flow.py",
    ],
)
def test_money_flow_modules_do_not_import_ingest_or_vnstock(rel):
    bad = {
        m
        for m in _imports(ROOT / rel)
        if m.split(".")[0] in FORBIDDEN or m.startswith("valuation.ingest")
    }
    assert bad == set()


def test_view_import_chain_has_no_network_packages():
    code = (
        # gồm cả module mà render nạp lười (trong hàm): kiểm diff sys.modules ở T16 rỗng nghĩa khi
        # chạy cả suite vì test khác đã nạp sẵn valuation.ingest/vnstock lúc collection
        "import sys, valuation.views.money_flow, valuation.views.vn100_ranking, "
        "valuation.analysis.investment_ranking, valuation.db.flow_models, "
        "valuation.db.session, plotly.subplots; "
        "print(sorted(m for m in sys.modules if m.split('.')[0] in "
        "{'vnstock','vnstock_data','vnii','vnai'} or m.startswith('valuation.ingest')))"
    )
    out = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "[]"


def _tab_lists() -> list[list[str]]:
    tree = ast.parse((ROOT / "streamlit_app.py").read_text(encoding="utf-8"))
    return [
        [e.value for e in node.args[0].elts]
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and getattr(node.func, "attr", None) == "tabs"
        and node.args
        and isinstance(node.args[0], ast.List)
    ]


def test_app_adds_money_flow_tab_last_in_both_branches():
    lists = _tab_lists()
    assert sorted(len(x) for x in lists) == [2, 5]  # D80: Định giá + CTCK gộp một tab
    assert all(x[-1] == "Dòng tiền ngành" for x in lists)


def test_css_hides_valuation_head_on_reference_tabs_and_labels_money():
    css = (ROOT / "valuation/views/assets/workspace.css").read_text(encoding="utf-8")
    # Chỉ số tab lấy từ chính streamlit_app.py → đổi thứ tự/số tab mà quên CSS thì test đỏ.
    full = max(_tab_lists(), key=len)
    idx = [full.index(n) + 1 for n in ("Cổ tức & quyền mua", "VN100 & tích sản", "Dòng tiền ngành")]
    assert ":is(" + ", ".join(f":nth-of-type({i})" for i in idx) + ")" in css
    assert f':nth-of-type({len(full)})::after {{ content: "money"; }}' in css
    assert css.count('content: "money"') == 2  # tab cuối (đủ tab) + tab 2 (nhánh 2 tab)


def test_l5_spearman_hand_calculated():
    from valuation.views.money_flow_lessons import spearman_rf_ret

    def tk(r_f, ret):
        return {"flows": {"20": {"loai": {"r_f": r_f}}}, "ret20": ret}

    res = {"meta": {"window": 20}, "tickers": {}}
    res["tickers"] = {"A": tk(0.01, 0.1), "B": tk(0.02, 0.3), "C": tk(0.03, 0.2)}
    # hạng (1,2,3) vs (1,3,2): ρ = 1 − 6·Σd²/(n(n²−1)) = 1 − 6·2/24 = 0,5
    assert spearman_rf_ret(res) == (pytest.approx(0.5), 3)
    res["tickers"]["D"] = tk(None, 0.4)  # thiếu R_F → bỏ
    assert spearman_rf_ret(res)[1] == 3


# ---------- rà soát A3 ----------
def test_panel_key_changes_on_in_place_updates(tmp_path):
    """UPDATE tại chỗ (ghi đè số ngoại, điền ex_right_date) phải làm đổi khóa cache."""
    from sqlalchemy import update

    import valuation.views.money_flow as view
    from valuation.config import load_defaults
    from valuation.db.models import CorporateAction

    db = sessionmaker(bind=create_engine(_make_db(tmp_path / "k.db")))()
    cfg, now = load_defaults(), view._now_vn()
    db.add(
        CorporateAction(
            ticker="FPT", source_site="VCI", source_event_id="e1", event_type="STOCK_DIVIDEND",
            title="t", announcement_date=_sessions()[-3].date(), content_hash="h",
        )
    )  # fmt: skip
    db.commit()
    keys = [view.panel_key(db, cfg, None, now)]
    last = _sessions()[-1].date()
    db.execute(
        update(PricesDaily)
        .where(PricesDaily.ticker == "FPT", PricesDaily.trade_date == last)
        .values(foreign_net_val=-4 * BN, foreign_sell_val=4 * BN)
    )
    db.commit()
    keys.append(view.panel_key(db, cfg, None, now))
    db.execute(
        update(CorporateAction).values(ex_right_date=last)
    )  # không đổi updated_at
    db.commit()
    keys.append(view.panel_key(db, cfg, None, now))
    db.close()
    assert len(set(keys)) == 3


def test_status_line_names_update_paths():
    from valuation.views.money_flow import status_line

    meta = {
        "price_date": "2026-10-23", "flow_date": "2026-10-22", "flow_coverage": 100,
        "universe": 100, "prop_coverage": 76, "n_sessions": 20, "window_start": "2026-09-24",
        "gap_sessions": 0, "config_hash": "abcd1234", "sources": {"A": 100},
    }  # fmt: skip
    assert "chỉ cập nhật khi bấm «Quét VN100 hàng tuần»" in status_line(meta, "loai")
    meta["sources"] = {"exact": 50, "A": 50}
    s = status_line(meta, "loai")
    assert (
        "flow_daily theo job hằng ngày; prices_daily khi bấm «Quét VN100 hàng tuần»"
        in s
    )


def test_l10_calculator_warns_when_position_exceeds_capital(run_tab):
    at = run_tab("FPT")
    at.run()
    # 100.000.000 × 2% / (50.000 − 49.900) = 20.000 cp → 1 tỷ đồng > vốn 100 triệu
    for k, v in {
        "flow_calc_cap": 100_000_000.0,
        "flow_calc_risk": 2.0,
        "flow_calc_entry": 50_000.0,
        "flow_calc_stop": 49_900.0,
    }.items():
        at.number_input(key=k).set_value(v)
    at.run()
    assert any("**20.000 cp**" in s.value for s in at.success)
    assert any("vượt vốn" in w.value for w in at.warning)


def test_t16_phone_branch_and_rendered_text_clean(run_tab, monkeypatch):
    """Nhánh điện thoại + quét chữ do VIEW render (không chỉ chữ của lõi) tìm nan/None/cụm cấm."""
    import re

    import valuation.views.money_flow as view
    from valuation.config import load_defaults
    from valuation.views import device

    monkeypatch.setattr(view, "is_phone", lambda: True)
    monkeypatch.setattr(device, "is_phone", lambda: True)  # phone_collapsible
    at = run_tab("FPT")
    at.run()
    assert not at.exception, at.exception
    assert any(e.label == "Bản đồ ngành đầy đủ" for e in at.expander)
    at.toggle(key="flow_detail").set_value(True).run()
    assert not at.exception, at.exception
    texts = [m.value for m in at.markdown] + [c.value for c in at.caption]
    texts += [m.proto.help for m in at.markdown if m.proto.help]  # hướng dẫn trong dấu (?)
    for df in at.dataframe:
        v = df.value
        texts += [x for c in v.columns for x in v[c] if isinstance(x, str)]
    assert any("Richards 2005" in s for s in texts)  # hướng dẫn trong dấu (?) có được quét
    forbidden = load_defaults()["money_flow"]["forbidden_phrases"]
    for s in texts:
        if s.startswith("**L4 "):  # bài L4 cố ý nhắc «tiền vào/tiền ra» để giải thích
            continue
        low = s.lower()
        assert not re.search(r"\b(nan|none|nat)\b", low), s
        assert not any(ph in low for ph in forbidden), s


# ---------- D74: biểu đồ dòng tiền, dải 20 phiên, bản đồ nhiệt ----------
def test_spark_heights_colors_and_missing():
    from valuation.views.money_flow import spark

    # |10| = max → █ (bậc 7); |−5| → int(5/10 × 7) = 3 → ▄; None → ·; 0 → ▁ xám
    assert spark([10.0, -5.0, None, 0.0]) == ":green[█]:red[▄]:gray[·]:gray[▁]"
    assert spark([None, None]) == ":gray[·]:gray[·]"


def test_chart_slice_cumulative_skips_missing_days():
    from valuation.views.money_flow import chart_slice

    idx = pd.bdate_range(end="2026-10-22", periods=5)
    h = pd.DataFrame(
        {
            "close": [1.0] * 5,
            "f": [9.0, 1.0, float("nan"), 2.0, -1.0],
            "p": [float("nan")] * 5,
            "f_block": [float("nan"), float("nan"), -5.0, float("nan"), float("nan")],
            "p_block": [float("nan")] * 5,
            "dom": [float("nan")] * 5,
        },
        index=idx,
    )
    v = chart_slice(h, 4)  # bỏ phiên đầu (9) khỏi khung
    assert v["cum_f"].tolist() == [
        1.0,
        1.0,
        3.0,
        2.0,
    ]  # ngày thiếu giữ nguyên, không cộng 0 giả
    assert v["cum_f_gom"].tolist() == [
        1.0,
        -4.0,
        -2.0,
        -3.0,
    ]  # Gồm cộng cả thỏa thuận −5
    assert v["cum_p"].isna().all()  # không có số tự doanh → không vẽ đường 0 giả


def test_flow_chart_layers_macd_optional_no_rsi():
    from valuation.analysis.money_flow import ticker_history
    from valuation.views.money_flow import LAYERS, chart_slice, flow_chart

    sys.path.insert(0, str(Path(__file__).parent))
    import test_money_flow as core

    df, ex = core._mch()
    v = chart_slice(ticker_history(df, ex, None, core.CFG, core.NOW), 63)
    loai = {t.name for t in flow_chart(v, list(LAYERS), "loai", False).data}
    assert {"Thỏa thuận lớn", "Trong nước (suy ra)", "MACD", "KL khớp"} <= loai
    # Loại: phiên thỏa thuận cực lớn không vẽ cột (méo trục), chỉ ◆ trên tầng giá
    assert not {"KL thỏa thuận", "Khối ngoại thỏa thuận"} & loai
    assert not any("RSI" in (n or "") for n in loai)
    gom = {t.name for t in flow_chart(v, ["Khối lượng", "Khối ngoại"], "gom", True).data}
    assert {"KL thỏa thuận", "Khối ngoại thỏa thuận", "Khối ngoại lũy kế"} <= gom
    assert "MACD" not in gom


def test_flow_chart_gom_xa_gop_cmf20_va_co_dau_hoi_giai_thich():
    """Tầng « Ai gom/xả » chứa luôn nền CMF20 (trục trái, 0 trùng 0 của lũy kế); mọi tiêu đề có (?) + giải thích."""
    from valuation.analysis.money_flow import ticker_history
    from valuation.config import load_defaults
    from valuation.views.money_flow import LAYERS, chart_slice, flow_chart

    sys.path.insert(0, str(Path(__file__).parent))
    import test_money_flow as core

    assert "CMF20" not in LAYERS
    assert load_defaults()["money_flow_chart"]["default_range"] == "1N"
    df, ex = core._mch()
    v = chart_slice(ticker_history(df, ex, None, core.CFG, core.NOW), 63)
    fig = flow_chart(v, ["Ai gom/xả"], "loai", False)
    by = {t.name: t for t in fig.data}
    assert by["CMF20 > 0"].yaxis == "y2" and by["Khối ngoại"].yaxis == "y3"  # cùng tầng 2, khác trục
    r2, r3 = fig.layout.yaxis2.range, fig.layout.yaxis3.range
    assert r2[0] == -r2[1] and r3[0] == -r3[1]  # đối xứng quanh 0 → hai đường 0 trùng
    assert len(fig.layout.annotations) == 2
    for a in fig.layout.annotations:
        assert a.text.endswith("(?)") and a.hovertext
    assert "CMF" in fig.layout.annotations[1].hovertext


def test_heatmap_clips_color_keeps_value():
    from valuation.views.money_flow import sector_heatmap

    sd = {"sectors": ["A"], "dates": ["2026-10-22"], "f": [[-30e9]], "r": [[-0.4]]}
    fig = sector_heatmap(sd, {"heat_clip": 0.05}, False)
    assert fig.data[0].z[0][0] == -0.05 and fig.data[0].customdata[0][0] == -30.0


def test_valuation_tab_no_longer_has_technical_chart():
    src = (
        Path(__file__).resolve().parents[1] / "valuation/views/results.py"
    ).read_text()
    assert "render_tradingview_widget" not in src and "Dòng tiền ngành" in src


def test_moi_tieu_de_cot_tab_money_co_dong_giai_thich():
    """Rê chuột vào tiêu đề cột nào trong tab Dòng tiền ngành cũng có giải thích (kể cả cột tên động)."""
    from valuation.views import money_flow as mfv
    from valuation.views import money_flow_lessons as lessons

    cols = [
        "Ngành", "n", "Ngoại 20p", "Độ rộng ngoại", "Tự doanh 20p", "Gom / xả", "Mã chi phối", "RS20", "Cờ",  # bản đồ ngành
        "Mã", "Nhãn", "Phiếu", "Bối cảnh", "Ngoại (tỷ)", "R_F (%)", "Tự doanh (tỷ)", "CMF20",  # danh sách mã
        "ret20 (%)", "Giữ nhãn từ", "Upside (%)", "Huy hiệu",
        "Ngày", "Thỏa thuận", "Dạng",  # phiên thỏa thuận
        "Đo", "Ngưỡng", "Ghi chú", "Cửa sổ", "Phủ TD (%)",  # bảng phiếu / cửa sổ
        "Ngoại mua (cp)", "Ngoại bán (cp)", "TD mua (cp)", "TD bán (cp)", "KL khớp (cp)",  # thỏa thuận
    ]
    assert [c for c in cols if not lessons.column_help(c)] == []
    cfg = mfv._help_cfg(pd.DataFrame(columns=["Mã", "CMF20", "Cột lạ"]), {"Mã": {"pinned": True, "help": None}})
    assert cfg["Mã"]["pinned"] is True and cfg["Mã"]["help"] == lessons.COLUMN_HELP["Mã"]  # giữ cấu hình riêng
    assert cfg["CMF20"]["help"].startswith("Chaikin") and "Cột lạ" not in cfg  # không bịa cho cột chưa biết
