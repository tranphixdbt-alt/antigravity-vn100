"""Nạp TPCP_10Y tự động từ worldgovernmentbonds.com và cảnh báo khi chuỗi cũ (D100).

Vì sao nguồn này:
- Chuỗi ngày của WGB khớp nguồn nạp tay trước đó (investing.com): 23 phiên 19/10–20/11/2026 lệch
  tối đa 0,001 điểm % (20/11 cùng 4,568%). Giữ được tính liên tục của rf.
- HNX công bố đường cong ƯỚC LƯỢNG (par yield 10 năm 4,458% cùng tuần), khác thước đo → không trộn
  vào cùng chuỗi.
- Trang render số bằng JavaScript nên mở bằng Chromium headless (Playwright, có sẵn trong image VPS)
  và đọc biến `jsGlobalResult.result.quote` mà chính trang dựng để vẽ bảng. Trình duyệt chỉ được tải
  tài nguyên từ host trong `macro_sources.allowed_domains`; quảng cáo/tracker bị chặn.

Quy tắc ghi:
- Chỉ THÊM ngày CHƯA CÓ trong DB, trong `lookback_days` gần nhất (lấp cả ngày job lỡ); ngày đã có
  (kể cả từ nguồn khác) không bao giờ bị ghi đè.
- Chỉ thứ Hai–thứ Sáu (WGB lặp giá trị cho cuối tuần) và trước hôm nay (điểm của hôm nay còn đổi
  trong ngày; ghi sớm thì sẽ không được sửa vì ngày đã có không bị ghi đè).
- WGB chụp số vài lần mỗi ngày (giờ UTC); điểm của một ngày là lần chụp cuối ngày đó, có hôm là giữa
  phiên → có thể lệch giá đóng cửa ~0,1–2 bp. Ngày lễ VN WGB lặp số hôm trước (không phân biệt được).
- Giá trị ngoài khoảng hợp lý → lỗi, không ghi gì. Ghi qua `upsert_macro_series` (chạy lại không
  nhân đôi). Gỡ: xóa dòng `indicator_code='TPCP_10Y' AND source='worldgovernmentbonds.com'`.
"""
from __future__ import annotations

import datetime
import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from valuation.config import get_macro_allowed_domains, load_defaults
from valuation.data_access.freshness import MACRO_RF_MAX_AGE_DAYS
from valuation.ingest.macro_store import MacroPoint, upsert_macro_series
from valuation.ingest.tpcp_scraper import _assert_allowed_host

logger = logging.getLogger(__name__)

INDICATOR = "TPCP_10Y"
SOURCE = "worldgovernmentbonds.com"

# url -> giá trị thô của `jsGlobalResult.result.quote`. Injectable để test không chạm mạng.
QuoteFetcher = Callable[[str], Any]
# Nội dung tin -> True nếu đã gửi được.
Notifier = Callable[[str], bool]


@dataclass(frozen=True)
class WgbConfig:
    url: str
    lookback_days: int
    min_pct: float
    max_pct: float
    alert_after_days: int
    page_timeout_sec: float


def load_wgb_config() -> WgbConfig:
    """Đọc `macro_sources.tpcp_10y_wgb` trong config/defaults.yaml (không có số cứng trong code)."""
    cfg = load_defaults()["macro_sources"]["tpcp_10y_wgb"]
    lo, hi = cfg["sane_range_pct"]
    return WgbConfig(
        url=str(cfg["url"]),
        lookback_days=int(cfg["lookback_days"]),
        min_pct=float(lo),
        max_pct=float(hi),
        alert_after_days=int(cfg["alert_after_days"]),
        page_timeout_sec=float(cfg["page_timeout_sec"]),
    )


