"""Tổng quan thị trường, chỉ số vĩ mô, xếp hạng VN100 và lịch quyền cho web hợp nhất btinvest.vn.

Lát 3 (docs/PLAN_WEB_HOP_NHAT.md mục 12). Chỉ đọc: lắp ráp y như `views.market_overview.render_market_overview`,
`views.macro_panel.render_macro_panel` và `views.vn100_ranking.render_vn100_ranking`, rồi đổi sang JSON.
Không gọi mạng, không AI: bản tin vĩ mô chỉ đọc bản đã lưu (`get_macro_bulletin_cached(force=False)`); job
`ban-tin-vi-mo` (scripts/refresh_macro_bulletin.py, D122) viết lại mỗi sáng ngày giao dịch.
"""

from __future__ import annotations

import datetime as dt
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from valuation.analysis.investment_ranking import load_ranking_config
from valuation.config import get_macro_series_registry, load_defaults
from valuation.data_access import macro_news as mn
from valuation.data_access.corporate_actions import (
    load_upcoming_vn100_corporate_actions,
)
from valuation.services.ranking_store import latest_snapshot
from valuation.services.web_flow import _cached, clean, data_version
from valuation.views import macro_panel as mp
from valuation.views import market_overview as mo
from valuation.views import vn100_ranking as vr

_VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def headline(label: str, pillars: list) -> str:
    """Câu một dòng dưới chỉ số, rút gọn từ `mo.headline` (người dùng 26/11/2026: bớt chữ, nhìn là hiểu).

    "**Khó khăn**: vĩ mô, xu hướng, khối ngoại xấu; định giá tốt". Trụ cột trung tính không nêu.
    """
    bad = [mo._SHORT.get(p.name, p.name) for p in pillars if p.score == -1]
    good = [mo._SHORT.get(p.name, p.name) for p in pillars if p.score == 1]
    parts = [f"{', '.join(bad)} xấu"] * bool(bad) + [f"{', '.join(good)} tốt"] * bool(
        good
    )
    head = f"**{label[:1].upper()}{label[1:].lower()}**"
    return head + (": " + "; ".join(parts) if parts else "")


def _today() -> dt.date:
    return dt.datetime.now(_VN_TZ).date()


def _frequencies() -> dict[str, str]:
    return {
        k: v.get("frequency", "DAILY") for k, v in get_macro_series_registry().items()
    }


def market(db: Any) -> dict:
    """Đèn tổng, bốn trụ cột, VN-Index, kịch bản sắp tới, ngành và mã nổi bật, nhãn tin."""

    def make() -> dict:
        defaults = load_defaults()
        cfg, mcfg = defaults["market_overview"], defaults.get("macro_dashboard") or {}
        vni, closes, flows, universe = mo.load_market_data(db, cfg)
        ups, src = mo.model_upsides(closes)
        pillars = [
            mo.macro_pillar(mp.build_snapshot(db, mcfg, _frequencies()), mcfg, cfg),
            mo.trend_pillar(vni, closes, cfg),
            mo.foreign_pillar(flows, universe, cfg),
            mo.valuation_pillar(ups, src, cfg),
        ]
        label = mo.overall(pillars, cfg)[0]
        tk, sec = mo.leaders(closes, flows, mo.sector_map(), cfg)
        view = mo.index_view(vni, cfg)
        dates = [d for d in (vni.index.max(), closes.index.max()) if pd.notna(d)]
        oldest = min(dates).date() if dates else None
        index = None
        if view:
            index = {
                "diem": view.last,
                "diem_chu": mo._vi(view.last, 2),
                "ngay": view.date,
                "thay_doi": [
                    {"phien": n, "ty_le": c, "chu": mo._chg(c)} for n, c in view.changes
                ],
                "xu_huong": [{"khung": w, "huong": s} for w, s in view.trends],
                "rsi": view.rsi,
                "khang_cu": (
                    None
                    if not view.resistance
                    else {
                        "muc": mo._vi(view.resistance[0]),
                        "nguon": view.resistance[1],
                    }
                ),
                "ho_tro": (
                    None
                    if not view.support
                    else {"muc": mo._vi(view.support[0]), "nguon": view.support[1]}
                ),
                "sap_toi": mo.outlook(view, label, pillars, cfg),
            }
        return {
            "nhan": label,
            "tieu_de": headline(label, pillars),
            "gia_den": oldest,
            "cu": (
                None
                if oldest is None
                else (_today() - oldest).days > int(cfg["stale_days"])
            ),
            "tru_cot": [
                {
                    "ten": p.name,
                    "diem": p.score,
                    "tom_tat": p.summary,
                    "chi_tiet": list(p.details),
                }
                for p in pillars
            ],
            "chi_so": index,
            "so_phien": int(cfg["return_sessions"]),
            "nganh_manh": ([] if sec.empty else sec[sec.state == 1].index[:3].tolist()),
            "nganh_yeu": (
                []
                if sec.empty
                else sec[sec.state == -1].sort_values("rel").index[:3].tolist()
            ),
            "ma_co_luc": (
                []
                if tk.empty
                else tk[tk.support]["Mã"].head(int(cfg["top_n"])).tolist()
            ),
            "bang_nganh": (
                []
                if sec.empty
                else [
                    {"nganh": name, "rel": r.rel, "flow": r.flow, "state": r.state}
                    for name, r in sec.iterrows()
                ]
            ),
            "ma_manh": (
                []
                if tk.empty
                else [
                    {
                        "ma": r["Mã"],
                        "ret": r["ret"],
                        "flow": r["flow"],
                        "co_luc": bool(r["support"]),
                    }
                    for _, r in tk.head(10).iterrows()
                ]
            ),
            "nhan_tin": mn.latest_news_tags(),
        }

    # D128: khóa gắn dấu phiên bản DB → job 15:45, 17:45 vừa ghi thì trang Hôm nay tính lại ngay
    return clean(_cached(f"market:{data_version(db)}", make))


