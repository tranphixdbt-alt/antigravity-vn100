"""Định giá, báo cáo tài chính, công ty chứng khoán, cổ tức và báo cáo AI đã lưu của một mã.

Lát 2 của web hợp nhất btinvest.vn (docs/PLAN_WEB_HOP_NHAT.md mục 12). Chỉ đọc: gọi lại đúng đường tab định
giá đang dùng (`build_company_data` chế độ TTM, không lấy giá mạng → `valuate`) và các hàm dựng báo cáo ở
`report/report_data.py`; không tính lại, không đổi công thức. Không sinh báo cáo AI mới (tốn tiền DeepSeek):
chỉ đọc bản đã lưu.
"""

from __future__ import annotations

import datetime as dt
import json
from typing import Any

from valuation.config import load_defaults
from valuation.data_access.corporate_actions import load_corporate_actions
from valuation.data_access.repo import build_company_data
from valuation.db.models import ConsensusSynthesis
from valuation.engine.flag_descriptions import describe_flags
from valuation.engine.sensitivity import calculate_sensitivity_matrix
from valuation.engine.valuate import valuate
from valuation.models.financials_bank import CompanyBank
from valuation.report import report_data
from valuation.report import verified_summary as vs
from valuation.services.web_flow import _cached, clean, ticker_list

_MODE = "TTM"  # mặc định của app (`current_mode`); web chưa có nút đổi sang FY
# Lỗi tính toán có thể gặp khi một phương pháp không áp dụng cho mã đang xem (ngân hàng, bảo hiểm, thiếu số).
# Bắt đúng các loại này để báo "không áp dụng" kèm lý do; lỗi khác vẫn nổi lên thành HTTP 500.
_NOT_APPLICABLE = (ValueError, ZeroDivisionError, AttributeError, TypeError, KeyError)
_ACTION_FIELDS = (
    "event_type",
    "title",
    "announcement_date",
    "ex_right_date",
    "record_date",
    "payment_date",
    "listing_date",
    "cash_amount_vnd_per_share",
    "exercise_ratio",
    "issue_price_vnd",
    "source_url",
)


def known(db: Any, ma: str) -> bool:
    """Mã có trong bảng `tickers` (whitelist trước khi gọi bộ máy, AGENTS.md mục 5)."""
    return any(r["ma"] == ma for r in ticker_list(db))


def _sensitivity(company: Any) -> dict:
    """Bảng độ nhạy y như tab định giá (`views/results.py`): trục X là WACC, với ngân hàng là COE."""
    a = company.assumptions
    try:
        if isinstance(company, CompanyBank):
            base_x = a.cost_of_equity or (a.risk_free_rate + a.beta * a.erp)
            x_label = "Chi phí vốn cổ phần (COE)"
        else:
            from valuation.engine.models.dcf import DCFValuationModel

            base_x = DCFValuationModel.from_pydantic(company).wacc
            x_label = "WACC"
        base_y = a.terminal_growth_rate
        x, y, matrix = calculate_sensitivity_matrix(company, base_x, base_y)
    except _NOT_APPLICABLE as exc:
        return {"ap_dung": False, "ly_do": f"{type(exc).__name__}: {exc}"}
    return {
        "ap_dung": True,
        "nhan_x": x_label,
        "nhan_y": "Tăng trưởng vĩnh viễn g",
        "x": x,
        "y": y,
        "bang": matrix,
        "goc_x": base_x,
        "goc_y": base_y,
    }


def _try(build: Any, *args: Any, **kwargs: Any) -> Any:
    """Gọi một hàm dựng bảng; phương pháp không áp dụng thì trả lý do thay vì làm hỏng cả trang."""
    try:
        return build(*args, **kwargs)
    except _NOT_APPLICABLE as exc:
        return {"ap_dung": False, "ly_do": f"{type(exc).__name__}: {exc}"}


def _bundle(db: Any, ma: str) -> dict:
    """Một lần nạp + định giá cho mỗi mã, giữ trong bộ nhớ đệm (ngân hàng nạp khoảng 11 giây)."""

    def make() -> dict:
        company = build_company_data(db, ma, mode=_MODE, fetch_live=False)
        result = valuate(company)
        fv = result.get("blended_fair_value_per_share")
        return {
            "company": company,
            "result": result,
            "lich_su": _try(report_data.build_historical_analysis, company),
            "phu_luc": _try(report_data.build_appendix_financials, company),
            "gia_dinh": _try(report_data.build_assumptions_table, company),
            "wacc": _try(report_data.build_wacc_breakdown, company),
            "kich_ban": _try(report_data.build_scenarios, company),
            "do_nhay": _sensitivity(company),
            "ctck": (
                _try(
                    report_data.build_consensus_comparison,
                    company.ticker,
                    float(fv),
                    db,
                    current_price=company.current_price,
                )
                if fv
                else None
            ),
        }

    return _cached(f"valuation:{ma}", make)