def parse_wgb_quotes(raw: Any) -> list[tuple[datetime.date, float]]:
    """Chuẩn hóa `quote` của WGB thành [(ngày, lợi suất %)] tăng dần theo ngày.

    WGB trả dict {"1": {"CLOSE_VAL": 4.568, "DATA_VAL": "2026-11-20", ...}, ...} (có thể là list).
    Phần tử sai dạng → ValueError: định dạng nguồn đổi thì phải lộ ra, không bỏ qua im lặng.
    """
    items: Iterable[Any]
    if isinstance(raw, dict):
        items = raw.values()
    elif isinstance(raw, list):
        items = raw
    else:
        raise TypeError(f"quote WGB không phải dict/list: {type(raw).__name__}")

    out: dict[datetime.date, float] = {}
    for item in items:
        if not isinstance(item, dict) or "DATA_VAL" not in item or "CLOSE_VAL" not in item:
            raise ValueError(f"phần tử quote WGB thiếu DATA_VAL/CLOSE_VAL: {item!r}")
        day = datetime.date.fromisoformat(str(item["DATA_VAL"]))
        val = item["CLOSE_VAL"]
        if isinstance(val, bool) or not isinstance(val, (int, float, str)):
            raise TypeError(f"CLOSE_VAL không phải số ở {day}: {val!r}")
        out[day] = float(val)
    if not out:
        raise ValueError("quote WGB rỗng")
    return sorted(out.items())


def select_new_points(
    quotes: list[tuple[datetime.date, float]],
    existing_dates: set[datetime.date],
    today: datetime.date,
    cfg: WgbConfig,
) -> list[MacroPoint]:
    """Chọn các điểm cần thêm: ngày thường, trong `lookback_days`, trước `today`, chưa có trong DB.

    Lợi suất % → decimal_rate (4,568% → 0,04568) theo registry.
    """
    start = today - datetime.timedelta(days=cfg.lookback_days)
    points: list[MacroPoint] = []
    for day, pct in quotes:
        if day < start or day >= today or day.weekday() >= 5 or day in existing_dates:
            continue
        if not cfg.min_pct <= pct <= cfg.max_pct:
            raise ValueError(
                f"TPCP_10Y {day} = {pct}% ngoài khoảng hợp lý "
                f"[{cfg.min_pct}; {cfg.max_pct}]% — không ghi (kiểm tra nguồn)."
            )
        points.append(MacroPoint(INDICATOR, day, round(pct / 100.0, 8), SOURCE))
    return points


def stale_alert_message(
    last_date: datetime.date | None,
    last_value: float | None,
    today: datetime.date,
    alert_after_days: int,
    fetch_error: str | None = None,
) -> str | None:
    """Nội dung cảnh báo nếu điểm TPCP_10Y mới nhất cũ hơn `alert_after_days` ngày; None nếu còn tươi.

    Cờ chặn STALE_MACRO_RF bật khi tuổi > MACRO_RF_MAX_AGE_DAYS (30) → ngày bị chặn đầu tiên là
    last_date + 31 ngày.
    """
    reason = f" Lần nạp vừa rồi lỗi: {fetch_error}" if fetch_error else ""
    if last_date is None:
        return (
            "TPCP_10Y chưa có điểm nào trong DB: cả 100 mã bị chặn xếp hạng (STALE_MACRO_RF)."
            + reason
        )
    age = (today - last_date).days
    if age <= alert_after_days:
        return None
    block_from = last_date + datetime.timedelta(days=MACRO_RF_MAX_AGE_DAYS + 1)
    value_txt = f" ({last_value * 100:.3f}%)" if last_value is not None else ""
    if today >= block_from:
        status = f"ĐANG chặn cả 100 mã khỏi xếp hạng từ {block_from:%d/%m/%Y} (STALE_MACRO_RF)."
    else:
        status = f"Cả 100 mã sẽ bị chặn khỏi xếp hạng từ {block_from:%d/%m/%Y} (STALE_MACRO_RF)."
    return (
        f"TPCP_10Y cũ {age} ngày: điểm mới nhất {last_date:%d/%m/%Y}{value_txt}. {status}"
        f"{reason} Nạp tay: scripts/ingest_tpcp_10y.py (CSV investing.com)."
    )


def short_error(exc: BaseException, max_len: int = 300) -> str:
    """Một dòng, tối đa `max_len` ký tự cho tin Discord (lỗi Playwright dài nhiều dòng);
    traceback đầy đủ vẫn nằm trong log job."""
    first = next((ln.strip() for ln in str(exc).splitlines() if ln.strip()), "")
    text = f"{type(exc).__name__}: {first}" if first else type(exc).__name__
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def latest_point(db: Session) -> tuple[datetime.date | None, float | None]:
    from valuation.db.models import MacroSeries

    row = (
        db.query(MacroSeries.date, MacroSeries.value)
        .filter(MacroSeries.indicator_code == INDICATOR)
        .order_by(MacroSeries.date.desc())
        .first()
    )
    if row is None:
        return None, None
    return row[0], float(row[1]) if row[1] is not None else None


