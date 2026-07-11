"""
TTM Helper — Utility tổng hợp Trailing Twelve Months từ dữ liệu quý trong DB.

Mục đích:
- Lấy giá trị Balance Sheet (quý cuối cùng)
- Tổng hợp Income Statement / Cash Flow theo TTM (sum 4 quý gần nhất)
- Tính shares outstanding từ Vốn điều lệ / mệnh giá
- Tính các driver lịch sử (NIM, CIR, credit growth) từ dữ liệu thật
"""
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc
from valuation.db.models import FinancialsQuarterly, MacroSeries



def _find_latest_4_quarters(db: Session, ticker: str) -> List[Tuple[int, int]]:
    """Tìm 4 quý gần nhất có dữ liệu cho ticker."""
    rows = (
        db.query(
            FinancialsQuarterly.fiscal_year,
            FinancialsQuarterly.fiscal_quarter,
        )
        .filter(
            FinancialsQuarterly.ticker == ticker,
            FinancialsQuarterly.fiscal_quarter > 0,  # Bỏ annual (Q=0)
        )
        .distinct()
        .order_by(
            desc(FinancialsQuarterly.fiscal_year),
            desc(FinancialsQuarterly.fiscal_quarter),
        )
        .limit(4)
        .all()
    )
    return [(r[0], r[1]) for r in rows]


def _query_value(
    db: Session,
    ticker: str,
    keywords: List[str],
    year: int,
    quarter: int,
) -> float:
    """
    Tìm giá trị cho một line_item bằng keyword matching.

    Chiến lược matching (theo thứ tự ưu tiên):
    1. Line item BẮT ĐẦU bằng keyword (startswith) → match chính xác nhất
    2. Line item CHỨA keyword (contains) → fallback

    Ví dụ: keyword='IX. Chi phí hoạt động' sẽ match đúng dòng tổng
    chứ không bị shadowed bởi '4. Chi phí hoạt động dịch vụ'.
    """
    rows = (
        db.query(FinancialsQuarterly)
        .filter(
            FinancialsQuarterly.ticker == ticker,
            FinancialsQuarterly.fiscal_year == year,
            FinancialsQuarterly.fiscal_quarter == quarter,
        )
        .all()
    )
    # Pass 1: ưu tiên startswith
    for kw in keywords:
        kw_lower = kw.lower()
        for r in rows:
            if r.line_item.lower().startswith(kw_lower):
                return float(r.value) if r.value is not None else 0.0

    # Pass 2: fallback contains
    for kw in keywords:
        kw_lower = kw.lower()
        for r in rows:
            if kw_lower in r.line_item.lower():
                return float(r.value) if r.value is not None else 0.0
    return 0.0


def get_latest_balance(
    db: Session, ticker: str, keywords: List[str]
) -> float:
    """
    Lấy giá trị Balance Sheet từ quý gần nhất.
    Dùng cho: Tổng tài sản, VCSH, Cho vay KH, Tiền gửi KH...
    """
    quarters = _find_latest_4_quarters(db, ticker)
    if not quarters:
        return 0.0
    latest_yr, latest_q = quarters[0]
    return _query_value(db, ticker, keywords, latest_yr, latest_q)


def get_ttm_value(
    db: Session, ticker: str, keywords: List[str]
) -> float:
    """
    Tổng hợp TTM (sum 4 quý gần nhất) cho Income Statement items.
    Dùng cho: LNST, Thu nhập lãi thuần, Chi phí hoạt động...
    """
    quarters = _find_latest_4_quarters(db, ticker)
    if len(quarters) < 4:
        # Không đủ 4 quý → annualize quý có sẵn
        if not quarters:
            return 0.0
        total = sum(
            _query_value(db, ticker, keywords, yr, q)
            for yr, q in quarters
        )
        return total * (4 / len(quarters))

    return sum(
        _query_value(db, ticker, keywords, yr, q)
        for yr, q in quarters
    )


