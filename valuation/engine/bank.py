from valuation.models.financials import Company

def calculate_bank_parameters(company: Company) -> tuple[float, float, float]:
    """
    Tính toán các tham số chính cho mô hình định giá ngân hàng:
    Re (Cost of Equity), ROE dự phóng, và g (tăng trưởng dài hạn).
    """
    assumptions = company.assumptions
    
    # 1. Chi phí vốn cổ phần (Re) theo CAPM
    rf = assumptions.risk_free_rate
    erp = assumptions.equity_risk_premium
    beta = assumptions.beta
    re = rf + beta * erp
    
    # 2. Tăng trưởng dài hạn (g)
    g = assumptions.terminal_growth
    
    # 3. ROE dự phóng năm đầu tiên
    income = company.income
    balance = company.balance
    
    historical_years = sorted([y for y in income.revenue.keys() if y not in assumptions.forecast_years])
    base_year = historical_years[-1]
    forecast_years = sorted(assumptions.forecast_years)
    target_year = forecast_years[0] if forecast_years else base_year
    
    # --- B3 FIX: Dùng ROE bền vững (sustainable ROE) cho Justified P/B ---
    # Lý thuyết CFA: Justified P/B = (ROE_sustainable - g) / (Re - g)
    # ROE năm 1 không đại diện cho trạng thái bền vững dài hạn.
    sustainable_roe = getattr(assumptions, 'sustainable_roe', None)
    if sustainable_roe and sustainable_roe > 0:
        roe = sustainable_roe
    else:
        # Fallback: ROE năm đầu dự phóng (hành vi cũ)
        npatmi_val = income.npatmi.get(target_year, income.npatmi[base_year])
        equity_val = balance.equity.get(target_year, balance.equity[base_year])
        roe = (npatmi_val / equity_val) if equity_val > 0 else 0.15
    
    return re, roe, g

def calculate_justified_pb(company: Company) -> float:
    """
    Tính P/B hợp lý (Justified P/B) cho ngân hàng.
    Công thức: Justified P/B = (ROE - g) / (Re - g)
    """
    re, roe, g = calculate_bank_parameters(company)
    
    if g >= re:
        raise ValueError(f"Tăng trưởng dài hạn g ({g*100:.2f}%) phải nhỏ hơn Chi phí vốn cổ phần Re ({re*100:.2f}%). Gordon Growth không hợp lệ.")
        
    justified_pb = (roe - g) / (re - g)
    return max(justified_pb, 0.0)

def value_bank(company: Company) -> float:
    """
    Định giá cổ phiếu ngân hàng bằng phương pháp Justified P/B.
    Target Price = Justified P/B * BVPS
    """
    justified_pb = calculate_justified_pb(company)
    
    balance = company.balance
    income = company.income
    historical_years = sorted([y for y in company.income.revenue.keys() if y not in company.assumptions.forecast_years])
    base_year = historical_years[-1]
    forecast_years = sorted(company.assumptions.forecast_years)
    target_year = forecast_years[0] if forecast_years else base_year
    
    # BVPS (nghìn đồng/cổ phiếu) ở năm dự phóng mục tiêu
    equity_val = balance.equity.get(target_year, balance.equity[base_year])
    bvps = equity_val / balance.shares_outstanding
    
    target_price = justified_pb * bvps
    return target_price
