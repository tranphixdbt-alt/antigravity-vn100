"""Dựng PDF "20 cổ phiếu tích sản 1–3 năm" từ data_<ngày>.json + notes_<ngày>.yaml (D93). Chỉ đọc DB.

Chạy sau scripts/collect_top_picks.py:
    ~/.venv/bin/python scripts/build_top_picks_pdf.py 2026-11-11
Ra: reports_pdf/top20/Top20_tich_san_VN100_<ngày>.pdf (+ .html để soát).
"""

from __future__ import annotations

import base64
import datetime as dt
import io
import json
import re
import sqlite3
import statistics
import sys
from pathlib import Path

import jinja2
import matplotlib

matplotlib.use("Agg")
import matplotlib.dates
import matplotlib.pyplot as plt
import matplotlib.ticker
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from valuation.analysis.investment_ranking import load_ranking_config
from valuation.report.build_pdf import build_pdf_report

OUT = ROOT / "reports_pdf" / "top20"
DB = ROOT / "vn100_full.db"
ASSETS = ROOT / "valuation" / "views" / "assets"
GREEN, NAVY, MUTED, LINE, UP, DOWN = (
    "#00843d",
    "#1d4289",
    "#5b6478",
    "#e3e8ee",
    "#089981",
    "#F23645",
)
METHOD = {
    "RI_PB": "Thu nhập thặng dư + P/B (ngân hàng)",
    "DCF": "Chiết khấu dòng tiền (DCF)",
    "EV_EBITDA": "EV/EBITDA so sánh",
    "PE": "P/E so sánh",
}
FLAG_VI = {
    "CORPORATE_ACTION_UNDATED": "sự kiện cổ phiếu chưa có ngày GDKHQ",
    "MINORITY_AT_BOOK_MATERIAL": "lợi ích cổ đông thiểu số tính theo giá sổ",
    "UNEXPLAINED_CURRENT_ASSETS": "tài sản ngắn hạn cần đối chiếu BCTC gốc",
    "FILING_BS_INCOMPLETE": "bảng cân đối một kỳ nạp chưa đủ",
    "FILING_PRECEDENCE": "phải chọn giữa nhiều nguồn BCTC",
    "SOURCE_CONFLICT_IMMATERIAL": "lệch nhỏ giữa các nguồn",
    "CIP_LINE_MISSING": "thiếu dòng xây dựng dở dang",
    "BANK_LEVERAGE_ABOVE_HISTORY": "đòn bẩy cao hơn lịch sử",
    "BANK_ROE_FADE_PLUG": "lợi nhuận dài hạn dựa giả định hội tụ ROE",
}
SECTOR_VI = {"NH": "Ngân hàng", "Dệt may/TS": "Thủy sản"}
POSITIVE = {"MUA", "MUA MẠNH", "KHẢ QUAN", "TĂNG TỶ TRỌNG", "OUTPERFORM", "TÍCH LŨY"}


def vn(x: float | None, d: int = 0) -> str:
    """Số kiểu Việt: 1.234,5."""
    if x is None:
        return "–"
    s = f"{x:,.{d}f}"
    return s.replace(",", "#").replace(".", ",").replace("#", ".")


def pct(x: float | None, d: int = 1, sign: bool = True) -> str:
    if x is None:
        return "–"
    return (f"{x * 100:+.{d}f}" if sign else f"{x * 100:.{d}f}").replace(".", ",") + "%"


def dmy(iso: str | dt.date | None) -> str:
    if not iso:
        return "–"
    d = iso if isinstance(iso, dt.date) else dt.date.fromisoformat(str(iso)[:10])
    return d.strftime("%d/%m/%Y")


def friendly(text: str) -> str:
    """Thay mã cờ kỹ thuật (kèm phần ':...') bằng mô tả tiếng Việt cho người đọc báo cáo."""
    for code, vi in FLAG_VI.items():
        text = re.sub(rf"{code}(:[^,]*)?", vi, text)
    return text


