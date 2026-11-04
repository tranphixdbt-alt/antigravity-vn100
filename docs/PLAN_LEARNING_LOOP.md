# Kế hoạch: vòng học hằng tuần cho bộ định giá & dòng tiền

> Trạng thái (2026-10-26): người dùng chọn **Claude chạy Chủ nhật trên cloud, đọc dữ liệu trên Google Drive/Sheets**;
> cho phép tự đẩy riêng dữ liệu học mỗi tuần. **GĐ 1 xong** (nhật ký DeepSeek); **GĐ 2–4 xong** (`scripts/weekly_learning_digest.py`, 26/10); routine cloud bật.

## 1. Mục tiêu

Bộ định giá tự tốt lên qua thời gian bằng cách tích lũy bằng chứng từ ba nguồn — báo cáo DeepSeek, báo cáo CTCK, dữ liệu
đã lưu (giá, BCTC, dòng tiền) — và mỗi tuần Claude đọc **một bản tóm tắt ngắn** để đề xuất nâng cấp có đo lường.

## 2. Nguyên tắc (không thương lượng)

1. **Học = đề xuất có số đo, không tự sửa mô hình.** Claude hằng tuần chỉ viết đề xuất + chạy script đo tác động
   (chỉ đọc DB). Công thức/giả định/ngưỡng chỉ đổi khi người dùng duyệt, đi đúng quy trình (test tính tay, golden
   test, số quyết định D trong `DECISIONS.md`) — AGENTS.md §7 "không tự đổi model định giá".
2. **DeepSeek là giả thuyết, không phải sự thật.** Nhận định AI chỉ dùng để chỉ ra *chỗ cần kiểm tra*; mọi con số phải
   đối chiếu lại DB/BCTC trước khi thành bài học.
3. **Không ép khớp CTCK.** Lệch CTCK được phép nếu giải trình được (`calibration_registry.yaml`). Chỉ số "khớp CTCK"
   là một trong nhiều thước đo, không phải mục tiêu duy nhất.
4. **Chống quá khớp & lookahead.** Mọi đề xuất đo trên dữ liệu quá khứ với `as_of`, có tập kiểm tra riêng (dữ liệu
   gần nhất không dùng để chọn tham số), ghi số lần thử. Đề xuất không qua kiểm tra ngoài mẫu → không áp dụng.
5. **Tiết kiệm token.** Không thêm lời gọi DeepSeek nào (chỉ lưu cái đã sinh). Claude đọc bản tóm tắt ≤ ~400 dòng do
   Python tạo — không đọc JSON thô, PDF hay DB trực tiếp; 1 phiên/tuần, không chia nhiều agent.
6. **Bản quyền CTCK.** Chỉ lưu số liệu + tóm tắt bằng lời mình, không chép nguyên văn báo cáo.

## 3. Kiến trúc (cloud + Google Drive)

```
Máy chạy app (Mac / VPS)
  mỗi báo cáo DeepSeek ──► knowledge/ai_reports/<YYYY-MM>/<MÃ>_<ngày>_<fp8>.md + index.jsonl      (GĐ 1 — xong)
  Chủ nhật 18:00 (Python) ──► knowledge/weekly/<năm>-W<tuần>.md  + CSV trích từ DB (fv_history, calibration,
                              flow_labels, consensus_changes) — dạng ĐỌC ĐƯỢC, không phải file .db
        │  Mac (bản chính /Users/macos/antigravity-vn100, ngoài Drive): tóm tắt tuần chép knowledge/ → Drive (D85)
        │  VPS: tải lên đúng thư mục Drive bằng service account đã có (GOOGLE_SERVICE_ACCOUNT_JSON)
        ▼
Google Drive: …/chứng khoán định giá/vn100_knowledge/   (learning.knowledge_mirror_dir; webhook vẫn ở antigravity-vn100/)
        ▼
Chủ nhật 20:00 — routine Claude trên cloud (môi trường "chứng khoán", không phụ thuộc máy nào bật)
  - connector Google Drive: đọc digest tuần, CSV, LEARNINGS.md, đề xuất tuần trước
  - git: đọc code định giá (repo ngo-tuankiet/EA_dinhGiaP) để đề xuất đúng chỗ
  - connector Drive CHỈ ĐỌC (thử 26/10: không tạo được file) → gửi đề xuất + LEARNINGS.md qua Discord webhook
    (nhãn [VN100-LEARNING]) → bot lưu vào knowledge/proposals/ + LEARNINGS.md → Drive → tuần sau đọc lại
        ▼
Thứ 2: người dùng đọc đề xuất → duyệt → phiên làm việc riêng triển khai (test + golden + số D)
```