def get_mid_cycle_average(
    db: Session, ticker: str, keywords: List[str], years: int = 5
) -> float:
    """
    Tính trung bình của một chỉ tiêu (như LNST, EBITDA) trong chu kỳ 'years' năm (mặc định 5 năm).
    Nếu chưa đủ 5 năm thì tính trung bình số năm có sẵn.
    """
    rows = (
        db.query(
            FinancialsQuarterly.fiscal_year,
            FinancialsQuarterly.fiscal_quarter,
        )
        .filter(
            FinancialsQuarterly.ticker == ticker,
            FinancialsQuarterly.fiscal_quarter > 0,
        )
        .distinct()
        .order_by(
            desc(FinancialsQuarterly.fiscal_year),
            desc(FinancialsQuarterly.fiscal_quarter),
        )
        .limit(years * 4)
        .all()
    )
    if not rows:
        return 0.0
        
    # Tính tổng tất cả giá trị
    total_val = sum(
        _query_value(db, ticker, keywords, yr, q) for yr, q in rows
    )
    
    # Số năm thực tế có dữ liệu
    actual_years = len(rows) / 4.0
    if actual_years < 1.0:
        actual_years = 1.0
        
    return total_val / actual_years


def get_shares_outstanding(db: Session, ticker: str) -> float:
    """
    Tính shares outstanding từ:
    1. Trực tiếp từ outstanding_shares_volume hay shares_outstanding_value (HPG, SSI)
    2. Vốn điều lệ / Vốn góp / paid_in_capital (VCB, FPT) chia cho mệnh giá (10,000 VND/cp).
    """
    direct_shares = get_latest_balance(db, ticker, ["outstanding_shares_volume", "shares_outstanding_value"])
    if direct_shares > 0:
        return direct_shares

    # Vốn điều lệ thật: charter_capital/paid_in_capital. KHÔNG dùng owners_equity
    # làm proxy (đó là TỔNG vốn CSH, không phải vốn điều lệ → phóng đại số cp).
    von_dieu_le = get_latest_balance(
        db, ticker, ["charter_capital", "Vốn điều lệ", "Vốn góp của chủ sở hữu", "paid_in_capital", "common_shares"]
    )
    if von_dieu_le > 0:
        return von_dieu_le / 10_000  # Mệnh giá cổ phiếu VN = 10,000 VND

    raise ValueError(f"Không tìm được Vốn điều lệ hay Số lượng cổ phiếu cho {ticker} trong DB")


def get_balance_at_quarter(
    db: Session,
    ticker: str,
    keywords: List[str],
    year: int,
    quarter: int,
) -> float:
    """Lấy giá trị BS tại một quý cụ thể."""
    return _query_value(db, ticker, keywords, year, quarter)


def compute_historical_nim(
    db: Session, ticker: str, n_quarters: int = 4
) -> float:
    """
    Tính NIM thực tế TTM = Thu nhập lãi thuần TTM / Tổng tài sản trung bình.
    """
    quarters = _find_latest_4_quarters(db, ticker)
    if len(quarters) < n_quarters:
        return 0.0

    nii_ttm = sum(
        _query_value(db, ticker, ["net_interest_income", "Thu nhập lãi thuần"], yr, q)
        for yr, q in quarters[:n_quarters]
    )
    # Tổng tài sản: đầu kỳ (quý cũ nhất) và cuối kỳ (quý mới nhất)
    ta_end = _query_value(
        db, ticker, ["total_assets", "TỔNG TÀI SẢN"], quarters[0][0], quarters[0][1]
    )
    ta_start = _query_value(
        db, ticker, ["total_assets", "TỔNG TÀI SẢN"], quarters[-1][0], quarters[-1][1]
    )
    avg_ta = (ta_start + ta_end) / 2
    if avg_ta <= 0:
        return 0.0
    return nii_ttm / avg_ta


def compute_historical_cir(
    db: Session, ticker: str, n_quarters: int = 4
) -> float:
    """
    CIR TTM = Chi phí hoạt động TTM / Tổng thu nhập hoạt động TTM.
    """
    quarters = _find_latest_4_quarters(db, ticker)
    if len(quarters) < n_quarters:
        return 0.0

    opex_ttm = abs(sum(
        _query_value(db, ticker, ["general_and_admin_expenses", "IX. Chi phí hoạt động", "Chi phí hoạt động"], yr, q)
        for yr, q in quarters[:n_quarters]
    ))
    toi_ttm = sum(
        _query_value(db, ticker, ["total_operating_income", "VIII. Tổng thu nhập hoạt động", "Tổng thu nhập hoạt động"], yr, q)
        for yr, q in quarters[:n_quarters]
    )
    if toi_ttm <= 0:
        return 0.0
    return opex_ttm / toi_ttm


