"""Nhật ký báo cáo DeepSeek (docs/PLAN_LEARNING_LOOP.md GĐ 1)."""

import json

from valuation.report.ai_journal import backfill, journal_report

RESULT = {
    "ai_generated": True,
    "generated_at": "2026-10-26T01:42:32+00:00",
    "model": "deepseek-flash",
    "input_tokens": 16279,
    "output_tokens": 4150,
    "status": "WARNING",
    "ai_issues": [{"severity": "warning", "metric": "net_income", "period": "2026", "finding": "số dự phóng lẫn thực tế",
                   "action": "tách nhãn"}],
    "consensus_synthesis": {"diem_chung": ["5 CTCK tích cực"], "doi_chieu_noi_bo": "nội bộ thận trọng hơn"},
    "report_sections": {"thesis": "Luận điểm A", "risks": "Rủi ro B"},
}


def test_ghi_mot_lan_md_va_index(tmp_path):
    ctx = {"fv": 83361.7, "price": 75500, "upside": 10.4, "recommendation": "HOLD"}
    p1 = journal_report("mwg", "cbceb7f1d741", RESULT, ctx, root=tmp_path)
    p2 = journal_report("MWG", "cbceb7f1d741", RESULT, ctx, root=tmp_path)  # cùng fingerprint → không ghi lại
    assert p1 == p2 == tmp_path / "2026-10" / "MWG_2026-10-26_cbceb7f1.md"
    md = p1.read_text(encoding="utf-8")
    assert "83,362" in md and "+10.4%" in md and "giả thuyết chưa kiểm chứng" in md
    assert "`net_income` (2026): số dự phóng lẫn thực tế → tách nhãn" in md and "- 5 CTCK tích cực" in md
    rows = (tmp_path / "index.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(rows) == 1 and json.loads(rows[0])["issues"] == [{"severity": "warning", "metric": "net_income"}]


def test_bo_qua_khi_khong_phai_bao_cao_ai(tmp_path):
    assert journal_report("MWG", "x", {**RESULT, "ai_generated": False}, root=tmp_path) is None
    assert not (tmp_path / "index.jsonl").exists()


def test_backfill_tu_cache(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "v8_GAS_abcdef123456.json").write_text(
        json.dumps({"fingerprint": "abcdef123456", "saved_at": "2026-10-20T00:00:00+00:00", "result": RESULT}),
        encoding="utf-8")
    (cache / "hong.json").write_text("{khong phai json", encoding="utf-8")
    out = backfill(cache, root=tmp_path / "j")
    assert [p.name for p in out] == ["GAS_2026-10-26_abcdef12.md"]
