"""Job nạp flow_daily từ VCI (B1, D73). Mặc định kéo lại incremental_lookback_days ngày.

    ~/.venv/bin/python scripts/update_flow_daily.py --dry-run --tickers MCH FPT
    ~/.venv/bin/python scripts/update_flow_daily.py --backfill   # lần đầu: backfill_days
    ~/.venv/bin/python scripts/update_flow_daily.py              # hằng ngày, sau 17:30 giờ VN

--dry-run vẫn gọi VCI (tốn quota) nhưng không ghi DB lẫn status.json.

Mã thoát: 0 ổn · 1 có mã lỗi (mạng, VCI trả rỗng) · 2 chưa có bảng · 3 job khác giữ khóa ·
4 nguồn đổi schema/không trả dòng nào · 5 thư viện dừng tiến trình (thường do vượt hạn mức) ·
6 cấu hình sai (nguồn chưa hỗ trợ, domain ngoài allowlist). 4–6 dừng cả job.

Trạng thái: .flow_update/status.json (lượt mới nhất, ghi cả khi job bị dừng giữa chừng) và
.flow_update/batches.jsonl (mọi lượt, mỗi dòng 1 batch_id).
Rollback một lượt (backup DB trước): DELETE FROM flow_daily WHERE batch_id = '<batch_id>';
lệnh này xóa dòng lượt đó INSERT VÀ dòng tạm (is_final=0) của lượt trước mà lượt đó UPDATE
(giá trị cũ không được giữ) → sau rollback phải chạy lại job để kéo lại. Số đã chốt của lượt
trước không bị đụng (UPDATE không bao giờ ghi đè dòng is_final=1).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import math
import sys
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from sqlalchemy import Connection, Engine, inspect, select, text

from valuation.config import PROJECT_ROOT, load_defaults, settings
from valuation.db.flow_models import (
    MEASURE_COLUMNS,
    flow_daily,
    open_flow_engine,
)
from valuation.ingest.flow_client import (
    FlowClient,
    FlowConfigError,
    FlowRateLimited,
    FlowSchemaError,
    validate_tickers,
)
from valuation.services.ranking_store import exclusive_lock, write_json

STATE_DIR = PROJECT_ROOT / ".flow_update"
VN_TZ = dt.timezone(dt.timedelta(hours=7))
SAMPLE_COLS = [
    "ticker",
    "trade_date",
    "matched_val",
    "deal_vol",
    "fr_net_match_val",
    "fr_net_deal_val",
    "prop_net_match_val",
    "quality_flags",
]
logger = logging.getLogger("update_flow_daily")
# lỗi dừng cả job → mã thoát (xem docstring)
FATAL_EXIT = {FlowSchemaError: 4, FlowRateLimited: 5, FlowConfigError: 6}
_MISSING_GROUP = {
    "no_price",
    "no_prop",
}  # cả nhóm cột vắng → NULL, lượt sau phải lấp được


def now_vn() -> dt.datetime:
    return dt.datetime.now(VN_TZ).replace(tzinfo=None)


def is_final(
    trade_date: dt.date,
    fetched_at: dt.datetime,
    settle: str,
    flags: str | None = None,
) -> bool:
    """fetched_at (giờ VN) ≥ trade_date + prop_settle_time và không thiếu cả nhóm cột.

    Ngày đã qua luôn đạt giờ nên dòng backfill đủ cột tự là final; phiên hôm nay kéo trước giờ
    chốt tự doanh, hoặc dòng có cờ no_price/no_prop (nguồn công bố muộn/không đồng thời), thì chưa
    — để lượt kéo lại sau còn UPDATE được thay vì chốt NULL vĩnh viễn.
    """
    if isinstance(flags, str) and _MISSING_GROUP & set(flags.split(",")):
        return False
    return fetched_at >= dt.datetime.combine(trade_date, dt.time.fromisoformat(settle))


def exit_code(status: dict[str, Any]) -> int:
    if status.get("fatal_kind"):
        return {e.__name__: c for e, c in FATAL_EXIT.items()}[status["fatal_kind"]]
    return 1 if status["errors"] else 0


def save_status(status: dict[str, Any]) -> None:
    write_json(STATE_DIR / "status.json", status)
    with (STATE_DIR / "batches.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(status, ensure_ascii=False, default=str) + "\n")


def _num(value: Any) -> float | None:
    if value is None:
        return None
    out = float(value)
    return None if math.isnan(out) else out


def upsert_flow(
    conn: Connection,
    frame: pd.DataFrame,
    fetched_at: dt.datetime,
    batch_id: str,
    settle: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Chưa có → INSERT; có và chưa chốt → UPDATE; đã chốt → giữ nguyên, số lệch ghi log."""
    stats: dict[str, Any] = {
        "inserted": 0,
        "updated": 0,
        "skipped_final": 0,
        "mismatches": [],
    }
    c = flow_daily.c
    for (ticker, source), group in frame.groupby(["ticker", "source"], sort=False):
        dates = list(group["trade_date"])
        found = conn.execute(
            select(flow_daily).where(
                c.ticker == ticker,
                c.source == source,
                c.trade_date.between(min(dates), max(dates)),
            )
        ).mappings()
        existing = {row["trade_date"]: row for row in found}
        inserts: list[dict[str, Any]] = []
        updates: list[dict[str, Any]] = []
        for raw in group.to_dict("records"):
            rec = {
                "ticker": ticker,
                "trade_date": raw["trade_date"],
                "source": source,
                **{col: _num(raw[col]) for col in MEASURE_COLUMNS},
                "quality_flags": raw["quality_flags"],
                "fetched_at": fetched_at,
                "is_final": is_final(
                    raw["trade_date"], fetched_at, settle, raw["quality_flags"]
                ),
                "batch_id": batch_id,
            }
            old = existing.get(rec["trade_date"])
            if old is None:
                inserts.append(rec)
            elif not old["is_final"]:
                updates.append(rec)
            else:
                stats["skipped_final"] += 1
                for col in MEASURE_COLUMNS:
                    before = _num(old[col])
                    if before != rec[col]:
                        diff = {
                            "ticker": ticker,
                            "trade_date": str(rec["trade_date"]),
                            "column": col,
                            "final": before,
                            "new": rec[col],
                        }
                        stats["mismatches"].append(diff)
                        logger.warning("Lệch dòng đã chốt, KHÔNG ghi đè: %s", diff)
        if not dry_run:
            if inserts:
                conn.execute(flow_daily.insert(), inserts)
            for rec in updates:
                conn.execute(
                    flow_daily.update()
                    .where(
                        c.ticker == ticker,
                        c.source == source,
                        c.trade_date == rec["trade_date"],
                        c.is_final.is_(
                            False
                        ),  # chặn lần hai: không bao giờ đè dòng đã chốt
                    )
                    .values(**rec)
                )
        stats["inserted"] += len(inserts)
        stats["updated"] += len(updates)
    return stats