def compute_historical_credit_growth(
    db: Session, ticker: str
) -> float:
    """
    Credit growth YoY = (Cho vay KH quý cuối - Cho vay KH cùng quý năm trước) / Cho vay KH năm trước.
    """
    quarters = _find_latest_4_quarters(db, ticker)
    if not quarters:
        return 0.0
    latest_yr, latest_q = quarters[0]

    loans_now = _query_value(
        db, ticker, ["loans_and_advances_to_customers_net", "loans_and_advances_to_customers", "1. Cho vay khách hàng"], latest_yr, latest_q
    )
    loans_prev = _query_value(
        db, ticker, ["loans_and_advances_to_customers_net", "loans_and_advances_to_customers", "1. Cho vay khách hàng"], latest_yr - 1, latest_q
    )
    if loans_prev <= 0:
        return 0.0
    return (loans_now - loans_prev) / loans_prev


def compute_historical_credit_cost(
    db: Session, ticker: str, n_quarters: int = 4
) -> float:
    """
    Credit cost TTM = Chi phí dự phòng TTM / Cho vay KH trung bình.
    """
    quarters = _find_latest_4_quarters(db, ticker)
    if len(quarters) < n_quarters:
        return 0.0

    provision_ttm = abs(sum(
        _query_value(
            db, ticker,
            ["provision_for_credit_losses", "Chi phí dự phòng rủi ro tín dụng", "Chi phí dự phòng"],
            yr, q,
        )
        for yr, q in quarters[:n_quarters]
    ))
    loans_end = _query_value(
        db, ticker, ["loans_and_advances_to_customers_net", "loans_and_advances_to_customers", "1. Cho vay khách hàng"],
        quarters[0][0], quarters[0][1],
    )
    loans_start = _query_value(
        db, ticker, ["loans_and_advances_to_customers_net", "loans_and_advances_to_customers", "1. Cho vay khách hàng"],
        quarters[-1][0], quarters[-1][1],
    )
    avg_loans = (loans_start + loans_end) / 2
    if avg_loans <= 0:
        return 0.0
    return provision_ttm / avg_loans

def get_latest_tpcp_10y(db: Session) -> float:
    """Lấy lợi suất TPCP VN 10Y mới nhất từ bảng macro_series."""
    row = (
        db.query(MacroSeries)
        .filter(MacroSeries.indicator_code == "TPCP_10Y")
        .order_by(desc(MacroSeries.date))
        .first()
    )
    if row and row.value is not None:
        return float(row.value)
    return 0.032  # Fallback

def _beta_from_db(db: Session, ticker: str) -> Optional[float]:
    """Beta từ giá DB (PricesDaily) — KHÔNG gọi live. None nếu thiếu dữ liệu/VNINDEX."""
    import numpy as np
    import datetime
    from valuation.db.models import PricesDaily
    start = datetime.date.today() - datetime.timedelta(days=2 * 365)

    def series(tk):
        rows = (db.query(PricesDaily.trade_date, PricesDaily.close)
                .filter(PricesDaily.ticker == tk, PricesDaily.trade_date >= start)
                .order_by(PricesDaily.trade_date).all())
        return {d: float(c) for d, c in rows if c is not None}

    st, si = series(ticker), series("VNINDEX")
    common = sorted(set(st) & set(si))
    if len(common) < 30:
        return None
    pt = np.array([st[d] for d in common])
    pi = np.array([si[d] for d in common])
    rt, ri = np.diff(pt) / pt[:-1], np.diff(pi) / pi[:-1]
    var = np.var(ri, ddof=1)
    if var <= 0:
        return None
    return max(0.5, min(float(np.cov(rt, ri)[0, 1] / var), 1.5))


