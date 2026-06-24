from typing import Dict, Any
import copy

class BaseValuationModel:
    """
    Base class cho tất cả các mô hình định giá.
    Chứa logic dùng chung:
    - Lưu trữ dữ liệu tài chính và assumptions.
    - Logic tính Greeks (Sensitivity).
    - Validation cơ bản (g >= WACC, chia 0).
    """
    def __init__(self, ticker: str, current_financials: Dict[str, Any], assumptions: Dict[str, Any]):
        self.ticker = ticker
        self.current_financials = current_financials
        self.assumptions = assumptions
        
        # Biến được khai báo ở model cụ thể
        self.coe = assumptions.get('cost_of_equity', 0.13)
        self.wacc = assumptions.get('wacc', 0.11)
        self.g = assumptions.get('long_term_growth', 0.05)
        
        self.validators()

    def validators(self):
        """Kiểm tra các quy tắc tài chính cơ bản"""
        if self.g >= self.wacc and hasattr(self, 'use_wacc') and self.use_wacc:
            # Trong một số context, model có thể ko báo lỗi mà clamp lại
            self.g = self.wacc - 0.005 
        if self.g >= self.coe:
            self.g = self.coe - 0.005

    def forecast_drivers(self):
        """Phải được override bởi model con. Trả về dataframe hoặc dict forecast."""
        raise NotImplementedError

    def perform_valuation(self) -> Dict[str, Any]:
        """Phải được override bởi model con. Trả về kết quả định giá."""
        raise NotImplementedError

    def calculate_greeks(self) -> Dict[str, float]:
        """
        Tính đạo hàm bậc nhất (greeks) của fair value theo từng driver.
        Mô hình con cần define self.assumptions['drivers'] = {'nim': {'bump': 0.001}, ...}
        """
        base_valuation = self.perform_valuation()
        base_fv = base_valuation.get('blended_fair_value_per_share', 0.0)
        
        greeks = {}
        drivers = self.assumptions.get('drivers', {})
        
        for driver_name, config in drivers.items():
            bump_val = config.get('bump', 0.01)
            original_val = self.assumptions.get(driver_name)
            
            if original_val is None:
                continue
                
            # Tạo bản sao mô hình với giả định mới
            bumped_assumptions = copy.deepcopy(self.assumptions)
            bumped_assumptions[driver_name] = original_val + bump_val
            
            # Khởi tạo instance mới cùng type với class hiện tại
            model_class = type(self)
            try:
                bumped_model = model_class(self.ticker, self.current_financials, bumped_assumptions)
                bumped_valuation = bumped_model.perform_valuation()
                bumped_fv = bumped_valuation.get('blended_fair_value_per_share', 0.0)
                
                # Tính đạo hàm: dFV / dDriver
                if bump_val != 0:
                    delta = (bumped_fv - base_fv) / bump_val
                else:
                    delta = 0.0
            except Exception:
                delta = None
                
            greeks[f"delta_{driver_name}"] = delta
            
        return {
            "base_fair_value": base_fv,
            "greeks": greeks
        }