def run(
    engine: Engine,
    client: FlowClient,
    tickers: list[str],
    start: dt.date,
    end: dt.date,
    settle: str,
    batch_id: str,
    dry_run: bool,
    clock: Callable[[], dt.datetime] = now_vn,
    save: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Kéo từng mã; `save(status)` chạy trong finally (cả khi job bị dừng giữa chừng)."""
    status: dict[str, Any] = {
        "batch_id": batch_id,
        "dry_run": dry_run,
        "start": str(start),
        "end": str(end),
        "started_at": str(clock()),
        "tickers": len(tickers),
        "rows": 0,
        "inserted": 0,
        "updated": 0,
        "skipped_final": 0,
        "mismatches": [],
        "errors": [],
        "fatal": None,
        "fatal_kind": None,
    }
    try:
        for ticker in tickers:
            try:
                frame = client.fetch(ticker, start, end)
            except tuple(FATAL_EXIT) as exc:  # schema / hạn mức / cấu hình: dừng cả job
                logger.error("DỪNG: %s: %s", ticker, exc)
                status["fatal"] = f"{ticker}: {exc}"
                status["fatal_kind"] = type(exc).__name__
                break
            # lỗi mạng một mã: ghi vào status, exit ≠ 0, chạy mã khác
            except Exception as exc:  # noqa: BLE001
                logger.error("%s: %s: %s", ticker, type(exc).__name__, exc)
                status["errors"].append(
                    {"ticker": ticker, "error": f"{type(exc).__name__}: {exc}"}
                )
                continue
            # vnstock_data trả DataFrame rỗng khi JSON đổi cấu trúc (cảnh báo bị _muted nuốt)
            # → rỗng, hoặc chỉ có tự doanh mà không có giá, là lỗi chứ không phải "không có dòng".
            # Chỉ thiếu tự doanh thì không: nhiều mã không có số tự doanh (dòng có cờ no_prop).
            if (
                frame.empty
                or frame["quality_flags"].fillna("").str.contains("no_price").all()
            ):
                why = "rỗng" if frame.empty else "price_history rỗng (chỉ có tự doanh)"
                logger.error("%s: VCI trả %s trong %s..%s", ticker, why, start, end)
                status["errors"].append({"ticker": ticker, "error": f"VCI trả {why}"})
                if frame.empty:
                    continue
            if status["rows"] == 0:
                logger.info(
                    "Mẫu %s:\n%s",
                    ticker,
                    frame[SAMPLE_COLS].tail(3).to_string(index=False),
                )
            with engine.begin() as conn:
                stats = upsert_flow(conn, frame, clock(), batch_id, settle, dry_run)
            status["rows"] += len(frame)
            for key in ("inserted", "updated", "skipped_final"):
                status[key] += stats[key]
            status["mismatches"] += stats["mismatches"]
            logger.info(
                "%s: %d dòng · mới %d · cập nhật %d · giữ (đã chốt) %d",
                ticker,
                len(frame),
                stats["inserted"],
                stats["updated"],
                stats["skipped_final"],
            )
        if tickers and not status["fatal"] and status["rows"] == 0:
            status["fatal"] = (
                "VCI không trả dòng nào cho mọi mã (nghi nguồn đổi cấu trúc)"
            )
            status["fatal_kind"] = FlowSchemaError.__name__
            logger.error("DỪNG: %s", status["fatal"])
    except (
        BaseException
    ) as exc:  # vd sqlite "database is locked": ghi status rồi nổi lỗi
        status["fatal"] = status["fatal"] or f"bị dừng: {type(exc).__name__}"
        raise
    finally:
        status["finished_at"] = str(clock())
        if save is not None:
            save(status)
    return status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--backfill", action="store_true", help="Kéo flow_ingest.backfill_days ngày"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Gọi VCI, không ghi DB/status"
    )
    parser.add_argument(
        "--tickers", nargs="+", help="Chỉ các mã này (phải thuộc VN100)"
    )
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    cfg = load_defaults()
    ingest = cfg["flow_ingest"]
    settle = cfg["money_flow"]["prop_settle_time"]
    engine = open_flow_engine(settings.database_url_write)
    if not inspect(engine).has_table(flow_daily.name):
        logger.error(
            "Chưa có bảng flow_daily: chạy scripts/migrate_flow_daily.py --apply trước"
        )
        return 2
    try:
        with exclusive_lock(STATE_DIR / "worker.lock"):
            with engine.connect() as conn:
                universe = {
                    r[0]
                    for r in conn.execute(
                        text("SELECT ticker FROM tickers WHERE is_vn100 = 1")
                    )
                }
            tickers = validate_tickers(args.tickers or sorted(universe), universe)
            end = now_vn().date()
            days = (
                ingest["backfill_days"]
                if args.backfill
                else ingest["incremental_lookback_days"]
            )
            batch_id = f"{now_vn():%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:8]}"
            status = run(
                engine,
                FlowClient(ingest),
                tickers,
                end - dt.timedelta(days=days),
                end,
                settle,
                batch_id,
                args.dry_run,
                save=None if args.dry_run else save_status,
            )
    except BlockingIOError:
        logger.error("Job flow_daily khác đang chạy (%s)", STATE_DIR / "worker.lock")
        return 3
    summary = {k: v for k, v in status.items() if k != "mismatches"} | {
        "mismatches": len(status["mismatches"])
    }
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return exit_code(status)


if __name__ == "__main__":
    raise SystemExit(main())
