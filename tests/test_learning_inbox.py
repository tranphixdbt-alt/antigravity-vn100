"""Hộp thư vòng học: chỉ lưu đúng file, giữ bản cũ (docs/PLAN_LEARNING_LOOP.md)."""

from valuation.services.learning_inbox import MAX_BYTES, save_learning_attachment


def test_luu_de_xuat_va_giu_ban_cu(tmp_path):
    p = save_learning_attachment("2026-W44.md", "# Đề xuất 1".encode(), root=tmp_path)
    assert p == tmp_path / "proposals" / "2026-W44.md" and p.read_text(encoding="utf-8") == "# Đề xuất 1"
    save_learning_attachment("2026-W44.md", b"# ban 2", root=tmp_path)  # chạy lại cùng tuần → ghi đè, giữ bản cũ
    assert p.read_text(encoding="utf-8") == "# ban 2"
    assert [f.read_text(encoding="utf-8") for f in (tmp_path / "proposals").glob("*.prev.md")] == ["# Đề xuất 1"]


def test_learnings_co_lich_su(tmp_path):
    save_learning_attachment("LEARNINGS.md", b"v1", root=tmp_path)
    save_learning_attachment("LEARNINGS.md", b"v2", root=tmp_path)
    assert (tmp_path / "LEARNINGS.md").read_text() == "v2"
    assert [f.read_text() for f in (tmp_path / "learnings_history").iterdir()] == ["v1"]


def test_tu_choi_ten_la_nhi_phan_qua_lon(tmp_path):
    for name, data in [("../../streamlit_app.py", b"x"), ("note.md", b"x"), ("2026-W44.md", b"\xff\xfe\x00"),
                       ("2026-W44.md", b"a" * (MAX_BYTES + 1))]:
        assert save_learning_attachment(name, data, root=tmp_path) is None
    assert not any(tmp_path.rglob("*"))