def macro(db: Any) -> dict:
    """Bảng chỉ số vĩ mô (đã định dạng như app cũ), nhận định nhanh và bản tin vĩ mô đã lưu."""
    cfg = load_defaults().get("macro_dashboard") or {}
    snap = mp.build_snapshot(db, cfg, _frequencies())
    today = _today()
    rows: list[dict[str, Any]] = []
    for code, label, kind in mp.PANEL:
        obs = snap.get(code)
        if obs is None:
            rows.append(
                {
                    "ma": code,
                    "ten": label,
                    "gia_tri": None,
                    "thay_doi": None,
                    "ngay": None,
                    "cu": None,
                }
            )
            continue
        value, delta = mp._fmt_value(obs, kind)
        if code == "FED_FUNDS_UPPER" and "FED_FUNDS_LOWER" in snap:
            low = f"{snap['FED_FUNDS_LOWER'].value * 100:.2f}".replace(".", ",")
            value = f"{low}–{value}"
        rows.append(
            {
                "ma": code,
                "ten": label,
                "gia_tri": value,
                "thay_doi": delta,
                "ngay": obs.date,
                "cu": mp.is_stale(obs, cfg, today),
            }
        )
    age = mn.get_macro_cache_age_hours()
    tickers, sectors = mn._allowed_tags()
    text = mn.split_news_tags(
        mn.get_macro_bulletin_cached(force=False), set(tickers) | set(sectors)
    )[0]
    return clean(
        {
            "chi_so": rows,
            "nhan_dinh": mp.quick_takes(snap, cfg, today),
            "ban_tin": text,
            "ban_tin_tuoi_gio": age,
            # giờ viết bản tin (giờ VN) và ngưỡng cũ: quá ngưỡng thì web hiện nút lưu ý (D122, job ban-tin-vi-mo 07:30)
            "ban_tin_luc": (
                None
                if age is None
                else (dt.datetime.now(_VN_TZ) - dt.timedelta(hours=age)).strftime(
                    "%H:%M %d/%m/%Y"
                )
            ),
            "ban_tin_cu_gio": int(cfg["bulletin_stale_hours"]),
        }
    )


def ranking(db: Any) -> dict:
    """Bảng xếp hạng VN100 theo upside của đợt định giá gần nhất và nhóm ứng viên tích sản."""

    def make() -> dict:
        snapshot = latest_snapshot()
        if not snapshot:
            return {"co": False}
        cfg = snapshot.get("config", load_ranking_config())
        table = vr.ranking_table(
            snapshot,
            vr.market_data(db),
            cfg,
            snap_closes=vr.snapshot_closes(db, snapshot),
        )
        done = dt.datetime.fromisoformat(snapshot["completed_at"])
        dates = table["_price_date"].dropna()
        picks = vr.accumulation_picks(table, int(cfg.get("max_per_sector", 2)))
        pick_cols = ["Mã", "Upside (%)", "Giá (đ)", "Giá trị hợp lý (đ)", "Ngành"]
        return {
            "co": True,
            "dot": done.date(),
            "gia_den": max(dates) if len(dates) else None,
            "so_ma": len(table),
            "so_dinh_gia": int(table["Hạng"].notna().sum()),
            "quy_doi": [{"ma": t, "he_so": k} for t, k in vr.scaled_fv(table)],
            "cu": (vr.local_now() - done).days >= cfg["price_max_age_days"],
            "bang": table.drop(columns=vr._HIDDEN).to_dict("records"),
            "tich_san": [] if picks.empty else picks[pick_cols].to_dict("records"),
            "bo_loc": {
                "upside_toi_da": cfg["max_upside_pct"],
                "thanh_khoan_toi_thieu_ty": cfg["scales"]["min_traded_value_vnd"] / 1e9,
                "toi_da_moi_nganh": cfg.get("max_per_sector", 2),
            },
        }

    return clean(_cached("ranking", make))


def upcoming(db: Any) -> dict:
    """Lịch cổ tức và quyền mua VN100 sắp tới (số ngày như tab cũ: `market_upcoming_days`)."""
    days = int((load_defaults().get("corporate_actions") or {})["market_upcoming_days"])
    rows = load_upcoming_vn100_corporate_actions(db, future_days=days)
    return clean(
        {
            "so_ngay": days,
            "su_kien": [
                {
                    "ma": r.action.ticker,
                    "ten": r.company_name,
                    "ngay": r.event_date,
                    "moc": r.date_role,
                    "noi_dung": r.action.title or r.action.event_type,
                    "tien_mat": r.action.cash_amount_vnd_per_share,
                    "ty_le": r.action.exercise_ratio,
                }
                for r in rows
            ],
        }
    )
