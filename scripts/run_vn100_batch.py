"""Định giá batch toàn VN100 (router-driven) → CSV + Google Sheets.

Chỉ định giá mã đã có dữ liệu trong DB; mã thiếu data → cột Cờ ghi lý do.
  ./venv/bin/python -m scripts.run_vn100_batch
"""
from valuation.db.session import SessionLocalRead
from valuation.db.models import FinancialsQuarterly
from sqlalchemy import distinct
from valuation.engine.batch import value_all
from valuation.output.gsheets_exporter import build_vn100_dataframe, export_vn100_valuations_to_gsheets
from valuation.config import PROJECT_ROOT


def main():
    db = SessionLocalRead()
    have = sorted(r[0] for r in db.query(distinct(FinancialsQuarterly.ticker)).all() if r[0] != "VNINDEX")
    results = value_all(db, have)
    df = build_vn100_dataframe(results)

    out_csv = PROJECT_ROOT / "vn100_valuations.csv"
    df.to_csv(out_csv, index=False)
    ok = sum(1 for r in results if "error" not in r)
    print(f"Đã định giá {ok}/{len(have)} mã → {out_csv}")

    res = export_vn100_valuations_to_gsheets(results)
    print("Google Sheets:", res.get("status"))


if __name__ == "__main__":
    main()
