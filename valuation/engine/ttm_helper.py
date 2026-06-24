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


def get_shares_outstanding(db: Session, ticker: str) -> float:
    """
    Tính shares outstanding từ Vốn điều lệ / mệnh giá (10,000 VND/cp).
    Fallback: dùng keyword "Vốn góp của chủ sở hữu" nếu không tìm thấy VĐL.
    """
    von_dieu_le = get_latest_balance(
        db, ticker, ["Vốn điều lệ"]
    )
    if von_dieu_le > 0:
        return von_dieu_le / 10_000  # Mệnh giá cổ phiếu VN = 10,000 VND

    # Fallback
    von_gop = get_latest_balance(
        db, ticker, ["Vốn góp của chủ sở hữu"]
    )
    if von_gop > 0:
        return von_gop / 10_000

    raise ValueError(f"Không tìm được Vốn điều lệ cho {ticker} trong DB")


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
        _query_value(db, ticker, ["Thu nhập lãi thuần"], yr, q)
        for yr, q in quarters[:n_quarters]
    )
    # Tổng tài sản: đầu kỳ (quý cũ nhất) và cuối kỳ (quý mới nhất)
    ta_end = _query_value(
        db, ticker, ["TỔNG TÀI SẢN"], quarters[0][0], quarters[0][1]
    )
    ta_start = _query_value(
        db, ticker, ["TỔNG TÀI SẢN"], quarters[-1][0], quarters[-1][1]
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
        _query_value(db, ticker, ["IX. Chi phí hoạt động", "Chi phí hoạt động"], yr, q)
        for yr, q in quarters[:n_quarters]
    ))
    toi_ttm = sum(
        _query_value(db, ticker, ["VIII. Tổng thu nhập hoạt động", "Tổng thu nhập hoạt động"], yr, q)
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
        db, ticker, ["1. Cho vay khách hàng"], latest_yr, latest_q
    )
    loans_prev = _query_value(
        db, ticker, ["1. Cho vay khách hàng"], latest_yr - 1, latest_q
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
            ["Chi phí dự phòng rủi ro tín dụng", "Chi phí dự phòng"],
            yr, q,
        )
        for yr, q in quarters[:n_quarters]
    ))
    loans_end = _query_value(
        db, ticker, ["1. Cho vay khách hàng"],
        quarters[0][0], quarters[0][1],
    )
    loans_start = _query_value(
        db, ticker, ["1. Cho vay khách hàng"],
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

def estimate_vcb_beta(db: Session, ticker: str = "VCB") -> float:
    """
    Ước lượng beta của ticker so với VNINDEX từ giá lịch sử 2 năm qua.
    Sử dụng vnstock_client để lấy dữ liệu động. Fallback về 0.7674 nếu có lỗi.
    """
    import numpy as np
    import pandas as pd
    from valuation.ingest.vnstock_client import vnstock_client
    import datetime

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
            # Giới hạn beta trong khoảng hợp lý cho ngân hàng
            return max(0.5, min(beta, 1.5))
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
    nii = get_ttm_value(db, ticker, ["I. Thu nhập lãi thuần", "Thu nhập lãi thuần"])
    toi = get_ttm_value(db, ticker, ["VIII. Tổng thu nhập hoạt động", "Tổng thu nhập hoạt động"])
    non_interest_income = toi - nii

    return {
        "total_equity": get_latest_balance(db, ticker, ["Vốn chủ sở hữu"]),
        "total_assets": get_latest_balance(db, ticker, ["TỔNG TÀI SẢN"]),
        "customer_loans": get_latest_balance(db, ticker, ["1. Cho vay khách hàng"]),
        "customer_deposits": get_latest_balance(
            db, ticker, ["Tiền gửi của khách hàng"]
        ),
        "net_income": get_ttm_value(
            db, ticker, ["XIV. Lợi nhuận sau thuế", "Lợi nhuận sau thuế"]
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

    COE Convention (Chốt từ nguyên tắc):
      rf  = TPCP VN 10Y (lấy động từ DB)
      erp = Mature market ERP + Country Risk Premium VN = erp_total (đọc từ config defaults.yaml)
      beta = ước lượng từ giá VCB vs VNINDEX
      COE = rf + beta * erp
    """
    rf_dynamic = get_latest_tpcp_10y(db)
    beta_dynamic = estimate_vcb_beta(db, ticker)
    
    from valuation.config import load_defaults
    config_defaults = load_defaults()
    coe_conv = config_defaults.get("coe_convention", {})
    erp_total = coe_conv.get("erp_total", 0.082)  # Đọc động từ defaults.yaml

    if coe_config is None:
        coe_config = {
            "risk_free_rate": rf_dynamic,
            "erp": erp_total,
            "beta": beta_dynamic,
            "terminal_growth_rate": 0.02,
        }
    else:
        # Nếu là giá trị cũ từ config cứng, ta ghi đè bằng giá trị động
        if coe_config.get("risk_free_rate") == 0.043:
            coe_config["risk_free_rate"] = rf_dynamic
        if coe_config.get("beta") == 1.0:
            coe_config["beta"] = beta_dynamic
        # Nếu erp cũ là 6.0% hoặc chưa cập nhật, ta cập nhật lên erp_total mới
        if coe_config.get("erp") in (0.060, 0.082) or coe_config.get("erp") is None:
            coe_config["erp"] = erp_total

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
