"""Kiểm chứng dữ liệu và sinh nháp báo cáo bằng đúng một DeepSeek API call.

Module này không được gọi khi render trang. Caller duy nhất trong UI là nút
"Kiểm chứng dữ liệu & sinh báo cáo" tại tab BCTC. Kiểm tra số học do Python
thực hiện; DeepSeek không được tự sửa hay ghi dữ liệu vào DB.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import math
import statistics
import threading
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from valuation.config import load_defaults, settings
from valuation.models.financials_bank import CompanyBank


_STATUS_RANK = {"OK": 0, "WARNING": 1, "ERROR": 2}
_REPORT_KEYS = ("thesis", "overview", "industry", "risks", "corporate_actions")
_CONSENSUS_LIST_KEYS = ("diem_chung", "diem_rieng", "diem_mau_chot")
_CACHE_VERSION = "v4"
_REPORT_CACHE_DIR = Path(__file__).resolve().parents[2] / ".deepseek_report_cache"
_REPORT_CACHE_LOCK = threading.Lock()


def verified_summary_session_key(ticker: str) -> str:
    """Khóa cache dùng chung giữa tab BCTC và tab xuất báo cáo."""
    return f"verified_ai_summary_{_CACHE_VERSION}_{ticker.upper()}"


def _config() -> Dict[str, Any]:
    return (load_defaults().get("deepseek_report") or {}).copy()


def _without_volatile_fields(value: Any) -> Any:
    """Bỏ timestamp kiểm tra nguồn, nhưng giữ nguyên dữ liệu dùng để phân tích."""
    if isinstance(value, dict):
        return {
            key: _without_volatile_fields(item)
            for key, item in value.items()
            if key not in {"last_checked_at", "generated_at", "cache_hit"}
        }
    if isinstance(value, list):
        return [_without_volatile_fields(item) for item in value]
    return value


def verified_summary_fingerprint(
    *,
    company: Any,
    blended_fv: float,
    current_price: float,
    upside: float,
    recommendation: str,
    consensus_context: Optional[Dict[str, Any]] = None,
    corporate_actions_context: Optional[Dict[str, Any]] = None,
) -> str:
    """Dấu vân tay thay đổi khi bất kỳ dữ liệu phân tích thực chất nào đổi."""
    deterministic = run_deterministic_checks(
        company, blended_fv=blended_fv, upside=upside
    )
    payload = _compact_payload(
        company,
        blended_fv=blended_fv,
        current_price=current_price,
        upside=upside,
        recommendation=recommendation,
        deterministic_issues=deterministic,
        consensus_context=consensus_context,
        corporate_actions_context=corporate_actions_context,
    )
    canonical = json.dumps(
        _without_volatile_fields(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(f"{_CACHE_VERSION}:{canonical}".encode("utf-8")).hexdigest()


def _report_cache_path(
    ticker: str, fingerprint: str, cache_dir: Optional[Path] = None
) -> Path:
    safe_ticker = "".join(ch for ch in ticker.upper() if ch.isalnum() or ch in "_-")
    return (
        cache_dir or _REPORT_CACHE_DIR
    ) / f"{_CACHE_VERSION}_{safe_ticker}_{fingerprint}.json"


def load_verified_summary_cache(
    ticker: str,
    fingerprint: str,
    *,
    cache_dir: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    path = _report_cache_path(ticker, fingerprint, cache_dir)
    if not path.exists():
        return None
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    result = saved.get("result")
    if saved.get("fingerprint") != fingerprint or not isinstance(result, dict):
        return None
    if not result.get("ai_generated"):
        return None
    return result


def save_verified_summary_cache(
    ticker: str,
    fingerprint: str,
    result: Dict[str, Any],
    *,
    cache_dir: Optional[Path] = None,
) -> None:
    if not result.get("ai_generated"):
        return
    path = _report_cache_path(ticker, fingerprint, cache_dir)
    payload = {
        "fingerprint": fingerprint,
        "saved_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "result": result,
    }
    with _REPORT_CACHE_LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        temporary.replace(path)


def _finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _derived_quality_metrics(company: Any) -> Dict[str, Optional[float]]:
    """Tính quality metrics cơ bản từ BCTC đã chuẩn hóa tỷ đồng.

    Các tỷ số này chỉ dùng cho payload kiểm chứng AI. Nếu mẫu số không hợp lệ,
    trả None để DeepSeek hiểu là thiếu dữ liệu thay vì hiểu nhầm là bằng 0.
    """
    if isinstance(company, CompanyBank):
        raw = company.quality_metrics.model_dump() if company.quality_metrics else {}
        return {key: value for key, value in raw.items() if value is not None}

    statements = list(getattr(company, "historical_is", []) or [])
    balances = list(getattr(company, "historical_bs", []) or [])
    cashflows = list(getattr(company, "historical_cf", []) or [])
    if not statements or not balances:
        return {}

    latest_is = statements[-1]
    latest_bs = balances[-1]
    prev_bs = balances[-2] if len(balances) >= 2 else latest_bs
    latest_cf = next(
        (row for row in reversed(cashflows) if row.year == latest_is.year),
        cashflows[-1] if cashflows else None,
    )

    def _ratio(num: float, den: float) -> Optional[float]:
        if not _finite(num) or not _finite(den) or abs(float(den)) <= 1e-9:
            return None
        return float(num) / float(den)

    avg_equity = (float(prev_bs.total_equity) + float(latest_bs.total_equity)) / 2.0
    total_debt = float(latest_bs.short_term_debt) + float(latest_bs.long_term_debt)
    cash_like = (
        float(latest_bs.cash_and_equivalents)
        + float(getattr(latest_bs, "short_term_financial_investments", 0.0) or 0.0)
    )
    avg_prev_debt = float(prev_bs.short_term_debt) + float(prev_bs.long_term_debt)
    avg_cash_like = (
        float(prev_bs.cash_and_equivalents)
        + float(getattr(prev_bs, "short_term_financial_investments", 0.0) or 0.0)
        + cash_like
    ) / 2.0
    avg_invested_capital = (
        avg_equity + ((avg_prev_debt + total_debt) / 2.0) - avg_cash_like
    )
    if avg_invested_capital <= 0:
        avg_invested_capital = avg_equity + ((avg_prev_debt + total_debt) / 2.0)

    depreciation = float(getattr(latest_cf, "depreciation", 0.0) or 0.0) if latest_cf else 0.0
    ebitda = float(latest_is.ebit) + depreciation
    net_debt = total_debt - cash_like
    nopat = float(latest_is.ebit) * (1.0 - float(company.assumptions.tax_rate))

    return {
        "roe": _ratio(float(latest_is.net_income), avg_equity),
        "roic": _ratio(nopat, avg_invested_capital),
        "debt_to_equity": _ratio(total_debt, float(latest_bs.total_equity)),
        "net_debt_to_ebitda": _ratio(net_debt, ebitda),
    }


def _relative_diff_pct(actual: float, expected: float) -> float:
    return abs(float(actual) - float(expected)) / max(abs(float(actual)), 1.0) * 100.0


def _issue(code: str, severity: str, message: str, period: Optional[int] = None) -> Dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "period": period,
        "message": message,
        "origin": "python",
    }


def _identity_issue(
    issues: List[Dict[str, Any]],
    *,
    code: str,
    label: str,
    actual: float,
    expected: float,
    year: int,
    tolerance_pct: float,
) -> None:
    diff_pct = _relative_diff_pct(actual, expected)
    if diff_pct > tolerance_pct:
        issues.append(
            _issue(
                code,
                "error",
                f"{label} năm {year} lệch {diff_pct:.2f}% "
                f"(ghi nhận {actual:,.1f}; tính lại {expected:,.1f} tỷ đồng).",
                year,
            )
        )


def _growth_issues(
    values: Iterable[tuple[int, float]], label: str, limit_pct: float
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    rows = list(values)
    for (prev_year, prev), (year, current) in zip(rows, rows[1:]):
        if not _finite(prev) or not _finite(current) or abs(prev) < 1.0:
            continue
        growth = (float(current) / float(prev) - 1.0) * 100.0
        if abs(growth) > limit_pct:
            out.append(
                _issue(
                    "ABNORMAL_GROWTH",
                    "warning",
                    f"{label} {year} biến động {growth:+.1f}% so với {prev_year}; "
                    "cần đối chiếu lại kỳ báo cáo, đơn vị và khoản bất thường.",
                    year,
                )
            )
    return out


def run_deterministic_checks(
    company: Any,
    *,
    blended_fv: float,
    upside: float,
) -> List[Dict[str, Any]]:
    """Kiểm tra tái lập được; không gọi mạng và không dùng AI."""
    cfg = _config()
    identity_tolerance = float(cfg.get("identity_tolerance_pct", 0.5))
    growth_limit = float(cfg.get("growth_warning_pct", 100.0))
    upside_limit = float(cfg.get("upside_warning_pct", 100.0))
    issues: List[Dict[str, Any]] = []

    if not _finite(company.current_price) or company.current_price <= 0:
        issues.append(_issue("INVALID_PRICE", "error", "Giá thị trường thiếu hoặc không dương."))
    if not _finite(company.shares_outstanding) or company.shares_outstanding <= 0:
        issues.append(_issue("INVALID_SHARES", "error", "Số cổ phiếu lưu hành thiếu hoặc không dương."))
    if not _finite(blended_fv) or blended_fv <= 0:
        issues.append(_issue("INVALID_FAIR_VALUE", "error", "Giá trị hợp lý thiếu hoặc không dương."))
    if _finite(upside) and abs(float(upside)) > upside_limit:
        issues.append(
            _issue(
                "ABNORMAL_UPSIDE",
                "warning",
                f"Upside {float(upside):+.1f}% vượt ngưỡng phản biện {upside_limit:.0f}%.",
            )
        )

    for flag in list(getattr(company, "data_flags", []) or []):
        issues.append(_issue(str(flag), "warning", f"Cờ chất lượng dữ liệu: {flag}."))
    for warning in list(getattr(company, "warnings", []) or []):
        issues.append(_issue("MODEL_WARNING", "warning", str(warning)))

    statements = list(getattr(company, "historical_is", []) or [])
    balances = list(getattr(company, "historical_bs", []) or [])
    if not statements:
        issues.append(_issue("MISSING_IS", "error", "Không có dữ liệu báo cáo kết quả kinh doanh."))
    if not balances:
        issues.append(_issue("MISSING_BS", "error", "Không có dữ liệu bảng cân đối kế toán."))

    if isinstance(company, CompanyBank):
        for row in statements:
            _identity_issue(
                issues,
                code="BANK_TOI_MISMATCH",
                label="TOI != NII + thu nhập ngoài lãi",
                actual=row.total_operating_income,
                expected=row.net_interest_income + row.non_interest_income,
                year=row.year,
                tolerance_pct=identity_tolerance,
            )
            _identity_issue(
                issues,
                code="BANK_PPOP_MISMATCH",
                label="PPOP != TOI - chi phí hoạt động",
                actual=row.pre_provision_profit,
                expected=row.total_operating_income - row.operating_expenses,
                year=row.year,
                tolerance_pct=identity_tolerance,
            )
            _identity_issue(
                issues,
                code="BANK_PBT_MISMATCH",
                label="LNTT != PPOP - dự phòng",
                actual=row.pretax_income,
                expected=row.pre_provision_profit - row.provision_expense,
                year=row.year,
                tolerance_pct=identity_tolerance,
            )
        growth_values = ((row.year, row.total_operating_income) for row in statements)
        growth_label = "Tổng thu nhập hoạt động"
    else:
        for row in statements:
            _identity_issue(
                issues,
                code="GROSS_PROFIT_MISMATCH",
                label="Lợi nhuận gộp != doanh thu - giá vốn",
                actual=row.gross_profit,
                expected=row.revenue - row.cogs,
                year=row.year,
                tolerance_pct=identity_tolerance,
            )
            _identity_issue(
                issues,
                code="EBIT_MISMATCH",
                label="EBIT != lợi nhuận gộp - OPEX",
                actual=row.ebit,
                expected=row.gross_profit - row.opex,
                year=row.year,
                tolerance_pct=identity_tolerance,
            )
        growth_values = ((row.year, row.revenue) for row in statements)
        growth_label = "Doanh thu"

    for row in balances:
        _identity_issue(
            issues,
            code="BALANCE_SHEET_MISMATCH",
            label="Tổng tài sản != tổng nguồn vốn",
            actual=row.total_assets,
            expected=row.total_liabilities_and_equity,
            year=row.year,
            tolerance_pct=identity_tolerance,
        )

    issues.extend(_growth_issues(growth_values, growth_label, growth_limit))
    return issues


def _compact_payload(
    company: Any,
    *,
    blended_fv: float,
    current_price: float,
    upside: float,
    recommendation: str,
    deterministic_issues: List[Dict[str, Any]],
    consensus_context: Optional[Dict[str, Any]] = None,
    corporate_actions_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    is_bank = isinstance(company, CompanyBank)
    income_rows = [row.model_dump() for row in company.historical_is[-5:]]
    balance_rows = [row.model_dump() for row in company.historical_bs[-5:]]
    assumptions = company.assumptions.model_dump()
    assumptions = {
        key: value
        for key, value in assumptions.items()
        if key not in {"rnav_projects", "sotp_segments", "land_bank_projects"}
    }
    return {
        "ticker": company.ticker,
        "company_name": company.name,
        "sector": company.sector,
        "company_type": "bank" if is_bank else "non_bank",
        "unit_financials": "billion_VND",
        "current_price_vnd": current_price,
        "target_price_vnd": blended_fv,
        "upside_pct": upside,
        "recommendation": recommendation,
        "shares_outstanding_million": company.shares_outstanding,
        "income_statements": income_rows,
        "balance_sheets": balance_rows,
        "assumptions": assumptions,
        "quality_metrics": _derived_quality_metrics(company),
        "python_checks": deterministic_issues,
        "consensus_ctck": consensus_context or {"available": False, "reports": []},
        "corporate_actions": corporate_actions_context
        or {"available": False, "events": []},
    }


def collect_consensus_context(
    *,
    ticker: str,
    blended_fv: float,
    current_price: float,
    db: Any = None,
    fetcher: Any = None,
) -> Dict[str, Any]:
    """Gom ngữ cảnh CTCK cho cùng lượt sinh báo cáo, không gọi LLM.

    Ưu tiên phần tóm tắt công khai của báo cáo. Nếu nguồn web tạm lỗi, dùng
    bảng đồng thuận đã lưu trong DB và trả cảnh báo rõ ràng để UI hiển thị.
    """
    cfg = _config()
    max_reports = int(cfg.get("consensus_max_reports", 8))
    max_chars = int(cfg.get("consensus_summary_max_chars", 1200))
    timeout = float(cfg.get("consensus_fetch_timeout_sec", 12.0))
    window_days = int(cfg.get("consensus_window_days", 180))
    as_of = datetime.date.today()
    window_start = as_of - datetime.timedelta(days=window_days)
    ticker = ticker.upper()
    warnings: List[str] = []
    summaries: List[Dict[str, Any]] = []

    # Đọc cache trước để một lần bấm thường không phải cào lại các trang CTCK.
    if db is not None:
        try:
            from sqlalchemy import inspect

            if inspect(db.get_bind()).has_table("consensus_report_text"):
                from valuation.db.models import ConsensusReportText

                cached = (
                    db.query(ConsensusReportText)
                    .filter(
                        ConsensusReportText.ticker == ticker,
                        ConsensusReportText.report_date >= window_start,
                        ConsensusReportText.report_date <= as_of,
                    )
                    .order_by(ConsensusReportText.report_date.desc())
                    .limit(max_reports)
                    .all()
                )
                summaries = [
                    {
                        "broker": row.broker_canon,
                        "report_date": row.report_date,
                        "target_price": (row.extracted or {}).get("target_price"),
                        "rating": None,
                        "summary": row.summary_text or row.title or "",
                    }
                    for row in cached
                ]
        except Exception as exc:
            warnings.append(f"Không đọc được cache luận điểm CTCK: {exc}")

    if not summaries:
        if fetcher is None:
            from valuation.ingest.scrapers.broker_24hmoney import fetch_report_summaries

            fetcher = fetch_report_summaries
        try:
            summaries = list(fetcher(ticker, timeout=timeout) or [])
        except Exception as exc:
            warnings.append(f"Không tải được tóm tắt CTCK mới: {exc}")

    comparison = None
    if db is not None:
        from valuation.report.report_data import build_consensus_comparison

        comparison = build_consensus_comparison(
            ticker, blended_fv, db, current_price=current_price
        )

    def _report_date(value: Any) -> Optional[datetime.date]:
        if isinstance(value, datetime.datetime):
            return value.date()
        if isinstance(value, datetime.date):
            return value
        for pattern in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.datetime.strptime(str(value), pattern).date()
            except ValueError:
                continue
        return None

    reports: List[Dict[str, Any]] = []
    for item in summaries:
        if len(reports) >= max_reports:
            break
        summary = str(item.get("summary") or "").strip()
        report_date = _report_date(item.get("report_date"))
        if not summary or report_date is None or not window_start <= report_date <= as_of:
            continue
        reports.append(
            {
                "broker": str(item.get("broker") or "Không rõ"),
                "report_date": report_date.isoformat(),
                "target_price_vnd": item.get("target_price"),
                "rating": item.get("rating"),
                "summary": summary[:max_chars],
            }
        )

    # Fallback có truy vết: chỉ dùng số liệu CTCK đang hiển thị trên app, không
    # tự dựng luận điểm khi nguồn tóm tắt chi tiết không sẵn có.
    if not reports and comparison:
        for row in list(comparison.get("broker_rows") or [])[:max_reports]:
            report_date = _report_date(row.get("report_date"))
            if report_date is None or not window_start <= report_date <= as_of:
                continue
            reports.append(
                {
                    "broker": row.get("broker"),
                    "report_date": report_date.isoformat(),
                    "target_price_vnd": row.get("target_price"),
                    "rating": row.get("rating"),
                    "summary": "Chỉ có dữ liệu khuyến nghị và giá mục tiêu; không có tóm tắt luận điểm.",
                }
            )

    target_prices = [
        float(item["target_price_vnd"])
        for item in reports
        if item.get("target_price_vnd") is not None
        and _finite(item.get("target_price_vnd"))
        and float(item["target_price_vnd"]) > 0
    ]
    median = comparison.get("consensus_median") if comparison else None
    if median is None and target_prices:
        median = statistics.median(target_prices)
    brokers = list(dict.fromkeys(str(item.get("broker") or "Không rõ") for item in reports))

    return {
        "available": bool(reports),
        "ticker": ticker,
        "internal_target_vnd": blended_fv,
        "current_price_vnd": current_price,
        "consensus_median_vnd": median,
        "consensus_thin": comparison.get("consensus_thin") if comparison else None,
        "consensus_stale": comparison.get("consensus_stale") if comparison else None,
        "n_reports": len(reports),
        "brokers": brokers,
        "reports": reports,
        "collection_warning": " | ".join(warnings) or None,
    }


def _prompt(payload: Dict[str, Any]) -> str:
    return f"""Bạn là Senior Equity Analyst kiêm Data Reviewer cho thị trường Việt Nam.

