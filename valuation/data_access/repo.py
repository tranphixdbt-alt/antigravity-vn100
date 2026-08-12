"""
Repository module — Truy vấn dữ liệu tài chính từ PostgreSQL, chuẩn hóa đơn vị và kỳ báo cáo.
"""
from typing import List, Dict, Any, Union, Tuple
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import desc
from valuation.db.models import Ticker, FinancialsQuarterly, PricesDaily, MacroSeries
from valuation.data_access.units import to_billion_vnd, clean_value
from valuation.data_access.periodize import periodize_quarters_to_annual, get_latest_quarters_for_ticker
from valuation.models.financials import IncomeStatement, BalanceSheet, CashFlow, Company, Assumptions
from valuation.models.financials_bank import IncomeStatementBank, BalanceSheetBank, CompanyBank, AssumptionsBank
from valuation.engine.ttm_helper import estimate_vcb_beta, get_latest_tpcp_10y

# Từ khóa matching cho Phi tài chính
NON_FIN_KEYWORDS = {
    "revenue": ["net_revenue_from_goods_and_services_rendered", "net_sales", "Doanh thu thuần", "Doanh thu hoạt động"],
    "cogs": ["cost_of_goods_sold", "cogs", "Giá vốn hàng bán", "Chi phí hoạt động tự doanh"],
    "gross_profit": ["gross_profit", "Lợi nhuận gộp"],
    # OPEX tách 2 cấu phần để CỘNG (không dùng chung 1 key — xem build_company_data).
    "selling_expenses": ["selling_expenses", "Chi phí bán hàng"],
    "ga_expenses": ["general_and_admin_expenses", "Chi phí quản lý doanh nghiệp", "Chi phí quản lý"],
    "opex_total": ["operating_expenses", "operating_expense", "Chi phí hoạt động"],
    "operating_profit": ["operating_profit_loss", "Lợi nhuận từ hoạt động kinh doanh", "Lợi nhuận thuần từ hoạt động kinh doanh"],
    "interest_expense": ["interest_expenses", "interest_expense", "Chi phí lãi vay"],
    "tax": ["corporate_income_tax", "tax_rate_value", "Chi phí thuế TNDN hiện hành", "Thuế thu nhập doanh nghiệp"],
    # net_profit_attributable... + profit_after_tax cho ngành bảo hiểm (BVH) — IS bảo
    # hiểm KHÔNG có net_profit_loss_after_tax; nếu thiếu, fallback ebit×0.8 lấy nhầm
    # doanh thu phí (ROE phi lý). Đặt SAU key chuẩn để DN thường vẫn match key đầu.
    "net_income": ["net_profit_loss_after_tax", "net_profit_attributable_to_shareholders_of_the_group", "profit_after_tax", "net_income", "Lợi nhuận sau thuế"],
    
    "cash": ["cash_and_cash_equivalents", "short_term_financial_investments", "Tiền và các khoản tương đương tiền", "Đầu tư tài chính ngắn hạn"],
    "receivables": ["short_term_trade_receivables", "short_term_receivables", "Phải thu ngắn hạn của khách hàng", "Các khoản phải thu"],
    "inventory": ["inventories", "inventory", "Hàng tồn kho"],
    "fixed_assets": ["tangible_fixed_assets", "fixed_assets", "Tài sản cố định", "Tài sản cố định hữu hình"],
    "total_assets": ["total_assets", "Tổng tài sản", "TỔNG TÀI SẢN"],
    "st_debt": ["short_term_borrowings", "short_term_debt", "Vay và nợ thuê tài chính ngắn hạn", "Vay ngắn hạn"],
    "lt_debt": ["long_term_borrowings", "long_term_debt", "Vay và nợ thuê tài chính dài hạn", "Vay dài hạn"],
    "accounts_payable": ["short_term_trade_payables", "accounts_payable", "Phải trả người bán ngắn hạn", "Phải trả người bán"],
    "total_equity": ["owners_equity", "shareholders_equity", "capital_and_reserves", "Vốn chủ sở hữu"],
    
    "cfo": ["net_cash_inflows_outflows_from_operating_activities", "net_cash_flows_from_operating_activities", "cfo", "Lưu chuyển tiền thuần từ hoạt động kinh doanh"],
    "capex": ["purchases_of_fixed_assets_and_other_long_term_assets", "payments_for_purchase_of_fixed_assets", "capex", "Tiền chi để mua sắm, xây dựng TSCĐ"],
    "depreciation": ["depreciation_and_amortization", "depreciation", "Khấu hao tài sản cố định", "Khấu hao TSCĐ và BĐSĐT"],
}