Lý do không đọc thẳng file `vn100_full.db`: connector Drive chỉ đọc được văn bản/Sheets, không mở được SQLite
nhị phân 88MB. Python trích sẵn đúng phần cần đọc thành CSV/MD — vừa đọc được, vừa ít token.

## 4. Các giai đoạn

### GĐ 1 — Lưu tóm tắt mỗi báo cáo DeepSeek (tuần 1)

- Móc vào **một chỗ duy nhất**: `valuation/report/verified_summary.save_verified_summary_cache` (nơi mọi báo cáo
  DeepSeek đã được lưu cache JSON). Sau khi lưu cache, ghi thêm file `.md` tóm tắt:
  - Đầu file: mã, ngày, model, token vào/ra, fingerprint, thị giá, FV + phương pháp (mô hình riêng hay BROKER_SYNTH),
    upside, cờ chính, trung vị CTCK.
  - **Nghi vấn dữ liệu** của AI (`ai_issues`: chỉ tiêu, kỳ, mức độ, phát hiện, hành động gợi ý).
  - **Tổng hợp CTCK** (`consensus_synthesis`: điểm chung, điểm riêng, điểm mấu chốt, đối chiếu nội bộ).
  - Rủi ro & luận điểm (rút gọn ~10 dòng mỗi phần).
- `knowledge/ai_reports/index.jsonl`: 1 dòng/báo cáo, trường máy đọc được (để tổng hợp theo tuần).
- Backfill 12 báo cáo đang có trong `.deepseek_report_cache/`.
- Test: lưu cache → có đúng 1 file .md + 1 dòng index; chạy lại cùng fingerprint không nhân đôi.
- Chi phí: 0 lời gọi AI thêm.

### GĐ 2 — Bộ nhớ kết quả định giá (tuần 1–2)

- **Lịch sử FV hằng tuần**: từ snapshot xếp hạng (đã có 18 bản) → `knowledge/fv_history.jsonl`
  (ngày, mã, phương pháp, FV, giá, trung vị CTCK, cờ). Dùng để đo: lệch CTCK theo thời gian, FV có ổn định không,
  và về sau (≥ 3–6 tháng) **giá thực tế đi về FV hay không**.
- **Lưu kết quả hiệu chuẩn mỗi tuần**: `scripts/run_calibration.py` đã có nhưng bảng `calibration_runs` đang trống —
  chạy hằng tuần có `--label` để có chuỗi xu hướng (% mã trong band, trung vị lệch theo ngành/phương pháp).
- **Sổ tay phương pháp CTCK theo ngành** `knowledge/broker_methods.md`: tự sinh từ `config/broker_synth/*.yaml`
  (phương pháp, bội số, chiết khấu từng CTCK) + `consensus_history` (671 báo cáo). Khi phải đọc PDF mới: đổi sang .md
  trước, chỉ trích phần định giá. Đây là nơi Claude học "CTCK định giá ngành X thế nào" (vd thép/HPG: P/E forward,
  khác mô hình mình — D70).

### GĐ 3 — Kiểm chứng dòng tiền bằng dữ liệu 2 năm (tuần 2–3)

`flow_daily` đã có 10/2024 → 10/2026 cho 100 mã → đo được ngay, không phải chờ:

