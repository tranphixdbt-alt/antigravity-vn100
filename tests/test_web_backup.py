"""Web hợp nhất, lát 6 (docs/PLAN_WEB_HOP_NHAT.md mục 14): sao lưu tệp dữ liệu người dùng.

Tệp gốc là SQLite tạm dựng bằng đúng schema của ứng dụng, không mở kết nối mạng. Kiểm: bản sao đọc lại đủ
dòng, chạy hai lần trong ngày không thành hai bản, giữ đúng số bản, tệp lạ trong thư mục không bị đụng,
tệp gốc không bị ghi, lỗi thì báo và giữ nguyên bản cũ.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from valuation.config import load_defaults, settings
from valuation.db import web_user as wu
from valuation.services import web_backup, web_users
from valuation.services.web_auth import Identity

NGAY = dt.date(2026, 11, 25)
ROOT = Path(__file__).resolve().parents[1]


def nguoi(ma: str) -> Identity:
    return Identity(coin_user_id=ma, email=f"{ma}@thu.local", username=None, name=None)


@pytest.fixture
def goc(tmp_path, monkeypatch):
    """Tệp dữ liệu người dùng tạm: 2 tài khoản (2 dòng nhật ký), 1 mức giá, chưa có lệnh. Giữ 3 bản."""
    # thư mục có dấu cách và dấu tiếng Việt: địa chỉ mở tệp phải được mã hóa đúng
    path = tmp_path / "dữ liệu" / "web_user.db"
    path.parent.mkdir()
    engine = create_engine(f"sqlite:///{path}")
    wu.init_schema(engine)
    with Session(engine) as db:
        an = web_users.ensure_user(db, nguoi("an"))
        web_users.ensure_user(db, nguoi("binh"))
        db.add(
            wu.WebPriceLevel(
                user_id=an.id, ma="VRE", chieu="tren", muc=20000.0, tao_luc=wu.now_utc()
            )
        )
        db.commit()
    monkeypatch.setattr(settings, "web_user_db_url", f"sqlite:///{path}")
    monkeypatch.setattr(web_backup, "_cfg", lambda: {"dir_name": "sao_luu", "keep": 3})
    return {"path": path, "engine": engine, "thu_muc": path.parent / "sao_luu"}


def dem(path: Path, bang: str) -> int:
    conn = sqlite3.connect(path)
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {bang}").fetchone()[0]
    finally:
        conn.close()


def ten(goc) -> list[str]:
    return sorted(p.name for p in goc["thu_muc"].iterdir())


def test_ban_sao_doc_lai_du_dong(goc):
    truoc = goc["path"].read_bytes()
    kq = web_backup.backup(NGAY)
    assert kq.path == goc["thu_muc"] / "web_user-20261125.db"
    # đếm tay: 2 tài khoản, mỗi tài khoản 1 dòng nhật ký lúc tạo, 1 mức giá, 0 lệnh, 1 dòng phiên bản schema
    assert kq.rows == {
        "web_audit": 2,
        "web_meta": 1,
        "web_orders": 0,
        "web_price_levels": 1,
        "web_users": 2,
    }
    assert kq.removed == []
    assert dem(kq.path, "web_users") == 2
    assert dem(kq.path, "web_price_levels") == 1
    conn = sqlite3.connect(kq.path)
    try:
        assert conn.execute(
            "SELECT ma, chieu, muc FROM web_price_levels"
        ).fetchall() == [("VRE", "tren", 20000.0)]
    finally:
        conn.close()
    # tệp gốc không bị ghi, và không để lại tệp tạm
    assert goc["path"].read_bytes() == truoc
    assert ten(goc) == ["web_user-20261125.db"]


def test_chay_lai_trong_ngay_khong_thanh_hai_ban(goc):
    web_backup.backup(NGAY)
    with Session(goc["engine"]) as db:
        web_users.ensure_user(db, nguoi("chi"))
    kq = web_backup.backup(NGAY)
    assert ten(goc) == ["web_user-20261125.db"]
    assert kq.rows["web_users"] == 3  # bản của hôm nay là trạng thái lúc chạy sau cùng


def test_giu_dung_so_ban_va_khong_dung_tep_la(goc):
    goc["thu_muc"].mkdir()
    (goc["thu_muc"] / "ghi_chu.txt").write_text(
        "không phải bản sao lưu", encoding="utf-8"
    )
    (goc["thu_muc"] / "web_user-thu.db").write_text(
        "tên không đúng mẫu", encoding="utf-8"
    )
    xoa = []
    for ngay in range(21, 26):  # 5 ngày liên tiếp, giữ 3
        xoa += web_backup.backup(dt.date(2026, 11, ngay)).removed
    assert ten(goc) == [
        "ghi_chu.txt",
        "web_user-20261123.db",
        "web_user-20261124.db",
        "web_user-20261125.db",
        "web_user-thu.db",
    ]
    assert xoa == ["web_user-20261121.db", "web_user-20261122.db"]


def test_ban_chep_hong_thi_bao_loi_va_giu_ban_cu(goc, monkeypatch):
    web_backup.backup(NGAY)
    cu = (goc["thu_muc"] / "web_user-20261125.db").read_bytes()
    monkeypatch.setattr(web_backup, "_verify", lambda conn: "row 3 missing from index")
    with pytest.raises(web_backup.BackupError, match="row 3 missing from index"):
        web_backup.backup(NGAY)
    assert ten(goc) == ["web_user-20261125.db"]
    assert (goc["thu_muc"] / "web_user-20261125.db").read_bytes() == cu


def test_thieu_tep_goc_hoac_khong_phai_sqlite_thi_bao_loi(goc, monkeypatch):
    monkeypatch.setattr(
        settings, "web_user_db_url", f"sqlite:///{goc['path'].parent / 'khong_co.db'}"
    )
    with pytest.raises(web_backup.BackupError, match="Chưa có tệp dữ liệu người dùng"):
        web_backup.backup(NGAY)
    assert not goc["thu_muc"].exists()  # không tạo gì khi chưa có tệp gốc
    monkeypatch.setattr(settings, "web_user_db_url", "postgresql://may-khac/web")
    with pytest.raises(web_backup.BackupError, match="không phải tệp SQLite"):
        web_backup.backup(NGAY)
    monkeypatch.setattr(settings, "web_user_db_url", "sqlite://")
    with pytest.raises(web_backup.BackupError, match="không phải tệp SQLite"):
        web_backup.backup(NGAY)


def test_so_ban_giu_lai_phai_tu_mot(goc, monkeypatch):
    monkeypatch.setattr(web_backup, "_cfg", lambda: {"dir_name": "sao_luu", "keep": 0})
    with pytest.raises(web_backup.BackupError, match="keep"):
        web_backup.backup(NGAY)
    assert not goc["thu_muc"].exists()


def test_cau_hinh_mac_dinh():
    cfg = load_defaults()["web"]["backup"]
    assert cfg["keep"] >= 7
    assert cfg["dir_name"] and "/" not in cfg["dir_name"]


def test_script_in_so_dong_va_tra_ma_loi(goc, monkeypatch, capsys):
    spec = importlib.util.spec_from_file_location(
        "backup_web_user_db", ROOT / "scripts" / "backup_web_user_db.py"
    )
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    assert script.main() == 0
    ra = capsys.readouterr().out
    assert "web_users 2" in ra and "web_price_levels 1" in ra
    assert "thu.local" not in ra  # chỉ in số dòng, không in dữ liệu của ai
    monkeypatch.setattr(settings, "web_user_db_url", "sqlite:////khong/co/web_user.db")
    assert script.main() == 1
    assert "LỖI" in capsys.readouterr().out