def _blume_adjust(raw_beta: float) -> float:
    """Điều chỉnh Blume: beta_dùng = 0.67·beta_thô + 0.33·1.0.

    Chuẩn ngành (Bloomberg, Value Line) để SỬA SAI SỐ ƯỚC LƯỢNG beta — beta hồi
    quy có xu hướng hồi về 1.0 và bị thiên lệch xuống cho mã thanh khoản mỏng/
    mới niêm yết (vd NAB beta thô 0.59 phi thực tế cho bank nhỏ). Kéo các beta
    cực đoan về gần 1, ít đổi các beta vốn đã gần 1. Chặn dải hợp lý [0.6, 1.5].
    """
    adj = 0.67 * raw_beta + 0.33 * 1.0
    return max(0.6, min(adj, 1.5))


def estimate_vcb_beta(db: Session, ticker: str = "VCB") -> float:
    """
    Ước lượng beta vs VNINDEX từ giá 2 năm, có ĐIỀU CHỈNH BLUME (chống thiên
    lệch ước lượng). ƯU TIÊN giá DB (PricesDaily, không gọi live — an toàn cho
    batch); chỉ fallback live vnstock nếu DB thiếu VNINDEX. Fallback cuối 0.7674.
    """
    import numpy as np
    import pandas as pd
    from valuation.ingest.vnstock_client import vnstock_client
    import datetime

    db_beta = _beta_from_db(db, ticker)
    if db_beta is not None:
        return _blume_adjust(db_beta)

    try:
        # Lấy dữ liệu 2 năm trước đến nay
        start_date = (datetime.date.today() - datetime.timedelta(days=2*365)).strftime("%Y-%m-%d")
        
        # Tải giá lịch sử
        df_ticker = vnstock_client.get_historical_prices(ticker, start_date)
        df_vni = vnstock_client.get_historical_prices("VNINDEX", start_date)
        
        if df_ticker.empty or df_vni.empty:
            return 0.7674  # Fallback
            
        df_t = df_ticker[['time', 'close']].rename(columns={'close': 'close_t'})
        df_i = df_vni[['time', 'close']].rename(columns={'close': 'close_i'})
        
        df = pd.merge(df_t, df_i, on='time')
        if len(df) < 30:
            return 0.7674
            
        df['ret_t'] = df['close_t'].pct_change()
        df['ret_i'] = df['close_i'].pct_change()
        df = df.dropna()
        
        cov = np.cov(df['ret_t'], df['ret_i'])[0, 1]
        var = np.var(df['ret_i'], ddof=1)
        if var > 0:
            beta = float(cov / var)
            # Điều chỉnh Blume (chống thiên lệch ước lượng) + chặn dải hợp lý.
            return _blume_adjust(max(0.5, min(beta, 1.5)))
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Error estimating beta for {ticker}: {e}. Fallback to 0.7674")
        
    return 0.7674  # Fallback

def build_vcb_current_financials(db: Session, ticker: str = "VCB") -> dict:
    """
    Xây dựng dict current_financials cho VCB từ dữ liệu thật trong DB.
    BS items: lấy quý cuối.
    IS items: tổng hợp TTM (4 quý).
    """
    # Ưu tiên key tiếng Anh (vnstock English line_item), fallback tiếng Việt.
    nii = get_ttm_value(db, ticker, ["net_interest_income", "I. Thu nhập lãi thuần", "Thu nhập lãi thuần"])
    toi = get_ttm_value(db, ticker, ["total_operating_income", "VIII. Tổng thu nhập hoạt động", "Tổng thu nhập hoạt động"])
    non_interest_income = toi - nii

    return {
        "total_equity": get_latest_balance(db, ticker, ["owners_equity", "shareholders_equity", "Vốn chủ sở hữu"]),
        "total_assets": get_latest_balance(db, ticker, ["total_assets", "TỔNG TÀI SẢN"]),
        "customer_loans": get_latest_balance(db, ticker, ["loans_and_advances_to_customers_net", "loans_and_advances_to_customers", "1. Cho vay khách hàng"]),
        "customer_deposits": get_latest_balance(
            db, ticker, ["deposits_from_customers", "Tiền gửi của khách hàng"]
        ),
        "net_income": get_ttm_value(
            db, ticker, ["net_profit_loss_after_tax", "XIV. Lợi nhuận sau thuế", "Lợi nhuận sau thuế"]
        ),
        "net_interest_income": nii,
        "non_interest_income": non_interest_income,
        "shares_outstanding": get_shares_outstanding(db, ticker),
        "current_price": 0.0,  # Được gán bên ngoài từ PricesDaily
    }


