# DECISIONS.md — Quyết định kỹ thuật dự án antigravity-vn100

> Ghi lại theo yêu cầu AGENTS.md. Mỗi mục: quyết định, lý do, file/dòng liên quan.

---

## Sprint: Nâng cấp độ chính xác định giá (2026-06)

### B1 — EBITDA = EBIT + D&A (không dùng magic multiplier)

**Quyết định:** EBITDA được tính là `EBIT + D&A_est`, trong đó `D&A_est = depr_to_revenue[0] × revenue`.

**Lý do:** Code cũ dùng `EBIT × 1.25` — con số ma thuật không có cơ sở tài chính. Theo định nghĩa chuẩn: EBITDA = EBIT + Depreciation & Amortization.

**Files:** `valuation/engine/models/dcf.py:27-28`, `valuation/engine/sensitivity.py:79-80`

---

### B2 — WACC dùng market-cap weights, không dùng book equity

**Quyết định:** `E = shares_outstanding × current_price` (market cap). Fallback về book equity chỉ khi `current_price = 0`, kèm warning vào `company.warnings`.

**Lý do:** CFA/Damodaran chuẩn: WACC weights phải theo giá trị thị trường. Book equity gây bias nặng cho các công ty tăng trưởng cao (VD: FPT có market cap >> book equity).

**Files:** `valuation/engine/models/dcf.py:51-68`, `valuation/engine/sensitivity.py:104-110`

---

### B3 — Justified P/B dùng sustainable ROE, không dùng ROE năm gốc

**Quyết định:** `bank.py` ưu tiên `assumptions.sustainable_roe` nếu được cung cấp. Chỉ fallback về ROE lịch sử nếu `sustainable_roe` là None hoặc <= 0.

**Lý do:** ROE năm gốc có thể bị distort bởi các yếu tố nhất thời (dự phòng lớn, hoàn nhập, lãi/lỗ bất thường). Justified P/B theo Gordon Growth cần ROE dài hạn bền vững.

**Files:** `valuation/engine/bank.py` (hàm calculate_bank_parameters), `valuation/models/financials_bank.py:57` (field sustainable_roe)

---

### B4 — Tax rate ngân hàng lấy từ assumptions.tax_rate, không hardcode 0.20

**Quyết định:** `forecast_bank.py` đọc `tax_rate = getattr(assumptions, 'tax_rate', 0.20)`.

**Lý do:** Hardcode 0.20 cho mọi ngân hàng là không chính xác — một số ngân hàng có ưu đãi thuế (vùng kinh tế đặc biệt, dự án xã hội hóa). Cho phép cấu hình per-company.

**Files:** `valuation/engine/forecast_bank.py:~65`, `valuation/models/financials_bank.py:50` (field tax_rate)

---

### B5 — Effective tax rate và EV/EBITDA target lấy từ config, không hardcode

**Quyết định:**
- Tax rate: tính median từ 3 năm lịch sử (PBT > 0 và tax > 0). Fallback: `config/defaults.yaml → sector_tax_rates`.
- EV/EBITDA target: `config/defaults.yaml → sector_ev_ebitda`, match keyword trên `sector_str`.
- Giới hạn: `effective_tax` trong [0.05, 0.25] để tránh outlier.

**Lý do:** Hardcode tax/multiple theo ngành vào Python code vi phạm nguyên tắc "no magic numbers". Config yaml dễ update mà không cần sửa code.

**Files:** `valuation/data_access/repo.py` (hàm build_company_from_db), `config/defaults.yaml` (blocks sector_tax_rates, sector_ev_ebitda)

---

### Golden Test — Fixture tính tay FPT-like & VCB-like

**Quyết định:** Golden test dùng fixture synthetic (không pull DB) với số tính tay verify ±10% per AGENTS.md.

- **FPT-like:** revenue=100 ty, ebit=15 ty, depr_to_rev=3%, price=100,000 VND, shares=1,000M → EBITDA=18 ty
- **VCB-like:** equity=120,000 ty, shares=3,723M, sustainable_roe=20%, g=3%, Re=12% → BVPS=32,235 VND, Justified P/B≈1.94, FV≈62,536 VND

**Lý do:** Fixture độc lập với DB, chạy nhanh, không phụ thuộc network. Số tính tay cho phép detect regression ngay lập tức.

**Files:** `tests/test_valuation_accuracy.py` (13 tests, tất cả PASSED)

---

### Kiến trúc — Hai engine path độc lập cần sync

**Quyết định:** `engine/models/dcf.py` (DCFValuationModel.from_pydantic) và `engine/sensitivity.py` (run_valuation_engine) đều build cf_dict độc lập. Cả hai phải được cập nhật đồng thời khi sửa B1/B2.

**Lý do:** Phát hiện trong sprint này: sensitivity.py có code duplicate của dcf.py. Đây là tech debt — cần refactor về 1 điểm duy nhất trong tương lai, nhưng chưa làm ngay để tránh phá interface.

**Action item (future):** Extract `_build_cf_dict(company)` và `_compute_wacc(company, cf_dict)` thành utility functions dùng chung.

---

### Kiến trúc — legacy bank.py vs bank_general.py

**Quyết định:** `engine/bank.py` (legacy dict API) và `engine/models/bank_general.py` (Pydantic) là hai implementation riêng. B3 chỉ applied vào `bank.py`. `bank_general.py` dùng ROE dự phóng năm 5 — chấp nhận được vì projection model sẽ converge về sustainable ROE.

**Lý do:** Không touch `bank_general.py` để tránh phá Streamlit UI đang dùng nó. Tech debt cần xử lý sau.
