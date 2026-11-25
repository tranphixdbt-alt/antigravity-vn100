"""Báo cáo AI bản ngắn trên tờ mã của web hợp nhất (lát 7, D116, mục 15 của docs/PLAN_WEB_HOP_NHAT.md).

Người dùng chốt 25/11/2026: mọi tài khoản đã duyệt bấm được, mỗi tài khoản 5 lượt sinh mới mỗi ngày, báo cáo
khoảng 500 từ gồm tổng quan công ty và nhận định sâu về mã.

Cùng nguồn số với bản dài của web cũ (`valuation/report/verified_summary.py`): Python kiểm số học BCTC, gom ngữ
cảnh công ty chứng khoán, thị trường, cổ tức và áp cổng công bố (`_compact_payload`); thêm phần dòng tiền mà tờ mã
đang hiện (`web_flow.ticker`). DeepSeek chỉ viết lời từ đúng gói dữ liệu đó trong một lần gọi. Không ghi gì vào DB
định giá.

Hạn mức đếm trên nhật ký `web_audit` (việc `bao_cao_ai`): mỗi lần sinh mới thành công ghi một dòng. Lỗi, hoặc dữ
liệu không đổi nên dùng lại bản cũ, không tính lượt.

Bản mới nhất của mỗi mã lưu thành tệp JSON trong thư mục con của thư mục đệm bản dài (`.deepseek_report_cache/`,
trên VPS là volume riêng nên còn qua deploy). Thư mục con để các việc quét `*.json` của bản dài không đọc nhầm.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import os
import re
import threading
from pathlib import Path
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from valuation.config import load_defaults, settings
from valuation.db.web_user import WebAudit, WebUser, now_utc
from valuation.report import verified_summary as vs
from valuation.services import web_flow, web_valuation

logger = logging.getLogger(__name__)

VIEC = "bao_cao_ai"  # tên việc trong web_audit; đổi tên là đếm lại hạn mức từ đầu
# đổi câu lệnh cho AI thì tăng, để bản cũ không được dùng lại như bản mới
PROMPT_VERSION = "ngan-v3"
_VN = dt.timezone(dt.timedelta(hours=7))
_MA = re.compile(r"[A-Z0-9]{3,4}")
_SECTIONS = ("ket_luan", "tong_quan", "so_voi_nganh", "nhan_dinh")
_LISTS = ("diem_an", "rui_ro")  # các phần là danh sách ý
_LOCKS: dict[int, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()
_FILE_LOCK = threading.Lock()


class AiReportError(Exception):
    """Không sinh được báo cáo; `status` là mã HTTP trả cho giao diện, `detail` là câu báo cho người dùng."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


def _cfg() -> dict[str, Any]:
    return dict(load_defaults()["web"]["ai_report"])


def _check_ma(ma: str) -> str:
    if not _MA.fullmatch(ma):
        raise AiReportError(422, "Mã không hợp lệ.")
    return ma


def cache_dir() -> Path:
    return vs._REPORT_CACHE_DIR / str(_cfg()["dir_name"])


def _path(ma: str) -> Path:
    return cache_dir() / f"{_check_ma(ma)}.json"


# ---------- hạn mức ----------


def day_start_utc(now: dt.datetime) -> dt.datetime:
    """Đầu ngày theo giờ Việt Nam của thời điểm `now` (UTC không kèm múi), đổi về UTC không kèm múi như cột `luc`."""
    vn = now.replace(tzinfo=dt.timezone.utc).astimezone(_VN)
    start = vn.replace(hour=0, minute=0, second=0, microsecond=0)
    return start.astimezone(dt.timezone.utc).replace(tzinfo=None)


def used_today(
    udb: Session, user_id: int, now: dt.datetime | None = None, viec: str = VIEC
) -> int:
    """Số dòng việc `viec` của người này trong ngày (giờ Việt Nam) chứa thời điểm `now`.

    Mặc định đếm lần sinh báo cáo AI; góc chat (web_chat) đếm việc `hoi_ai` bằng cùng hàm.
    """
    since = day_start_utc(now or now_utc())
    until = since + dt.timedelta(days=1)
    return int(
        udb.query(func.count(WebAudit.id))
        .filter(
            WebAudit.user_id == user_id,
            WebAudit.viec == viec,
            WebAudit.luc >= since,
            WebAudit.luc < until,
        )
        .scalar()
        or 0
    )