# Từ khóa matching cho Ngân hàng.
# Ưu tiên key tiếng Anh (vnstock English line_item) ĐẶT TRƯỚC để match qua
# startswith trước; giữ key tiếng Việt phía sau để tương thích nguồn cũ.
BANK_KEYWORDS = {
    "net_interest_income": ["net_interest_income", "I. Thu nhập lãi thuần", "Thu nhập lãi thuần"],
    "non_interest_income": ["non_interest_income"], # Tính gián tiếp TOI - NII
    "total_operating_income": ["total_operating_income", "VIII. Tổng thu nhập hoạt động", "Tổng thu nhập hoạt động"],
    "operating_expenses": ["general_and_admin_expenses", "IX. Chi phí hoạt động", "Chi phí hoạt động"],
    "provision_expense": ["provision_for_credit_losses", "Chi phí dự phòng rủi ro tín dụng", "Chi phí dự phòng"],
    "pretax_income": ["net_accounting_profit_loss_before_tax", "XI. Tổng lợi nhuận trước thuế", "Tổng lợi nhuận trước thuế"],
    "net_income": ["net_profit_loss_after_tax", "XIV. Lợi nhuận sau thuế", "Lợi nhuận sau thuế"],

    "customer_loans": ["loans_and_advances_to_customers_net", "loans_and_advances_to_customers", "1. Cho vay khách hàng"],
    "customer_deposits": ["deposits_from_customers", "Tiền gửi của khách hàng", "Tiền gửi khách hàng"],
    "total_assets": ["total_assets", "TỔNG TÀI SẢN", "Tổng tài sản"],
    "total_equity": ["owners_equity", "shareholders_equity", "Vốn chủ sở hữu"],
}

def _quarterly_revenues(db: Session, ticker: str) -> List[float]:
    """Doanh thu thuần theo TỪNG QUÝ, sắp xếp cũ -> mới (D32).

    Dùng cho động lượng năm gốc dự phóng. Dữ liệu quý vốn đã có sẵn trong DB
    nhưng `build_company_data` chỉ dùng nó để ráp thành năm — thông tin về xu
    hướng gần đây bị mất trong lúc gộp.
    """
    rows = (
        db.query(FinancialsQuarterly)
        .filter(FinancialsQuarterly.ticker == ticker,
                FinancialsQuarterly.statement == "IS")
        .all()
    )
    by_period: Dict[tuple, Dict[str, float]] = {}
    for r in rows:
        if r.fiscal_quarter is None or r.fiscal_quarter == 0:
            continue  # bỏ dòng năm, chỉ lấy quý
        key = (r.fiscal_year, r.fiscal_quarter)
        by_period.setdefault(key, {})[r.line_item] = float(r.value or 0.0)

    out: List[float] = []
    for key in sorted(by_period):
        rev = _match_value(by_period[key], NON_FIN_KEYWORDS["revenue"])
        if rev and rev > 0:
            out.append(rev)
    return out


def _match_value(data: Dict[str, float], keywords: List[str], fallback: float = 0.0) -> float:
    """Tìm giá trị khớp với từ khóa trong dict dữ liệu."""
    for kw in keywords:
        kw_lower = kw.lower()
        # Ưu tiên startswith
        for k, v in data.items():
            if k.lower().startswith(kw_lower):
                return clean_value(v)
        # Fallback contains
        for k, v in data.items():
            if kw_lower in k.lower():
                return clean_value(v)
    return fallback

def get_historical_years(db: Session, ticker: str) -> List[int]:
    """Lấy danh sách các năm có dữ liệu BCTC (bỏ qua năm rỗng)."""
    rows = (
        db.query(FinancialsQuarterly.fiscal_year)
        .filter(FinancialsQuarterly.ticker == ticker)
        .distinct()
        .order_by(FinancialsQuarterly.fiscal_year.asc())
        .all()
    )
    return [r[0] for r in rows if r[0] > 0]

def get_latest_price(db: Session, ticker: str, fetch_live: bool = True) -> float:
    """Lấy giá đóng cửa gần nhất của ticker (VND). Ưu tiên lấy giá live từ vnstock."""
    if fetch_live:
        try:
            from valuation.ingest.vnstock_client import vnstock_client
            live_price = vnstock_client.get_live_price(ticker)
            if live_price > 0:
                return live_price
        except Exception:
            pass

    row = (
        db.query(PricesDaily)
        .filter(PricesDaily.ticker == ticker)
        .order_by(PricesDaily.trade_date.desc())
        .first()
    )
    return float(row.close) if row and row.close is not None else 0.0

def load_ticker_metadata(db: Session, ticker: str) -> Ticker:
    """Tải thông tin ngành và sàn giao dịch của ticker."""
    return db.query(Ticker).filter(Ticker.ticker == ticker).first()

def get_shares_outstanding_repo(db: Session, ticker: str) -> float:
    """Lấy số lượng cổ phiếu lưu hành (đổi sang triệu cổ phiếu)."""
    from valuation.engine.ttm_helper import get_shares_outstanding
    try:
        shares = get_shares_outstanding(db, ticker)
        # ttm_helper trả về số cp thô (ví dụ: 8,355,675,094)
        # Ta đổi sang triệu cp (chia 10^6)
        return shares / 1e6
    except Exception:
        return 1000.0  # Fallback 1000 triệu cp