def build_vcb_assumptions_from_history(
    db: Session,
    ticker: str = "VCB",
    coe_config: Optional[dict] = None,
) -> dict:
    """
    Xây dựng assumptions cho VCB từ lịch sử thật, có declining schedule.

    COE Convention (Chốt từ nguyên tắc — chuẩn Damodaran):
      rf  = TPCP VN 10Y (lấy động từ DB)
      erp = Mature market ERP + Country Risk Premium VN (mature + CRP ≈ 8.2%)
      beta = ước lượng từ giá VCB vs VNINDEX
      COE = rf + beta * erp
    """
    rf_dynamic = get_latest_tpcp_10y(db)
    beta_dynamic = estimate_vcb_beta(db, ticker)

    # VND-base convention: erp = mature + CRP (CRP là rủi ro vốn cổ phần TT mới
    # nổi, tách biệt rủi ro vỡ nợ trong TPCP). Nguồn sự thật: coe.get_erp()
    from valuation.engine.coe import get_erp
    erp_vn = get_erp()

    if coe_config is None:
        coe_config = {
            "risk_free_rate": rf_dynamic,
            "erp": erp_vn,
            "beta": beta_dynamic,
            "terminal_growth_rate": 0.02,
        }
    else:
        # Nếu là giá trị cũ từ config cứng, ta ghi đè bằng giá trị động
        if coe_config.get("risk_free_rate") == 0.043:
            coe_config["risk_free_rate"] = rf_dynamic
        if coe_config.get("beta") == 1.0:
            coe_config["beta"] = beta_dynamic
        # Ghi đè ERP cũ (mature-only 4.5% / fallback 6.0%) bằng erp đúng convention
        if coe_config.get("erp") in (0.045, 0.060) or coe_config.get("erp") is None:
            coe_config["erp"] = erp_vn

    # Lấy driver thật từ DB
    hist_nim = compute_historical_nim(db, ticker)
    hist_cir = compute_historical_cir(db, ticker)
    hist_credit_growth = compute_historical_credit_growth(db, ticker)
    hist_credit_cost = compute_historical_credit_cost(db, ticker)

    # Declining schedule: driver giảm dần về dài hạn (5 năm)
    # NIM: giảm ~10-15bps qua 5 năm
    nim_schedule = [
        hist_nim,
        hist_nim - 0.001,
        hist_nim - 0.002,
        hist_nim - 0.002,
        hist_nim - 0.003,
    ]
    # Credit growth: giảm dần từ mức hiện tại về ~8-10%
    cg_floor = 0.08
    cg_step = max(0, (hist_credit_growth - cg_floor) / 4)
    credit_growth_schedule = [
        hist_credit_growth,
        hist_credit_growth - cg_step,
        hist_credit_growth - 2 * cg_step,
        hist_credit_growth - 3 * cg_step,
        max(hist_credit_growth - 4 * cg_step, cg_floor),
    ]
    # CIR: cải thiện nhẹ
    cir_schedule = [
        hist_cir,
        hist_cir - 0.005,
        hist_cir - 0.010,
        hist_cir - 0.015,
        hist_cir - 0.020,
    ]
    # Credit cost: giảm nhẹ
    cc_schedule = [
        hist_credit_cost,
        hist_credit_cost,
        hist_credit_cost - 0.001,
        hist_credit_cost - 0.001,
        hist_credit_cost - 0.002,
    ]

    return {
        "credit_growth": credit_growth_schedule,
        "nim": nim_schedule,
        "cir": cir_schedule,
        "credit_cost": cc_schedule,
        "dividend_payout_ratio": 0.15,  # VCB payout thấp ~15%
        # ROE bền vững dài hạn cho terminal value (RI + justified P/B). Bank VN ROE
        # ~20% hiện tại bị cạnh tranh/tích lũy vốn nén dần; 15% là mức thận trọng,
        # tunable. Model chặn trên = min(terminal_roe, roe_ttm) — không bao giờ nâng.
        "terminal_roe": 0.15,
        "risk_free_rate": coe_config["risk_free_rate"],
        "beta": coe_config["beta"],
        "erp": coe_config["erp"],
        "terminal_growth_rate": coe_config["terminal_growth_rate"],
        # Driver config cho Greeks
        "drivers": {
            "nim": {"bump": 0.001},
            "cir": {"bump": 0.01},
            "credit_cost": {"bump": 0.001},
        },
        # Metadata
        "_source": "ttm_helper.build_vcb_assumptions_from_history",
        "_hist_nim": hist_nim,
        "_hist_cir": hist_cir,
        "_hist_credit_growth": hist_credit_growth,
        "_hist_credit_cost": hist_credit_cost,
    }


