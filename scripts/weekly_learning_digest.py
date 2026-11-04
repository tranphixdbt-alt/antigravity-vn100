"""Tạo bản tóm tắt tuần cho vòng học (docs/PLAN_LEARNING_LOOP.md). Không gọi AI, chỉ ĐỌC DB.

  python scripts/weekly_learning_digest.py                 # đầy đủ (~5–8 phút: định giá 100 mã + dòng tiền)
  python scripts/weekly_learning_digest.py --no-flow       # bỏ kiểm chứng dòng tiền
  python scripts/weekly_learning_digest.py --no-valuation  # bỏ định giá lại (dùng khi thử)

Lịch: Chủ nhật 18:00 giờ VN (launchd trên Mac / systemd trên VPS), trước routine Claude cloud 20:00.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from valuation.services import learning_digest as ld

logging.disable(logging.WARNING)


def _valuation(db, today: dt.date) -> list[dict]:
    from valuation.engine.batch import value_ticker
    from valuation.engine.consensus_helper import get_consensus_stats
    from valuation.ingest.universe import get_vn100_symbols

    rows = []
    for t in get_vn100_symbols():
        r = value_ticker(db, t)
        cons = get_consensus_stats(t, today, db) or {}
        rows.append({
            "ticker": t, "group": r.get("group"), "method": r.get("method"),
            "published": r.get("fair_value") is not None and not r.get("error"),
            "synth": "BROKER_SYNTHESIZED" in (r.get("flags") or []),
            "fv": r.get("fair_value"), "price": r.get("price"),
            "cons_median": cons.get("median"), "cons_n": cons.get("count") or 0, "error": r.get("error"),
        })
    return rows


def _ctck_lines(db, today: dt.date) -> dict:
    from sqlalchemy import text

    since = (today - dt.timedelta(days=7)).isoformat()
    new = db.execute(text(
        "SELECT ticker, COALESCE(broker_canon, broker) b, report_date, target_price FROM consensus_history "
        "WHERE report_date >= :s AND target_price IS NOT NULL ORDER BY ticker, report_date"), {"s": since}).fetchall()
    lines = []
    for t, b, d, tp in new[:30]:
        prev = db.execute(text(
            "SELECT target_price FROM consensus_history WHERE ticker=:t AND COALESCE(broker_canon, broker)=:b "
            "AND report_date < :d AND target_price IS NOT NULL ORDER BY report_date DESC LIMIT 1"),
            {"t": t, "b": b, "d": d}).scalar()
        lines.append(f"{t} · {b} · {str(d)[:10]}: {float(tp):,.0f}" + (f" (trước {float(prev):,.0f})" if prev else " (lần đầu)"))
    return {"n_new": len(new), "lines": lines}


def _flow(db, today: dt.date) -> tuple[dict, pd.DataFrame]:
    from valuation.config import load_defaults
    from valuation.views.market_overview import sector_map
    from valuation.views.money_flow import load_flow_panel

    cfg = load_defaults()["money_flow"]
    days = (today - ld.FLOW_BACKTEST_START).days + int(cfg["history_days"]) + 30
    panel = load_flow_panel(db, cfg, days=days)
    prices = panel["prices"].reset_index(drop=True)
    pdates = sorted(set(pd.to_datetime(prices["trade_date"]).dt.date))
    dates = ld.week_ends(pdates, ld.FLOW_BACKTEST_START, pdates[-1])
    cache_path = ld.KNOWLEDGE / "flow_backtest_labels.csv"
    cache = pd.read_csv(cache_path) if cache_path.exists() else pd.DataFrame(columns=["date"])
    # Tuần cuối luôn tính lại (dữ liệu tuần đó có thể vừa bổ sung); tuần cũ dùng bộ nhớ đệm.
    keep = cache[cache["date"].isin([d.isoformat() for d in dates[:-1]])]
    todo = [d for d in dates if d.isoformat() not in set(keep["date"])]
    labels = pd.concat([keep, ld.compute_flow_labels(panel, sector_map(), cfg, todo)], ignore_index=True)
    labels = labels.sort_values(["date", "ticker"]).reset_index(drop=True)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    labels.to_csv(cache_path, index=False)
    close = ld.close_matrix(prices)
    events = ld.attach_forward_returns(labels, close)
    stats = ld.label_stats(events)
    last = labels[labels["date"] == dates[-1].isoformat()]
    info = {
        "dist": ", ".join(f"{k} {v}" for k, v in Counter(last["label"]).most_common()),
        "single": ", ".join(sorted(last.loc[last["single_session"].astype(bool), "ticker"])),
        "n_weeks": len(dates), "range": f"{dates[0].isoformat()} → {dates[-1].isoformat()}",
        "stats": stats.to_dict("records"),
    }
    return info, stats


def _proposals() -> list[str]:
    out = []
    for f in sorted((ld.KNOWLEDGE / "proposals").glob("*.md")):
        if ".prev" in f.name:
            continue
        heads = [ln.lstrip("#").strip() for ln in f.read_text(encoding="utf-8").splitlines() if ln.startswith("### ")]
        out.append(f"{f.stem}: " + (" | ".join(heads[:3]) or "(không đọc được tiêu đề)"))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-flow", action="store_true")
    ap.add_argument("--no-valuation", action="store_true")
    args = ap.parse_args()

    from valuation.db.session import SessionLocalRead

    today = dt.datetime.now(ld.VN).date()
    week = ld.iso_week(today)
    out_dir = ld.KNOWLEDGE / "weekly"
    out_dir.mkdir(parents=True, exist_ok=True)
    db = SessionLocalRead()
    try:
        rows = [] if args.no_valuation else _valuation(db, today)
        val = ld.valuation_summary(rows)
        if rows:
            vdf = pd.DataFrame(rows)
            vdf["dev"] = vdf["fv"] / vdf["cons_median"] - 1
            vdf.to_csv(out_dir / f"{week}_valuation.csv", index=False)
            hist_path = ld.KNOWLEDGE / "fv_history.csv"
            hist = pd.read_csv(hist_path) if hist_path.exists() else pd.DataFrame()
            if len(hist):
                hist = hist[hist["week"] != week]  # chạy lại cùng tuần → thay, không nhân đôi
            cur = vdf[["ticker", "method", "synth", "published", "fv", "price", "cons_median", "cons_n"]].assign(
                date=today.isoformat(), week=week)
            pd.concat([hist, cur], ignore_index=True).to_csv(hist_path, index=False)
            (out_dir / f"{week}_summary.json").write_text(json.dumps(val, ensure_ascii=False, default=str), encoding="utf-8")
        prev = sorted(p for p in out_dir.glob("*_summary.json") if not p.name.startswith(week))
        prev_val = json.loads(prev[-1].read_text(encoding="utf-8")) if prev else None
        pub = [r for r in rows if r["published"] and r["cons_median"] and r["cons_n"] >= 2]
        top = sorted(pub, key=lambda r: -abs(r["fv"] / r["cons_median"] - 1))[:10]
        top_dev = [{**r, "dev": r["fv"] / r["cons_median"] - 1,
                    "kind": "BROKER_SYNTH" if r["synth"] else r.get("method") or "?"} for r in top]
        index = ld.read_index(ld.KNOWLEDGE / "ai_reports" / "index.jsonl")
        ai = {"n_week": sum(1 for r in index if str(r.get("date", "")) >= (today - dt.timedelta(days=7)).isoformat()),
              "n_total": len(index), "top": ld.ai_issue_counts(index).most_common(12)}
        ctck = _ctck_lines(db, today)
        if args.no_flow:
            flow = {"dist": "(bỏ qua)", "single": "", "n_weeks": 0, "range": "—", "stats": []}
        else:
            flow, stats = _flow(db, today)
            stats.to_csv(out_dir / f"{week}_flow_stats.csv", index=False)
    finally:
        db.close()
    md = ld.render_digest(week, today, val, prev_val, top_dev, ai, ctck, flow, _proposals())
    (out_dir / f"{week}.md").write_text(md, encoding="utf-8")
    print(f"Đã ghi {out_dir / f'{week}.md'} ({len(md.splitlines())} dòng)")
    _mirror()


def _mirror() -> None:
    from valuation.config import load_defaults

    mirror = (load_defaults().get("learning") or {}).get("knowledge_mirror_dir")
    if not mirror:
        return
    dst = Path(mirror).expanduser()
    if not dst.parent.is_dir():
        print(f"Bỏ qua chép knowledge: không thấy {dst.parent} (máy không gắn Google Drive)")
        return
    print(f"Đã chép {ld.mirror_knowledge(ld.KNOWLEDGE, dst)} file knowledge sang {dst}")


if __name__ == "__main__":
    main()
