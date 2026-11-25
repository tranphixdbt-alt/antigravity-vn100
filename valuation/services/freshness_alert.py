"""Báo Discord khi dữ liệu trên web cũ hơn mức cho phép (D121, docs/PLAN_CAP_NHAT_DU_LIEU.md bước C).

Hai loại kiểm, chạy sau mỗi lượt tải giá (job `kiem-du-lieu` 08:20 và 16:10 thứ Hai–thứ Sáu):
- Giá: phiên mới nhất trong DB so với phiên đáng lẽ đã có (ngày làm việc gần nhất; sau 16:00 là hôm nay), cho phép
  trễ `market_session.max_lag_weekdays` ngày (ngày nghỉ lễ giữa tuần như 24/11/2026 không bị báo nhầm). Thêm: số mã
  VN100 có giá ở phiên mới nhất phải đủ `market_session.min_tickers_on_latest` (bắt cả dòng lạc của một mã).
- Vĩ mô: tuổi kỳ số liệu mới nhất của từng chuỗi (`freshness_alert.macro_max_age_days`), chỉ báo vào các thứ trong
  `macro_alert_weekdays` để không lặp mỗi ngày.

Không ghi gì vào DB. Không có lịch nghỉ lễ: Tết sẽ báo nhầm, tin báo có ghi chú điều đó.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.orm import Session

from valuation.config import load_defaults

Notifier = Callable[[str], bool]


@dataclass(frozen=True)
class FreshnessConfig:
    close: str
    after_close_check: str
    max_lag_weekdays: int
    min_tickers: int
    macro_max_age_days: dict[str, int]
    macro_alert_weekdays: tuple[int, ...]


def load_config() -> FreshnessConfig:
    d = load_defaults()
    ms, fa = d["market_session"], d["freshness_alert"]
    return FreshnessConfig(
        close=str(ms["close"]),
        after_close_check=str(fa["after_close_check"]),
        max_lag_weekdays=int(ms["max_lag_weekdays"]),
        min_tickers=int(ms["min_tickers_on_latest"]),
        macro_max_age_days={
            str(k): int(v) for k, v in fa["macro_max_age_days"].items()
        },
        macro_alert_weekdays=tuple(int(x) for x in fa["macro_alert_weekdays"]),
    )


def expected_session(now: dt.datetime, after_close_check: str) -> dt.date:
    """Phiên giao dịch gần nhất đáng lẽ đã nằm trong DB lúc `now` (giờ VN), bỏ qua thứ Bảy, Chủ nhật.

    Ngày thường từ `after_close_check` trở đi: hôm nay (lượt 15:45 đã chạy). Trước đó: ngày làm việc liền trước.
    """
    day = now.date()
    if day.weekday() < 5 and now.strftime("%H:%M") >= after_close_check:
        return day
    day -= dt.timedelta(days=1)
    while day.weekday() >= 5:
        day -= dt.timedelta(days=1)
    return day


def weekday_lag(latest: dt.date, expected: dt.date) -> int:
    """Số ngày làm việc (T2–T6) sau `latest` tới hết `expected`; 0 nếu đã đủ."""
    lag, day = 0, latest
    while day < expected:
        day += dt.timedelta(days=1)
        if day.weekday() < 5:
            lag += 1
    return lag


def price_problems(
    latest: dt.date | None,
    have: set[str],
    universe: set[str],
    now: dt.datetime,
    cfg: FreshnessConfig,
) -> list[str]:
    """Các câu báo về giá; rỗng nếu ổn."""
    if latest is None:
        return ["Chưa có giá nào của rổ VN100 trong DB."]
    out = []
    expected = expected_session(now, cfg.after_close_check)
    lag = weekday_lag(latest, expected)
    if lag > cfg.max_lag_weekdays:
        out.append(
            f"Giá mới nhất trong DB là phiên {latest:%d/%m/%Y}, chậm {lag} ngày làm việc so với {expected:%d/%m/%Y}"
            " (nếu đang nghỉ lễ thì bỏ qua tin này)."
        )
    missing = sorted(universe - have)
    if len(have & universe) < cfg.min_tickers:
        names = ", ".join(missing[:12]) + ("…" if len(missing) > 12 else "")
        out.append(
            f"Phiên {latest:%d/%m/%Y} chỉ {len(have & universe)}/{len(universe)} mã VN100 có giá; thiếu: {names}."
        )
    return out


def macro_problems(
    latest: dict[str, dt.date | None], today: dt.date, cfg: FreshnessConfig
) -> list[str]:
    """Chuỗi vĩ mô có kỳ số liệu mới nhất cũ hơn ngưỡng của nó."""
    out = []
    for code, max_age in cfg.macro_max_age_days.items():
        last = latest.get(code)
        if last is None:
            out.append(f"{code}: chưa có số nào.")
        elif (today - last).days > max_age:
            out.append(
                f"{code}: kỳ mới nhất {last:%d/%m/%Y}, cũ {(today - last).days} ngày (ngưỡng {max_age})."
            )
    return out


def _db_state(
    db: Session, macro_codes: list[str]
) -> tuple[dt.date | None, set[str], set[str], dict]:
    from valuation.db.models import MacroSeries, PricesDaily, Ticker

    universe = {t for (t,) in db.query(Ticker.ticker).filter(Ticker.is_vn100)}
    latest = (
        db.query(func.max(PricesDaily.trade_date))
        .filter(
            PricesDaily.ticker.in_(universe | {"VNINDEX"}),
            PricesDaily.close.isnot(None),
        )
        .scalar()
    )
    have: set[str] = set()
    if latest is not None:
        have = {
            t
            for (t,) in db.query(PricesDaily.ticker).filter(
                PricesDaily.trade_date == latest, PricesDaily.close.isnot(None)
            )
        }
    macro = {
        code: db.query(func.max(MacroSeries.date))
        .filter(MacroSeries.indicator_code == code)
        .scalar()
        for code in macro_codes
    }
    return latest, have, universe, macro


def run_check(
    db: Session,
    now: dt.datetime,
    notifier: Notifier | None = None,
    cfg: FreshnessConfig | None = None,
    dry_run: bool = False,
) -> dict:
    """Kiểm giá + vĩ mô, gửi MỘT tin Discord gộp nếu có vấn đề. Trả kết quả để in vào nhật ký job."""
    cfg = cfg or load_config()
    latest, have, universe, macro = _db_state(db, list(cfg.macro_max_age_days))
    prices = price_problems(latest, have, universe, now, cfg)
    macro_due = now.weekday() in cfg.macro_alert_weekdays
    macros = macro_problems(macro, now.date(), cfg) if macro_due else []
    lines = [*(f"- Giá: {p}" for p in prices), *(f"- Vĩ mô: {m}" for m in macros)]
    message = ("Dữ liệu btinvest.vn cần xem:\n" + "\n".join(lines)) if lines else None
    sent = False
    if message and not dry_run:
        sent = (notifier or _discord)(message)
    return {
        "latest_price": latest.isoformat() if latest else None,
        "tickers_on_latest": len(have & universe),
        "universe": len(universe),
        "price_problems": prices,
        "macro_checked": macro_due,
        "macro_problems": macros,
        "message": message,
        "sent": sent,
    }


def _discord(message: str) -> bool:
    from valuation.output.discord_alerter import notify_discord

    resp = notify_discord(content=message[:1900])
    return resp is not None and getattr(resp, "status_code", 0) in (200, 204)