def build_fpt_current_financials(db: Session, ticker: str = "FPT") -> dict:
    """
    Xây dựng current_financials cho FPT từ DB (dùng line items tiếng Anh).
    """
    equity = get_latest_balance(db, ticker, ["owners_equity", "shareholders_equity", "capital_and_reserves", "Vốn chủ sở hữu"])
    assets = get_latest_balance(db, ticker, ["total_assets", "Tổng tài sản"])
    cash = get_latest_balance(db, ticker, ["cash_and_cash_equivalents", "Tiền và các khoản tương đương tiền"])
    
    st_borrow = get_latest_balance(db, ticker, ["short_term_borrowings", "Vay ngắn hạn"])
    lt_borrow = get_latest_balance(db, ticker, ["long_term_borrowings", "Vay dài hạn"])
    total_debt = st_borrow + lt_borrow
    
    net_sales = get_ttm_value(db, ticker, ["net_sales", "Doanh thu thuần"])
    net_income = get_ttm_value(db, ticker, ["net_profit_loss_after_tax", "Lợi nhuận sau thuế"])
    
    # EBITDA = operating_profit_loss + depreciation_and_amortization
    operating_profit = get_ttm_value(db, ticker, ["operating_profit_loss", "Lợi nhuận từ hoạt động kinh doanh"])
    depr = get_ttm_value(db, ticker, ["depreciation_and_amortization", "Khấu hao"])
    ebitda = operating_profit + depr if operating_profit > 0 or depr > 0 else net_income * 1.2
    
    return {
        "total_equity": equity,
        "total_assets": assets,
        "cash_and_equivalents": cash,
        "total_debt": total_debt,
        "total_revenue": net_sales,
        "net_income": net_income,
        "ebitda": ebitda,
        "shares_outstanding": get_shares_outstanding(db, ticker),
        "current_price": 0.0,
    }


def build_hpg_current_financials(db: Session, ticker: str = "HPG") -> dict:
    """
    Xây dựng current_financials cho HPG từ DB.
    """
    equity = get_latest_balance(db, ticker, ["owners_equity", "shareholders_equity", "capital_and_reserves", "Vốn chủ sở hữu"])
    assets = get_latest_balance(db, ticker, ["total_assets", "Tổng tài sản"])
    cash = get_latest_balance(db, ticker, ["cash_and_cash_equivalents", "Tiền và các khoản tương đương tiền"])
    st_invest = get_latest_balance(db, ticker, ["short_term_financial_investments", "Đầu tư tài chính ngắn hạn"])
    cash_total = cash + st_invest
    
    st_borrow = get_latest_balance(db, ticker, ["short_term_borrowings", "Vay ngắn hạn"])
    lt_borrow = get_latest_balance(db, ticker, ["long_term_borrowings", "Vay dài hạn"])
    total_debt = st_borrow + lt_borrow
    
    net_sales = get_ttm_value(db, ticker, ["net_revenue_from_goods_and_services_rendered", "net_sales", "Doanh thu thuần"])
    net_income = get_ttm_value(db, ticker, ["net_profit_loss_after_tax", "Lợi nhuận sau thuế"])
    
    # HPG: EBITDA thật từ vnstock có thể không có dòng "ebitda". Dự phòng EBITDA = EBIT + D&A.
    # EBIT = operating_profit_loss hoặc net_profit_loss_before_tax + interest_expenses.
    # Ta lấy ebitda từ DB, nếu bằng 0 thì tính toán xấp xỉ
    ebitda = get_ttm_value(db, ticker, ["ebitda"])
    if ebitda <= 0:
        operating_profit = get_ttm_value(db, ticker, ["operating_profit_loss", "Lợi nhuận từ hoạt động kinh doanh"])
        depr = get_ttm_value(db, ticker, ["depreciation_and_amortization", "Khấu hao"])
        ebitda = operating_profit + depr if operating_profit > 0 or depr > 0 else net_income * 1.2
    
    return {
        "total_equity": equity,
        "total_assets": assets,
        "cash_and_equivalents": cash_total,
        "total_debt": total_debt,
        "total_revenue": net_sales,
        "net_income": net_income,
        "ebitda": ebitda,
        "shares_outstanding": get_shares_outstanding(db, ticker),
        "current_price": 0.0,
    }


