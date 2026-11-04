"""Tin công bố doanh nghiệp: phân loại và rút số theo luật cố định (D89). Không gọi mạng/AI.

Chỉ để hiển thị và cảnh báo trong tab Cổ tức & quyền mua — không đi vào số định giá.
"""

from __future__ import annotations

import datetime as dt
import re
import unicodedata
from typing import Any

# (nhãn, từ khóa trong tiêu đề, ảnh hưởng). Thứ tự = ưu tiên khi tiêu đề khớp nhiều nhóm
# (vd "phát hành cổ phiếu để tăng vốn từ NVCSH" là thưởng, không phải phát hành thêm).
_RULES: tuple[tuple[str, tuple[str, ...], str], ...] = (
    (
        "Quyền mua",
        ("quyền mua", "cổ đông hiện hữu"),
        "Cổ đông được mua thêm cổ phiếu ở giá phát hành; không mua thì tỷ lệ sở hữu bị pha loãng.",
    ),
    (
        "Cổ phiếu thưởng / cổ tức CP",
        (
            "cổ phiếu thưởng",
            "cổ tức bằng cổ phiếu",
            "để trả cổ tức",
            "nguồn vốn chủ",
            "từ nvcsh",
        ),
        "Số cổ phiếu tăng nhưng giá trị công ty không đổi; ngày GDKHQ giá điều chỉnh giảm theo tỷ lệ.",
    ),
    (
        "Cổ tức tiền",
        (
            "tạm ứng cổ tức",
            "cổ tức bằng tiền",
            "cổ tức tiền",
            "chi trả cổ tức",
            "trả cổ tức",
        ),
        "Tiền về tài khoản; ngày GDKHQ giá tham chiếu giảm đúng phần cổ tức, tổng tài sản không đổi.",
    ),
    (
        "Cổ tức",
        ("cổ tức",),
        "Có thông tin cổ tức; đọc chi tiết để biết trả tiền hay cổ phiếu và ngày chốt.",
    ),
    (
        "Cổ phiếu quỹ",
        ("cổ phiếu quỹ", "mua lại cổ phiếu"),
        "Số cổ phiếu lưu hành giảm; có lợi cho cổ đông còn lại nếu mua dưới giá trị.",
    ),
    (
        "Phát hành thêm",
        ("phát hành", "chào bán", "esop", "riêng lẻ"),
        "Số cổ phiếu tăng; nếu giá phát hành thấp hơn giá trị thì EPS và giá trị mỗi cổ phiếu bị pha loãng.",
    ),
    (
        "Lãnh đạo / cổ đông lớn giao dịch",
        (
            "người nội bộ",
            "cổ đông lớn",
            "người có liên quan",
            "đăng ký mua",
            "đăng kí mua",
            "đăng ký bán",
            "đăng kí bán",
            "giao dịch cổ phiếu",
        ),
        "Tín hiệu tham khảo về kỳ vọng của người trong cuộc; không làm đổi giá trị nội tại.",
    ),
    (
        "Kết quả kinh doanh",
        (
            "kết quả kinh doanh",
            "báo cáo tài chính",
            "bctc",
            "lợi nhuận",
            "doanh thu",
            "kế hoạch kinh doanh",
        ),
        "Có số liệu mới: đối chiếu với giả định trong mô hình định giá.",
    ),
    (
        "Quản trị / nhân sự",
        (
            "đại hội",
            "đhđcđ",
            "hđqt",
            "hội đồng quản trị",
            "bổ nhiệm",
            "miễn nhiệm",
            "từ nhiệm",
            "nghị quyết",
            "ban kiểm soát",
            "tổng giám đốc",
        ),
        "Quyết định HĐQT/ĐHĐCĐ hoặc thay đổi nhân sự; đọc chi tiết xem có kế hoạch vốn, cổ tức.",
    ),
    (
        "Thủ tục",
        (
            "niêm yết",
            "lưu ký",
            "đăng ký doanh nghiệp",
            "điều lệ",
            "giấy chứng nhận",
            "số lượng cổ phiếu",
            "giải trình",
            "thay đổi thông tin",
        ),
        "Thủ tục pháp lý, thường không ảnh hưởng giá trị.",
    ),
)
_OTHER = ("Khác", "Đọc chi tiết để đánh giá ảnh hưởng.")
OFFICIAL_SOURCES = frozenset({"HOSE", "HNX", "UPCOM", "SSC", "UBCK", "VSD", "VSDC"})
# Nhãn tin → loại sự kiện trong lịch quyền (corporate_actions.event_type) dùng để đối chiếu.
_CALENDAR_TYPES = {"Cổ tức tiền": {"CASH_DIVIDEND"}, "Quyền mua": {"RIGHTS_ISSUE"}}
_CASH_LABELS = {"Cổ tức tiền", "Cổ tức"}