def remaining(udb: Session, user_id: int, now: dt.datetime | None = None) -> int:
    return max(int(_cfg()["daily_limit"]) - used_today(udb, user_id, now), 0)


# ---------- bản đã lưu ----------


def latest(ma: str) -> dict[str, Any] | None:
    """Bản mới nhất đã lưu của mã; tệp hỏng thì coi như chưa có (ghi cảnh báo), không làm hỏng tờ mã."""
    path = _path(ma)
    if not path.is_file():
        return None
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning("Không đọc được báo cáo AI bản ngắn %s: %s", path.name, exc)
        return None
    return saved if isinstance(saved, dict) and saved.get("van_ban") else None


def _save(ma: str, report: dict[str, Any]) -> None:
    path = _path(ma)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".json.tmp")
    with _FILE_LOCK:
        temp.write_text(
            json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        os.replace(temp, path)


def _public(report: dict[str, Any] | None) -> dict[str, Any] | None:
    """Phần đưa ra giao diện: bỏ dấu vân tay và số token (chỉ để truy vết, nằm trong tệp)."""
    if report is None:
        return None
    keep = ("ma", "tao_luc", "mo_hinh", "van_ban", "nguon", "so_tu")
    return {k: report.get(k) for k in keep}


def status(
    udb: Session, user: WebUser, ma: str, now: dt.datetime | None = None
) -> dict[str, Any]:
    """Bản đã lưu của mã (nếu có) và số lượt người này còn trong ngày."""
    return {
        "ma": ma,
        "bao_cao": _public(latest(ma)),
        "con_lai": remaining(udb, user.id, now),
        "gioi_han": int(_cfg()["daily_limit"]),
        "so_tu": int(_cfg()["target_words"]),
    }


# ---------- gói dữ liệu và lời gọi AI ----------


def _flow_summary(db: Any, ma: str) -> dict[str, Any]:
    """Phần dòng tiền đang hiện trên tờ mã (chế độ mặc định: loại phiên thỏa thuận)."""
    d = web_flow.ticker(db, ma, "loai")
    if d is None:
        return {"available": False, "reason": "Mã không có trong bảng dòng tiền VN100."}
    votes = d.get("phieu") or {}
    return {
        "available": True,
        "nhan": (d.get("nhan") or {}).get("text"),
        "ly_do": (d.get("nhan") or {}).get("reason"),
        "boi_canh": d.get("boi_canh"),
        "phieu": {
            k: (votes.get(k) or {}).get("chip")
            for k in ("foreign", "pv", "prop", "rvol")
            if votes.get(k)
        },
        "huy_hieu": d.get("huy_hieu"),
        "cua_so_phien": d.get("cua_so"),
        "gia_den": d.get("gia_den"),
        "dong_tien_den": d.get("dong_tien_den"),
        "ghi_chu": "Khối ngoại và tự doanh tính bằng % giá trị giao dịch; phiếu là bằng chứng của nhãn gom/xả.",
    }


def _derived(payload: dict[str, Any]) -> dict[str, Any]:
    """Các phần trăm Python tính sẵn để AI không phải tự tính (lần thử đầu AI tự chia và gọi trung vị là trung bình).

    Cùng định nghĩa upside của web: giá tham chiếu ÷ thị giá − 1, đơn vị %.
    """
    price = payload.get("current_price_vnd")
    median = (payload.get("consensus_ctck") or {}).get("consensus_median_vnd")
    target = payload.get("target_price_vnd")

    def up(ref: Any) -> float | None:
        if (
            not price
            or not ref
            or not vs._finite(price)
            or not vs._finite(ref)
            or float(price) <= 0
        ):
            return None
        return round((float(ref) / float(price) - 1.0) * 100.0, 1)

    return {
        "trung_vi_gia_muc_tieu_ctck_vnd": median,
        "trung_vi_ctck_so_voi_thi_gia_pct": up(median),
        "gia_tri_hop_ly_mo_hinh_so_voi_thi_gia_pct": up(target),
        "dinh_nghia": "giá tham chiếu ÷ thị giá − 1; gia_tri_hop_ly trống khi kết quả mô hình chưa được công bố",
    }


def _hide_model_value(payload: dict[str, Any], ma: str) -> None:
    """Cổng công bố: kết quả chưa được công bố thì AI không được thấy giá trị hợp lý của mô hình cho mã này.

    `_compact_payload` đã bỏ ở phần chính, nhưng gói công ty chứng khoán và bảng cùng ngành (lấy từ đợt xếp hạng
    VN100) của bản dài vẫn chép lại giá trị đó: bỏ nốt ở hai chỗ này.
    """
    if isinstance(payload.get("consensus_ctck"), dict):
        payload["consensus_ctck"] = {
            **payload["consensus_ctck"],
            "internal_target_vnd": None,
        }
    peers = (payload.get("market_context") or {}).get("sector_peers")
    if not isinstance(peers, dict) or not peers.get("available"):
        return
    hidden = {"fair_value": None, "upside_pct": None, "mos": None}
    if isinstance(peers.get("own"), dict):
        peers["own"] = {**peers["own"], **hidden}
    peers["peers"] = [
        {**row, **hidden} if isinstance(row, dict) and row.get("ticker") == ma else row
        for row in peers.get("peers") or []
    ]


def build_inputs(db: Any, ma: str) -> dict[str, Any]:
    """Gói dữ liệu duy nhất AI được dùng, dấu vân tay của nó và mô hình AI sẽ gọi."""
    from valuation.data_access.corporate_actions import corporate_actions_context

    bundle = web_valuation._bundle(db, ma)
    company, result = bundle["company"], bundle["result"]
    fv = result.get("blended_fair_value_per_share")
    if not fv:
        raise AiReportError(
            409, f"Bộ máy chưa ra giá trị hợp lý cho {ma} nên chưa viết được báo cáo."
        )
    price = float(company.current_price)
    upside = float(result.get("upside") or 0.0)
    # như app cũ (streamlit_app.py): kết quả chưa được công bố thì coi là chưa xếp hạng, AI không được nêu giá mục tiêu
    rec = str(result.get("recommendation") or "NOT_RATED")
    if not result.get("publication_allowed", True):
        rec = "NOT_RATED"
    corp = corporate_actions_context(
        db,
        ticker=ma,
        current_price_vnd=price,
        shares_outstanding=float(company.shares_outstanding) * 1_000_000.0,
    )
    consensus = vs.collect_consensus_context(
        ticker=ma, blended_fv=float(fv), current_price=price, db=db
    )
    market = vs.collect_market_context(
        ticker=ma, sector=company.sector, db=db, current_price=price
    )
    checks = vs.run_deterministic_checks(company, blended_fv=float(fv), upside=upside)
    payload = vs._compact_payload(
        company,
        blended_fv=float(fv),
        current_price=price,
        upside=upside,
        recommendation=rec,
        deterministic_issues=checks,
        consensus_context=consensus,
        corporate_actions_context=corp,
        market_context=market,
    )
    if rec == "NOT_RATED":
        _hide_model_value(payload, ma)
    payload["dong_tien_web"] = _flow_summary(db, ma)
    payload["tinh_san"] = _derived(payload)
    payload["method_label"] = result.get("method_label")
    canonical = json.dumps(
        vs._without_volatile_fields(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    fingerprint = hashlib.sha256(f"{PROMPT_VERSION}:{canonical}".encode()).hexdigest()
    # như bản dài: dữ liệu có lỗi hoặc từ hai cảnh báo trở lên thì dùng mô hình mạnh hơn
    long_cfg = vs._config()
    use_pro = vs._status_from_issues(checks) == "ERROR" or len(checks) >= int(
        long_cfg.get("pro_warning_count", 2)
    )
    model = str(
        long_cfg.get("pro_model" if use_pro else "fast_model", "deepseek-v4-flash")
    )
    sources = {
        "gia": price,
        "gia_tri_hop_ly": float(fv),
        "duoc_cong_bo": bool(result.get("publication_allowed", True)),
        "khuyen_nghi": rec,
        "so_bao_cao_ctck": len((consensus or {}).get("reports") or []),
        "gia_den": payload["dong_tien_web"].get("gia_den"),
        "dong_tien_den": payload["dong_tien_web"].get("dong_tien_den"),
    }
    return {
        "payload": payload,
        "fingerprint": fingerprint,
        "model": model,
        "nguon": sources,
    }


def prompt(payload: dict[str, Any], words: int) -> str:
    ma = payload.get("ticker")
    return f"""Bạn là chuyên viên phân tích cổ phiếu Việt Nam, viết cho nhà đầu tư cá nhân và đội môi giới.

Viết một báo cáo NGẮN về {ma}, khoảng {words} từ. Người đọc cần nắm nhanh CHIỀU HƯỚNG và những điều QUAN TRỌNG MÀ ÍT
NGƯỜI NHÌN THẤY ở công ty này, cùng vị trí của nó so với đối thủ cùng ngành; không cần đọc lại bảng số.

CÁCH VIẾT (bắt buộc):
1. Ít con số: cả bài dùng tối đa 5 con số, chỉ khi con số đó là then chốt. Còn lại diễn đạt bằng chiều hướng: tăng,
   giảm, cải thiện, xấu đi, cao hơn, thấp hơn, đi ngược nhau. Không liệt kê số theo từng năm.
2. Mọi nhận định phải có căn cứ trong JSON bên dưới; số nào nêu ra phải có sẵn trong JSON. Không tự tính phần trăm:
   phần trăm so với thị giá lấy ở `tinh_san`. Không có căn cứ thì không viết.
3. Đơn vị: BCTC tính bằng tỷ đồng (`unit_financials`); giá tính bằng đồng mỗi cổ phiếu. Dòng có `period` là TTM là
   4 quý gần nhất, không phải dự phóng.
4. Nếu `publication_allowed` là false hoặc `recommendation` là NOT_RATED: KHÔNG nêu giá trị hợp lý, giá mục tiêu hay
   khuyến nghị của mô hình; nói kết quả định giá của mô hình đang chờ rà soát và lý do theo `flag_explanations`.
5. Giá mục tiêu và luận điểm của công ty chứng khoán chỉ lấy từ `consensus_ctck`; không bịa tên, ngày, luận điểm.
   `consensus_median_vnd` là TRUNG VỊ, không gọi là trung bình.
6. Mô tả hoạt động kinh doanh chỉ ở mức chung (ngành, mảng chính), không dùng từ so sánh nhất (lớn nhất, hàng đầu,
   số một) khi JSON không có căn cứ. Khi so với đối thủ, không nêu giá trị hợp lý hay upside của từng mã.
7. Không khuyên mua hay bán, không khẳng định thao túng. Không viết tên trường JSON, mã cờ (như STALE_PRICE) hay chữ
   NOT_RATED: diễn đạt bằng lời thường.

NỘI DUNG (tổng cộng 420 đến 520 từ, không vượt):
- "ket_luan": 1 đến 2 câu: chiều hướng chính của {ma} lúc này.
- "tong_quan": khoảng 70 từ: công ty làm gì và xu hướng kinh doanh mấy năm gần đây, bằng lời.
- "diem_an": 2 đến 3 ý, mỗi ý 1 đến 2 câu: điều quan trọng mà nhìn qua giá hay lợi nhuận dễ bỏ sót. Tìm ở: lợi nhuận
  và doanh thu đi ngược nhau, chất lượng lợi nhuận (khoản bất thường, thu nhập tài chính), dòng tiền kinh doanh so
  với lợi nhuận, biên lợi nhuận, nợ vay, phụ thuộc một mảng, các công ty chứng khoán nhìn khác nhau, dòng tiền đi
  ngược chiều giá, cờ cảnh báo dữ liệu. Mỗi ý nói rõ căn cứ bằng lời.
- "so_voi_nganh": khoảng 100 từ: {ma} mạnh hơn và yếu hơn các đối thủ cùng ngành ở đâu (ROE, tăng trưởng doanh thu,
  nợ vay, chuyển đổi tiền, điểm phòng thủ và tích sản), gọi tên đối thủ có trong `market_context.sector_peers`.
  Không có dữ liệu cùng ngành thì viết đúng câu "Chưa đủ dữ liệu cùng ngành để so sánh."
- "nhan_dinh": khoảng 100 từ: nghiêng về tích cực, trung tính hay thận trọng, và vì sao: định giá so với thị giá và
  giá mục tiêu công ty chứng khoán, dòng tiền (nhãn gom hoặc xả trong `dong_tien_web`), kỹ thuật, bối cảnh ngành.
- "rui_ro": đúng 3 ý, mỗi ý một câu dưới 25 từ.

Trả về JSON thuần đúng schema:
{{"ket_luan": "...", "tong_quan": "...", "diem_an": ["...", "..."], "so_voi_nganh": "...", "nhan_dinh": "...",
"rui_ro": ["...", "...", "..."]}}

DỮ LIỆU DUY NHẤT ĐƯỢC PHÉP DÙNG:
{json.dumps(payload, ensure_ascii=False, default=str)}"""


def call_model(payload: dict[str, Any], model: str) -> dict[str, Any]:
    """Một lần gọi DeepSeek; trả các phần báo cáo, tên mô hình và số token. Lỗi thành AiReportError."""
    import openai

    cfg = _cfg()
    if not settings.deepseek_api_key:
        raise AiReportError(
            503, "Máy chủ chưa có khóa DeepSeek nên chưa sinh được báo cáo AI."
        )
    client = openai.OpenAI(
        api_key=settings.deepseek_api_key,
        base_url="https://api.deepseek.com",
        timeout=float(cfg["timeout_seconds"]),
        max_retries=0,  # mỗi lần bấm tốn đúng một lời gọi; lỗi thì người dùng tự bấm lại
    )
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Output valid JSON only. Never invent or silently correct financial data.",
                },
                {"role": "user", "content": prompt(payload, int(cfg["target_words"]))},
            ],
            response_format={"type": "json_object"},
            max_tokens=int(cfg["max_output_tokens"]),
            temperature=float(cfg["temperature"]),
            extra_body={"thinking": {"type": "disabled"}},
        )
    except (openai.APIStatusError, openai.APIConnectionError) as exc:
        # không đưa thông điệp gốc ra giao diện: nó có thể chứa đuôi khóa API
        code = getattr(exc, "status_code", None)
        hint = {
            401: "khóa DeepSeek không hợp lệ",
            402: "tài khoản DeepSeek hết số dư",
            429: "DeepSeek đang giới hạn lượt gọi, thử lại sau",
        }.get(code or 0, "lỗi kết nối hoặc máy chủ DeepSeek, thử lại sau")
        logger.warning(
            "DeepSeek từ chối báo cáo bản ngắn (%s)", code or type(exc).__name__
        )
        raise AiReportError(
            502, f"Chưa sinh được báo cáo: {hint}. Lượt này không bị tính."
        ) from exc
    choice = response.choices[0]
    if getattr(choice, "finish_reason", None) == "length":
        raise AiReportError(
            502,
            "Báo cáo bị cắt giữa chừng (chạm giới hạn độ dài). Lượt này không bị tính.",
        )
    try:
        data = vs.parse_first_json_object(choice.message.content or "")
    except ValueError as exc:
        raise AiReportError(
            502, "AI trả về không đúng định dạng. Lượt này không bị tính."
        ) from exc
    parts: dict[str, Any] = {k: str(data.get(k) or "").strip() for k in _SECTIONS}
    for k in _LISTS:
        value = data.get(k)
        items = value if isinstance(value, list) else []
        parts[k] = [str(x).strip() for x in items if str(x).strip()]
    if not all(parts.values()):
        raise AiReportError(
            502, "AI trả thiếu phần bắt buộc của báo cáo. Lượt này không bị tính."
        )
    usage = getattr(response, "usage", None)
    return {
        "phan": parts,
        "mo_hinh": str(getattr(response, "model", None) or model),
        "token_vao": getattr(usage, "prompt_tokens", None),
        "token_ra": getattr(usage, "completion_tokens", None),
    }