def build_ssi_current_financials(db: Session, ticker: str = "SSI") -> dict:
    """
    Xây dựng current_financials cho SSI từ DB.
    """
    equity = get_latest_balance(db, ticker, ["owners_equity", "shareholders_equity", "capital_and_reserves", "Vốn chủ sở hữu"])
    assets = get_latest_balance(db, ticker, ["total_assets", "Tổng tài sản"])
    net_sales = get_ttm_value(db, ticker, ["net_revenue_from_goods_and_services_rendered", "net_sales", "Doanh thu thuần"])
    net_income = get_ttm_value(db, ticker, ["net_profit_loss_after_tax", "Lợi nhuận sau thuế"])
    
    return {
        "total_equity": equity,
        "total_assets": assets,
        "total_revenue": net_sales,
        "net_income": net_income,
        "shares_outstanding": get_shares_outstanding(db, ticker),
        "current_price": 0.0,
    }


def build_dgc_current_financials(db: Session, ticker: str = "DGC") -> dict:
    """
    Xây dựng current_financials cho DGC từ DB.
    """
    equity = get_latest_balance(db, ticker, ["owners_equity", "shareholders_equity", "capital_and_reserves", "Vốn chủ sở hữu"])
    assets = get_latest_balance(db, ticker, ["total_assets", "Tổng tài sản"])
    cash = get_latest_balance(db, ticker, ["cash_and_cash_equivalents", "Tiền và các khoản tương đương tiền"])
    st_invest = get_latest_balance(db, ticker, ["short_term_financial_investments", "Đầu tư tài chính ngắn hạn"])
    cash_total = cash + st_invest
    
    st_borrow = get_latest_balance(db, ticker, ["short_term_borrowings", "Vay ngắn hạn"])
    lt_borrow = get_latest_balance(db, ticker, ["long_term_borrowings", "Vay dài hạn"])
    total_debt = st_borrow + lt_borrow
    
    net_sales = get_ttm_value(db, ticker, ["net_revenue_from_goods_and_services_rendered", "net_sales", "Doanh thu thuần"])
    net_income = get_ttm_value(db, ticker, ["net_profit_loss_after_tax", "Lợi nhuận sau thuế"])
    
    # EBITDA = operating_profit_loss + depreciation_and_amortization
    ebitda = get_ttm_value(db, ticker, ["ebitda"])
    if ebitda <= 0:
        operating_profit = get_ttm_value(db, ticker, ["operating_profit_loss", "Lợi nhuận từ hoạt động kinh doanh"])
        depr = get_ttm_value(db, ticker, ["depreciation_and_amortization", "Khấu hao"])
        ebitda = operating_profit + depr if operating_profit > 0 or depr > 0 else net_income * 1.2
        
    return {
        "total_equity": equity,
        "total_assets": assets,
        "cash_and_equivalents": cash_total,
        "total_debt": total_debt,
        "total_revenue": net_sales,
        "net_income": net_income,
        "ebitda": ebitda,
        "shares_outstanding": get_shares_outstanding(db, ticker),
        "current_price": 0.0,
    }

