# PROGRESS — việc đã làm / còn chờ

> Quy ước: xong một việc → chuyển xuống "Đã xong", đánh `[x]`, ghi ngày và số quyết định (Dxx — chi tiết kỹ thuật
> trong `DECISIONS.md`). Việc mới hoặc việc chờ người dùng → thêm vào "Đang chờ". Mỗi dòng ngắn gọn, một việc.

## Đang chờ

- [ ] Đẩy GitHub các thay đổi từ 23/10 (gói VPS, vòng học, gộp tab, tab money, tóm tắt tuần) — chờ người dùng bảo "đẩy lên"
- [ ] VPS: nhân viên chạy `bash deploy/setup_vps.sh`, chép `.env` bằng `scp`; tắt launchd trên Mac khi VPS chạy
- [ ] VPS → Google Drive: tự tải `knowledge/` lên Drive khi app/bot chạy trên VPS (để routine cloud đọc được)
- [ ] 4 test vàng lệch dữ liệu thật (04/11): TCB cổ phiếu +50% sau chia, ACB chi phí tín dụng TTM và MSN SOTP đổi khi có quý 3, registry đồng thuận 28/09 hết hạn — cần cập nhật số kỳ vọng
- [ ] PNJ (vụ P-Lab): chờ báo cáo CTCK lập sau 25/09/2026
- [ ] 8 mã chưa có báo cáo CTCK nào: DIG, DSE, KDC, KOS, NAB, SJS, VIC, VPI
- [ ] Bảo mật: kiểm tra ai có quyền thư mục Drive `DATA-G` (`.env` và `learning_webhook.env` nằm trong đó)
- [ ] Xóa thư mục rỗng "VN100 - De xuat hang tuan" trong Drive rosinante2037 (do lần thử tạo)
- [ ] Bản máy: MSN, VTP chưa có giá phiên 28/10 (job sáng 29/10 tự lấy lại — kiểm tra)
- [ ] Routine Chủ nhật 01/11 20:00: kiểm tra đọc được `vn100_knowledge` trên Drive (D85)
- [ ] VNM: chờ VCI đăng thông báo cổ tức mới (người dùng chọn chờ)

- [ ] KIỂM THỬ 29/10 — lỗi vnai `threading` (UnboundLocalError) làm hỏng tải giá MSB/VPX sáng nay + xếp hạng (flow-daily đã tự thử lại, D88)
- [ ] KIỂM THỬ 29/10 — giá mục tiêu CTCK không điều chỉnh khi chia cổ phiếu (HDB 30%, TCB 50% từ 29/10, PC1 15% từ 04/11) → trung vị CTCK cao ~30%
- [ ] KIỂM THỬ 29/10 — xếp hạng 27/10 lỗi mạng: 23/100 mã không có FV (VHM, BCM, NLG… dù app định giá được); cần chạy lại
- [ ] KIỂM THỬ 29/10 — "5 mã ứng viên" bỏ qua chốt chặn backend (backend 0 mã đạt); SHB +97,5% không có CTCK nào đứng đầu
- [ ] KIỂM THỬ 29/10 — 1103152/1103194 dòng BCTC thiếu published_at → mọi mã bị chặn "chưa xác minh độ mới"
- [ ] KIỂM THỬ 29/10 — bảng tickers: 16 mã tên giả "Công ty cổ phần VCB", 68 mã ngành là số "8355", 67 mã thiếu sàn
- [ ] KIỂM THỬ 29/10 — cột "Giá trị hợp lý (đ)" hiện 15.112,164 (lẻ phần nghìn đồng); khối ngoại sidebar 22.133 tỷ vs tab money 23.119 tỷ
- [ ] KIỂM THỬ 29/10 — bộ test mất 61 phút (dựng lại dữ liệu mã cùng ngành mỗi lần); tin vĩ mô AI cũ 9 ngày

## Đã xong

### 2026-11-04
- [x] Biểu đồ dòng tiền: KL khớp lồng vào tầng giá; thêm Volume profile bật/tắt, mặc định tắt (D91)
- [x] Dòng tiền thiếu 03/11: nạp tay; job vượt hạn mức giờ chờ 65 s rồi thử lại thay vì bỏ cả ngày; giữ lịch 18:00 (D93)
- [x] "Tải mới" mã: chạy song song, tự tải khi mở mã chỉ kéo BCTC khi có quý mới — 9–13 s → 1–5 s (D92)
- [x] Dọn thư mục dự án 5,6 GB → 931 MB: venv/.venv/dist/build vào Thùng rác, backups → `~/vn100_backups` (D92)
- [x] Tab Cổ tức: tin công bố chỉ hiện 5 tin mới nhất, còn lại sau nút "Hiện thêm"
- [x] Biểu đồ dòng tiền chuyển sang TradingView Lightweight Charts, giữ đủ các tầng (D90)
- [x] Tab Cổ tức: thêm "Thông tin doanh nghiệp công bố" (tin sàn + báo chí qua VCI, tóm tắt theo luật, bấm đọc sâu) và cảnh báo cổ tức đã công bố nhưng lịch chưa có (D89)

### 2026-11-03
- [x] Dòng tiền: lịch 08:30 đầu phiên, thử lại mã lỗi (bug vnai), nút Quét VN100 cập nhật luôn dòng tiền (D88)

