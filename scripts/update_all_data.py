"""
Script cập nhật dữ liệu tài chính & giá mới nhất cho toàn bộ danh mục VN100,
sau đó tái tính toán định giá và xuất báo cáo (CSV + Google Sheets).
"""
import os
import sys
import logging
from datetime import datetime

# Import DB và pipeline
from valuation.db.session import SessionLocalWrite, SessionLocalRead
from valuation.db.models import Ticker, FinancialsQuarterly, PricesDaily
from valuation.ingest.pipeline import run_ingest
from sqlalchemy import distinct, func
from valuation.engine.batch import value_all
from valuation.models.macro_env import MacroEnvironment
from valuation.output.gsheets_exporter import build_vn100_dataframe, export_vn100_valuations_to_gsheets
from valuation.config import PROJECT_ROOT

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingest_update")

def main():
    print("=" * 60)
    print("1. KHỞI CHẠY CẬP NHẬT DỮ LIỆU TÀI CHÍNH & GIÁ THỊ TRƯỜNG MỚI NHẤT")
    print("=" * 60)

    db_write = SessionLocalWrite()
    try:
        tickers = [t.ticker for t in db_write.query(Ticker.ticker).order_by(Ticker.ticker.asc()).all()]
        print(f"-> Tìm thấy {len(tickers)} mã cổ phiếu trong danh mục.")
    finally:
        db_write.close()

    success_count = 0
    fail_count = 0
    
    for idx, ticker in enumerate(tickers, start=1):
        print(f"[{idx}/{len(tickers)}] Đang cập nhật {ticker}...", end=" ", flush=True)
        try:
            run_ingest(ticker, ['prices', 'financials'], incremental=True)
            print("OK")
            success_count += 1
        except Exception as e:
            print(f"LỖI: {e}")
            fail_count += 1

    print("\n" + "=" * 60)
    print(f"HOÀN THÀNH INGESTION: {success_count} thành công, {fail_count} thất bại.")
    print("=" * 60)

    print("\n2. TÁI TÍNH TOÁN ĐỊNH GIÁ TOÀN BỘ DANH MỤC VN100...")
    db_read = SessionLocalRead()
    try:
        normal_env = MacroEnvironment(inflation_rate=0.03, sbv_stance="Neutral")
        have = sorted(r[0] for r in db_read.query(distinct(FinancialsQuarterly.ticker)).all() if r[0] != "VNINDEX")
        
        results = value_all(db_read, macro_env=normal_env)
        df = build_vn100_dataframe(results)

        # Xuất CSV
        out_csv = PROJECT_ROOT / "vn100_valuations.csv"
        df.to_csv(out_csv, index=False, encoding="utf-8-sig")
        
        ok_val = sum(1 for r in results if "error" not in r)
        print(f"-> Đã tái định giá thành công {ok_val}/{len(have)} mã.")
        print(f"-> Đã lưu kết quả ra file: {out_csv}")

        # Xuất Google Sheets
        print("-> Đang đồng bộ kết quả lên Google Sheets...")
        res_gsheets = export_vn100_valuations_to_gsheets(results, sheet_name="VN100_Valuations")
        print("-> Google Sheets status:", res_gsheets.get("status"))

        # Thống kê tổng hợp báo cáo
        max_price_date = db_read.query(func.max(PricesDaily.trade_date)).scalar()
        max_yr_q = db_read.query(
            func.max(FinancialsQuarterly.fiscal_year),
            func.max(FinancialsQuarterly.fiscal_quarter)
        ).first()

        print("\n" + "=" * 60)
        print("BÁO CÁO TỔNG HỢP SAU CẬP NHẬT:")
        print(f"- Ngày giá thị trường mới nhất trong DB: {max_price_date}")
        print(f"- Kỳ báo cáo tài chính mới nhất: Năm {max_yr_q[0]} Quý {max_yr_q[1]}")
        print(f"- Tổng số mã trong danh mục: {len(results)}")
        
        rec_counts = {}
        for r in results:
            rec = r.get("recommendation", "UNKNOWN")
            rec_counts[rec] = rec_counts.get(rec, 0) + 1
            
        print("- Phân bổ khuyến nghị định giá:")
        for rec, cnt in rec_counts.items():
            print(f"  + {rec}: {cnt} mã")
        print("=" * 60)

    finally:
        db_read.close()

if __name__ == "__main__":
    main()
