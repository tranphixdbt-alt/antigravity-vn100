from typing import Dict, Any, Union
from .base import BaseValuationModel
from valuation.models.financials import Company

class DCFValuationModel(BaseValuationModel):
    """
    Mô hình định giá DCF (FCFF) + Multiples.
    Dùng chung cho các ngành phi tài chính: FPT, HPG, VNM, GAS...
    Hỗ trợ cả interface dict cũ và Pydantic Company mới.
    """
    def __init__(self, ticker: str, current_financials: Dict[str, Any], assumptions: Dict[str, Any]):
        super().__init__(ticker, current_financials, assumptions)
        self.use_wacc = True
        self.validators()

    @classmethod
    def from_pydantic(cls, company: Company) -> "DCFValuationModel":
        """
        Khởi tạo model từ đối tượng Pydantic Company (adapter quý -> năm & đơn vị).
        """
        # Chuyển đổi dữ liệu sang dạng dict thô (nhân lại đơn vị Đồng thô cho phù hợp logic cũ)
        base_bs = company.historical_bs[-1]
        base_is = company.historical_is[-1]
        
        # --- B1 FIX: EBITDA = EBIT + D&A (không dùng magic multiplier 1.25) ---
        # D&A được ước lượng từ giả định depr_to_revenue[0] × doanh thu gốc
        depr_est = company.assumptions.depr_to_revenue[0] * base_is.revenue
        ebitda_est = base_is.ebit + depr_est  # tỷ đồng

        cf_dict = {
            'total_equity': base_bs.total_equity * 1e9,
            'total_assets': base_bs.total_assets * 1e9,
            'cash_and_equivalents': (
                base_bs.cash_and_equivalents
                + base_bs.short_term_financial_investments
            ) * 1e9,
            'minority_interest': base_bs.minority_interest * 1e9,
            'total_debt': (base_bs.short_term_debt + base_bs.long_term_debt) * 1e9,
            'total_revenue': base_is.revenue * 1e9,
            'cogs': base_is.cogs * 1e9,
            'ebitda': ebitda_est * 1e9,          # B1 Fix: EBIT + D&A
            'shares_outstanding': company.shares_outstanding * 1e6,
            'current_price': company.current_price,
            # Lịch sử LNST (đồng) để tính nhánh so sánh P/E khi cần.
            'net_income_history': [is_.net_income * 1e9 for is_ in company.historical_is],
        }

        # --- B2 FIX: WACC dùng market cap weights (không dùng book equity) ---
        # Theo CFA/Damodaran: E = market cap = shares × current_price
        rf = company.assumptions.risk_free_rate
        beta = company.assumptions.beta
        erp = company.assumptions.erp
        coe = company.assumptions.cost_of_equity or (rf + beta * erp)
        D = float(cf_dict['total_debt'])
        tax = company.assumptions.tax_rate
        cod = company.assumptions.cost_of_debt if company.assumptions.cost_of_debt is not None else (rf + 0.03)

        market_cap = company.shares_outstanding * 1e6 * company.current_price  # đồng
        if market_cap > 0:
            E = market_cap
        else:
            # Fallback về book equity nếu chưa có giá (ghi cảnh báo)
            E = float(cf_dict['total_equity'])
            if not hasattr(company, '_wacc_book_warned'):
                company.warnings.append(
                    "WACC_BOOK_EQUITY_FALLBACK: current_price = 0, dùng book equity "
                    "thay market cap cho WACC weights. Cập nhật giá thị trường để định giá chính xác."
                )
                object.__setattr__(company, '_wacc_book_warned', True)

        from valuation.engine.wacc import compute_wacc, DEFAULT_DEBT_SPREAD
        wacc_val = compute_wacc(coe, cod, E, D, tax, floor=rf + DEFAULT_DEBT_SPREAD)

        # Phương pháp so sánh phụ để blend với DCF (theo tài liệu lõi định giá):
        #   Compounder/Retail → P/E (bán lẻ/tăng trưởng định giá theo lợi nhuận)
        #   còn lại (Cyclical/Utility/Developer...) → EV/EBITDA (loại nhiễu D&A + nợ)
        # Trước đây MỌI mã DCF đều blend EV/EBITDA → méo cho retail biên mỏng (FRT).
        from valuation.engine.sector_router import route as _route_fn
        _plan = _route_fn(company.ticker) or {}
        _nature = _plan.get("business_nature", "Unknown")
        _secondary = "PE" if _nature in ("Compounder", "Retail") else "EV_EBITDA"
        from valuation.engine.models.pe_relative import PERelativeValuationModel
        _target_pe = PERelativeValuationModel._target_pe(_plan.get("group") or company.sector)

        ass_dict = {
            'secondary_multiple': _secondary,
            'target_pe': _target_pe,
            'norm_years': 3,
            'cost_of_equity': coe,
            'wacc': wacc_val,
            'revenue_growth_1_to_3': company.assumptions.revenue_growth[0],
            'revenue_growth_4_to_5': company.assumptions.revenue_growth[3],
            'ebit_margin': company.assumptions.ebit_margin[0],
            'mid_cycle_ebit_margin': company.assumptions.mid_cycle_ebit_margin,
            'tax_rate': company.assumptions.tax_rate,
            'capex_to_revenue': company.assumptions.capex_to_revenue[0],
            'depr_to_revenue': company.assumptions.depr_to_revenue[0],
            'dso': company.assumptions.dso[0],
            'dio': company.assumptions.dio[0],
            'dpo': company.assumptions.dpo[0],
            'interest_rate': company.assumptions.interest_rate[0],
            # Debt Schedule
            'debt_repayment_rate': company.assumptions.debt_repayment_rate[0],
            'new_borrowing_rate': company.assumptions.new_borrowing_rate[0],
            'target_ev_ebitda': company.assumptions.target_ev_ebitda,
            'long_term_growth': company.assumptions.terminal_growth_rate,
            'weight_dcf': company.assumptions.weight_dcf
        }
        
        return cls(company.ticker, cf_dict, ass_dict)

    def forecast_drivers(self) -> Dict[str, Any]:
        """
        Dự phóng cơ bản 5 năm với Detailed Schedules:
        - Revenue, EBIT, NOPAT
        - Working Capital (DSO, DIO, DPO)
        - Capex, Depreciation
        - FCFF = NOPAT + Depr - Capex - Delta NWC
        """
        rev_g_1_3 = self.assumptions.get('revenue_growth_1_to_3', 0.1)
        rev_g_4_5 = self.assumptions.get('revenue_growth_4_to_5', 0.08)
        ebit_m = self.assumptions.get('ebit_margin', 0.15)
        tax = self.assumptions.get('tax_rate', 0.20)
        
        capex_to_rev = self.assumptions.get('capex_to_revenue', 0.05)
        depr_to_rev = self.assumptions.get('depr_to_revenue', 0.04)
        dso = self.assumptions.get('dso', 30.0)
        dio = self.assumptions.get('dio', 30.0)
        dpo = self.assumptions.get('dpo', 30.0)
        int_rate = self.assumptions.get('interest_rate', 0.06)
        repayment_rate = self.assumptions.get('debt_repayment_rate', 0.20)
        new_borrow_rate = self.assumptions.get('new_borrowing_rate', 0.05)
        
        base_rev = self.current_financials.get('total_revenue', 100000.0)
        if base_rev is None or base_rev == 0.0:
            base_rev = 100000.0 * 1e9
            
        base_cogs = self.current_financials.get('cogs', base_rev * (1 - ebit_m))
        cogs_ratio = base_cogs / base_rev if base_rev > 0 else (1 - ebit_m)
        
        # NWC đầu kỳ
        prev_nwc = (base_rev * (dso / 365)) + (base_rev * cogs_ratio * (dio / 365)) - (base_rev * cogs_ratio * (dpo / 365))
        
        # Debt Schedule: khởi tạo tổng nợ đầu kỳ
        curr_debt = self.current_financials.get('total_debt', 0.0)
            
        forecasts = []
        curr_rev = base_rev
        
        for year in range(1, 6):
            if year <= 3:
                curr_rev *= (1 + rev_g_1_3)
            else:
                curr_rev *= (1 + rev_g_4_5)
                
            curr_cogs = curr_rev * cogs_ratio
            ebit = curr_rev * ebit_m
            nopat = ebit * (1 - tax)
            
            # Schedules
            curr_nwc = (curr_rev * (dso / 365)) + (curr_cogs * (dio / 365)) - (curr_cogs * (dpo / 365))
            delta_nwc = curr_nwc - prev_nwc
            prev_nwc = curr_nwc
            
            capex = curr_rev * capex_to_rev
            depr = curr_rev * depr_to_rev
            
            # FCFF = NOPAT + D&A - Capex - ΔNWC (Damodaran)
            # FCFF KHÔNG bị ảnh hưởng bởi Interest Expense
            fcff = nopat + depr - capex - delta_nwc
            reinvestment = capex + delta_nwc - depr
            
            # Debt Schedule
            debt_repay = curr_debt * repayment_rate
            new_borrow = curr_rev * new_borrow_rate
            end_debt = curr_debt + new_borrow - debt_repay
            avg_debt = (curr_debt + end_debt) / 2
            interest_expense = avg_debt * int_rate
            
            # Net Income (FCFE path): (EBIT - Interest) × (1 - tax)
            ebt = ebit - interest_expense
            net_income = ebt * (1 - tax)
            
            forecasts.append({
                'year': year,
                'revenue': curr_rev,
                'ebit': ebit,
                'nopat': nopat,
                'capex': capex,
                'depreciation': depr,
                'delta_nwc': delta_nwc,
                'reinvestment': reinvestment,
                'fcff': fcff,
                # Debt Schedule output
                'beginning_debt': curr_debt,
                'new_borrowing': new_borrow,
                'debt_repayment': debt_repay,
                'ending_debt': end_debt,
                'interest_expense': interest_expense,
                'net_income': net_income,
            })
            
            curr_debt = end_debt

        # GUARDRAIL CYCLICAL (G3): terminal NOPAT phải dùng biên MID-CYCLE, tuyệt đối
        # không ngoại suy biên đỉnh chu kỳ. Nếu caller cấp mid_cycle_ebit_margin (ngành
        # cyclical: thép/hóa chất/dầu khí), terminal tính lại theo biên trung bình chu kỳ.
        terminal_nopat = forecasts[-1]['nopat']
        mid_cycle_m = self.assumptions.get('mid_cycle_ebit_margin')
        if mid_cycle_m is not None:
            term_rev = forecasts[-1]['revenue']
            terminal_nopat = term_rev * mid_cycle_m * (1 - tax)
            if mid_cycle_m < ebit_m - 1e-9:
                self.valuation_warnings.append(
                    f"CYCLICAL_TERMINAL_MIDCYCLE: terminal margin ép về {mid_cycle_m:.1%} "
                    f"(mid-cycle) thay vì biên dự phóng {ebit_m:.1%} (chống ngoại suy đỉnh)."
                )

        return {'forecasts': forecasts, 'terminal_nopat': terminal_nopat}

    def perform_valuation(self) -> Dict[str, Any]:
        forecast_data = self.forecast_drivers()
        forecasts = forecast_data['forecasts']
        term_nopat = forecast_data['terminal_nopat']
        
        # 1. DCF Valuation (FCFF)
        pv_fcff = 0.0
        for f in forecasts:
            pv_fcff += f['fcff'] / ((1 + self.wacc) ** f['year'])
            
        term_reinv_rate = self.g / self.assumptions.get('roic_terminal', self.wacc)
        # Bắt buộc reinv_rate <= 1.0
        term_reinv_rate = min(term_reinv_rate, 1.0)
        
        term_fcff = (term_nopat * (1 + self.g)) * (1 - term_reinv_rate)
        terminal_value = term_fcff / (self.wacc - self.g)
        pv_tv = terminal_value / ((1 + self.wacc) ** 5)
        
        enterprise_value_dcf = pv_fcff + pv_tv
        
        # Từ EV ra Equity Value
        net_debt = self.current_financials.get('total_debt', 0.0) - self.current_financials.get('cash_and_equivalents', 0.0)
        minority_interest = self.current_financials.get('minority_interest', 0.0)
        equity_value_dcf = enterprise_value_dcf - net_debt - minority_interest
        shares_out = self.current_financials.get('shares_outstanding', 1000.0)
        dcf_fvps = equity_value_dcf / shares_out if shares_out > 0 else 0.0
        
        # 2. Định giá so sánh phụ — chọn bội số theo bản chất kinh doanh:
        #    P/E cho Compounder/Retail; EV/EBITDA cho phần còn lại (mặc định).
        secondary = self.assumptions.get('secondary_multiple', 'EV_EBITDA')
        if secondary == "PE":
            import statistics as _stats
            ni_hist = [x for x in self.current_financials.get('net_income_history', []) if x is not None]
            n = int(self.assumptions.get('norm_years', 3))
            window = ni_hist[-n:] if len(ni_hist) >= n else ni_hist
            norm_ni = _stats.median(window) if window else 0.0
            target_pe = self.assumptions.get('target_pe', 12.0) or 12.0
            if norm_ni > 0 and shares_out > 0:
                # P/E dựa trên EPS chuẩn hóa (median LNST lịch sử) — chống nhiễu 1 năm.
                multi_fvps = (norm_ni * target_pe) / shares_out
            else:
                # LNST âm/0 → P/E vô nghĩa; fallback về DCF thuần (không kéo blend về 0).
                multi_fvps = dcf_fvps
            multi_label = "PE"
        else:
            target_ev_ebitda = self.assumptions.get('target_ev_ebitda', 8.0)
            base_ebitda = self.current_financials.get('ebitda', term_nopat)  # Fallback
            ev_multiples = base_ebitda * target_ev_ebitda
            equity_value_multi = ev_multiples - net_debt - minority_interest
            multi_fvps = equity_value_multi / shares_out if shares_out > 0 else 0.0
            multi_label = "EV_EBITDA"

        # 3. Blend 50/50
        weight_dcf = self.assumptions.get('weight_dcf', 0.5)
        weight_multi = 1.0 - weight_dcf

        blended_fvps = (dcf_fvps * weight_dcf) + (multi_fvps * weight_multi)

        # Cờ minh bạch + chặn về 0 khi vốn cổ phần ÂM (nợ ròng > giá trị doanh
        # nghiệp). Giá cổ phiếu không thể âm; trả số âm là vô lý (vd NKG thép
        # biên mỏng + nợ lớn). KHÔNG có nghĩa DN vô giá trị — cần đối chiếu
        # thêm phương pháp & rủi ro tài chính. (Nhất quán với EV/EBITDA — C9.)
        if blended_fvps < 0:
            self.valuation_warnings.append("NEGATIVE_EQUITY_VALUE_DCF")
        blended_fvps = max(0.0, blended_fvps)

        return {
            "blended_fair_value_per_share": blended_fvps,
            "dcf_fvps": dcf_fvps,
            "multiples_fvps": multi_fvps,
            "secondary_multiple": multi_label,
            "weight_dcf": weight_dcf,
            "enterprise_value_dcf": enterprise_value_dcf,
            "equity_value_dcf": equity_value_dcf,
            "forecasts": forecasts
        }