def existing_dates_since(db: Session, start: datetime.date) -> set[datetime.date]:
    from valuation.db.models import MacroSeries

    rows = (
        db.query(MacroSeries.date)
        .filter(MacroSeries.indicator_code == INDICATOR, MacroSeries.date >= start)
        .all()
    )
    return {r[0] for r in rows}


def request_allowed(url: str, allowed_hosts: set[str]) -> bool:
    """Trình duyệt headless chỉ được tải tài nguyên từ host trong allowlist (chặn quảng cáo/tracker)."""
    host = (urlparse(url).hostname or "").lower()
    return host in allowed_hosts


def playwright_fetch_quotes(url: str, timeout_sec: float) -> Any:
    """Mở trang lịch sử WGB bằng Chromium headless, trả `jsGlobalResult.result.quote`."""
    from playwright.sync_api import Route, sync_playwright

    allowed = {d.lower() for d in get_macro_allowed_domains()}
    timeout_ms = timeout_sec * 1000

    def _route(route: Route) -> None:
        if request_allowed(route.request.url, allowed):
            route.continue_()
        else:
            route.abort()

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception:  # noqa: BLE001 — máy chưa `playwright install` (Mac) → Chrome của máy, như build_pdf
            browser = p.chromium.launch(headless=True, channel="chrome")
        try:
            page = browser.new_page()
            page.route("**/*", _route)
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_function(
                "() => window.jsGlobalResult && window.jsGlobalResult.result"
                " && window.jsGlobalResult.result.quote",
                timeout=timeout_ms,
            )
            return page.evaluate("() => window.jsGlobalResult.result.quote")
        finally:
            browser.close()


def discord_notify(message: str) -> bool:
    from valuation.output.discord_alerter import notify_discord

    resp = notify_discord(content=message)
    return resp is not None and getattr(resp, "status_code", 0) in (200, 204)


def run_tpcp_update(
    db: Session,
    today: datetime.date | None = None,
    fetcher: QuoteFetcher | None = None,
    notifier: Notifier | None = None,
    cfg: WgbConfig | None = None,
    dry_run: bool = False,
) -> dict:
    """Tải WGB → thêm điểm mới → kiểm tra tuổi chuỗi → báo Discord nếu cũ quá ngưỡng.

    Lỗi tải/parse không chặn bước kiểm tra tuổi (nguồn hỏng đúng là lúc cần cảnh báo); lỗi được trả
    trong `error` để script thoát mã ≠ 0 và in traceback vào log job.
    """
    cfg = cfg or load_wgb_config()
    today = today or datetime.date.today()  # noqa: DTZ011 — TZ container = Asia/Ho_Chi_Minh, như freshness.py
    fetcher = fetcher or (lambda u: playwright_fetch_quotes(u, cfg.page_timeout_sec))
    notifier = notifier or discord_notify

    last_before, _ = latest_point(db)
    points: list[MacroPoint] = []
    written = 0
    error: str | None = None
    try:
        _assert_allowed_host(cfg.url)
        quotes = parse_wgb_quotes(fetcher(cfg.url))
        have = existing_dates_since(db, today - datetime.timedelta(days=cfg.lookback_days))
        points = select_new_points(quotes, have, today, cfg)
        if points and not dry_run:
            written = upsert_macro_series(points, db)
    except Exception as exc:
        logger.exception("Nạp TPCP_10Y từ WGB lỗi")
        error = short_error(exc)

    last_date, last_value = latest_point(db)
    message = stale_alert_message(last_date, last_value, today, cfg.alert_after_days, error)
    alert_sent = False
    if message and not dry_run:
        alert_sent = notifier(message)

    return {
        "today": today.isoformat(),
        "last_before": last_before.isoformat() if last_before else None,
        "points": [(p.date.isoformat(), p.value) for p in points],
        "written": written,
        "last_date": last_date.isoformat() if last_date else None,
        "last_value": last_value,
        "age_days": (today - last_date).days if last_date else None,
        "alert": message,
        "alert_sent": alert_sent,
        "error": error,
        "dry_run": dry_run,
    }