def to_markdown(ma: str, phan: dict[str, Any]) -> str:
    def ds(items: list[str]) -> str:
        return "\n".join(f"- {x}" for x in items)

    return (
        f"**{phan['ket_luan']}**\n\n"
        f"#### Tổng quan công ty\n{phan['tong_quan']}\n\n"
        f"#### Điều ít người để ý\n{ds(phan['diem_an'])}\n\n"
        f"#### So với cùng ngành\n{phan['so_voi_nganh']}\n\n"
        f"#### Nhận định về {ma}\n{phan['nhan_dinh']}\n\n"
        f"#### Rủi ro cần theo dõi\n{ds(phan['rui_ro'])}\n"
    )


def word_count(text: str) -> int:
    return len(re.findall(r"[^\s#*\-]+", text))


def number_count(text: str) -> int:
    """Số con số trong bài (kiểu 7.361, 14,9%, 2025), để theo dõi AI có giữ "tối đa 5 con số" không."""
    return len(re.findall(r"\d+(?:[.,]\d+)*", text))


# ---------- sinh mới ----------


def _user_lock(user_id: int) -> threading.Lock:
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(user_id, threading.Lock())


def generate(
    db: Any, udb: Session, user: WebUser, ma: str, now: dt.datetime | None = None
) -> dict[str, Any]:
    """Sinh bản mới cho mã (một lần gọi DeepSeek), hoặc trả bản đã lưu nếu dữ liệu không đổi.

    Mỗi người chỉ một lượt đang chạy một lúc (khóa theo người), nên hai lần bấm liền không vượt hạn mức.
    """
    _check_ma(ma)
    limit = int(_cfg()["daily_limit"])
    lock = _user_lock(user.id)
    if not lock.acquire(blocking=False):
        raise AiReportError(
            409, "Bạn đang có một báo cáo đang viết, chờ xong rồi bấm tiếp."
        )
    try:
        if used_today(udb, user.id, now) >= limit:
            raise AiReportError(
                429,
                f"Bạn đã dùng hết {limit} lượt sinh báo cáo AI hôm nay. Lượt mới có lại sau 0 giờ.",
            )
        inputs = build_inputs(db, ma)
        saved = latest(ma)
        if saved and saved.get("dau_vao") == inputs["fingerprint"]:
            return {**status(udb, user, ma, now), "dung_lai": True}
        out = call_model(inputs["payload"], inputs["model"])
        text = to_markdown(ma, out["phan"])
        report = {
            "ma": ma,
            "phien_ban": PROMPT_VERSION,
            "tao_luc": (now or now_utc()).replace(microsecond=0).isoformat() + "Z",
            "mo_hinh": out["mo_hinh"],
            "van_ban": text,
            "phan": out["phan"],
            "so_tu": word_count(text),
            "so_con_so": number_count(text),
            "nguon": inputs["nguon"],
            "dau_vao": inputs["fingerprint"],
            "token_vao": out["token_vao"],
            "token_ra": out["token_ra"],
        }
        _save(ma, report)
        udb.add(
            WebAudit(
                luc=now or now_utc(),
                user_id=user.id,
                viec=VIEC,
                doi_tuong=f"co_phieu:{ma}",
                chi_tiet=json.dumps(
                    {
                        "mo_hinh": out["mo_hinh"],
                        "token_vao": out["token_vao"],
                        "token_ra": out["token_ra"],
                        "dau_vao": inputs["fingerprint"][:16],
                    },
                    ensure_ascii=False,
                ),
            )
        )
        udb.commit()
        return {**status(udb, user, ma, now), "dung_lai": False}
    finally:
        lock.release()
