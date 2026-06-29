import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class VCBValuationModel:
    """
    Mô hình định giá VCB (Ngân hàng) bằng Residual Income + P/B.

    COE Convention (Damodaran Global — chống double-count country risk):
    ----------------------------------------------------------------
    Quy tắc:
      rf  = UST 10Y (risk-free toàn cầu, ~4.3%)
      erp = Mature market ERP (~4.5%) + Country Risk Premium VN (~1.5%) = 6.0%
      COE = rf + beta * erp

    CẢNH BÁO DOUBLE-COUNT:
      Nếu rf = TPCP VN (~3%) → erp PHẢI = mature ERP ONLY (~4.5%)
        vì TPCP VN đã chứa lạm phát + rủi ro quốc gia VN
      KHÔNG BAO GIỜ dùng rf=TPCP VN + erp gồm CRP → sẽ double-count!
    """

    def __init__(self, current_financials: dict, assumptions: dict):
        """
        current_financials: dict chứa số liệu TTM/quý cuối:
            - total_equity      (Balance Sheet — quý cuối)
            - total_assets      (Balance Sheet — quý cuối)
            - customer_loans    (Balance Sheet — quý cuối)
            - customer_deposits (Balance Sheet — quý cuối)
            - net_income        (Income Statement — TTM 4 quý)
            - shares_outstanding (tính từ Vốn điều lệ / 10,000)
            - current_price
        assumptions: dict chứa giả định:
            - credit_growth (list 5 floats hoặc scalar — declining schedule)
            - nim           (list 5 floats hoặc scalar — declining schedule)
            - cir           (list 5 floats hoặc scalar)
            - credit_cost   (list 5 floats hoặc scalar)
            - dividend_payout_ratio (float)
            - risk_free_rate (float) — UST 10Y hoặc TPCP VN (xem docstring)
            - beta (float)
            - erp (float) — đã bao gồm CRP nếu rf=UST, hoặc mature-only nếu rf=TPCP VN
            - terminal_growth_rate (float)
        """
        self.current_financials = current_financials
        self.assumptions = assumptions
        self.years = 5

        # Prepare assumptions arrays (declining schedule nếu là list)
        self.credit_growth = self._get_array(assumptions.get('credit_growth', 0.12))
        self.nim = self._get_array(assumptions.get('nim', 0.028))
        self.cir = self._get_array(assumptions.get('cir', 0.38))
        self.credit_cost = self._get_array(assumptions.get('credit_cost', 0.008))

        self.payout_ratio = assumptions.get('dividend_payout_ratio', 0.15)
        self.rf = assumptions.get('risk_free_rate', 0.043)
        self.beta = assumptions.get('beta', 1.0)
        self.erp = assumptions.get('erp', 0.060)
        self.g = assumptions.get('terminal_growth_rate', 0.02)

        self.coe = self.rf + self.beta * self.erp

        # Tính tỷ lệ thu nhập ngoài lãi từ lịch sử
        hist_non_ii = self.current_financials.get('non_interest_income', 0.0)
        hist_assets = self.current_financials.get('total_assets', 0.0)
        self.non_ii_to_assets = hist_non_ii / hist_assets if hist_assets > 0 else 0.005


        # --- Sanity Floor Check (VND-base: equity premium >= MIN_EQUITY_PREMIUM) ---
        from valuation.engine.coe import MIN_EQUITY_PREMIUM
        if self.coe < self.rf + MIN_EQUITY_PREMIUM:
            raise ValueError(
                f"COE_TOO_LOW: Chi phí vốn cổ phần COE={self.coe:.2%} quá thấp (thấp hơn rf={self.rf:.2%} + {MIN_EQUITY_PREMIUM:.1%}). "
                f"Vui lòng kiểm tra lại hệ số Beta ({self.beta}) hoặc ERP ({self.erp:.2%})."
            )

        # --- Implied P/B Sanity Check ---
        hist_equity = self.current_financials.get('total_equity', 0.0)
        hist_ni = self.current_financials.get('net_income', 0.0)
        self.roe_ttm = hist_ni / hist_equity if hist_equity > 0 else 0.18

        # --- ROE fade: terminal/perpetuity dùng ROE bền vững, KHÔNG dùng ROE năm 5 ---
        # Bank VN ROE ~20% hiện tại nhưng cạnh tranh + tích lũy vốn nén dần về mức
        # bền vững dài hạn. terminal_roe chặn trên ROE dùng cho terminal value (RI + P/B).
        # Mặc định 0.15; không bao giờ NÂNG ROE (min với roe hiện tại).
        self.terminal_roe = min(
            assumptions.get('terminal_roe', 0.15),
            self.roe_ttm if self.roe_ttm > 0 else 0.15,
        )

        if self.coe > self.g:
            self.implied_pb = (self.roe_ttm - self.g) / (self.coe - self.g)
            if self.implied_pb > 4.0 or self.implied_pb < 0.5:
                logger.warning(
                    f"[IMPLIED_PB_WARNING] P/B ngầm định = {self.implied_pb:.2f}x nằm ngoài vùng hợp lý [0.5, 4.0]. "
                    f"Cờ cảnh báo: IMPLIED_PB_OUT_OF_BOUNDS. "
                    f"ROE={self.roe_ttm:.2%}, COE={self.coe:.2%}, g={self.g:.2%}."
                )
        else:
            self.implied_pb = None

        # --- Double-count detection ---
        # Nếu rf > 2.5% (có vẻ là local rate) VÀ erp > 0.085 (có vẻ gồm CRP quá cao)
        # → rất có thể đang double-count country risk
        if self.rf > 0.025 and self.erp > 0.085:
            logger.warning(
                f"DOUBLE-COUNT WARNING: rf={self.rf:.1%} (looks like local rate) "
                f"+ erp={self.erp:.1%} (looks like it includes CRP). "
                f"COE={self.coe:.1%} may be inflated. "
                f"Rule: rf=TPCP VN → erp=mature only (~4.5%); "
                f"rf=UST → erp=mature+CRP."
            )

        # --- Terminal growth validation ---
        if self.g >= self.coe:
            raise ValueError(
                f"Terminal growth rate g={self.g:.1%} >= COE={self.coe:.1%}. "
                f"Điều này khiến Terminal Value âm vô cực. "
                f"Kiểm tra lại giả định."
            )
            
    def _get_array(self, val):
        if isinstance(val, (list, np.ndarray)):
            if len(val) >= self.years:
                return np.array(val[:self.years])
            else:
                return np.array(list(val) + [val[-1]]*(self.years - len(val)))
        return np.array([val]*self.years)

    def forecast_drivers(self):
        """
        Projects financials for 5 years.
        Returns a DataFrame of projections.
        """
        f = self.current_financials
        
        proj = {
            'year': list(range(1, self.years + 1)),
            'customer_loans': np.zeros(self.years),
            'total_assets': np.zeros(self.years),
            'total_equity': np.zeros(self.years),
            'net_interest_income': np.zeros(self.years),
            'non_interest_income': np.zeros(self.years), # Simplify: assume constant % of assets or flat growth
            'operating_income': np.zeros(self.years),
            'operating_expense': np.zeros(self.years),
            'provision_expense': np.zeros(self.years),
            'net_income': np.zeros(self.years),
            'dividends': np.zeros(self.years)
        }
        
        curr_loans = f['customer_loans']
        curr_assets = f['total_assets']
        curr_equity = f['total_equity']
        
        # Tỷ lệ thu nhập ngoài lãi lấy động từ lịch sử
        non_ii_to_assets = self.non_ii_to_assets

        
        for i in range(self.years):
            # Balance sheet (BOP to EOP)
            next_loans = curr_loans * (1 + self.credit_growth[i])
            # Assume assets grow with loans
            next_assets = curr_assets * (next_loans / curr_loans) if curr_loans > 0 else curr_assets * (1 + self.credit_growth[i])
            
            # Income statement
            # NII = NIM * Average Assets (approximate with EOP or average)
            avg_assets = (curr_assets + next_assets) / 2
            nii = self.nim[i] * avg_assets
            non_ii = non_ii_to_assets * avg_assets
            op_income = nii + non_ii
            
            opex = self.cir[i] * op_income
            # Provision = credit cost * average loans
            avg_loans = (curr_loans + next_loans) / 2
            provision = self.credit_cost[i] * avg_loans
            
            # Pre-tax income
            pbt = op_income - opex - provision
            # Assuming 20% tax rate
            ni = pbt * (1 - 0.20)
            if ni < 0: ni = 0 # basic floor
            
            div = ni * self.payout_ratio
            retained_earnings = ni - div
            
            next_equity = curr_equity + retained_earnings
            
            # Store
            proj['customer_loans'][i] = next_loans
            proj['total_assets'][i] = next_assets
            proj['total_equity'][i] = next_equity
            proj['net_interest_income'][i] = nii
            proj['non_interest_income'][i] = non_ii
            proj['operating_income'][i] = op_income
            proj['operating_expense'][i] = opex
            proj['provision_expense'][i] = provision
            proj['net_income'][i] = ni
            proj['dividends'][i] = div
            
            # Roll forward
            curr_loans = next_loans
            curr_assets = next_assets
            curr_equity = next_equity
            
        self.projections = pd.DataFrame(proj)
        return self.projections

    def calculate_residual_income(self):
        if not hasattr(self, 'projections'):
            self.forecast_drivers()
            
        proj = self.projections
        ri = np.zeros(self.years)
        pv_ri = 0
        
        # Beginning equity is previous year's ending equity
        beg_equity = self.current_financials['total_equity']
        
        for i in range(self.years):
            # RI = Net Income - (Beginning Equity * Cost of Equity)
            ri[i] = proj['net_income'][i] - (beg_equity * self.coe)
            
            # Discount to PV
            pv_ri += ri[i] / ((1 + self.coe) ** (i + 1))
            
            beg_equity = proj['total_equity'][i]

        # Terminal Value RI — DÙNG ROE BỀN VỮNG (fade), không dùng ri[-1] (ROE năm 5
        # còn cao). Sau khi loop, beg_equity = vốn cuối năm 5 = vốn đầu kỳ terminal.
        # RI_perpetuity = (terminal_roe - coe) * equity_đầu_terminal, tăng g vĩnh viễn.
        eq_terminal_begin = beg_equity
        sustainable_ri = (self.terminal_roe - self.coe) * eq_terminal_begin
        terminal_ri = sustainable_ri / (self.coe - self.g)
        pv_terminal_ri = terminal_ri / ((1 + self.coe) ** self.years)
        
        total_ri_value = pv_ri + pv_terminal_ri
        equity_value_ri = self.current_financials['total_equity'] + total_ri_value
        
        self.ri_valuation = {
            'pv_ri': pv_ri,
            'pv_terminal_ri': pv_terminal_ri,
            'equity_value': equity_value_ri,
            'fair_value_per_share': equity_value_ri / self.current_financials['shares_outstanding']
        }
        return self.ri_valuation

    def calculate_pb_valuation(self):
        if not hasattr(self, 'projections'):
            self.forecast_drivers()
            
        # ROE năm 5 (tham chiếu, để báo cáo)
        ni_yr5 = self.projections['net_income'].iloc[-1]
        eq_yr4 = self.projections['total_equity'].iloc[-2] # Beg equity for yr 5
        roe_yr5 = ni_yr5 / eq_yr4 if eq_yr4 > 0 else 0

        # Justified P/B dùng ROE BỀN VỮNG (fade), không dùng ROE năm 5 còn cao.
        long_term_roe = self.terminal_roe
        # Target P/B = (ROE_bền_vững - g) / (CoE - g)
        if self.coe <= self.g:
            target_pb = 1.0 # fallback
        else:
            target_pb = (long_term_roe - self.g) / (self.coe - self.g)
            
        equity_value_pb = target_pb * self.current_financials['total_equity']
        
        self.pb_valuation = {
            'long_term_roe': long_term_roe,
            'roe_yr5': roe_yr5,
            'target_pb': target_pb,
            'equity_value': equity_value_pb,
            'fair_value_per_share': equity_value_pb / self.current_financials['shares_outstanding']
        }
        return self.pb_valuation

    def blend_valuation(self, weight_ri=0.5, weight_pb=0.5):
        ri_val = self.calculate_residual_income()
        pb_val = self.calculate_pb_valuation()
        
        blended_ev = weight_ri * ri_val['equity_value'] + weight_pb * pb_val['equity_value']
        blended_fvps = blended_ev / self.current_financials['shares_outstanding']
        
        if blended_fvps <= 0:
            raise ValueError(f"Blended Fair Value is non-positive: {blended_fvps}")
            
        self.blended_valuation = {
            'blended_equity_value': blended_ev,
            'blended_fair_value_per_share': blended_fvps,
            'ri_weight': weight_ri,
            'pb_weight': weight_pb,
            'ri_fvps': ri_val['fair_value_per_share'],
            'pb_fvps': pb_val['fair_value_per_share']
        }
        return self.blended_valuation

    def calculate_greeks(self):
        """
        Calculates sensitivity (Greeks) for key drivers.
        Returns % change in Fair Value for a 1-unit bump in drivers.
        """
        # Base FV
        base_fv = self.blend_valuation()['blended_fair_value_per_share']
        
        greeks = {}
        
        # Helper to bump and calc
        def bump_and_recalc(driver_name, bump_amount):
            # Save original
            orig = np.copy(getattr(self, driver_name))
            # Bump
            setattr(self, driver_name, orig + bump_amount)
            # Clear cache
            if hasattr(self, 'projections'): delattr(self, 'projections')
            # Recalc
            try:
                new_fv = self.blend_valuation()['blended_fair_value_per_share']
                delta = (new_fv - base_fv) / base_fv
            except Exception:
                delta = None
            # Restore
            setattr(self, driver_name, orig)
            if hasattr(self, 'projections'): delattr(self, 'projections')
            
            return delta

        # Bump NIM by +10 bps (0.001)
        greeks['delta_nim_10bps'] = bump_and_recalc('nim', 0.001)
        
        # Bump CIR by +1% (0.01) (Expected negative impact)
        greeks['delta_cir_1pct'] = bump_and_recalc('cir', 0.01)
        
        # Bump Credit Cost by +10 bps (0.001) (Expected negative impact)
        greeks['delta_credit_cost_10bps'] = bump_and_recalc('credit_cost', 0.001)
        
        # For cost of equity, it's not a list, so we handle it manually
        orig_coe = self.coe
        self.coe = orig_coe + 0.005 # +50 bps
        try:
            new_fv_coe = self.blend_valuation()['blended_fair_value_per_share']
            greeks['delta_coe_50bps'] = (new_fv_coe - base_fv) / base_fv
        except ValueError:
            greeks['delta_coe_50bps'] = None
        self.coe = orig_coe
        
        return {
            'base_fvps': base_fv,
            'greeks': greeks
        }