### 2026-10-30
- [x] 30/10 — Cờ CORPORATE_ACTION_UNDATED hạ xuống cảnh báo, không chặn xếp hạng (D86)
- [x] 30/10 — Mở/đổi mã trên app tự tải mới giá, BCTC, báo cáo CTCK của mã đó (D87)

### 2026-10-29
- [x] Kiểm thử toàn dự án: 1152 test đạt; báo cáo sáng D84 chạy đúng (100/100 mã sự kiện); 8 lỗi ghi ở "Đang chờ"

### 2026-10-28
- [x] Kiểm tra cổ tức/quyền mua 100 mã mỗi sáng + mục "7 ngày tới" trong báo cáo Discord; TCB 50% đã vào DB (D84)
- [x] Sửa lỗi thử lại bị chặn (FRESH); 100/100 mã kiểm tra OK, thêm PC1 cổ tức CP 15% GDKHQ 04/11 (D84)
- [x] Chốt bản chính = `/Users/macos/antigravity-vn100` (bản Drive không đụng tới); chép việc 27–28/10 sang, 71 test đạt (D84)
- [x] Bản máy: làm mới giá tới 28/10 + sự kiện 100/100 mã (TCB 50%, PC1 15%, CTD +1)
- [x] Vòng học: tóm tắt tuần chép `knowledge/` sang Drive `vn100_knowledge`, routine đổi nguồn (D85)

### 2026-10-26 → 27
- [x] Lỗi `pivot`/`unstack` trên Python 3.14: gốc là numpy 2.2.6 tự build → nâng 2.3.5, chốt chặn khi import, test 544×100 (D82)
- [x] Đề xuất W44 #1 tín dụng NH: đo xong, bác bỏ — giữ trần 25% (D83)
- [x] Đề xuất W44 #2 BCTC BSI & dòng tiền: đo xong, dữ liệu nhất quán — bác bỏ (D83)
- [x] Đề xuất W44 #3: dữ liệu gửi DeepSeek ghi kỳ TTM/FY + định nghĩa ROE, D/E (D83)
- [x] Tạo `knowledge/LEARNINGS.md` (bài học đã đo — routine tuần đọc để không đề xuất lại)
- [x] Quyết định 27/10: MSN, GEX, REE, TCH giữ công bố theo CTCK (không bật SOTP riêng)
- [x] Quyết định 27/10: mã chu kỳ (HPG, BSR, VTP, SSI…) giữ mô hình thận trọng, không đổi sang LN dự phóng
- [x] Tạo PROGRESS.md; quy tắc hỏi quyết định bằng câu hỏi tick
- [x] Slide giới thiệu 10 trang: cách dùng, công thức từng tab, lưu ý (artifact "Hướng dẫn sử dụng VN100")
- [x] Bản tóm tắt tuần `scripts/weekly_learning_digest.py` + kiểm chứng nhãn dòng tiền 91 tuần + lịch Chủ nhật 18:00 (D82)
- [x] Routine Claude cloud Chủ nhật 20:00 → đề xuất qua Discord webhook → bot lưu `knowledge/proposals/` (D81)
- [x] Nhật ký báo cáo DeepSeek → `knowledge/ai_reports/` + backfill 12 báo cáo (D81)
- [x] Kế hoạch vòng học `docs/PLAN_LEARNING_LOOP.md`
- [x] Gộp tab "Định giá & dự phóng" + "So sánh CTCK" → "Định giá & CTCK"; sửa CSS thanh tab điện thoại (D80)
- [x] Đọc dòng tiền MWG (hướng dẫn dùng tab money)

### 2026-10-24
- [x] Tab money: dòng giải thích khi rê chuột mọi tiêu đề cột; bỏ bảng "Phiên ảnh hưởng lớn nhất", thêm ⚠ "Dồn 1 phiên" (D73)
- [x] Gói triển khai VPS: `deploy/setup_vps.sh`, `update_vps.sh`, systemd, `docs/DEPLOY_VPS.md`; thêm `discord.py` (D72)

### 2026-10-23
- [x] Mô hình tổng hợp CTCK nhiều nguồn (TARGET_PRICE) cho 15 mã còn lại → 91/100 công bố (D71)
- [x] Nạp lại BCTC Q3/2026 TCB, HT1, MSN; TTM dừng ở quý đủ (NT2); sửa lookahead số cổ phiếu (D71b)
- [x] Cập nhật bảng xếp hạng VN100 (không gọi AI)
- [x] Đẩy GitHub commit `fe02fd2` (repo ngo-tuankiet/EA_dinhGiaP)

### 2026-10-22
- [x] Excel ghi đúng nhãn BROKER_SYNTH (D68d)
- [x] Rà mô hình: giữ ROIC dài hạn = WACC; ngân hàng không lỗi công thức (D69); thử s2c 5 năm cho HPG — không áp dụng (D70)
- [x] BROKER_SYNTH 15 mã đầu + sửa 8 lỗi test (D68–D68c); tách DECISIONS cũ sang `docs/archive/`; xuất Excel tổng hợp

### Trước 22/10 (tóm tắt)
- [x] Nâng cấp định giá toàn VN100: ngân hàng, DCF, SOTP, kịch bản Bull/Bear (D61–D67)
- [x] Phân tích chu kỳ thép & HPG (artifact), xuất PDF báo cáo