def cash_dividends(
    con: sqlite3.Connection, t: str, as_of: dt.date
) -> list[tuple[str, float]]:
    """Cổ tức tiền có GDKHQ trong 365 ngày TRƯỚC ngày báo cáo; bỏ bản trùng (cùng ngày, cùng số tiền)."""
    rows = con.execute(
        "select ex_right_date, cash_amount_vnd_per_share from corporate_actions where ticker=? and "
        "event_type='CASH_DIVIDEND' and cash_amount_vnd_per_share is not null and ex_right_date > ? "
        "and ex_right_date < ? order by ex_right_date",
        (t, (as_of - dt.timedelta(days=365)).isoformat(), as_of.isoformat()),
    ).fetchall()
    return sorted({(str(d)[:10], float(a)) for d, a in rows})


def chart_svg(
    con: sqlite3.Connection,
    t: str,
    end: str,
    lines: dict[str, float | None],
    zone: float,
) -> str:
    start = (dt.date.fromisoformat(end) - dt.timedelta(days=365)).isoformat()
    px = con.execute(
        "select trade_date, close from prices_daily where ticker=? and trade_date between ? and ? "
        "and close is not null order by trade_date",
        (t, start, end),
    ).fetchall()
    fl = con.execute(
        "select trade_date, fr_net_match_val from flow_daily where ticker=? and trade_date between ? and ? "
        "order by trade_date",
        (t, start, end),
    ).fetchall()
    dates = [dt.date.fromisoformat(str(d)[:10]) for d, _ in px]
    close = [float(c) for _, c in px]
    plt.rcParams.update(
        {"font.family": "Arial", "font.size": 7.5, "svg.fonttype": "path"}
    )
    fig, (ax, bx) = plt.subplots(
        2,
        1,
        figsize=(7.1, 3.5),
        sharex=True,
        gridspec_kw={"height_ratios": [3, 1.1], "hspace": 0.08},
    )
    lo = min(close + [v for v in lines.values() if v] + [zone]) * 0.92
    ax.axhspan(lo, zone, color=GREEN, alpha=0.07, lw=0)
    ax.plot(dates, close, color=NAVY, lw=1.4)
    styles = {"Giá trị mô hình": (GREEN, "--"), "Trung vị CTCK": ("#b26b00", ":")}
    for label, val in lines.items():
        if val:
            c, ls = styles[label]
            ax.axhline(val, color=c, ls=ls, lw=1.1)
            ax.text(
                dates[-1],
                val,
                f" {label} {vn(val)}",
                color=c,
                va="bottom",
                ha="right",
                fontsize=7,
            )
    ax.text(
        dates[0],
        lo,
        f" Vùng gom ≤ {vn(zone)}",
        color=GREEN,
        va="bottom",
        ha="left",
        fontsize=7,
    )
    ax.set_ylim(bottom=lo)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: vn(v)))
    if fl:
        fd = [dt.date.fromisoformat(str(d)[:10]) for d, _ in fl]
        cum, run = [], 0.0
        for _, v in fl:
            run += float(v or 0) / 1e9
            cum.append(run)
        bx.fill_between(
            fd,
            cum,
            0,
            where=[c >= 0 for c in cum],
            color=UP,
            alpha=0.35,
            lw=0,
            interpolate=True,
        )
        bx.fill_between(
            fd,
            cum,
            0,
            where=[c < 0 for c in cum],
            color=DOWN,
            alpha=0.35,
            lw=0,
            interpolate=True,
        )
        bx.plot(fd, cum, color="#333", lw=0.8)
        bx.axhline(0, color="#999", lw=0.5)
        bx.set_ylabel("Ngoại lũy kế\n(tỷ, khớp)", fontsize=6.5, color=MUTED)
    for a in (ax, bx):
        for s in ("top", "right"):
            a.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            a.spines[s].set_color("#c9d1da")
        a.tick_params(colors=MUTED, length=2)
        a.grid(axis="y", color="#eef1f4", lw=0.6)
    bx.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%m/%y"))
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return (
        "<svg" + buf.getvalue().split("<svg", 1)[1]
    )  # bỏ phần khai báo XML để nhúng thẳng vào HTML