NHIỆM VỤ DUY NHẤT:
1. Phản biện tính hợp lý của dữ liệu trong JSON. Các phép cân đối trong
   `python_checks` là kết quả tất định: không được hạ mức độ nghiêm trọng.
2. Chỉ được gọi một số liệu là "nghi vấn" nếu chỉ ra đúng metric, kỳ và giá trị
   có trong JSON. Không có filing gốc trong payload, vì vậy không được tuyên bố
   đã đối chiếu nguồn chính thức và không được tự đưa ra số thay thế.
3. Viết nháp báo cáo khách quan, không hô hào; nếu có WARNING/ERROR phải nêu rõ
   giới hạn dữ liệu trước phần khuyến nghị.
4. Nếu `consensus_ctck.available=true`, đồng thời tổng hợp điểm chung, điểm riêng,
   điểm mấu chốt và đối chiếu mô hình nội bộ. Chỉ dùng đúng báo cáo được cung cấp;
   nếu báo cáo chỉ có giá mục tiêu thì không được bịa thêm luận điểm định tính.
5. Nếu `corporate_actions.available=true`, phân tích cổ tức, quyền mua và tăng vốn
   bằng đúng kết quả cơ học do Python cung cấp. Viết cho người không chuyên, giải
   thích thuật ngữ ngay khi dùng và ưu tiên ví dụ người đang giữ 1.000 cổ phiếu.
   Không gọi cổ phiếu thưởng là tạo thêm giá trị; không gọi quyền mua hấp dẫn nếu
   thiếu giá phát hành hoặc mục đích vốn.
