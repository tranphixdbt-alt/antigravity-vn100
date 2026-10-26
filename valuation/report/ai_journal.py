"""Nhật ký báo cáo DeepSeek cho vòng học hằng tuần (docs/PLAN_LEARNING_LOOP.md, GĐ 1).

Mỗi báo cáo DeepSeek mới → knowledge/ai_reports/<YYYY-MM>/<MÃ>_<ngày>_<fp8>.md + 1 dòng index.jsonl.
Không gọi thêm API nào; chỉ ghi lại cái đã sinh. Nội dung AI là GIẢ THUYẾT chưa kiểm chứng — file ghi rõ.
Thư mục dự án nằm trên Google Drive nên file tự đồng bộ cho phiên Claude trên cloud đọc.

  python -m valuation.report.ai_journal --backfill   # ghi lại các báo cáo đang có trong .deepseek_report_cache/
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from valuation.config import PROJECT_ROOT

JOURNAL_DIR = PROJECT_ROOT / "knowledge" / "ai_reports"
_SECTIONS = (
    ("thesis", "Luận điểm"),
    ("risks", "Rủi ro"),
    ("market_view", "Kỹ thuật / dòng tiền / vị thế"),
    ("industry", "Bối cảnh ngành"),
)
_CONSENSUS = (
    ("diem_chung", "Điểm chung các CTCK"),
    ("diem_rieng", "Điểm riêng từng CTCK"),
    ("diem_mau_chot", "Điểm mấu chốt"),
    ("doi_chieu_noi_bo", "Đối chiếu với mô hình nội bộ"),
)


def _num(x: Any, fmt: str = "{:,.0f}") -> str:
    try:
        return fmt.format(float(x))
    except (TypeError, ValueError):
        return "—"


def _lines(v: Any) -> list[str]:
    items = v if isinstance(v, list) else [v] if v else []
    return [f"- {str(i).strip()}" for i in items if str(i).strip()]


def render_markdown(ticker: str, fingerprint: str, result: dict[str, Any], ctx: dict[str, Any]) -> str:
    issues = [i for i in result.get("ai_issues") or [] if isinstance(i, dict)]
    out = [
        f"# {ticker} — báo cáo DeepSeek {str(result.get('generated_at', ''))[:10]}",
        "",
        "> Nội dung AI là **giả thuyết chưa kiểm chứng** — chỉ dùng để chỉ ra chỗ cần kiểm tra; số liệu phải đối chiếu DB.",
        "",
        (
            f"- Thị giá: {_num(ctx.get('price'))} · Giá trị hợp lý: {_num(ctx.get('fv'))} · "
            f"Upside: {_num(ctx.get('upside'), '{:+.1f}%')} · Khuyến nghị mô hình: {ctx.get('recommendation') or '—'}"
        ),
        (
            f"- Model: {result.get('model') or '—'} · token vào/ra: {result.get('input_tokens') or '—'}/"
            f"{result.get('output_tokens') or '—'} · trạng thái kiểm chứng: {result.get('status') or '—'} · "
            f"fingerprint: {fingerprint[:12]}"
        ),
        "",
        f"## Nghi vấn dữ liệu ({len(issues)})",
    ]
    out += [
        f"- [{i.get('severity', '?')}] `{i.get('metric', '?')}` ({i.get('period', '?')}): {i.get('finding', '')}"
        + (f" → {i['action']}" if i.get("action") else "")
        for i in issues
    ] or ["- (không có)"]
    cs = result.get("consensus_synthesis") or {}
    for key, title in _CONSENSUS:
        if cs.get(key):
            out += ["", f"## {title}", *_lines(cs[key])]
    sections = result.get("report_sections") or {}
    for key, title in _SECTIONS:
        if sections.get(key):
            out += ["", f"## {title}", str(sections[key]).strip()]
    return "\n".join(out) + "\n"


def journal_report(
    ticker: str,
    fingerprint: str,
    result: dict[str, Any],
    ctx: dict[str, Any] | None = None,
    *,
    root: Path | None = None,
) -> Path | None:
    """Ghi 1 báo cáo; đã có file cùng fingerprint → không ghi lại (idempotent). Trả đường dẫn file."""
    if not result.get("ai_generated") or not result.get("report_sections"):
        return None
    root = root or JOURNAL_DIR
    ctx = ctx or {}
    day = str(result.get("generated_at") or "")[:10] or "unknown"
    path = root / day[:7] / f"{ticker.upper()}_{day}_{fingerprint[:8]}.md"
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown(ticker.upper(), fingerprint, result, ctx), encoding="utf-8")
    issues = [i for i in result.get("ai_issues") or [] if isinstance(i, dict)]
    row = {
        "ticker": ticker.upper(),
        "date": day,
        "fingerprint": fingerprint,
        "file": str(path.relative_to(root)),
        "model": result.get("model"),
        "input_tokens": result.get("input_tokens"),
        "output_tokens": result.get("output_tokens"),
        "status": result.get("status"),
        "price": ctx.get("price"),
        "fv": ctx.get("fv"),
        "upside": ctx.get("upside"),
        "recommendation": ctx.get("recommendation"),
        "issues": [{"severity": i.get("severity"), "metric": i.get("metric")} for i in issues],
    }
    with open(root / "index.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    return path


def backfill(cache_dir: Path, root: Path | None = None) -> list[Path]:
    """Ghi lại các báo cáo trong cache cũ (cache không lưu FV/giá → để trống)."""
    done = []
    for f in sorted(cache_dir.glob("*.json")):
        try:
            saved = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        result = saved.get("result") or {}
        ticker = f.stem.split("_")[1] if f.stem.count("_") >= 2 else ""
        result.setdefault("generated_at", saved.get("saved_at"))
        if ticker and (p := journal_report(ticker, str(saved.get("fingerprint") or f.stem), result, root=root)):
            done.append(p)
    return done


if __name__ == "__main__":
    import sys

    if "--backfill" in sys.argv:
        paths = backfill(PROJECT_ROOT / ".deepseek_report_cache")
        print(f"Đã ghi {len(paths)} báo cáo vào {JOURNAL_DIR}")