- Chạy lại nhãn gom/xả lùi theo từng tuần quá khứ (đúng `as_of`, chỉ dùng dữ liệu tới ngày đó).
- Đo lợi nhuận **5 và 20 phiên sau** so với trung vị VN100 cho từng nhãn, từng phiếu (Ngoại, CMF, Tự doanh), từng ngành;
  cảnh báo "Dồn 1 phiên" có làm tín hiệu kém đi thật không.
- Chia thời gian: 10/2024–03/2026 để tìm hiểu, 04/2026–10/2026 để kiểm tra ngoài mẫu.
- Đầu ra mô tả (tỷ lệ đúng, số mẫu, khoảng tin cậy) — **không phải khuyến nghị**, giữ danh sách cụm từ cấm của tab.
- Kết hợp định giá × dòng tiền: nhóm "rẻ theo mô hình + dấu hiệu gom" có khác nhóm còn lại không (khi đủ lịch sử FV).

### GĐ 4 — Bản tóm tắt tuần + phiên duyệt của Claude (tuần 2)

**`scripts/weekly_learning_digest.py`** (Python, không AI) → `knowledge/weekly/<năm>-W<tuần>.md`, cấu trúc cố định:

1. Chất lượng định giá: số mã công bố (mô hình riêng vs BROKER_SYNTH), % trong ±15%/±25% CTCK, trung vị lệch — so tuần trước,
   theo ngành/phương pháp.
2. Top 10 mã lệch nhiều nhất và thay đổi so tuần trước.
3. DeepSeek trong tuần: số báo cáo, nghi vấn dữ liệu lặp lại (chỉ tiêu × số lần), rủi ro lặp lại, "điểm mấu chốt" CTCK
   khác mô hình mình.
4. CTCK: báo cáo mới, thay đổi giá mục tiêu, phương pháp mới.
5. Dòng tiền: phân bố nhãn, tỷ lệ đúng cập nhật (GĐ 3), mã có cảnh báo dồn 1 phiên.
6. Trạng thái đề xuất các tuần trước (đã duyệt / từ chối / đang đo).

**Phiên Claude hằng tuần** (1 phiên, đọc digest + `knowledge/LEARNINGS.md` + đề xuất tuần trước):
- Viết `knowledge/proposals/<tuần>.md`: tối đa **3** đề xuất, mỗi cái gồm giả thuyết, bằng chứng (dòng nào của digest),
  cách đo, **kết quả đo** (chạy script đọc-only trên DB), rủi ro, file sẽ sửa, mức ưu tiên.
- Cập nhật `knowledge/LEARNINGS.md` (≤ 200 dòng, bài học đã xác nhận bằng số; bỏ bài học bị dữ liệu mới bác bỏ).
- Gửi Discord 1 tin ngắn có link file đề xuất.
- **Không** sửa code mô hình, config định giá, DB.

### GĐ 5 — Triển khai đề xuất đã duyệt (liên tục)

Người dùng duyệt đề xuất nào → phiên làm việc riêng: test tính tay → sửa → golden test toàn rổ → so trước/sau →
`DECISIONS.md`. Đề xuất bị từ chối ghi lý do vào LEARNINGS để tuần sau không đề xuất lại.

## 5. Routine trên cloud — cấu hình & điều kiện

- **Môi trường**: "chứng khoán" (Anthropic cloud) — chạy dù Mac/VPS tắt.
- **Lịch**: Chủ nhật 20:00 giờ VN = 13:00 UTC → cron `0 13 * * 0`. Python tạo digest trước đó (18:00).
- **Model**: claude-sonnet-5-5 (đủ cho đọc + đo; đổi nếu muốn).
- **Connector Google Drive**: người dùng phải kết nối tại https://claude.ai/customize/connectors bằng tài khoản Google
  thấy được thư mục dự án (thư mục là shortcut chia sẻ — tài khoản đó cần quyền đọc/ghi thư mục `knowledge/`).