6. Với sự kiện quá khứ, phải tách rõ: biến động giá thô, phần điều chỉnh cơ học,
   phản ứng so với giá lý thuyết và diễn biến sau 5/20 phiên. Đây chỉ là event
   study mô tả; không được tuyên bố sự kiện là nguyên nhân duy nhất của biến động.
7. Với 12 tháng tới, chỉ phân tích sự kiện đã công bố trong payload. Nêu rõ người
   giữ cổ phiếu nhận/trả gì, giá có thể điều chỉnh cơ học ra sao, điều kiện để sự
   kiện tạo giá trị, rủi ro pha loãng và dữ liệu còn thiếu. Không dự đoán ngày,
   tỷ lệ, giá phát hành hay sự kiện chưa được công bố.

Trả về JSON thuần với đúng schema:
{{
  "audit_status": "OK|WARNING|ERROR",
  "audit_findings": [
    {{"severity":"warning|error", "metric":"...", "period":"...", "observed":"...", "finding":"...", "action":"..."}}
  ],
  "thesis": "3-5 luận điểm đầu tư",
  "overview": "tổng quan và xu hướng tài chính gần nhất",
  "industry": "bối cảnh ngành, không bịa số ngành",
  "risks": "rủi ro dữ liệu, doanh nghiệp và định giá",
  "corporate_actions": "bản giải thích dễ hiểu nhưng chi tiết: (1) sự kiện đã công bố trong 12 tháng tới, tác động lên người giữ 1.000 cổ phiếu, điều chỉnh giá cơ học, điều kiện tạo giá trị và rủi ro; (2) sự kiện quá khứ, tách biến động thô khỏi điều chỉnh cơ học, phản ứng tương đối và diễn biến sau 5/20 phiên; (3) dữ liệu còn thiếu và việc cần kiểm chứng",
  "consensus_synthesis": {{
    "diem_chung": ["..."],
    "diem_rieng": ["..."],
    "diem_mau_chot": ["..."],
    "doi_chieu_noi_bo": "..."
  }}
}}