def build(as_of: dt.date) -> Path:
    data = json.loads(
        (OUT / f"data_{as_of.isoformat()}.json").read_text(encoding="utf-8")
    )
    notes = yaml.safe_load(
        (OUT / f"notes_{as_of.isoformat()}.yaml").read_text(encoding="utf-8")
    )
    min_mos = float(load_ranking_config()["profiles"]["growth"]["min_mos"])
    rows = {r["ticker"]: r for r in data["rows"]}
    con = sqlite3.connect(DB)
    picks = []
    for rank, t in enumerate(data["picks"], 1):
        r, cs, fl, note = (
            rows[t],
            data["consensus"][t],
            data["flows"].get(t, {}),
            notes[t],
        )
        price, fv, med = r["price"], r["fair_value"], cs.get("median")
        ref = min(fv, med) if med else fv
        zone = ref * (1 - min_mos)
        divs = cash_dividends(con, t, as_of)
        div_sum = sum(a for _, a in divs)
        sc = r.get("scenarios") or {}
        single = sc.get("Bear") == sc.get("Bull")
        m = r["metrics"]
        pos = sum(
            1 for q in cs["quotes"] if (q.get("rating") or "").upper() in POSITIVE
        )
        f20, f60 = fl["flows"]["20"]["loai"], fl["flows"]["60"]["loai"]
        vf, vp = fl["votes"]["foreign"], fl["votes"]["pv"]
        conf = r["confidence"]
        valuation_pts = [
            f"Phương pháp: {METHOD.get(r['method'], r['method'])}. Giá trị cơ sở {vn(fv)} đ/cp"
            + (
                " (một kịch bản)."
                if single
                else f" (xấu {vn(sc.get('Bear'))} – tốt {vn(sc.get('Bull'))})."
            ),
            (
                f"Trung vị {cs['count']} CTCK trong 180 ngày: {vn(med)} đ/cp ({pct(med / price - 1)} so với giá), "
                f"khoảng {vn(cs['min'])}–{vn(cs['max'])}; {pos}/{cs['count']} khuyến nghị tích cực."
                if med
                else "Chưa có giá mục tiêu CTCK trong 180 ngày để đối chiếu."
            ),
            f"Năm 2025: ROE {pct(m.get('roe'), 1, False)}, tăng trưởng "
            + ("thu nhập hoạt động" if r.get("is_bank") else "doanh thu")
            + f" 3 năm {pct(m.get('revenue_cagr'))}/năm"
            + (
                f", nợ vay/VCSH {vn(m['debt_to_equity'], 2)} lần"
                if m.get("debt_to_equity") is not None
                else ""
            )
            + (
                f", dòng tiền KD/lãi ròng {vn(m['cash_conversion'], 2)} lần"
                if m.get("cash_conversion") is not None
                else ""
            )
            + ".",
        ]
        flow_pts = [
            (
                f"{fl['label']['text']}: khối ngoại ròng {pct(vf.get('value'))} giá trị giao dịch 20 phiên "
                f"({vf.get('pos')} phiên mua, {vf.get('neg')} phiên bán); chỉ báo giá–khối lượng CMF20 "
                f"{vn(vp.get('value'), 2) if vp.get('value') is not None else '–'}."
            ),
            (
                f"Khối ngoại ròng (khớp lệnh): 20 phiên {vn(f20['f'] / 1e9, 1)} tỷ · 60 phiên "
                f"{vn(f60['f'] / 1e9, 1)} tỷ; tự doanh 20 phiên {vn(f20['p'] / 1e9, 1)} tỷ."
            ),
            f"Giá 20 phiên {pct(fl.get('ret20'))}; giao dịch bình quân {vn((m.get('avg_traded_value') or 0) / 1e9, 1)} tỷ/phiên.",
        ]
        picks.append(
            {
                "rank": rank,
                "t": t,
                "name": note["name"],
                "sector": note["sector"],
                "score": r["composite"],
                "grade": conf["grade"],
                "criteria": [
                    (ok, friendly(text)) for ok, text in conf["criteria"].values()
                ],
                "price": price,
                "fv": fv,
                "med": med,
                "n": cs["count"],
                "ref": ref,
                "zone": zone,
                "up_model": r["upside_pct"] / 100,
                "up_ref": ref / price - 1,
                "in_zone": price <= zone,
                "div_sum": div_sum,
                "div_yield": div_sum / price if price else None,
                "divs": divs,
                "flow_label": fl["label"]["text"],
                "flow_code": fl["label"]["code"],
                "valuation_pts": valuation_pts,
                "flow_pts": flow_pts,
                "thesis": note["thesis"],
                "risks": note["risks"],
                "period": r.get("financial_period"),
                "chart": chart_svg(
                    con,
                    t,
                    r["price_date"],
                    {"Giá trị mô hình": fv, "Trung vị CTCK": med},
                    zone,
                ),
            }
        )
    con.close()
    excluded: dict[str, int] = {}
    for r in data["rows"]:
        if r["excluded"]:
            key = r["excluded"].split(":")[0]
            excluded[key] = excluded.get(key, 0) + 1
    grades = {g: [p["t"] for p in picks if p["grade"] == g] for g in "ABC"}
    by_flow: dict[str, list[str]] = {}
    for p in picks:
        by_flow.setdefault(p["flow_label"], []).append(p["t"])
    sectors: dict[str, int] = {}
    for t in data["picks"]:
        sec = SECTOR_VI.get(rows[t]["sector"], rows[t]["sector"])
        sectors[sec] = sectors.get(sec, 0) + 1
    ups = [p["up_ref"] for p in picks]
    top_div = sorted(
        (p for p in picks if p["div_yield"]), key=lambda p: -p["div_yield"]
    )[:4]
    font = {
        w: base64.b64encode((ASSETS / f"manrope-{w}.woff2").read_bytes()).decode()
        for w in (400, 700)
    }
    price_date = rows[data["picks"][0]]["price_date"]
    html = (
        jinja2.Environment(autoescape=True)
        .from_string(TEMPLATE)
        .render(
            picks=picks,
            as_of=dmy(as_of),
            price_date=dmy(price_date),
            flow_date=dmy(data["flow_meta"]["flow_date"]),
            n_rows=len(data["rows"]),
            n_ok=sum(1 for r in data["rows"] if not r["excluded"]),
            excluded=sorted(excluded.items(), key=lambda kv: -kv[1]),
            grades=grades,
            by_flow=by_flow,
            sectors=sorted(sectors.items(), key=lambda kv: -kv[1]),
            up_med=statistics.median(ups),
            up_min=min(ups),
            up_max=max(ups),
            top_div=top_div,
            min_mos=min_mos,
            font=font,
            max_per_sector=data["max_per_sector"],
            vn=vn,
            pct=pct,
            dmy=dmy,
        )
    )
    html_path = OUT / f"Top20_tich_san_VN100_{as_of.isoformat()}.html"
    html_path.write_text(html, encoding="utf-8")
    pdf_path = html_path.with_suffix(".pdf")
    if not build_pdf_report(html, str(pdf_path)):
        raise RuntimeError("Không xuất được PDF")
    return pdf_path