_DATE = r"(?<!\d)(\d{1,2})/(\d{1,2})(?:/(\d{4}))?(?!\d)"
_NUM = r"(\d{1,3}(?:\.\d{3})+|\d+)"
_CASH = (
    re.compile(rf"nhận\s+{_NUM}\s*(?:đồng|đ)\b"),
    re.compile(rf"{_NUM}\s*(?:đồng|đ)\s*/\s*(?:cổ phiếu|cp)"),
)
_RATIO = re.compile(r"t[ỷỉ] lệ\s*(?:là\s*)?(\d+(?:,\d+)?)\s*%")
_RECORD = re.compile(rf"(?:chốt danh sách|đăng ký cuối cùng)\D{{0,40}}?{_DATE}")
_PAYMENT = re.compile(rf"(?:chi trả|thanh toán)\D{{0,30}}?{_DATE}")
_ATTACHMENT = re.compile(r"[\w.\-]+\.(?:pdf|docx?|xlsx?|zip|rar)", re.IGNORECASE)


def _nfc(text: Any) -> str:
    return " ".join(unicodedata.normalize("NFC", str(text or "")).split())


def classify_disclosure(title: str) -> tuple[str, str]:
    """(nhãn, ảnh hưởng) theo từ khóa tiêu đề; không khớp → "Khác"."""
    lowered = _nfc(title).lower()
    for label, keywords, impact in _RULES:
        if any(k in lowered for k in keywords):
            return label, impact
    return _OTHER


def _date_from(match: re.Match[str] | None, published: dt.date) -> dt.date | None:
    if match is None:
        return None
    day, month, year = match.groups()
    try:
        parsed = dt.date(int(year or published.year), int(month), int(day))
    except ValueError:
        return None
    # Văn bản hay ghi "ngày 30/11" không có năm: lùi xa hơn 60 ngày so với ngày đăng → năm sau.
    if year is None and parsed < published - dt.timedelta(days=60):
        parsed = parsed.replace(year=parsed.year + 1)
    return parsed


def disclosure_facts(text: str, *, published: dt.date) -> dict[str, Any]:
    """Số rút từ văn bản (máy đọc — UI ghi rõ phải đối chiếu bản gốc). Chỉ trả khóa tìm thấy."""
    lowered = _nfc(text).lower()
    facts: dict[str, Any] = {}
    for pattern in _CASH:
        if match := pattern.search(lowered):
            facts["cash_vnd_per_share"] = float(re.sub(r"\D", "", match.group(1)))
            break
    if match := _RATIO.search(lowered):
        facts["ratio_pct"] = float(match.group(1).replace(",", "."))
    for key, pattern in (("record_date", _RECORD), ("payment_date", _PAYMENT)):
        if found := _date_from(pattern.search(lowered), published):
            facts[key] = found
    return facts


def _published(item: dict[str, Any]) -> dt.date | None:
    try:
        return dt.datetime.fromisoformat(
            str(item.get("publish_time") or "")[:19]
        ).date()
    except ValueError:
        return None


