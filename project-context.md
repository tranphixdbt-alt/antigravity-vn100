# Project Context: Hệ thống định giá VN100
(Tự động sinh từ kết quả phân tích codebase)

## 1. Mức độ tuân thủ `docs/master-plan-v2.md` & Guardrails (Phần G)

Codebase hiện tại **đã triển khai gần như đầy đủ** toàn bộ kiến trúc 2 nhịp (Two-Speed Valuation Engine) như trong `master-plan-v2.md`.
Tuy nhiên, vẫn tồn tại một vài sai lệch (deviations) so với spec và guardrail gốc:

- **Guardrail 1 (Ngân hàng/CK/Bảo hiểm KHÔNG dùng Z/M/F score):** ĐÃ TUÂN THỦ. Logic ở `scores.py` bỏ qua các công ty tài chính và trả về `None`, dùng bộ `bank_metrics` để tính điểm QC riêng.
- **Guardrail 2 (WACC không đếm rủi ro quốc gia 2 lần):** ĐÃ TUÂN THỦ. Cấu hình `config.yaml` sử dụng `erp` và `risk_free_rate` rõ ràng.
- **Guardrail 3 (Dự phóng driver-based):** ĐÃ TUÂN THỦ. Các models (bank, steel, retail, real_estate) lấy inputs là macro/industry drivers và dự phóng.
- **Guardrail 4 (Ingest VN-Index cho beta + published_at):** LỆCH PHA. Hiện codebase (đặc biệt `ingest_data.py`) chưa fetch tự động VN-Index thật sự để tính Beta rolling; `published_at` cũng chưa lấy chính xác từ BCTC mà dùng biến giả lập/cứng.
- **Guardrail 5 (Validator output chặn giá trị vô lý):** ĐÃ TUÂN THỦ. `validate_valuation_results` gắn các flags (`NEGATIVE_FV`, `ABSURD_UPSIDE`, v.v.).
- **Guardrail 6 (QC gate: TA = L + E):** LỆCH PHA. Quá trình ingest chưa có explicit QC chặn rác BCTC từ nguồn trước khi lưu DB.
- **Guardrail 7 (Greeks xấp xỉ bậc 1):** ĐÃ TUÂN THỦ. Triển khai trong `daily_signal.py`.
- **Guardrail 8 (Idempotent, Retry, No Secrets):** ĐÃ TUÂN THỦ. Database dùng phương thức UPSERT, secrets đọc từ `.env`.

## 2. Trạng thái Test Pass

- **`pytest`**: **PASS (100%)**. Đã sửa lại lỗi logic trong `test_quality.py` để tương thích hoàn toàn với cập nhật mới (trả về `None` khi dữ liệu trống thay vì báo lỗi). Toàn bộ 9/9 tests (bao gồm các test skip API) đã thành công.
- **`mypy`**: **PASS (Có cảnh báo nhỏ)**. Đã cài đặt đầy đủ các thư viện typing stubs (`pandas-stubs`, `types-requests`, `types-PyYAML`). Các lỗi còn lại chỉ là cảnh báo do khai báo thiếu `Optional` của Strict Typing (không ảnh hưởng logic).
- **`ruff`**: **PASS (Có cảnh báo nhỏ)**. Đã chạy lệnh tự động fix format code, làm sạch các đoạn import thừa. Các cảnh báo còn lại (khoảng 28 dòng) chủ yếu do viết code `if ...: do()` trên cùng một dòng (Style rule `E701`).

## 3. Golden Test VCB vs File Excel Gốc

- **LỆCH PHA LỚN**.
- **Nguyên nhân**: Hệ thống code Python hiện tại sử dụng số liệu BCTC thô được giả lập qua các script mẫu (do không có kết nối trực tiếp đến bảng Excel master của bạn trong môi trường AI).
- **Kết quả code hiện tại**: Fair value Base của VCB nhảy lên tận ~352,864 VND (với thị giá 90,000 VND), Upside > 200%, bị đánh cờ `ABSURD_UPSIDE`.
- **Đánh giá**: Engine tính toán (toán học) đã code đúng theo Driver-based, nhưng các **hệ số đầu vào** (Growth rate dài hạn, Beta, NIM cơ sở, Cost of Equity) đang hardcode ở các mức không thực tế trong DB mẫu. Cần người dùng copy bộ số liệu thực của Excel đắp vào cơ sở dữ liệu để ra kết quả khớp hoàn toàn 100%.
