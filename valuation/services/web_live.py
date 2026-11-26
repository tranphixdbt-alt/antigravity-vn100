"""Giá trong phiên cho trang Hôm nay của btinvest.vn (D122): VN-Index, VN30 và mã VN100 tăng, giảm mạnh nhất.

Nguồn: bảng giá và biểu đồ Vietcap (`web.live` trong config), cùng nguồn repo `cw_scanner` đang dùng cho chứng quyền,
phái sinh. Đo 26/11/2026 từ VPS: 0,35–1,5 giây mỗi lượt.
- Chỉ số: nến ngày của biểu đồ, gồm nến hôm nay đang chạy trong phiên; thay đổi so với nến phiên trước.
- Cổ phiếu: một lời gọi bảng giá cho cả 100 mã; thay đổi so với giá tham chiếu. Mã chưa khớp lệnh (giá khớp 0) không tính.

Trong giờ giao dịch (`live_hours`, T2–T6) máy chủ lấy số nhiều nhất mỗi `cache_seconds` giây, dùng chung cho mọi
người xem, nên số lượt gọi Vietcap không tăng theo số người. Ngoài giờ (người dùng 26/11/2026) số đã lấy dùng tiếp, chỉ
lấy lại khi qua một mốc kiểm `off_hours_checks` (4 giờ, 8 giờ sáng) hoặc lúc vừa hết giờ giao dịch (giá đã chốt). Chỉ hiển thị, KHÔNG ghi DB: giá phiên chưa chốt không được vào DB (D121, `ingest/session_guard.py`).
Lỗi nguồn không bị nuốt: trả câu báo trong `loi` để web hiện nút cảnh báo, phần còn lại vẫn hiện.
"""

from __future__ import annotations

import datetime as dt
import json
import threading
import time
import urllib.error
import urllib.request
from typing import Any
from zoneinfo import ZoneInfo

from valuation.config import load_defaults

INDICES = ("VNINDEX", "VN30")


class LiveDataError(RuntimeError):
    """Nguồn giá trong phiên trả lỗi hoặc số không đọc được."""


def _cfg() -> dict:
    return load_defaults()["web"]["live"]


def _tz() -> ZoneInfo:
    return ZoneInfo(load_defaults()["market_session"]["timezone"])


def _post(url: str, body: dict) -> Any:
    cfg = _cfg()
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), headers=dict(cfg["headers"])
    )
    try:
        with urllib.request.urlopen(req, timeout=float(cfg["timeout_seconds"])) as r:
            return json.load(r)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise LiveDataError(f"Vietcap không trả lời ({type(exc).__name__})") from exc


def _chart(symbol: str) -> list[dict]:
    cfg = _cfg()
    return _post(
        cfg["chart_url"],
        {
            "timeFrame": "ONE_DAY",
            "symbols": [symbol],
            "to": int(time.time()),
            "countBack": int(cfg["chart_bars"]),
        },
    )


def _board(symbols: list[str]) -> list[dict]:
    return _post(_cfg()["board_url"], {"symbols": symbols})


def _vn100() -> list[str]:
    from valuation.db.models import Ticker
    from valuation.db.session import SessionLocalRead

    db = SessionLocalRead()
    try:
        return sorted(t for (t,) in db.query(Ticker.ticker).filter(Ticker.is_vn100))
    finally:
        db.close()


def index_row(symbol: str, chart: list[dict], now: dt.datetime) -> dict:
    """Điểm mới nhất của một chỉ số và thay đổi so với phiên trước, từ nến ngày Vietcap (ngày nến = 0 giờ UTC)."""
    try:
        bars = chart[0]
        days = [
            dt.datetime.fromtimestamp(int(t), dt.timezone.utc).date() for t in bars["t"]
        ]
        closes = [float(c) for c in bars["c"]]
    except (IndexError, KeyError, TypeError, ValueError) as exc:
        raise LiveDataError(f"không đọc được biểu đồ {symbol}") from exc
    if len(closes) < 2 or closes[-2] <= 0:
        raise LiveDataError(f"biểu đồ {symbol} thiếu phiên trước")
    local = now.astimezone(_tz())
    close_hhmm = str(load_defaults()["market_session"]["close"])
    last, prev = closes[-1], closes[-2]
    return {
        "ma": symbol,
        "diem": last,
        "ngay": days[-1],
        "thay_doi": round(last - prev, 2),
        "ty_le": last / prev - 1,
        "trong_phien": days[-1] == local.date()
        and local.strftime("%H:%M") < close_hhmm,
    }