def _facts_line(facts: dict[str, Any]) -> str:
    parts = []
    if "cash_vnd_per_share" in facts:
        parts.append(f"{facts['cash_vnd_per_share']:,.0f}".replace(",", ".") + " đ/cp")
    if "ratio_pct" in facts:
        parts.append(f"tỷ lệ {facts['ratio_pct']:g}%")
    if "record_date" in facts:
        parts.append(f"chốt {facts['record_date']:%d/%m/%Y}")
    if "payment_date" in facts:
        parts.append(f"trả {facts['payment_date']:%d/%m/%Y}")
    return " · ".join(parts)


def describe_disclosure(
    item: dict[str, Any], press_excerpt_chars: int
) -> dict[str, Any]:
    """Dữ liệu hiển thị một tin. Tin báo chí chỉ giữ đoạn đầu + link (bản quyền); tin sàn giữ toàn văn."""
    title = _nfc(item.get("title"))
    label, impact = classify_disclosure(title)
    source = _nfc(item.get("source")).upper()
    official = source in OFFICIAL_SOURCES
    content = _nfc(item.get("content"))
    body, _, tail = content.partition("Tài liệu đính kèm")
    body = body.strip()
    published = _published(item)
    facts = (
        disclosure_facts(f"{title}. {body}", published=published) if published else {}
    )
    if label not in _CASH_LABELS:
        # "x đồng/cổ phiếu" ở tin không phải cổ tức thường là giá thị trường/giá phát hành, không phải tiền chia.
        facts.pop("cash_vnd_per_share", None)
    first_sentence = re.split(r"(?<=[.!?])\s", body, maxsplit=1)[0] if body else ""
    if not official and len(body) > press_excerpt_chars:
        body = body[:press_excerpt_chars].rstrip() + "…"
    url = str(item.get("url") or "")
    return {
        "title": title,
        "label": label,
        "impact": impact,
        "official": official,
        "source": source or "BÁO CHÍ",
        "published": published,
        "facts": facts,
        "summary": _facts_line(facts) or first_sentence[:180],
        "body": body,
        "attachments": _ATTACHMENT.findall(tail),
        "url": url if url.startswith("https://") else None,
    }


def _on_calendar(
    row: Any, types: set[str], record: dt.date | None, published: dt.date
) -> bool:
    if row.event_type not in types:
        return False
    if record is not None:
        ex = row.ex_right_date
        return row.record_date == record or (
            ex is not None and 0 <= (record - ex).days <= 3
        )
    announced = row.announcement_date
    return announced is not None and -45 <= (announced - published).days <= 7


def uncalendared_payouts(
    items: list[dict[str, Any]],
    calendar_rows: list[Any],
    *,
    today: dt.date,
    alert_days: int,
) -> list[dict[str, Any]]:
    """Tin cổ tức tiền/quyền mua trong `alert_days` ngày mà lịch quyền chưa có sự kiện tương ứng.

    Khớp theo ngày chốt nếu đọc được (cùng ngày chốt, hoặc GDKHQ trước ngày chốt ≤ 3 ngày); không đọc
    được thì khớp sự kiện cùng loại công bố trong [ngày tin − 45, ngày tin + 7]. Mỗi (nhãn, ngày chốt)
    chỉ báo một lần — nhiều bài cùng nói một đợt cổ tức.
    """
    found: dict[tuple[str, dt.date | None], dict[str, Any]] = {}
    for item in items:
        view = describe_disclosure(item, press_excerpt_chars=0)
        types = _CALENDAR_TYPES.get(view["label"])
        published = view["published"]
        if not types or published is None or (today - published).days > alert_days:
            continue
        record = view["facts"].get("record_date")
        if record is not None and record < today:
            continue

        if any(_on_calendar(row, types, record, published) for row in calendar_rows):
            continue
        key = (view["label"], record)
        if key not in found or published > found[key]["published"]:
            found[key] = {**view, "record_date": record}
    return sorted(found.values(), key=lambda v: v["published"], reverse=True)