def valuation(db: Any, ma: str) -> dict:
    """Kết quả định giá, cờ cảnh báo, giả định, WACC, kịch bản, độ nhạy và dự phóng 5 năm."""
    b = _bundle(db, ma)
    company, r = b["company"], b["result"]
    return clean(
        {
            "ma": ma,
            "ten": getattr(company, "name", None),
            "che_do": _MODE,
            "gia": company.current_price,
            "fv": r.get("blended_fair_value_per_share"),
            "fv_noi_tai": r.get("intrinsic_fv"),
            "fv_tuong_doi": r.get("relative_fv"),
            "trong_so_noi_tai": r.get("weight_intrinsic"),
            "upside": r.get("upside"),
            "khuyen_nghi": r.get("recommendation"),
            "chua_xep_hang": r.get("not_rated"),
            "duoc_cong_bo": r.get("publication_allowed"),
            "phuong_phap": r.get("method"),
            "phuong_phap_chu": r.get("method_label"),
            "fv_mo_hinh_rieng": r.get("own_model_fv"),
            "quyet_dinh": r.get("decision"),
            "co": describe_flags(list(r.get("flags") or [])),
            "bao_cao_ctck": (r.get("broker_synth") or {}).get("reports"),
            "gia_dinh": b["gia_dinh"],
            "wacc": b["wacc"],
            "kich_ban": b["kich_ban"],
            "do_nhay": b["do_nhay"],
            "du_phong": r.get("projections"),
        }
    )


def financials(db: Any, ma: str) -> dict:
    """Bảng lịch sử (chỉ tiêu chính) và phụ lục báo cáo tài chính, đơn vị tỷ đồng như báo cáo cũ."""
    b = _bundle(db, ma)
    return clean(
        {
            "ma": ma,
            "don_vi": "tỷ đồng",
            "lich_su": b["lich_su"],
            "phu_luc": b["phu_luc"],
        }
    )


def consensus(db: Any, ma: str) -> dict:
    """So sánh với giá mục tiêu công ty chứng khoán và bản AI tổng hợp luận điểm đã lưu trong DB."""
    b = _bundle(db, ma)
    row = db.query(ConsensusSynthesis).filter(ConsensusSynthesis.ticker == ma).first()
    synthesis = (
        {c.name: getattr(row, c.name) for c in ConsensusSynthesis.__table__.columns}
        if row is not None
        else None
    )
    return clean({"ma": ma, "so_sanh": b["ctck"], "tong_hop": synthesis})


def dividends(db: Any, ma: str) -> dict:
    """Sự kiện cổ tức, tăng vốn, quyền mua đã công bố (cùng cửa sổ thời gian với tab cũ)."""
    cfg = load_defaults().get("corporate_actions") or {}
    rows = load_corporate_actions(
        db,
        ma,
        history_years=int(cfg.get("history_years", 5)),
        future_days=int(cfg.get("future_days", 365)),
    )
    events = [{f: getattr(r, f, None) for f in _ACTION_FIELDS} for r in rows]
    events.sort(
        key=lambda e: str(
            e["ex_right_date"] or e["record_date"] or e["announcement_date"] or ""
        ),
        reverse=True,
    )
    return clean({"ma": ma, "su_kien": events})


def ai_report(ma: str) -> dict:
    """Báo cáo AI gần nhất đã lưu cho mã này (không gọi DeepSeek).

    Bộ nhớ đệm của app khóa theo dấu vân tay toàn bộ đầu vào; ở đây lấy bản mới nhất của đúng phiên bản
    schema hiện hành, nên phải nói rõ ngày sinh để người xem biết nó có thể cũ hơn số liệu đang hiện.
    """
    safe = "".join(ch for ch in ma.upper() if ch.isalnum())
    files = sorted(
        vs._REPORT_CACHE_DIR.glob(f"{vs._CACHE_VERSION}_{safe}_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for path in files:
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue  # tệp đệm hỏng: thử bản cũ hơn, giống cách load_verified_summary_cache bỏ qua
        result = saved.get("result")
        if not isinstance(result, dict) or not result.get("ai_generated"):
            continue
        made = result.get("generated_at") or saved.get("saved_at")
        return clean(
            {
                "ma": ma,
                "co": True,
                "van_ban": vs.report_markdown(result),
                "tao_luc": made
                or dt.datetime.fromtimestamp(
                    path.stat().st_mtime, tz=dt.timezone.utc
                ).isoformat(timespec="seconds"),
                "mo_hinh": result.get("model"),
                "trang_thai": result.get("status"),
            }
        )
    return {
        "ma": ma,
        "co": False,
        "van_ban": None,
        "tao_luc": None,
        "mo_hinh": None,
        "trang_thai": None,
    }
