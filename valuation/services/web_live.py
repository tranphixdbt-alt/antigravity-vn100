"""Giá trong phiên cho trang Hôm nay của btinvest.vn (D122): VN-Index, VN30 và mã VN100 tăng, giảm mạnh nhất.

D128: cùng lượt bảng giá đó cho thêm phiên đang chạy của từng mã (`session_bars`: nến, khối ngoại) để biểu đồ và tab
Dòng tiền chạy trong phiên (`web_flow.with_session`, `web_flow.session_flows`), và khối ngoại VN100 ở trang Hôm nay.

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


def _num(x: Any) -> float | None:
    """Số dương đọc được; 0, âm, rỗng hay chữ là thiếu (bảng giá trả 0 cho trường chưa có số)."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None


def _money(x: Any) -> float | None:
    """Giá trị tiền (đồng) hoặc khối lượng: 0 là số thật (không ai mua), rỗng hay chữ là thiếu."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v >= 0 else None


def session_bars(rows: list[dict], tz: ZoneInfo) -> dict[str, dict]:
    """Phiên đang chạy (hoặc vừa đóng) của từng mã, đọc từ một lượt bảng giá (D128). Chỉ để HIỂN THỊ, không ghi DB.

    Ngày phiên = ngày (giờ Việt Nam) của lần khớp cuối `matchPrice.time`. Mã chưa khớp lệnh (giá khớp 0) bỏ qua.
    Đơn vị như prices_daily: giá đồng/cp, khối lượng cp, giá trị đồng. Khối ngoại trên bảng giá khớp từng đồng với số
    job 15:45 ghi vào DB (đo FPT, HPG 27/11/2026). Thiếu mở/cao/thấp thì không vẽ nến (`nen` False), khối ngoại vẫn dùng.
    """
    out: dict[str, dict] = {}
    for r in rows:
        m = r.get("matchPrice") or {}
        info = r.get("listingInfo") or {}
        ma, gia = m.get("symbol") or info.get("symbol"), _num(m.get("matchPrice"))
        if not ma or gia is None:
            continue
        try:
            luc = dt.datetime.fromisoformat(str(m["time"]).replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        if luc.tzinfo is None:
            continue  # không rõ múi giờ thì không suy được ngày phiên
        mua, ban = _money(m.get("foreignBuyValue")), _money(m.get("foreignSellValue"))
        mo, cao, thap = (_num(m.get(k)) for k in ("openPrice", "highest", "lowest"))
        out[ma] = {
            "ngay": luc.astimezone(tz).date(),
            "mo": mo,
            "cao": cao,
            "thap": thap,
            "gia": gia,
            "tham_chieu": _num(info.get("refPrice")),
            "kl": _money(m.get("accumulatedVolume")),
            "gt": _money(m.get("accumulatedValue")),
            "nn_mua": mua,
            "nn_ban": ban,
            "nn_rong": None if mua is None or ban is None else mua - ban,
            "nen": None not in (mo, cao, thap),
        }
    return out


def foreign_summary(bars: dict[str, dict], top_n: int) -> dict | None:
    """Khối ngoại của phiên mới nhất trên bảng giá: tổng ròng VN100, mã mua ròng và bán ròng nhiều nhất (đồng)."""
    if not bars:
        return None
    day = max(b["ngay"] for b in bars.values())
    net = {
        ma: b["nn_rong"]
        for ma, b in bars.items()
        if b["ngay"] == day and b["nn_rong"] is not None
    }
    if not net:
        return None
    buy = sorted((x for x in net.items() if x[1] > 0), key=lambda x: -x[1])
    sell = sorted((x for x in net.items() if x[1] < 0), key=lambda x: x[1])
    return {
        "ngay": day,
        "rong": sum(net.values()),
        "so_ma": len(net),
        "mua": [{"ma": m, "rong": v} for m, v in buy[:top_n]],
        "ban": [{"ma": m, "rong": v} for m, v in sell[:top_n]],
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
    """Giây trình duyệt chờ trước khi hỏi lại: trong giờ `poll_seconds`; ngoài giờ tới mốc kế tiếp (+5 giây), nhưng
    không quá `db_poll_seconds` để thấy DB vừa có số mới (D128; lượt hỏi đó không gọi Vietcap, xem `_fresh`).
    """
    cfg = _cfg()
    if in_live_hours(now):
        return int(cfg["poll_seconds"])
    return min(
        max(int((next_mark(now) - now).total_seconds()) + 5, 5),
        int(cfg["db_poll_seconds"]),
    )


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
    top, bars = None, {}
    try:
        rows = _board(_vn100())
        top_n = int(_cfg()["top_n"])
        top = movers(rows, top_n)
        bars = session_bars(rows, _tz())
        top["khoi_ngoai"] = foreign_summary(bars, top_n)
    except LiveDataError as exc:
        errors.append(f"Bảng giá VN100: {exc}")
    return {
        "luc": now.astimezone(_tz()).isoformat(timespec="seconds"),
        "chi_so": indices,
        "noi_bat": top,
        "loi": errors,
        "nguon": "Vietcap",
        "phien": bars,  # từng mã, không gửi nguyên cho trình duyệt (xem `snapshot`, `session_data`)
    }


def _hit(now: dt.datetime) -> dict:
    with _lock:
        hit = _memo.get("live")
        if hit is None or not _fresh(hit[0], hit[1], now):
            hit = (now, _build(now))
            _memo["live"] = hit
        return hit[1]


def snapshot(now: dt.datetime | None = None) -> dict:
    """Số trong phiên dùng chung cho mọi người xem; xem `_fresh` cho lúc nào lấy lại. Kèm `hoi_lai_giay` cho trình duyệt."""
    now = now or dt.datetime.now(_tz())
    value = {k: v for k, v in _hit(now).items() if k != "phien"}
    return {
        **value,
        "hoi_lai_giay": _poll_after(now),
        "trong_gio": in_live_hours(now),
        "hoi_bieu_do_giay": int(_cfg()["chart_poll_seconds"]),
        "hoi_phai_sinh_giay": int(_cfg()["ps_poll_seconds"]),
    }


def session_data(now: dt.datetime | None = None) -> tuple[dict[str, dict], list[str]]:
    """Phiên trên bảng giá của từng mã VN100 (cùng lượt lấy, cùng bộ nhớ với `snapshot`) và các lỗi nguồn."""
    value = _hit(now or dt.datetime.now(_tz()))
    return value["phien"], [x for x in value["loi"] if x.startswith("Bảng giá")]
