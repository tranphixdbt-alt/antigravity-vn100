# DECISIONS.md — Quyết định kỹ thuật dự án antigravity-vn100

> Ghi lại theo yêu cầu AGENTS.md. Mỗi mục: quyết định, lý do, file/dòng liên quan.

---

## Sprint: Sửa gốc upside phi lý (2026-07)

### C1 — COE VND-base CỘNG Country Risk Premium (đảo convention cũ)

**Quyết định:** ERP dùng cho COE = `erp_mature + crp_vn` (≈ 4.5% + 3.7% = 8.2%).
COE = rf_VN + beta × (erp_mature + crp_vn). Đảo lại "golden rule" cũ (chỉ dùng
erp_mature, bỏ CRP vì cho rằng rf_VN đã chứa rủi ro quốc gia).

**Lý do:** CRP là phần bù RỦI RO VỐN CỔ PHẦN của thị trường mới nổi (chuẩn
Damodaran), TÁCH BIỆT với rủi ro vỡ nợ nằm trong lợi suất TPCP. Bỏ CRP làm COE
chỉ ~8-9% → WACC ~8%, mẫu số (WACC−g) ~6% → fair value phình khổng lồ (upside
100-210% cho cả DCF phi TC lẫn RI/PB ngân hàng). Đã được người dùng chốt.

**Tác động:** COE ~8.5%→~11.5%. PLX +114%→−25%, VNM +36%→−2%, banks +200%→~90%.

**Files:** `valuation/engine/coe.py` (get_erp), `config/defaults.yaml` (golden
rule + erp_total là ERP đang dùng), `ttm_helper.py`, `bank_vcb.py`.
**Test:** `tests/test_coe_convention.py` (viết lại theo convention mới),
`tests/test_golden_vcb.py` (recalibrate band 42k-80k theo COE ~10.9%).

---

### C2 — depr_to_revenue lấy từ D&A THẬT, bỏ hardcode 4%

**Quyết định:** `depr_to_revenue = median(D&A/doanh thu lịch sử)` lấy từ line
item `depreciation_and_amortization` (CF). Chỉ fallback 4% khi thiếu dữ liệu.
Thêm field `CashFlow.depreciation`.

**Lý do:** Hardcode 4% cho MỌI mã (magic number, vi phạm AGENTS.md #5) trong khi
capex lấy theo từng công ty → với DN nhẹ tài sản (PNJ D&A thực ~0.2%, PLX ~0.7%)
FCFF bị cộng thêm ~3.8% doanh thu "tiền ảo" mỗi năm → overvaluation.

**Files:** `valuation/data_access/repo.py` (NON_FIN_KEYWORDS + derive),
`valuation/models/financials.py` (CashFlow.depreciation).
**Test:** `tests/test_nonfin_calibration.py::test_depr_derived_from_real_da_not_hardcoded`.

---

### C3 — OPEX = chi phí bán hàng + QLDN (cộng cả 2)

**Quyết định:** `opex = selling_expenses + general_and_admin_expenses` (fallback
`operating_expenses` gộp nếu không tách được).

**Lý do:** `_match_value` chỉ trả 1 dòng khớp đầu tiên → chỉ bắt selling, bỏ sót
G&A → EBIT bị thổi ~2pp margin cho mọi mã phi TC (PNJ 11%→8.6% sau sửa, khớp
operating_profit báo cáo).

**Files:** `valuation/data_access/repo.py` (build_company_data non-fin branch).
**Test:** `tests/test_nonfin_calibration.py::test_opex_includes_selling_and_ga`.

---

### C4 — Engine readonly chạy AUTOCOMMIT (sửa flaky test tận gốc)

**Quyết định:** `engine_read` dùng `isolation_level="AUTOCOMMIT"`.

**Lý do:** Luồng phân tích chỉ đọc, không cần transaction. Trước đây một query lỗi
để lại transaction "aborted", connection trả về pool ở trạng thái hỏng → poison
query test sau (flaky ngẫu nhiên do pytest-randomly, "UndefinedColumn" giả).

**Files:** `valuation/db/session.py`.

---

### C5 — Trả tech debt engine: một nguồn định giá duy nhất

**Quyết định:**
- **DCF/sensitivity:** đã hợp nhất từ trước (`run_valuation_engine` delegate sang
  `_dispatch_nonfin`, WACC tập trung ở `engine/wacc.py`). Xác nhận không còn
  code trùng dựng cf_dict/WACC — mục action item của B75 coi như đóng.
- **Bank:** XÓA `engine/bank.py` (legacy, chạy trên API Company cũ đã lỗi thời:
  `income`/`balance`/`equity_risk_premium`/`forecast_years` — không tồn tại trên
  model hiện tại; chỉ còn 1 test dùng). Nguyên tắc B3 (Justified P/B dùng
  sustainable ROE) được đưa vào model ACTIVE `bank_general.py`.

**Lý do:** B87 để lại 2 implementation ngân hàng, B3 chỉ áp cho bản legacy chết.
Nay chỉ còn `BankGeneralValuationModel` là nguồn sự thật, honor B3.

**Files:** xoá `valuation/engine/bank.py`; `valuation/engine/models/bank_general.py`
(calculate_pb_valuation ưu tiên sustainable_roe).
**Test:** `tests/test_valuation_accuracy.py::TestB3SustainableRoe` viết lại trên
bank_general; bỏ import legacy.

---

### C6 — Báo cáo định giá 11 phần chuẩn quỹ (SPEC PHẦN B)

**Quyết định:** nâng báo cáo PDF/Word từ 5 phần lên đủ 11 phần chuẩn CTCK/quỹ:
cover (thêm vốn hóa + band khuyến nghị 5 mức MUA/KHẢ QUAN/NẮM GIỮ/KÉM KHẢ
QUAN/BÁN đọc từ `config/defaults.yaml → rating_bands`), luận điểm đầu tư, tóm
tắt định giá, tổng quan DN, bối cảnh ngành, phân tích tài chính lịch sử (+2
biểu đồ mới), bảng giả định, chi tiết định giá (bóc tách WACC + đối chiếu
consensus), kịch bản Bull/Base/Bear + heatmap, rủi ro (+QC flags), phụ lục BCTC.

**Kiến trúc:** tách data khỏi GUI theo spec —
- `valuation/report/report_data.py`: builder thuần gom dữ liệu 11 phần, test độc lập.
- `valuation/report/ai_narrative.py`: DeepSeek sinh NHÁP 4 phần văn bản từ số
  liệu thật, luôn gắn `ai_generated` để template in dấu "Nháp do AI tạo — cần
  analyst review" (PHẦN G); fallback khung gợi ý khi thiếu key/lỗi mạng —
  không chặn xuất báo cáo. Trên UI: nút bấm sinh 1 lần/mã, cache session.
- Kịch bản Bull/Bear với phương pháp proxy (RNAV/SOTP) không co giãn theo
  growth/margin → builder gắn `applicable=False`, báo cáo in ghi chú thay bảng.

**Files:** `valuation/report/{report_data,ai_narrative}.py` (mới),
`template.html` + `build_docx.py` (viết lại 11 phần), `charts.py` (+2 chart),
`views/results.py` (wire), `config/defaults.yaml` (rating_bands).
**Test:** `tests/test_report_data.py` (6, có ca tính tay vốn hóa/ROE/COE),
`tests/test_report_render.py` (5, golden render ACB+FPT đủ 11 section, Word
build được, dấu AI chỉ hiện khi ai_generated). PDF mẫu:
`temp_reports/Bao_cao_chuan_quy_ACB.pdf` (6 trang, đủ 11 phần, verify pypdf).

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