def build_company_data(db: Session, ticker: str, mode: str = "TTM", fetch_live: bool = False) -> Union[Company, CompanyBank]:
    """
    Truy vấn dữ liệu tài chính lịch sử, quy đổi kỳ báo cáo và đơn vị,
    trả về đối tượng Pydantic Company (phi tài chính) hoặc CompanyBank (ngân hàng).
    """
    meta = load_ticker_metadata(db, ticker)
    if not meta:
        raise ValueError(f"Không tìm thấy ticker {ticker} trong DB")

    is_bank = meta.sector == "Banks"
    current_price = get_latest_price(db, ticker, fetch_live=fetch_live)
    shares = get_shares_outstanding_repo(db, ticker)

    # 1. Truy vấn toàn bộ dữ liệu quý của ticker
    records = db.query(FinancialsQuarterly).filter(FinancialsQuarterly.ticker == ticker).all()
    fin_data = [{
        "fiscal_year": r.fiscal_year,
        "fiscal_quarter": r.fiscal_quarter,
        "line_item": r.line_item,
        "value": float(r.value) if r.value is not None else 0.0
    } for r in records]
    df_fin = pd.DataFrame(fin_data)

    # Lấy danh sách các năm
    years = get_historical_years(db, ticker)
    if not years:
        raise ValueError(f"Không có dữ liệu tài chính cho {ticker}")

    # Xác định năm lớn nhất và quý lớn nhất
    latest_yr = max(years)
    sub_latest = df_fin[(df_fin["fiscal_year"] == latest_yr) & (df_fin["fiscal_quarter"] > 0)]
    latest_q = sub_latest["fiscal_quarter"].max() if not sub_latest.empty else 4

    historical_is = []
    historical_bs = []
    historical_cf = []

    # 2. Quy đổi dữ liệu quý -> năm cho từng năm lịch sử
    for y in years:
        # Nếu là năm gần nhất và mode == TTM, chạy periodize theo TTM
        # Nếu là năm cũ, luôn chạy theo FY (đầy đủ cả năm)
        if y == latest_yr and mode == "TTM":
            annual_data = periodize_quarters_to_annual(df_fin, y, mode="TTM", latest_quarter=latest_q)
        else:
            annual_data = periodize_quarters_to_annual(df_fin, y, mode="FY")

        if not annual_data:
            continue

        if is_bank:
            # Match dữ liệu bank
            nii = _match_value(annual_data, BANK_KEYWORDS["net_interest_income"])
            toi = _match_value(annual_data, BANK_KEYWORDS["total_operating_income"])
            opex = abs(_match_value(annual_data, BANK_KEYWORDS["operating_expenses"]))
            prov = abs(_match_value(annual_data, BANK_KEYWORDS["provision_expense"]))
            pbt = _match_value(annual_data, BANK_KEYWORDS["pretax_income"])
            ni = _match_value(annual_data, BANK_KEYWORDS["net_income"])
            
            loans = _match_value(annual_data, BANK_KEYWORDS["customer_loans"])
            deposits = _match_value(annual_data, BANK_KEYWORDS["customer_deposits"])
            assets = _match_value(annual_data, BANK_KEYWORDS["total_assets"])
            equity = _match_value(annual_data, BANK_KEYWORDS["total_equity"])
            
            # Tính toán gián tiếp nếu thiếu trường
            non_interest_income = toi - nii
            ppop = toi - opex
            if pbt == 0:
                pbt = ppop - prov
            if ni == 0:
                ni = pbt * 0.8
                
            other_earning_assets = max(0.0, assets - loans)
            other_liabilities = max(0.0, assets - deposits - equity)

            # Quy đổi sang Tỷ đồng (chia 10^9)
            historical_is.append(IncomeStatementBank(
                year=y,
                net_interest_income=to_billion_vnd(nii),
                non_interest_income=to_billion_vnd(non_interest_income),
                total_operating_income=to_billion_vnd(toi),
                operating_expenses=to_billion_vnd(opex),
                pre_provision_profit=to_billion_vnd(ppop),
                provision_expense=to_billion_vnd(prov),
                pretax_income=to_billion_vnd(pbt),
                net_income=to_billion_vnd(ni),
            ))
            
            historical_bs.append(BalanceSheetBank(
                year=y,
                customer_loans=to_billion_vnd(loans),
                other_earning_assets=to_billion_vnd(other_earning_assets),
                total_assets=to_billion_vnd(assets),
                customer_deposits=to_billion_vnd(deposits),
                other_liabilities=to_billion_vnd(other_liabilities),
                total_equity=to_billion_vnd(equity)
            ))
        else:
            # Match dữ liệu phi tài chính
            rev = _match_value(annual_data, NON_FIN_KEYWORDS["revenue"])
            cogs = abs(_match_value(annual_data, NON_FIN_KEYWORDS["cogs"]))
            gp = _match_value(annual_data, NON_FIN_KEYWORDS["gross_profit"])
            # OPEX = chi phí bán hàng + QLDN (PHẢI cộng cả 2). _match_value chỉ trả
            # 1 dòng khớp đầu → nếu dùng chung 1 key sẽ bắt mỗi selling_expenses,
            # bỏ sót G&A → EBIT bị thổi phồng (~2pp margin) cho mọi mã phi TC.
            sell_exp = abs(_match_value(annual_data, NON_FIN_KEYWORDS["selling_expenses"]))
            ga_exp = abs(_match_value(annual_data, NON_FIN_KEYWORDS["ga_expenses"]))
            opex = sell_exp + ga_exp
            if opex == 0:  # fallback: dòng chi phí hoạt động gộp (nếu không tách được)
                opex = abs(_match_value(annual_data, NON_FIN_KEYWORDS["opex_total"]))
            ebit_reported = _match_value(annual_data, NON_FIN_KEYWORDS["operating_profit"])
            int_exp = abs(_match_value(annual_data, NON_FIN_KEYWORDS["interest_expense"]))
            tax = abs(_match_value(annual_data, NON_FIN_KEYWORDS["tax"]))
            ni = _match_value(annual_data, NON_FIN_KEYWORDS["net_income"])

            # EBIT LÕI = gross_profit - opex. KHÔNG dùng operating_profit_loss làm
            # chính: với holding (vd REE) nó gồm lãi liên kết + lãi tài chính KHÔNG
            # co giãn theo doanh thu → chiếu doanh thu × biên sẽ thổi phồng. Chỉ
            # fallback về reported khi core <= 0 (thường do thiếu line opex).
            if gp == 0:
                gp = rev - cogs
            ebit_core = gp - opex
            if ebit_core > 0:
                ebit = ebit_core
            elif ebit_reported != 0:
                ebit = ebit_reported
            else:
                ebit = ebit_core
            if ni == 0:
                ni = (ebit - int_exp) * 0.8

            cash = _match_value(annual_data, NON_FIN_KEYWORDS["cash"])
            rec = _match_value(annual_data, NON_FIN_KEYWORDS["receivables"])
            inv = _match_value(annual_data, NON_FIN_KEYWORDS["inventory"])
            fixed = _match_value(annual_data, NON_FIN_KEYWORDS["fixed_assets"])
            assets = _match_value(annual_data, NON_FIN_KEYWORDS["total_assets"])
            st_debt = _match_value(annual_data, NON_FIN_KEYWORDS["st_debt"])
            lt_debt = _match_value(annual_data, NON_FIN_KEYWORDS["lt_debt"])
            pay = _match_value(annual_data, NON_FIN_KEYWORDS["accounts_payable"])
            equity = _match_value(annual_data, NON_FIN_KEYWORDS["total_equity"])
            
            # Đảm bảo Cân đối kế toán: Tổng Tài Sản = Nợ Phải Trả + Vốn Chủ Sở Hữu
            # Suy ra: Nợ Phải Trả mục tiêu = assets - equity
            target_liab = max(0.0, assets - equity)
            
            # Phân bổ tài sản còn lại
            known_assets = cash + rec + inv + fixed
            rem_assets = assets - known_assets
            if rem_assets >= 0:
                other_curr_assets = rem_assets * 0.5
                other_lt_assets = rem_assets * 0.5
            else:
                other_curr_assets = 0.0
                other_lt_assets = 0.0
                
            # Phân bổ nợ phải trả còn lại
            known_liab = st_debt + pay + lt_debt
            rem_liab = target_liab - known_liab
            if rem_liab >= 0:
                other_curr_liab = rem_liab * 0.5
                other_lt_liab = rem_liab * 0.5
            else:
                # Nếu known_liab đã lớn hơn target_liab (thường do lỗi dữ liệu)
                # Ép các khoản nợ khác về 0 và chấp nhận lệch hoặc tự động điều chỉnh st_debt/lt_debt
                other_curr_liab = 0.0
                other_lt_liab = 0.0
                
            # Đảm bảo Vốn chủ sở hữu chuẩn xác để khớp bảng
            equity = assets - (st_debt + pay + other_curr_liab + lt_debt + other_lt_liab)

            cfo = _match_value(annual_data, NON_FIN_KEYWORDS["cfo"])
            capex = abs(_match_value(annual_data, NON_FIN_KEYWORDS["capex"]))  # lấy trị tuyệt đối
            dep_amort = abs(_match_value(annual_data, NON_FIN_KEYWORDS["depreciation"]))  # D&A thật từ CF

            # Quy đổi sang Tỷ đồng
            historical_is.append(IncomeStatement(
                year=y,
                revenue=to_billion_vnd(rev),
                cogs=to_billion_vnd(cogs),
                gross_profit=to_billion_vnd(gp),
                opex=to_billion_vnd(opex),
                ebit=to_billion_vnd(ebit),
                interest_expense=to_billion_vnd(int_exp),
                tax=to_billion_vnd(tax),
                net_income=to_billion_vnd(ni)
            ))
            
            historical_bs.append(BalanceSheet(
                year=y,
                cash_and_equivalents=to_billion_vnd(cash),
                receivables=to_billion_vnd(rec),
                inventory=to_billion_vnd(inv),
                other_current_assets=to_billion_vnd(other_curr_assets),
                fixed_assets=to_billion_vnd(fixed),
                other_long_term_assets=to_billion_vnd(other_lt_assets),
                total_assets=to_billion_vnd(assets),
                short_term_debt=to_billion_vnd(st_debt),
                accounts_payable=to_billion_vnd(pay),
                other_current_liabilities=to_billion_vnd(other_curr_liab),
                long_term_debt=to_billion_vnd(lt_debt),
                other_long_term_liabilities=to_billion_vnd(other_lt_liab),
                total_equity=to_billion_vnd(equity)
            ))
            
            historical_cf.append(CashFlow(
                year=y,
                cfo=to_billion_vnd(cfo),
                capex=to_billion_vnd(capex),
                depreciation=to_billion_vnd(dep_amort)
            ))

    # 3. Tính toán giả định base case động
    rf_dynamic = get_latest_tpcp_10y(db)
    beta_dynamic = estimate_vcb_beta(db, ticker)

    # Macro overlay context: độ lệch vĩ mô theo momentum 12 tháng (giá trị mới
    # nhất vs ~1 năm trước). Robust khi dữ liệu vĩ mô trễ/sớm hơn năm tài chính.
    # Khi chưa có dữ liệu GDP/tín dụng, delta=0 → overlay no-op (an toàn).
    from valuation.forecast.drivers import (
        MacroContext,
        overlay_credit_growth,
        overlay_revenue_growth,
    )
    _macro_ctx = MacroContext.from_db_momentum(db)
    _sector_for_overlay = meta.sector

    from valuation.config import load_defaults
    config_defaults = load_defaults()
    # VND-base: erp = mature ERP + CRP VN (CRP là rủi ro vốn cổ phần TT mới nổi,
    # tách biệt rủi ro vỡ nợ trong TPCP — chuẩn Damodaran).
    from valuation.engine.coe import get_erp
    erp_vn = get_erp()

    if is_bank:
        # Tính toán NIM, CIR, Credit Cost trung bình lịch sử làm base case
        # (dùng 4 quý gần nhất của ttm_helper)
        from valuation.engine.ttm_helper import (
            compute_historical_nim,
            compute_historical_cir,
            compute_historical_credit_growth,
            compute_historical_credit_cost,
        )
        nim_val = compute_historical_nim(db, ticker) or 0.03
        cir_val = compute_historical_cir(db, ticker) or 0.35
        cg_val = compute_historical_credit_growth(db, ticker) or 0.12
        cc_val = compute_historical_credit_cost(db, ticker) or 0.01

        # Declining schedules
        credit_growth = [cg_val, cg_val - 0.01, cg_val - 0.02, cg_val - 0.02, max(cg_val - 0.03, 0.08)]
        # Macro overlay: điều chỉnh theo tăng trưởng tín dụng hệ thống (no-op nếu thiếu data)
        credit_growth = overlay_credit_growth(credit_growth, _sector_for_overlay, _macro_ctx)
        nim = [nim_val, nim_val, nim_val - 0.001, nim_val - 0.001, nim_val - 0.002]
        cir = [cir_val, cir_val, cir_val - 0.005, cir_val - 0.005, cir_val - 0.01]
        credit_cost = [cc_val, cc_val, cc_val, cc_val - 0.001, cc_val - 0.001]

        # ROE bền vững — D29: MEDIAN cửa sổ gần nhất, KHÔNG phải trung bình toàn lịch sử.
        #
        # Cách cũ `sum(roes)/len(roes)` trộn đỉnh chu kỳ 2018-2021 vào ước lượng
        # "bền vững": ACB ra 20,8% trong khi ROE thực tế đang phai rõ rệt
        # 23%→20%→17%→16%. Vì Target P/B = (ROE-g)/(COE-g) CỰC nhạy với ROE, sai
        # số này đẩy thẳng vào định giá — là nguyên nhân gốc của overshoot D20.
        #
        # Median (không phải trung bình) để một quý đột biến không kéo lệch ước lượng.
        _bank_cfg = config_defaults.get("bank_terminal", {}) or {}
        _roe_window = int(_bank_cfg.get("roe_window", 3))
        avg_roe = float(_bank_cfg.get("roe_fallback", 0.15))
        if historical_bs and historical_is:
            roes = [historical_is[i].net_income / historical_bs[i].total_equity
                    for i in range(len(historical_bs)) if historical_bs[i].total_equity > 0]
            if roes:
                import statistics as _stats
                avg_roe = _stats.median(roes[-_roe_window:])

        assumptions_bank = AssumptionsBank(
            risk_free_rate=rf_dynamic,
            beta=beta_dynamic,
            erp=erp_vn,
            credit_growth=credit_growth,
            nim=nim,
            cir=cir,
            credit_cost=credit_cost,
            dividend_payout_ratio=0.15 if ticker in ["VCB", "CTG", "BID"] else 0.25,
            terminal_growth_rate=0.02,
            sustainable_roe=avg_roe
        )

        from valuation.data_access.freshness import data_freshness_flags
        return CompanyBank(
            ticker=ticker,
            name=meta.company_name,
            current_price=current_price,
            shares_outstanding=shares,
            historical_is=historical_is,
            historical_bs=historical_bs,
            assumptions=assumptions_bank,
            data_flags=data_freshness_flags(db, ticker)
        )
    else:
        # Phi tài chính: dùng MEDIAN (không phải mean) cho growth & margin.
        # Median robust với năm bùng nổ/sập → chính là biên/tăng trưởng MID-CYCLE,
        # đặc biệt quan trọng cho ngành cyclical (thép/hóa chất/dầu khí) tránh
        # extrapolate đỉnh chu kỳ ra vĩnh viễn (chống overvaluation hệ thống).
        import statistics
        med_growth = 0.10
        med_ebit_m = 0.15
        if len(historical_is) >= 2:
            growths = [(historical_is[i].revenue - historical_is[i-1].revenue) / historical_is[i-1].revenue for i in range(1, len(historical_is)) if historical_is[i-1].revenue > 0]
            if growths:
                med_growth = statistics.median(growths)
            ebits = [historical_is[i].ebit / historical_is[i].revenue for i in range(len(historical_is)) if historical_is[i].revenue > 0]
            if ebits:
                med_ebit_m = statistics.median(ebits)
        # Chặn biên hợp lý: growth trong [0, 25%], margin >= 0
        med_growth = min(max(med_growth, 0.0), 0.25)
        med_ebit_m = max(med_ebit_m, 0.0)

        # Mức đầu tư CapEx, khấu hao và NWC.
        # capex_to_rev, depr_to_rev lấy TỪ DỮ LIỆU THẬT (median, robust ngoại lệ).
        # KHÔNG hardcode depr = 4%: mức đó bơm "tiền ảo" vào FCFF cho các DN nhẹ
        # tài sản (vd PNJ D&A thực ~0.2%, PLX ~0.7%) → overvaluation hệ thống.
        capex_to_rev = 0.05
        depr_to_rev = 0.04   # fallback chỉ dùng khi thiếu dữ liệu D&A
        nwc_to_rev = 0.12

        if historical_cf and historical_is:
            # Ưu tiên capex 3 KỲ GẦN NHẤT (không median toàn lịch sử) — công ty
            # vừa qua đỉnh đầu tư (VD: HPG hậu Dung Quất 2, capex/DT lịch sử
            # 3%-49%) sẽ bị chiếu nhầm capex thời xây dựng cho cả 5 năm tới nếu
            # trộn lẫn với giai đoạn cũ. 3 kỳ = cùng cửa sổ với effective_tax
            # bên dưới, đủ mượt để không bị lệch bởi 1 kỳ TTM nhiễu.
            # Điều tra 2026-07, xem DECISIONS.md.
            recent_cf, recent_is = historical_cf[-3:], historical_is[-3:]
            capexs_recent = [cf.capex / is_rec.revenue for cf, is_rec in zip(recent_cf, recent_is) if is_rec.revenue > 0]
            if capexs_recent:
                capex_to_rev = statistics.median(capexs_recent)
            else:
                capexs_all = [cf.capex / is_rec.revenue for cf, is_rec in zip(historical_cf, historical_is) if is_rec.revenue > 0]
                if capexs_all:
                    capex_to_rev = statistics.median(capexs_all)

            deprs = [cf.depreciation / is_rec.revenue for cf, is_rec in zip(historical_cf, historical_is) if is_rec.revenue > 0 and cf.depreciation > 0]
            if deprs:
                depr_to_rev = statistics.median(deprs)

            dsos, dios, dpos = [], [], []
            for bs, is_rec in zip(historical_bs, historical_is):
                if is_rec.revenue > 0:
                    dsos.append((bs.receivables / is_rec.revenue) * 365)
                if is_rec.cogs > 0:
                    dios.append((bs.inventory / is_rec.cogs) * 365)
                    dpos.append((bs.accounts_payable / is_rec.cogs) * 365)
            
            dso_avg = sum(dsos) / len(dsos) if dsos else 30.0
            dio_avg = sum(dios) / len(dios) if dios else 30.0
            dpo_avg = sum(dpos) / len(dpos) if dpos else 30.0

        # --- B5 FIX: Đọc tax_rate và ev_ebitda từ config theo sector ---
        # (không hardcode per-ticker, vi phạm AGENTS.md no-magic-numbers)
        sector_str = (meta.sector or "").lower()

        # GUARDRAIL CYCLICAL (G3): ngành chu kỳ → terminal margin ép về mid-cycle.
        _CYCLICAL_KW = ("steel", "metal", "chemical", "oil", "gas", "petroleum",
                        "fuel", "resource", "shipping", "rubber", "fertil")
        is_cyclical = any(k in sector_str for k in _CYCLICAL_KW)
        mid_cycle_margin = med_ebit_m if is_cyclical else None

        # 1. Effective tax rate: ưu tiên tính từ lịch sử >= 3 năm
        _tax_rates_hist = []
        for _is in historical_is[-3:]:
            _pbt = _is.ebit - _is.interest_expense
            if _pbt > 0 and _is.tax > 0:
                _tax_rates_hist.append(_is.tax / _pbt)
        if len(_tax_rates_hist) >= 2:
            effective_tax = min(max(sum(_tax_rates_hist) / len(_tax_rates_hist), 0.05), 0.25)
        else:
            _sector_tax_map = config_defaults.get('sector_tax_rates', {})
            if any(k in sector_str for k in ['tech', 'information', 'software']):
                effective_tax = _sector_tax_map.get('technology', 0.20)
            elif any(k in sector_str for k in ['industrial', 'zone']):
                effective_tax = _sector_tax_map.get('industrial_zone', 0.20)
            elif any(k in sector_str for k in ['agri', 'food']):
                effective_tax = _sector_tax_map.get('agriculture', 0.20)
            else:
                effective_tax = _sector_tax_map.get('default', 0.20)

        # 2. EV/EBITDA target: ƯU TIÊN nhóm từ routing.json (nguồn sự thật ngành
        # — D14), fallback keyword trên DB sector. Tránh lỗi ngành DB rộng
        # "Industrial Goods & Services" (gồm vận tải/cảng như PVT/HAH) bị khớp
        # nhầm 'industrial' → industrial_zone (12x) → định giá phóng đại.
        _ev_map = config_defaults.get('sector_ev_ebitda', {})
        _GROUP_EV_KEY = {
            "Thép": "steel", "Dầu khí": "oil_gas", "Hàng không": "aviation",
            "Cảng": "transport", "Vận tải": "transport", "Hàng hải": "transport",
            "Điện": "utilities", "Nước": "utilities", "Tiện ích": "utilities",
            "Công nghệ": "technology", "Bán lẻ": "retail", "Tiêu dùng": "consumer",
            "Dược": "consumer", "KCN": "industrial_zone", "BĐS": "real_estate",
            "Cao su/NN": "agriculture",
        }
        _ev_ebitda_from_group = None
        try:
            from valuation.engine.sector_router import route as _route_lookup
            _grp = (_route_lookup(ticker) or {}).get("group")
            _key = _GROUP_EV_KEY.get(_grp)
            if _key and _ev_map.get(_key) is not None:
                _ev_ebitda_from_group = _ev_map.get(_key)
        except Exception:
            _ev_ebitda_from_group = None

        if _ev_ebitda_from_group is not None:
            ev_ebitda_target = _ev_ebitda_from_group
        elif any(k in sector_str for k in ['tech', 'information', 'software']):
            ev_ebitda_target = _ev_map.get('technology', 7.0)
        elif any(k in sector_str for k in ['real', 'estate', 'property']):
            ev_ebitda_target = _ev_map.get('real_estate', 7.0)
        elif any(k in sector_str for k in ['steel', 'metal', 'material']):
            ev_ebitda_target = _ev_map.get('steel', 7.0)
        elif any(k in sector_str for k in ['consumer', 'food', 'beverage']):
            ev_ebitda_target = _ev_map.get('consumer', 7.0)
        elif any(k in sector_str for k in ['retail', 'wholesale']):
            ev_ebitda_target = _ev_map.get('retail', 7.0)
        elif any(k in sector_str for k in ['oil', 'petroleum', 'fuel']):
            # Phân phối/lọc dầu (PLX, BSR): biên mỏng, commodity → multiple thấp.
            # PHẢI đứng trước nhánh utilities vì "oil & gas" chứa 'gas'.
            ev_ebitda_target = _ev_map.get('oil_gas', 6.0)
        elif any(k in sector_str for k in ['travel', 'airline', 'aviation', 'leisure']):
            ev_ebitda_target = _ev_map.get('aviation', 6.0)
        elif any(k in sector_str for k in ['util', 'electric', 'power', 'gas']):
            ev_ebitda_target = _ev_map.get('utilities', 7.0)
        elif any(k in sector_str for k in ['industrial', 'zone']):
            ev_ebitda_target = _ev_map.get('industrial_zone', 7.0)
        else:
            ev_ebitda_target = _ev_map.get('default', 7.0)
        if ev_ebitda_target is None:
            ev_ebitda_target = 7.0

        # Revenue growth FADE từ median lịch sử (năm 1) về tăng trưởng GDP danh nghĩa
        # dài hạn (năm 5) — mean-reversion, chống extrapolate tăng trưởng đỉnh chu kỳ.
        g_lt = config_defaults.get('long_run_nominal_gdp_growth', 0.08)

        # D32 — NĂM GỐC DỰ PHÓNG (sau cờ, mặc định TRAILING = y hệt hành vi cũ).
        # Mô hình vốn dựng năm 1 từ median tăng trưởng LỊCH SỬ, tức nhìn hoàn toàn
        # về quá khứ, trong khi CTCK định giá trên dự phóng FY+1 — nguồn gốc khoảng
        # lệch âm cấu trúc của nhóm DCF (-30%).
        _fwd_flags: List[str] = []
        _fy1_growth = med_growth
        from valuation.forecast.base_year import (
            base_year_mode, build_forward_base, revenue_growth_path,
        )
        if base_year_mode() == "FORWARD":
            _q_rev = _quarterly_revenues(db, ticker)
            _fwd = build_forward_base(_q_rev, med_growth, sector_group=_sector_for_overlay)
            _fy1_growth = _fwd.fy1_revenue_growth
            _fwd_flags = list(_fwd.flags)
            if _fwd.method == "QUARTERLY_MOMENTUM":
                _fwd_flags.append(
                    f"FWD_BASE_YEAR: năm 1 {med_growth:+.1%} (median lịch sử) -> "
                    f"{_fy1_growth:+.1%} (động lượng 4 quý)")
        revenue_growth = revenue_growth_path(_fy1_growth, g_lt, years=5)
        revenue_growth = overlay_revenue_growth(revenue_growth, _sector_for_overlay, _macro_ctx)

        # Ước lượng debt_repayment_rate và new_borrowing_rate từ lịch sử
        debt_repay_default = 0.20
        new_borrow_default = 0.05
        if len(historical_bs) >= 2 and len(historical_is) >= 2:
            _repay_rates = []
            _borrow_rates = []
            for j in range(1, len(historical_bs)):
                prev_total_debt = historical_bs[j-1].short_term_debt + historical_bs[j-1].long_term_debt
                curr_total_debt = historical_bs[j].short_term_debt + historical_bs[j].long_term_debt
                curr_rev = historical_is[j].revenue
                if prev_total_debt > 0:
                    # Nếu nợ giảm → có trả nợ ròng
                    net_change = curr_total_debt - prev_total_debt
                    if net_change < 0:
                        _repay_rates.append(abs(net_change) / prev_total_debt)
                    else:
                        _repay_rates.append(debt_repay_default)
                if curr_rev > 0:
                    net_change = curr_total_debt - prev_total_debt
                    if net_change > 0:
                        _borrow_rates.append(net_change / curr_rev)
                    else:
                        _borrow_rates.append(new_borrow_default)
            if _repay_rates:
                debt_repay_default = min(max(sum(_repay_rates) / len(_repay_rates), 0.05), 0.50)
            if _borrow_rates:
                new_borrow_default = min(max(sum(_borrow_rates) / len(_borrow_rates), 0.0), 0.20)

        assumptions = Assumptions(
            risk_free_rate=rf_dynamic,
            beta=beta_dynamic,
            erp=erp_vn,
            cost_of_debt=rf_dynamic + 0.03,
            tax_rate=effective_tax,
            revenue_growth=revenue_growth,
            ebit_margin=[med_ebit_m] * 5,
            mid_cycle_ebit_margin=mid_cycle_margin,
            capex_to_revenue=[capex_to_rev] * 5,
            depr_to_revenue=[depr_to_rev] * 5,
            dso=[dso_avg] * 5,
            dio=[dio_avg] * 5,
            dpo=[dpo_avg] * 5,
            interest_rate=[rf_dynamic + 0.03] * 5,
            debt_repayment_rate=[debt_repay_default] * 5,
            new_borrowing_rate=[new_borrow_default] * 5,
            terminal_growth_rate=0.02,
            target_ev_ebitda=ev_ebitda_target,
            weight_dcf=0.5
        )

        from valuation.data_access.freshness import data_freshness_flags
        return Company(
            ticker=ticker,
            name=meta.company_name,
            sector=meta.sector or "Unknown",
            current_price=current_price,
            shares_outstanding=shares,
            historical_is=historical_is,
            historical_bs=historical_bs,
            historical_cf=historical_cf,
            assumptions=assumptions,
            data_flags=data_freshness_flags(db, ticker)
        )


def compute_midcycle_ebit_margin(db: Session, ticker: str) -> float | None:
    """
    Biên EBIT MID-CYCLE = median của (EBIT/Doanh thu) qua các năm lịch sử.
    Dùng cho guardrail G3: terminal margin ngành cyclical ép về mức này, không
    ngoại suy biên đỉnh. Trả None nếu không đủ dữ liệu.
    """
    import statistics
    try:
        company = build_company_data(db, ticker, mode="FY")
    except Exception:
        return None
    if not isinstance(company, Company):
        return None
    margins = [
        is_.ebit / is_.revenue
        for is_ in company.historical_is
        if is_.revenue and is_.revenue > 0
    ]
    return statistics.median(margins) if margins else None