TEMPLATE = r"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<style>
@font-face{font-family:Manrope;font-weight:400;src:url(data:font/woff2;base64,{{font[400]}}) format('woff2')}
@font-face{font-family:Manrope;font-weight:700;src:url(data:font/woff2;base64,{{font[700]}}) format('woff2')}
@page{size:A4;margin:0}
*{box-sizing:border-box}
body{margin:0;font-family:Manrope,Arial,sans-serif;color:#1f2a44;font-size:9.6pt;line-height:1.45;-webkit-print-color-adjust:exact;print-color-adjust:exact}
.page{width:210mm;height:297mm;padding:13mm 14mm 12mm;position:relative;overflow:hidden;page-break-after:always}
.page:last-child{page-break-after:auto}
.kicker{color:#00843d;font-weight:700;font-size:8pt;letter-spacing:.06em;text-transform:uppercase}
h1{font-size:23pt;line-height:1.2;margin:4mm 0 2mm;color:#1f2a44}
h2{font-size:12.5pt;margin:5mm 0 2mm;color:#1f2a44;border-bottom:1.5px solid #00843d;padding-bottom:1mm}
h3{font-size:10pt;margin:3mm 0 1.2mm;color:#1d4289;text-transform:uppercase;letter-spacing:.03em}
.sub{color:#5b6478;font-size:10.5pt;margin:0 0 4mm}
.tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:3mm;margin:3mm 0}
.tile{background:#f5f8f7;border-radius:2mm;padding:3mm}
.tile .l{color:#5b6478;font-size:7.8pt}.tile .v{font-size:14pt;font-weight:700;color:#00843d;line-height:1.25}.tile .s{font-size:7.5pt;color:#5b6478}
ul{margin:1mm 0;padding-left:4.5mm}li{margin:0 0 1.1mm}
ol{margin:1mm 0;padding-left:5mm}
.box{border:1px solid #e3e8ee;border-radius:2mm;padding:3mm 4mm;margin-top:3mm}
.warn{background:#fff8e6;border-color:#f0d9a0;font-size:8.2pt;color:#5a4a1a}
table{border-collapse:collapse;width:100%}
.list th{background:#1d4289;color:#fff;font-size:7.6pt;font-weight:700;padding:1.6mm 1.3mm;text-align:right}
.list td{font-size:8.1pt;padding:.75mm 1.3mm;border-bottom:1px solid #e3e8ee;text-align:right;white-space:nowrap}
.list td.l,.list th.l{text-align:left}.list tr:nth-child(even) td{background:#f8fafb}
.list .tk{font-weight:700;font-size:8.8pt}.list .sec{color:#5b6478;font-size:6.6pt;line-height:1.15;white-space:normal}
.g{display:inline-block;min-width:5.5mm;text-align:center;border-radius:1mm;font-weight:700;font-size:8pt;padding:.3mm 1.2mm}
.gA{background:#e6f4ec;color:#0f7b3e}.gB{background:#fff1cc;color:#8a5a00}.gC{background:#fde8e7;color:#b42318}
.pos{color:#0f7b3e}.neg{color:#b42318}
.fl-gom{color:#0f7b3e;font-weight:700}.fl-xa{color:#b42318;font-weight:700}
.legend td{font-size:8.2pt;padding:1.2mm 2mm;border-bottom:1px solid #e3e8ee;vertical-align:top}
.head{display:flex;justify-content:space-between;align-items:flex-start;border-bottom:2px solid #00843d;padding-bottom:2.5mm}
.rank{display:inline-flex;align-items:center;justify-content:center;width:11mm;height:11mm;border-radius:50%;background:#00843d;color:#fff;font-weight:700;font-size:11pt;margin-right:3mm;vertical-align:middle}
.tkr{font-size:22pt;font-weight:700;vertical-align:middle}
.nm{font-size:9.5pt;color:#5b6478;margin-top:1mm}
.badge{text-align:right}.badge .g{font-size:12pt;padding:1mm 3mm}.badge .sc{font-size:8pt;color:#5b6478;margin-top:1mm}
.kpi{display:grid;grid-template-columns:repeat(4,1fr);gap:0;margin:3mm 0 2mm;border:1px solid #e3e8ee;border-radius:2mm;overflow:hidden}
.kpi>div{padding:2mm 2.5mm;border-right:1px solid #e3e8ee;border-bottom:1px solid #e3e8ee}
.kpi>div:nth-child(4n){border-right:0}.kpi>div:nth-child(n+5){border-bottom:0}
.kpi .l{font-size:7.2pt;color:#5b6478}.kpi .v{font-size:11.5pt;font-weight:700}.kpi .s{font-size:7pt;color:#5b6478}
.chart svg{width:100%;height:auto;display:block}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:5mm}
.cols ul{font-size:8.6pt}
.crit{display:grid;grid-template-columns:1fr 1fr;gap:1mm 5mm;font-size:8pt}
.ok{color:#0f7b3e;font-weight:700}.no{color:#b42318;font-weight:700}
.verdict{background:#f5f8f7;border-left:3px solid #00843d;padding:2mm 3mm;font-size:9pt;margin-top:2.5mm}
.foot{position:absolute;left:14mm;right:14mm;bottom:6mm;font-size:6.8pt;color:#8a93a6;display:flex;justify-content:space-between;border-top:1px solid #e3e8ee;padding-top:1.5mm}
</style></head><body>

<section class="page">
  <div class="kicker">Báo cáo nội bộ · {{as_of}} · Hệ thống định giá VN100</div>
  <h1>20 cổ phiếu tích sản 1–3 năm</h1>
  <p class="sub">Chọn từ rổ VN100 bằng mô hình định giá nội bộ, đối chiếu đồng thuận công ty chứng khoán (CTCK) và dòng tiền. Phương pháp tích sản: mua dần, nắm giữ, rà soát mỗi quý.</p>
  <div class="tiles">
    <div class="tile"><div class="l">Danh sách</div><div class="v">20 mã</div><div class="s">{{sectors|length}} ngành · tối đa {{max_per_sector}} mã/ngành</div></div>
    <div class="tile"><div class="l">Tiềm năng theo giá thận trọng*</div><div class="v">{{pct(up_med,0)}}</div><div class="s">trung vị · từ {{pct(up_min,0)}} đến {{pct(up_max,0)}}</div></div>
    <div class="tile"><div class="l">Độ tin cậy</div><div class="v">{{grades.A|length}} A · {{grades.B|length}} B · {{grades.C|length}} C</div><div class="s">A = mô hình khớp đồng thuận CTCK</div></div>
    <div class="tile"><div class="l">Dữ liệu</div><div class="v" style="font-size:11pt">Giá {{price_date}}</div><div class="s">Dòng tiền {{flow_date}} · BCTC quý 3/2026</div></div>
  </div>
  <h2>Điểm chính</h2>
  <ul>
    <li><b>Độ tin cậy cao (A): {{grades.A|join(", ")}}.</b> Giá trị mô hình nằm trong ±20% đồng thuận CTCK, đủ người theo dõi, dữ liệu sạch.</li>
    <li><b>Cần thận trọng hơn (C): {{grades.C|join(", ")}}</b> — ít hoặc không có CTCK theo dõi, có cờ dữ liệu; chỉ nên tỷ trọng nhỏ sau khi tự kiểm chứng.</li>
    <li><b>Dòng tiền 20 phiên:</b> {% for k,v in by_flow.items() %}{{k}} ({{v|length}}): {{v|join(", ")}}{% if not loop.last %}; {% endif %}{% endfor %}. Dòng tiền là tín hiệu ngắn hạn — với tích sản 1–3 năm, giai đoạn bị bán ròng thường là lúc gom được giá tốt hơn.</li>
    <li><b>Cổ tức tiền 12 tháng cao nhất:</b> {% for p in top_div %}{{p.t}} {{pct(p.div_yield,1,False)}}{% if not loop.last %}, {% endif %}{% endfor %} — phù hợp phần danh mục ưu tiên dòng tiền.</li>
    <li><b>Cơ cấu ngành:</b> {% for s,n in sectors %}{{s}} {{n}}{% if not loop.last %} · {% endif %}{% endfor %}.</li>
  </ul>
  <h2>Cách chọn</h2>
  <ol>
    <li>Định giá lại toàn bộ {{n_rows}} mã VN100 ngày {{as_of}} bằng mô hình nội bộ (theo ngành: DCF, thu nhập thặng dư cho ngân hàng, P/E, EV/EBITDA) với BCTC mới nhất.</li>
    <li>Loại mã không đủ điều kiện: {% for k,n in excluded %}{{k}} ({{n}}){% if not loop.last %}, {% endif %}{% endfor %}. Còn {{n_ok}} mã.</li>
    <li>Xếp theo điểm tích sản của hệ thống (trung bình hồ sơ "thận trọng" và "tăng trưởng": biên an toàn định giá, chất lượng ROE/tăng trưởng, sức khỏe tài chính, dòng tiền ngoại), lấy 20 mã điểm cao nhất.</li>
    <li>Gắn độ tin cậy A/B/C cho từng mã theo 4 tiêu chí công khai (bảng dưới).</li>
  </ol>
  <h2>Đọc độ tin cậy</h2>
  <table class="legend">
    <tr><td><b>Đồng thuận</b></td><td>Giá trị mô hình lệch trung vị giá mục tiêu CTCK (180 ngày) không quá 20%.</td></tr>
    <tr><td><b>Độ phủ</b></td><td>Có ít nhất 3 CTCK theo dõi trong 180 ngày.</td></tr>
    <tr><td><b>Dữ liệu sạch</b></td><td>Không có cờ cảnh báo dữ liệu đầu vào của hệ thống.</td></tr>
    <tr><td><b>Kịch bản hẹp</b></td><td>Khoảng giá trị kịch bản xấu–tốt không quá 40% giá trị cơ sở.</td></tr>
    <tr><td colspan="2"><span class="g gA">A</span> đạt ≥3 tiêu chí, trong đó có Đồng thuận · <span class="g gB">B</span> đạt ≥2 · <span class="g gC">C</span> còn lại</td></tr>
  </table>
  <div class="box warn">*<b>Giá tham chiếu thận trọng</b> = giá trị thấp hơn giữa mô hình nội bộ và trung vị CTCK; <b>vùng gom</b> = giá tham chiếu × (1 − {{pct(min_mos,0,False)}}), tức còn biên an toàn {{pct(min_mos,0,False)}}.
  <b>Lưu ý:</b> báo cáo tổng hợp tự động từ dữ liệu quá khứ và mô hình nội bộ, <b>không phải khuyến nghị đầu tư</b>; giá trị mô hình có thể sai. Toàn bộ BCTC quý 3/2026 mới nạp chưa đối chiếu lại với nguồn gốc, và hồ sơ quản trị/lợi thế cạnh tranh chưa được kiểm chứng — hệ thống chưa xếp mã nào vào nhóm "đạt chuẩn đầy đủ". Cổ phiếu có thể giảm giá, kể cả mã độ tin cậy A.</div>
  <div class="foot"><span>Nguồn: DB nội bộ (giá VCI, dòng tiền VCI flow_daily, BCTC, giá mục tiêu CTCK) · Không phải khuyến nghị đầu tư</span><span>1</span></div>
</section>

<section class="page">
  <div class="kicker">Danh sách</div>
  <h1 style="font-size:17pt;margin:2mm 0 3mm">20 mã xếp theo điểm tích sản</h1>
  <table class="list">
    <tr><th>#</th><th class="l">Mã · ngành</th><th>Giá<br>{{price_date[:5]}}</th><th>Giá trị<br>mô hình</th><th>Trung vị<br>CTCK (n)</th><th>Tiềm năng<br>thận trọng*</th><th>Vùng gom<br>≤</th><th>Cổ tức<br>12T</th><th class="l">Dòng tiền<br>20 phiên</th><th>Điểm</th><th>Tin<br>cậy</th></tr>
    {% for p in picks %}
    <tr>
      <td>{{p.rank}}</td>
      <td class="l"><span class="tk">{{p.t}}</span><div class="sec">{{p.sector}}</div></td>
      <td>{{vn(p.price)}}</td><td>{{vn(p.fv)}}</td>
      <td>{% if p.med %}{{vn(p.med)}} ({{p.n}}){% else %}–{% endif %}</td>
      <td class="{{'pos' if p.up_ref>0 else 'neg'}}"><b>{{pct(p.up_ref,0)}}</b></td>
      <td>{{vn(p.zone)}}{% if p.in_zone %} ✓{% endif %}</td>
      <td>{% if p.div_yield %}{{pct(p.div_yield,1,False)}}{% else %}–{% endif %}</td>
      <td class="l {{'fl-gom' if p.flow_code in ('gom','noi_gom') else ('fl-xa' if p.flow_code in ('xa','noi_xa') else '')}}">{{p.flow_label}}</td>
      <td>{{vn(p.score,0)}}</td><td><span class="g g{{p.grade}}">{{p.grade}}</span></td>
    </tr>
    {% endfor %}
  </table>
  <div class="box" style="font-size:8pt;color:#5b6478">
    <b>Cách đọc:</b> Giá, giá trị và vùng gom tính bằng đồng/cổ phiếu. <b>Tiềm năng thận trọng</b> = giá tham chiếu thận trọng ÷ giá − 1. <b>Vùng gom ≤</b>: giá tham chiếu thận trọng trừ biên an toàn {{pct(min_mos,0,False)}}; dấu ✓ = giá hiện tại đã ở trong vùng. <b>Cổ tức 12T</b>: cổ tức tiền có ngày GDKHQ trong 12 tháng trước ngày báo cáo ÷ giá. <b>Dòng tiền 20 phiên</b>: nhãn của hệ thống từ khối ngoại, tự doanh và quan hệ giá–khối lượng (CMF20). <b>Điểm</b>: điểm tích sản 0–100 của hệ thống, chuẩn hóa theo phần có dữ liệu.
  </div>
  <div class="box" style="font-size:8pt">
    <b>Gợi ý quy trình tích sản (không phải khuyến nghị):</b> giải ngân dần theo nhiều đợt thay vì mua một lần; ưu tiên mua khi giá ở trong hoặc gần vùng gom; mã độ tin cậy C nên giữ tỷ trọng nhỏ; rà soát lại toàn bộ danh sách sau mỗi mùa BCTC quý, loại mã khi giá vượt giá tham chiếu hoặc luận điểm thay đổi.
  </div>
  <div class="foot"><span>Giá đóng cửa {{price_date}} · Đồng thuận CTCK 180 ngày, mỗi CTCK lấy báo cáo mới nhất · Không phải khuyến nghị đầu tư</span><span>2</span></div>
</section>

{% for p in picks %}
<section class="page">
  <div class="head">
    <div><span class="rank">{{p.rank}}</span><span class="tkr">{{p.t}}</span>
      <div class="nm">{{p.name}} · {{p.sector}}</div></div>
    <div class="badge"><span class="g g{{p.grade}}">Độ tin cậy {{p.grade}}</span><div class="sc">Điểm tích sản {{vn(p.score,0)}}/100 · hạng {{p.rank}}/20</div></div>
  </div>
  <div class="kpi">
    <div><div class="l">Giá {{price_date}}</div><div class="v">{{vn(p.price)}}</div><div class="s">đồng/cổ phiếu</div></div>
    <div><div class="l">Giá trị mô hình</div><div class="v">{{vn(p.fv)}}</div><div class="s">{{pct(p.up_model,0)}} so với giá</div></div>
    <div><div class="l">Trung vị CTCK</div><div class="v">{% if p.med %}{{vn(p.med)}}{% else %}–{% endif %}</div><div class="s">{% if p.med %}{{p.n}} CTCK · {{pct(p.med/p.price-1,0)}}{% else %}chưa có CTCK theo dõi{% endif %}</div></div>
    <div><div class="l">Tiềm năng thận trọng</div><div class="v {{'pos' if p.up_ref>0 else 'neg'}}">{{pct(p.up_ref,0)}}</div><div class="s">tới {{vn(p.ref)}}</div></div>
    <div><div class="l">Vùng gom tham khảo</div><div class="v">≤ {{vn(p.zone)}}</div><div class="s">{% if p.in_zone %}giá hiện tại đã trong vùng{% else %}cách giá hiện tại {{pct(p.zone/p.price-1,0)}}{% endif %}</div></div>
    <div><div class="l">Cổ tức tiền 12 tháng</div><div class="v">{% if p.div_sum %}{{vn(p.div_sum)}} đ{% else %}–{% endif %}</div><div class="s">{% if p.div_yield %}lợi suất {{pct(p.div_yield,1,False)}}{% else %}không trả tiền trong 12 tháng{% endif %}</div></div>
    <div><div class="l">Dòng tiền 20 phiên</div><div class="v {{'fl-gom' if p.flow_code in ('gom','noi_gom') else ('fl-xa' if p.flow_code in ('xa','noi_xa') else '')}}" style="font-size:10pt">{{p.flow_label}}</div><div class="s">khối ngoại, tự doanh, CMF20</div></div>
    <div><div class="l">Kỳ BCTC dùng</div><div class="v" style="font-size:10pt">{{p.period}}</div><div class="s">chỉ số năm: 2025</div></div>
  </div>
  <div class="chart">{{p.chart|safe}}</div>
  <div class="cols">
    <div>
      <h3>Định giá</h3><ul>{% for x in p.valuation_pts %}<li>{{x}}</li>{% endfor %}</ul>
      <h3>Dòng tiền</h3><ul>{% for x in p.flow_pts %}<li>{{x}}</li>{% endfor %}</ul>
    </div>
    <div>
      <h3>Tiềm năng 1–3 năm</h3><ul>{% for x in p.thesis %}<li>{{x}}</li>{% endfor %}</ul>
      <h3>Rủi ro cần theo dõi</h3><ul>{% for x in p.risks %}<li>{{x}}</li>{% endfor %}</ul>
    </div>
  </div>
  <div class="verdict"><b>Độ tin cậy {{p.grade}}</b> — <span class="crit" style="display:inline">{% for ok,text in p.criteria %}<span class="{{'ok' if ok else 'no'}}">{{'✓' if ok else '✗'}}</span> {{text}}{% if not loop.last %} · {% endif %}{% endfor %}</span></div>
  <div class="foot"><span>Biểu đồ: giá 12 tháng (VCI, đã điều chỉnh) · nền xanh = vùng gom · dưới: khối ngoại ròng khớp lệnh lũy kế · Không phải khuyến nghị đầu tư</span><span>{{p.rank + 2}}</span></div>
</section>
{% endfor %}
</body></html>
"""


if __name__ == "__main__":
    day = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else dt.date.today()
    print(build(day))