- **Repo code**: `ngo-tuankiet/EA_dinhGiaP` (công khai — chỉ để đọc code; KHÔNG đẩy dữ liệu học lên repo công khai này).
- **Đầu ra**: ghi file đề xuất vào `knowledge/proposals/` trên Drive. Nếu connector Drive không cho ghi, phương án dự
  phòng: routine trả đề xuất trong kết quả phiên (xem ở claude.ai/code/routines) và lần chạy Python kế tiếp lưu lại.
- **Kiểm chứng trước khi bật lịch**: tạo 1 lần chạy thử (run once) chỉ đọc thư mục `knowledge/` và báo lại thấy gì.
- **Tự đẩy dữ liệu (người dùng cho phép)**: chỉ áp dụng cho dữ liệu học lên Drive; code vẫn chỉ push GitHub khi người
  dùng bảo.

## 6. Thước đo "học tốt hơn" (đo mỗi tuần trong digest)

| Thước đo | Hiện tại (22–23/10) | Hướng |
|---|---|---|
| Mã công bố bằng **mô hình riêng** (không phải BROKER_SYNTH) | 61/91 | ↑ (giảm phụ thuộc CTCK) |
| Phi ngân hàng trong ±15% CTCK (≥ 2 CTCK) | 15/31 | ↑ |
| Trung vị \|lệch\| phi ngân hàng | 15,1% | ↓ ~12% sau 3 tháng |
| Nghi vấn dữ liệu DeepSeek lặp lại chưa xử lý | chưa đo | ↓ |
| Tỷ lệ đúng nhãn gom/xả ngoài mẫu (20 phiên) | chưa đo (GĐ 3) | > tỷ lệ cơ sở, ổn định qua các quý |
| Sai số FV vs giá sau 6 tháng | cần ≥ 6 tháng lịch sử | ↓ |

## 7. Rủi ro & kiểm soát

| Rủi ro | Kiểm soát |
|---|---|
| DeepSeek sai/ảo giác thành "bài học" | Chỉ là gợi ý; bài học phải có số đo từ DB |
| Quá khớp (thử nhiều lần tới khi đẹp) | Tách mẫu thời gian, ghi số lần thử, cần qua kiểm tra ngoài mẫu |
| Ép khớp CTCK làm mô hình mất độc lập | Không dùng khớp CTCK làm mục tiêu duy nhất; registry giải trình lệch |
| Tốn token | Digest ≤ ~400 dòng; 1 phiên/tuần; DeepSeek 0 lời gọi thêm |
| Hai máy cùng ghi knowledge/ | Tên file theo mã + ngày + fingerprint (không đè nhau); index.jsonl chỉ nối thêm |
| Lộ secret qua file lưu | Không lưu prompt/khóa; quét secret trước commit như hiện nay |

## 8. Lộ trình & việc cần người dùng quyết

| Tuần | Việc | Đầu ra |
|---|---|---|
| 1 | GĐ 1 + backfill; lịch sử FV từ snapshot; lưu calibration hằng tuần | file .md mỗi báo cáo, fv_history, calibration_runs có dữ liệu |
| 2 | Digest v1 + tác vụ hẹn giờ Claude (phương án A) + sổ tay phương pháp CTCK | digest tuần đầu, đề xuất tuần đầu |
| 3 | GĐ 3 kiểm chứng dòng tiền 2 năm | báo cáo tỷ lệ đúng nhãn, ngoài mẫu |
| 4+ | Vận hành; duyệt đề xuất; chuyển phương án B khi VPS ổn | LEARNINGS.md tích lũy |

**Còn cần người dùng:**
1. Kết nối connector **Google Drive** trên claude.ai (https://claude.ai/customize/connectors) bằng tài khoản thấy thư mục
   dự án → báo lại để tạo lần chạy thử.
2. Duyệt nguyên tắc §2 (Claude chỉ đề xuất, không tự sửa mô hình).