DỮ LIỆU DUY NHẤT ĐƯỢC PHÉP DÙNG:
{json.dumps(payload, ensure_ascii=False, default=str)}"""


def _safe_ai_findings(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []
    out = []
    for item in value[:12]:
        if not isinstance(item, dict):
            continue
        severity = str(item.get("severity") or "warning").lower()
        if severity not in {"warning", "error"}:
            severity = "warning"
        out.append(
            {
                "severity": severity,
                "metric": str(item.get("metric") or "Không xác định"),
                "period": str(item.get("period") or "Không xác định"),
                "observed": str(item.get("observed") or "Không xác định"),
                "finding": str(item.get("finding") or "Nghi vấn dữ liệu"),
                "action": str(item.get("action") or "Đối chiếu filing gốc"),
                "origin": "deepseek",
            }
        )
    return out


def _status_from_issues(issues: List[Dict[str, Any]]) -> str:
    if any(str(item.get("severity")).lower() == "error" for item in issues):
        return "ERROR"
    if issues:
        return "WARNING"
    return "OK"


def _safe_consensus_synthesis(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        value = {}
    out: Dict[str, Any] = {}
    for key in _CONSENSUS_LIST_KEYS:
        raw = value.get(key)
        if isinstance(raw, list):
            out[key] = [str(item) for item in raw[:6] if str(item).strip()]
        elif raw:
            out[key] = [str(raw)]
        else:
            out[key] = []
    out["doi_chieu_noi_bo"] = str(value.get("doi_chieu_noi_bo") or "")
    return out


def persist_consensus_synthesis(
    *, result: Dict[str, Any], context: Dict[str, Any], ticker: str, db: Any
) -> bool:
    """Upsert phần tổng hợp CTCK đã sinh trong lượt gọi chung, không gọi AI."""
    synthesis = result.get("consensus_synthesis") or {}
    if not result.get("ai_generated") or not context.get("available"):
        return False
    if not any(synthesis.get(key) for key in (*_CONSENSUS_LIST_KEYS, "doi_chieu_noi_bo")):
        return False

    from sqlalchemy.sql import func

    from valuation.db.models import ConsensusSynthesis
    from valuation.db.upsert import dialect_insert

    values = {
        "ticker": ticker.upper(),
        "n_reports": int(context.get("n_reports") or 0),
        "brokers": ", ".join(context.get("brokers") or []),
        "diem_chung": synthesis.get("diem_chung") or [],
        "diem_rieng": synthesis.get("diem_rieng") or [],
        "diem_mau_chot": synthesis.get("diem_mau_chot") or [],
        "doi_chieu_noi_bo": synthesis.get("doi_chieu_noi_bo") or "",
        "internal_fv": context.get("internal_target_vnd"),
        "consensus_median": context.get("consensus_median_vnd"),
        "model": result.get("model"),
        "generated_at": func.now(),
    }
    stmt = dialect_insert(db, ConsensusSynthesis).values(**values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["ticker"],
        set_={key: getattr(stmt.excluded, key) for key in values if key != "ticker"},
    )
    try:
        db.execute(stmt)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return True


def generate_verified_summary(
    *,
    company: Any,
    blended_fv: float,
    current_price: float,
    upside: float,
    recommendation: str,
    consensus_context: Optional[Dict[str, Any]] = None,
    corporate_actions_context: Optional[Dict[str, Any]] = None,
    client: Any = None,
) -> Dict[str, Any]:
    """Chạy kiểm chứng + sinh báo cáo bằng tối đa một API call."""
    cfg = _config()
    deterministic = run_deterministic_checks(
        company, blended_fv=blended_fv, upside=upside
    )
    python_status = _status_from_issues(deterministic)
    warning_count = len(deterministic)
    use_pro = python_status == "ERROR" or warning_count >= int(cfg.get("pro_warning_count", 2))
    model = str(cfg.get("pro_model" if use_pro else "fast_model", "deepseek-v4-flash"))

    if client is None:
        if not settings.deepseek_api_key:
            return {
                "ai_generated": False,
                "status": python_status,
                "python_issues": deterministic,
                "ai_issues": [],
                "error": "Không tìm thấy DEEPSEEK_API_KEY trong file .env.",
            }
        from openai import OpenAI

        client = OpenAI(api_key=settings.deepseek_api_key, base_url="https://api.deepseek.com")

    payload = _compact_payload(
        company,
        blended_fv=blended_fv,
        current_price=current_price,
        upside=upside,
        recommendation=recommendation,
        deterministic_issues=deterministic,
        consensus_context=consensus_context,
        corporate_actions_context=corporate_actions_context,
    )
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Output valid JSON only. Never invent or silently correct financial data.",
                },
                {"role": "user", "content": _prompt(payload)},
            ],
            response_format={"type": "json_object"},
            max_tokens=int(cfg.get("max_output_tokens", 4200)),
            temperature=float(cfg.get("temperature", 0.2)),
            extra_body={"thinking": {"type": "disabled"}},
        )
        raw = response.choices[0].message.content or ""
        data = json.loads(raw)
        ai_issues = _safe_ai_findings(data.get("audit_findings"))
        ai_status = str(data.get("audit_status") or "OK").upper()
        if ai_status not in _STATUS_RANK:
            ai_status = _status_from_issues(ai_issues)
        final_status = max((python_status, ai_status), key=_STATUS_RANK.get)
        sections = {key: str(data.get(key) or "") for key in _REPORT_KEYS}
        if not all(sections.values()):
            raise ValueError("DeepSeek trả thiếu phần báo cáo bắt buộc.")
        consensus_synthesis = _safe_consensus_synthesis(data.get("consensus_synthesis"))
        usage = getattr(response, "usage", None)
        return {
            "ai_generated": True,
            "status": final_status,
            "python_issues": deterministic,
            "ai_issues": ai_issues,
            "report_sections": sections,
            "consensus_synthesis": consensus_synthesis,
            "model": getattr(response, "model", model),
            "input_tokens": getattr(usage, "prompt_tokens", None),
            "output_tokens": getattr(usage, "completion_tokens", None),
            "error": None,
        }
    except Exception as exc:
        return {
            "ai_generated": False,
            "status": python_status,
            "python_issues": deterministic,
            "ai_issues": [],
            "model": model,
            "error": f"DeepSeek không trả được báo cáo JSON hợp lệ: {exc}",
        }


def generate_verified_summary_cached(
    *,
    company: Any,
    blended_fv: float,
    current_price: float,
    upside: float,
    recommendation: str,
    consensus_context: Optional[Dict[str, Any]] = None,
    corporate_actions_context: Optional[Dict[str, Any]] = None,
    force: bool = False,
    client: Any = None,
    cache_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Không gọi lại DeepSeek khi toàn bộ dữ liệu đầu vào vẫn giống hệt."""
    fingerprint = verified_summary_fingerprint(
        company=company,
        blended_fv=blended_fv,
        current_price=current_price,
        upside=upside,
        recommendation=recommendation,
        consensus_context=consensus_context,
        corporate_actions_context=corporate_actions_context,
    )
    cache_enabled = bool(_config().get("cache_enabled", True))
    if cache_enabled and not force:
        cached = load_verified_summary_cache(
            company.ticker, fingerprint, cache_dir=cache_dir
        )
        if cached is not None:
            return {
                **cached,
                "cache_hit": True,
                "input_fingerprint": fingerprint,
            }

    result = generate_verified_summary(
        company=company,
        blended_fv=blended_fv,
        current_price=current_price,
        upside=upside,
        recommendation=recommendation,
        consensus_context=consensus_context,
        corporate_actions_context=corporate_actions_context,
        client=client,
    )
    result = {
        **result,
        "cache_hit": False,
        "input_fingerprint": fingerprint,
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    if cache_enabled and result.get("ai_generated"):
        save_verified_summary_cache(
            company.ticker, fingerprint, result, cache_dir=cache_dir
        )
    return result


def report_markdown(result: Dict[str, Any]) -> str:
    """Ghép các phần đã kiểm chứng để hiển thị trong Streamlit."""
    sections = result.get("report_sections") or {}
    return "\n\n".join(
        [
            f"### Luận điểm đầu tư\n{sections.get('thesis', '')}",
            f"### Tổng quan doanh nghiệp\n{sections.get('overview', '')}",
            f"### Bối cảnh ngành\n{sections.get('industry', '')}",
            f"### Cổ tức, tăng vốn và quyền cổ đông\n{sections.get('corporate_actions', '')}",
            f"### Rủi ro và điểm cần theo dõi\n{sections.get('risks', '')}",
        ]
    )