def movers(rows: list[dict], top_n: int) -> dict:
    """Mã tăng, giảm mạnh nhất so với giá tham chiếu và đếm độ rộng; mã chưa khớp lệnh để riêng."""
    items: list[dict[str, Any]] = []
    waiting = 0
    for r in rows:
        info, match = r.get("listingInfo") or {}, r.get("matchPrice") or {}
        ref, price = info.get("refPrice") or 0, match.get("matchPrice") or 0
        if not ref or not price:
            waiting += 1
            continue
        items.append(
            {
                "ma": info.get("symbol"),
                "gia": float(price),
                "ty_le": float(price) / float(ref) - 1,
                "tran": bool(info.get("ceiling")) and price >= info["ceiling"],
                "san": bool(info.get("floor")) and price <= info["floor"],
            }
        )

    def rate(x: dict[str, Any]) -> float:
        return float(x["ty_le"])

    up = sorted((x for x in items if rate(x) > 0), key=rate, reverse=True)
    down = sorted((x for x in items if rate(x) < 0), key=rate)
    return {
        "tang": up[:top_n],
        "giam": down[:top_n],
        "do_rong": {
            "tang": len(up),
            "giam": len(down),
            "dung": len(items) - len(up) - len(down),
            "chua_khop": waiting,
        },
    }


_lock = threading.Lock()
_memo: dict[str, tuple[dt.datetime, dict]] = {}


def _at(day: dt.date, hhmm: str, tz: ZoneInfo) -> dt.datetime:
    h, m = (int(x) for x in hhmm.split(":"))
    return dt.datetime.combine(day, dt.time(h, m), tz)


def in_live_hours(now: dt.datetime) -> bool:
    """Trong giờ lấy giá liên tục: thứ Hai–thứ Sáu, giữa hai mốc `live_hours` (giờ Việt Nam)."""
    local = now.astimezone(_tz())
    start, end = _cfg()["live_hours"]
    return local.weekday() < 5 and start <= local.strftime("%H:%M") < end


def _marks(day: dt.date, tz: ZoneInfo) -> list[dt.datetime]:
    """Các mốc phải lấy lại số trong một ngày: mốc kiểm ngoài giờ, và lúc vào, lúc hết giờ giao dịch (ngày thường)."""
    cfg = _cfg()
    out = [_at(day, x, tz) for x in cfg["off_hours_checks"]]
    if day.weekday() < 5:
        out += [_at(day, x, tz) for x in cfg["live_hours"]]
    return out


def last_mark(now: dt.datetime) -> dt.datetime:
    """Mốc gần nhất đã qua; số lấy trước mốc này là cũ."""
    tz = _tz()
    local = now.astimezone(tz)
    for back in range(8):
        past = [
            m for m in _marks(local.date() - dt.timedelta(days=back), tz) if m <= local
        ]
        if past:
            return max(past)
    return local - dt.timedelta(
        days=1
    )  # không có mốc nào trong cấu hình: coi như số luôn cũ


def next_mark(now: dt.datetime) -> dt.datetime:
    """Mốc sắp tới; trình duyệt ngoài giờ hỏi lại đúng lúc này."""
    tz = _tz()
    local = now.astimezone(tz)
    for ahead in range(8):
        later = [
            m for m in _marks(local.date() + dt.timedelta(days=ahead), tz) if m > local
        ]
        if later:
            return min(later)
    return local + dt.timedelta(hours=6)


def _fresh(at: dt.datetime, value: dict, now: dt.datetime) -> bool:
    cfg = _cfg()
    age = (now - at).total_seconds()
    if value["loi"]:
        return age < float(cfg["error_cache_seconds"])
    if in_live_hours(now):
        return age < float(cfg["cache_seconds"])
    return at >= last_mark(now)


def _poll_after(now: dt.datetime) -> int:
    """Giây trình duyệt chờ trước khi hỏi lại: trong giờ `poll_seconds`; ngoài giờ tới mốc kế tiếp (+5 giây)."""
    if in_live_hours(now):
        return int(_cfg()["poll_seconds"])
    return max(int((next_mark(now) - now).total_seconds()) + 5, 5)


def clear_cache() -> None:
    with _lock:
        _memo.clear()


def _build(now: dt.datetime) -> dict:
    errors: list[str] = []
    indices = []
    for sym in INDICES:
        try:
            indices.append(index_row(sym, _chart(sym), now))
        except LiveDataError as exc:
            errors.append(f"{sym}: {exc}")
    top = None
    try:
        top = movers(_board(_vn100()), int(_cfg()["top_n"]))
    except LiveDataError as exc:
        errors.append(f"Bảng giá VN100: {exc}")
    return {
        "luc": now.astimezone(_tz()).isoformat(timespec="seconds"),
        "chi_so": indices,
        "noi_bat": top,
        "loi": errors,
        "nguon": "Vietcap",
    }


def snapshot(now: dt.datetime | None = None) -> dict:
    """Số trong phiên dùng chung cho mọi người xem; xem `_fresh` cho lúc nào lấy lại. Kèm `hoi_lai_giay` cho trình duyệt."""
    now = now or dt.datetime.now(_tz())
    with _lock:
        hit = _memo.get("live")
        if hit is None or not _fresh(hit[0], hit[1], now):
            hit = (now, _build(now))
            _memo["live"] = hit
        value = hit[1]
    return {**value, "hoi_lai_giay": _poll_after(now), "trong_gio": in_live_hours(now)}
