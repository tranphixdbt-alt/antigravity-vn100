import logging
import datetime
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
from sqlalchemy.orm import Session
from valuation.db.models import DailySignal, Ticker
from valuation.db.session import SessionLocalRead
from valuation.config import settings
from valuation.engine.ttm_helper import (
    build_vcb_current_financials,
    build_fpt_current_financials,
    build_hpg_current_financials,
    build_ssi_current_financials,
    build_dgc_current_financials
)
from valuation.engine.consensus_helper import get_consensus_stats
from valuation.analysis.ai_insight import generate_ai_insight

logger = logging.getLogger(__name__)

def export_daily_signals_to_gsheets(trade_date: datetime.date = None, db: Session = None):
    """
    Xuất bảng DailySignal trong ngày ra Google Sheets với giao diện chuyên nghiệp, các chỉ số bổ sung và nhận định AI.
    """
    if not settings.google_service_account_json or not settings.google_sheet_master_id:
        logger.warning("Google Sheets config missing. Skipping export.")
        return {"status": "skipped", "reason": "Missing GS config"}
        
    close_db = False
    if db is None:
        db = SessionLocalRead()
        close_db = True
        
    if trade_date is None:
        trade_date = datetime.date.today()
        
    try:
        # Fetch data
        signals = db.query(DailySignal).filter(DailySignal.trade_date == trade_date).all()
        if not signals:
            logger.info("No daily signals found for export.")
            return {"status": "success", "exported_rows": 0}
            
        # Tương thích với các hàm build_current_financials
        fin_builders = {
            "VCB": build_vcb_current_financials,
            "FPT": build_fpt_current_financials,
            "HPG": build_hpg_current_financials,
            "SSI": build_ssi_current_financials,
            "DGC": build_dgc_current_financials
        }
        
        # Map sector sang tiếng Việt chuyên nghiệp
        SECTOR_MAP = {
            "Banks": "Ngân hàng",
            "Technology": "Công nghệ",
            "Chemicals": "Hóa chất",
            "Securities": "Chứng khoán",
            "Thép / vật liệu": "Thép & Vật liệu"
        }
        
        data = []
        for s in signals:
            ticker_obj = db.query(Ticker).filter(Ticker.ticker == s.ticker).first()
            sector = ticker_obj.sector if ticker_obj else "Unknown"
            display_sector = SECTOR_MAP.get(sector, sector)
            
            close_price = float(s.close_price) if s.close_price else None
            fv_fast = float(s.fair_value_fast) if s.fair_value_fast else None
            
            # Tính toán các chỉ số cơ bản
            pe = None
            pb = None
            roe = None
            
            if s.ticker in fin_builders and close_price:
                try:
                    fin_data = fin_builders[s.ticker](db)
                    equity = float(fin_data.get("total_equity") or 0.0)
                    net_inc = float(fin_data.get("net_income") or 0.0)
                    shares = float(fin_data.get("shares_outstanding") or 0.0)
                    
                    if equity > 0:
                        roe = net_inc / equity
                    if shares > 0:
                        eps = net_inc / shares
                        bvps = equity / shares
                        if eps > 0:
                            pe = close_price / eps
                        if bvps > 0:
                            pb = close_price / bvps
                except Exception as e:
                    logger.warning(f"Error computing metrics for {s.ticker}: {e}")
            
            # Lấy thông tin đồng thuận CTCK (Consensus)
            consensus_target = None
            consensus_dev = None
            try:
                c_stats = get_consensus_stats(s.ticker, s.trade_date, db)
                if c_stats["median"] is not None:
                    consensus_target = float(c_stats["median"])
                    if fv_fast:
                        consensus_dev = (fv_fast - consensus_target) / consensus_target
            except Exception as e:
                logger.warning(f"Error fetching consensus for {s.ticker}: {e}")
                
            # Xác định khuyến nghị (Rating)
            rating = "THEO DÕI"
            if s.upside is not None and s.margin_of_safety is not None:
                upside_val = float(s.upside)
                mos_val = float(s.margin_of_safety)
                if upside_val > mos_val:
                    rating = "MUA"
                elif upside_val < 0:
                    rating = "BÁN"
                else:
                    rating = "THEO DÕI"
                    
            # Gọi DeepSeek tạo nhận định AI (AI Insight)
            ai_insight = generate_ai_insight(
                ticker=s.ticker,
                sector=display_sector,
                close_price=close_price,
                fair_value=fv_fast,
                upside=s.upside,
                flags=s.flags,
                roe=roe,
                pe=pe,
                pb=pb,
                consensus_target=consensus_target
            )
            
            data.append({
                "Mã CK": s.ticker,
                "Ngành": display_sector,
                "Ngày GD": s.trade_date.isoformat(),
                "Thị giá": close_price,
                "FV Nhịp Nhanh": fv_fast,
                "Upside": float(s.upside) if s.upside is not None else None,
                "Biên An Toàn": float(s.margin_of_safety) if s.margin_of_safety is not None else None,
                "Khuyến nghị": rating,
                "Điểm Conviction": float(s.conviction_score) if s.conviction_score is not None else None,
                "P/E": pe,
                "P/B": pb,
                "ROE": roe,
                "Định giá Consensus": consensus_target,
                "Độ lệch Consensus": consensus_dev,
                "Cờ Cảnh Báo": ", ".join(s.flags) if s.flags else "OK",
                "Nhận định AI": ai_insight
            })
            
        df = pd.DataFrame(data)
        
        # Sắp xếp theo Điểm Conviction giảm dần
        df = df.sort_values(by="Điểm Conviction", ascending=False)
        
        # Authenticate and Push
        gc = gspread.service_account(filename=settings.google_service_account_json)
        sh = gc.open_by_key(settings.google_sheet_master_id)
        
        try:
            worksheet = sh.worksheet("Daily_Screener")
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sh.add_worksheet(title="Daily_Screener", rows="100", cols="20")
            
        # Clear old data and insert new
        worksheet.clear()
        set_with_dataframe(worksheet, df)
        
        # === Định dạng Google Sheets chuyên nghiệp ===
        num_rows = len(df) + 1 # bao gồm cả header
        
        # 1. Định dạng header (Dòng 1 từ cột A đến P)
        worksheet.format('A1:P1', {
            'backgroundColor': {
                'red': 0.12,
                'green': 0.23,
                'blue': 0.35
            },
            'horizontalAlignment': 'CENTER',
            'verticalAlignment': 'MIDDLE',
            'textFormat': {
                'foregroundColor': {
                    'red': 1.0,
                    'green': 1.0,
                    'blue': 1.0
                },
                'fontSize': 10,
                'bold': True
            }
        })
        
        # 2. Định dạng font chữ chung cho data (A đến P)
        worksheet.format(f'A2:P{num_rows}', {
            'textFormat': {
                'fontSize': 10
            },
            'verticalAlignment': 'MIDDLE'
        })
        
        # 3. Định dạng căn lề và định dạng số cho từng cột
        worksheet.format(f'A2:A{num_rows}', {'horizontalAlignment': 'CENTER'})
        worksheet.format(f'B2:B{num_rows}', {'horizontalAlignment': 'LEFT'})
        worksheet.format(f'C2:C{num_rows}', {'horizontalAlignment': 'CENTER'})
        
        # Thị giá & FV Nhịp Nhanh: Số nguyên có phân cách hàng nghìn
        worksheet.format(f'D2:E{num_rows}', {
            'horizontalAlignment': 'RIGHT',
            'numberFormat': {'type': 'NUMBER', 'pattern': '#,##0'}
        })
        
        # Upside & Biên An Toàn: Phần trăm 1 chữ số thập phân
        worksheet.format(f'F2:G{num_rows}', {
            'horizontalAlignment': 'RIGHT',
            'numberFormat': {'type': 'PERCENT', 'pattern': '0.0%'}
        })
        
        # Khuyến nghị: Căn giữa, chữ in đậm
        worksheet.format(f'H2:H{num_rows}', {
            'horizontalAlignment': 'CENTER',
            'textFormat': {'bold': True}
        })
        
        # Điểm Conviction: Số thực 1 chữ số thập phân
        worksheet.format(f'I2:I{num_rows}', {
            'horizontalAlignment': 'RIGHT',
            'numberFormat': {'type': 'NUMBER', 'pattern': '0.0'}
        })
        
        # P/E & P/B: Số thực 2 chữ số thập phân
        worksheet.format(f'J2:K{num_rows}', {
            'horizontalAlignment': 'RIGHT',
            'numberFormat': {'type': 'NUMBER', 'pattern': '0.00'}
        })
        
        # ROE: Phần trăm 1 chữ số thập phân
        worksheet.format(f'L2:L{num_rows}', {
            'horizontalAlignment': 'RIGHT',
            'numberFormat': {'type': 'PERCENT', 'pattern': '0.0%'}
        })
        
        # Định giá Consensus: Số nguyên có phân cách hàng nghìn
        worksheet.format(f'M2:M{num_rows}', {
            'horizontalAlignment': 'RIGHT',
            'numberFormat': {'type': 'NUMBER', 'pattern': '#,##0'}
        })
        
        # Độ lệch Consensus: Phần trăm 1 chữ số thập phân
        worksheet.format(f'N2:N{num_rows}', {
            'horizontalAlignment': 'RIGHT',
            'numberFormat': {'type': 'PERCENT', 'pattern': '0.0%'}
        })
        
        worksheet.format(f'O2:O{num_rows}', {'horizontalAlignment': 'LEFT'})
        worksheet.format(f'P2:P{num_rows}', {'horizontalAlignment': 'LEFT'}) # Cột P: Nhận định AI
        
        # 4. Tô màu có điều kiện cho cột Khuyến nghị
        for idx, row in df.iterrows():
            row_num = idx + 2
            rating_val = row["Khuyến nghị"]
            cell_range = f"H{row_num}"
            if rating_val == "MUA":
                worksheet.format(cell_range, {
                    'textFormat': {
                        'bold': True,
                        'foregroundColor': {'red': 0.1, 'green': 0.5, 'blue': 0.1} # Xanh lá đậm
                    }
                })
            elif rating_val == "BÁN":
                worksheet.format(cell_range, {
                    'textFormat': {
                        'bold': True,
                        'foregroundColor': {'red': 0.8, 'green': 0.1, 'blue': 0.1} # Đỏ đậm
                    }
                })
            else: # THEO DÕI
                worksheet.format(cell_range, {
                    'textFormat': {
                        'bold': True,
                        'foregroundColor': {'red': 0.5, 'green': 0.5, 'blue': 0.5} # Xám
                    }
                })
                
        logger.info(f"Successfully exported {len(df)} rows to Google Sheets.")
        return {"status": "success", "exported_rows": len(df)}
        
    except Exception as e:
        logger.error(f"Failed to export to Google Sheets: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        if close_db:
            db.close()
