from typing import Dict, Tuple
from valuation.models.financials import Company, Assumptions

def calculate_wacc_details(assumptions: Assumptions) -> Dict[str, float]:
    """
    Tính toán chi tiết các thành phần WACC và trả về dưới dạng dictionary.
    """
    rf = assumptions.risk_free_rate
    erp = assumptions.equity_risk_premium
    beta = assumptions.beta
    rd = assumptions.cost_of_debt
    tax_rate = assumptions.tax_rate
    wd = assumptions.target_debt_weight
    we = 1.0 - wd
    
    # Chi phí vốn cổ phần (Re) theo mô hình CAPM
    re = rf + beta * erp

    # Chi phí nợ vay sau thuế (Rd_after_tax) — để báo cáo
    rd_after_tax = rd * (1.0 - tax_rate)

    # WACC theo trọng số MỤC TIÊU (we, wd). Dùng hàm chung; truyền trọng số như
    # "giá trị" (we, wd sum=1) để công thức tương đương we*re + wd*rd_after_tax.
    from valuation.engine.wacc import compute_wacc
    wacc = compute_wacc(re, rd, equity_value=we, debt_value=wd, tax_rate=tax_rate)
    
    return {
        "cost_of_equity": re,
        "cost_of_debt_after_tax": rd_after_tax,
        "weight_of_equity": we,
        "weight_of_debt": wd,
        "wacc": wacc
    }

def calculate_wacc(assumptions: Assumptions) -> float:
    """
    Tính WACC của doanh nghiệp.
    """
    return calculate_wacc_details(assumptions)["wacc"]

def calculate_fcff_forecast(company: Company) -> Dict[int, float]:
    """
    Tính toán dòng tiền FCFF dự phóng cho các năm tương lai.
    Công thức: FCFF_t = EBIT_t * (1 - tax_rate) + D&A_t - CapEx_t - Delta_NWC_t
    """
    if company.is_financial:
        raise ValueError("Không dùng mô hình FCFF cho các doanh nghiệp tài chính/ngân hàng.")
        
    income = company.income
    balance = company.balance
    cashflow = company.cashflow
    assumptions = company.assumptions
    
    historical_years = [y for y in income.revenue.keys() if y not in assumptions.forecast_years]
    if not historical_years:
        raise ValueError("Không tìm thấy dữ liệu lịch sử để xác định năm gốc.")
    base_year = max(historical_years)
    forecast_years = sorted(assumptions.forecast_years)
    
    # Tính NWC cho năm gốc và các năm dự phóng để tính Delta NWC chính xác
    nwc = {}
    
    # Lấy tỷ lệ NWC của năm dự phóng đầu tiên để gán cho năm gốc (nếu cần)
    first_forecast = forecast_years[0]
    base_nwc_pct = assumptions.nwc_pct_revenue.get(first_forecast, 0.02)
    nwc[base_year] = base_nwc_pct * income.revenue[base_year]
    
    for year in forecast_years:
        nwc_pct = assumptions.nwc_pct_revenue.get(year, 0.02)
        nwc[year] = nwc_pct * income.revenue[year]
        
    fcff = {}
    prev_year = base_year
    for year in forecast_years:
        ebit = income.ebit.get(year, 0.0)
        depr = cashflow.depreciation.get(year, 0.0)
        
        # Dùng trị tuyệt đối của capex để tránh nhầm lẫn về dấu (CapEx luôn trừ đi)
        capex_val = abs(cashflow.capex.get(year, 0.0))
        
        # Delta NWC = NWC_t - NWC_{t-1}
        delta_nwc = nwc[year] - nwc[prev_year]
        
        # FCFF = EBIT * (1 - t) + D&A - CapEx - Delta NWC
        fcff_val = ebit * (1.0 - assumptions.tax_rate) + depr - capex_val - delta_nwc
        fcff[year] = fcff_val
        
        prev_year = year
        
    return fcff

def value_dcf(company: Company) -> Tuple[float, Dict[int, float], Dict[str, float]]:
    """
    Thực hiện định giá doanh nghiệp theo mô hình chiết khấu dòng tiền FCFF.
    Trả về: (Giá mục tiêu (nghìn VND/cp), Dòng tiền FCFF dự phóng, Chi tiết WACC)
    """
    if company.is_financial:
        raise ValueError("Không dùng mô hình DCF/FCFF cho doanh nghiệp tài chính/ngân hàng.")
        
    # 1. Tính WACC
    wacc_details = calculate_wacc_details(company.assumptions)
    wacc = wacc_details["wacc"]
    
    # 2. Tính FCFF dự phóng
    fcff_forecast = calculate_fcff_forecast(company)
    
    # 3. Tính Terminal Value (TV)
    forecast_years = sorted(company.assumptions.forecast_years)
    last_year = forecast_years[-1]
    fcff_n = fcff_forecast[last_year]
    
    if company.assumptions.terminal_method == "gordon":
        g = company.assumptions.terminal_growth
        if g >= wacc:
            raise ValueError(f"Tỷ lệ tăng trưởng vĩnh viễn g ({g*100:.2f}%) phải nhỏ hơn WACC ({wacc*100:.2f}%). Gordon Growth không hợp lệ.")
        tv = (fcff_n * (1.0 + g)) / (wacc - g)
    else:
        # exit_multiple
        # EBITDA_n = EBIT_n + depreciation_n
        ebit_n = company.income.ebit[last_year]
        depr_n = company.cashflow.depreciation[last_year]
        ebitda_n = ebit_n + depr_n
        exit_multiple = company.assumptions.exit_ev_ebitda or 10.0
        tv = ebitda_n * exit_multiple
        
    # 4. Chiết khấu các dòng tiền về hiện tại (PV)
    pv_fcff_sum = 0.0
    for idx, year in enumerate(forecast_years, start=1):
        discount_factor = (1.0 + wacc) ** idx
        pv_fcff_sum += fcff_forecast[year] / discount_factor
        
    # Chiết khấu Terminal Value
    tv_discount_factor = (1.0 + wacc) ** len(forecast_years)
    pv_tv = tv / tv_discount_factor
    
    # Enterprise Value (EV)
    ev = pv_fcff_sum + pv_tv
    
    # 5. Tính Giá trị vốn chủ sở hữu (Equity Value)
    historical_years = [y for y in company.income.revenue.keys() if y not in company.assumptions.forecast_years]
    base_year = max(historical_years)
    
    total_debt_base = company.balance.total_debt.get(base_year, 0.0)
    cash_base = company.balance.cash.get(base_year, 0.0)
    st_invest_base = company.balance.short_term_invest.get(base_year, 0.0)
    
    net_debt = total_debt_base - cash_base - st_invest_base
    equity_value = ev - net_debt
    
    # 6. Tính giá trị mỗi cổ phiếu (nghìn đồng/cổ phiếu)
    shares = company.balance.shares_outstanding
    target_price_per_share = equity_value / shares
    
    return target_price_per_share, fcff_forecast, wacc_details
