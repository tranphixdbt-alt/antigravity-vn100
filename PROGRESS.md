# PROGRESS — việc đã làm / còn chờ

> Quy ước: xong một việc → chuyển xuống "Đã xong", đánh `[x]`, ghi ngày và số quyết định (Dxx — chi tiết kỹ thuật
> trong `DECISIONS.md`). Việc mới hoặc việc chờ người dùng → thêm vào "Đang chờ". Mỗi dòng ngắn gọn, một việc.

## Đang chờ

- [ ] VPS: gỡ một thiết bị Linux cũ tại vnstocks.com/account?section=devices (golden đủ 2 máy Linux) → đăng nhập vnstock 6 trong vn100-worker; người dùng tự `vnstock keys set fhsc` (D96)
- [ ] VPS 3,9 GB không swap: đề nghị chủ máy thêm swap 4 GB hoặc nâng RAM (treo 18/11) (D96)
- [ ] Dòng tiền khối ngoại/tự doanh DỪNG từ 12/11: gói tài trợ vnstock thế hệ 4 bị khóa ("ngừng xác thực từ 10/11/2026"), job flow_daily FlowRateLimited 16/11 và 17/11 → chuyển flow_daily sang FHSC: (1) trong giờ 06:00–21:00 thử `columns="all"` xem FHSC có tách khớp/thỏa thuận không + chạy lại S2 cả rổ; (2) chọn cách lưu khi FHSC chỉ có ròng gộp (cần duyệt vì đụng định nghĩa D73)
- [ ] Lịch flow-daily trên Mac vẫn 18:00: người dùng chạy lệnh launchctl của D88 để đổi sang 08:30
- [ ] vnstock thế hệ 6 — kiểm tra lượt chạy thật đầu tiên qua FHSC: job giá 07:50 ngày 13/11 (báo cáo sáng, nguồn giá) (D95) — 13/11 CHƯA ĐẠT: FHSC lỗi mạng (ReadError) cả 100 mã, job tự dùng VCI, giá phiên 12/11 đủ 100/100; kiểm lại lượt 07:50 kế tiếp. ~10:00: trình duyệt cùng máy cũng không vào invest.fhsc.com.vn, máy chủ nước ngoài cũng bị cắt → FHSC sự cố hoặc chặn IP nhà; chờ thử bằng 4G
- [ ] vnstock thế hệ 6 — S2: chạy lại đối chiếu khối ngoại/tự doanh FHSC trong giờ 06:00–21:00 (đêm 12/11 mới được 3/100 mã) — 13/11 08:17 chạy lại được 0/100 mã (FHSC ReadError), chạy lại khi FHSC kết nối được
- [ ] vnstock thế hệ 6 — S3–S7: BCTC, sự kiện quyền, tin công bố, chuyển môi trường app (`docs/PLAN_VNSTOCK_V6.md`)
- [ ] Trùng số D93: báo cáo PDF tích sản (11/11) dùng lại D93 của job dòng tiền (04/11, đã đẩy GitHub) — đổi báo cáo PDF sang số mới
- [ ] VPS: nhân viên chạy `bash deploy/setup_vps.sh`, chép `.env` bằng `scp`; tắt launchd trên Mac khi VPS chạy
- [ ] VPS → Google Drive: tự tải `knowledge/` lên Drive khi app/bot chạy trên VPS (để routine cloud đọc được)
- [ ] 5 test vàng lệch dữ liệu thật (04/11, thêm 12/11): TCB cổ phiếu +50% sau chia, ACB chi phí tín dụng TTM và MSN SOTP đổi khi có quý 3, registry đồng thuận 28/09 hết hạn, BAF nợ vay (test lấy quý mới nhất, DB đã có Q3/2026 thay Q2) — cần cập nhật số kỳ vọng
- [ ] PNJ (vụ P-Lab): chờ báo cáo CTCK lập sau 25/09/2026
- [ ] 8 mã chưa có báo cáo CTCK nào: DIG, DSE, KDC, KOS, NAB, SJS, VIC, VPI
- [ ] Bảo mật: kiểm tra ai có quyền thư mục Drive `DATA-G` (`.env` và `learning_webhook.env` nằm trong đó)
- [ ] Xóa thư mục rỗng "VN100 - De xuat hang tuan" trong Drive rosinante2037 (do lần thử tạo)
- [ ] Bản máy: MSN, VTP chưa có giá phiên 28/10 (job sáng 29/10 tự lấy lại — kiểm tra)
- [ ] Routine Chủ nhật 01/11 20:00: kiểm tra đọc được `vn100_knowledge` trên Drive (D85)
- [ ] VNM: chờ VCI đăng thông báo cổ tức mới (người dùng chọn chờ)

- [ ] KIỂM THỬ 29/10 — giá mục tiêu CTCK không điều chỉnh khi chia cổ phiếu (HDB 30%, TCB 50% từ 29/10, PC1 15% từ 04/11) → trung vị CTCK cao ~30%
- [ ] KIỂM THỬ 29/10 — xếp hạng 27/10 lỗi mạng: 23/100 mã không có FV (VHM, BCM, NLG… dù app định giá được); cần chạy lại
- [ ] KIỂM THỬ 29/10 — "5 mã ứng viên" bỏ qua chốt chặn backend (backend 0 mã đạt); SHB +97,5% không có CTCK nào đứng đầu
- [ ] KIỂM THỬ 29/10 — 1103152/1103194 dòng BCTC thiếu published_at → mọi mã bị chặn "chưa xác minh độ mới"
- [ ] KIỂM THỬ 29/10 — bảng tickers: 16 mã tên giả "Công ty cổ phần VCB", 68 mã ngành là số "8355", 67 mã thiếu sàn
- [ ] KIỂM THỬ 29/10 — cột "Giá trị hợp lý (đ)" hiện 15.112,164 (lẻ phần nghìn đồng); khối ngoại sidebar 22.133 tỷ vs tab money 23.119 tỷ
- [ ] KIỂM THỬ 29/10 — bộ test mất 61 phút (dựng lại dữ liệu mã cùng ngành mỗi lần); tin vĩ mô AI cũ 9 ngày

## Đã xong

### 2026-11-18
- [x] VPS chạy thay Mac: vnstock 4 (chép từ Mac) + vnstock 6, `.env` đầy đủ, container lịch job (07:50/08:30/CN 18:00) + bot Discord, trạng thái Mac chép sang volume; launchd Mac đã tắt hẳn; thêm discord-webhook/pypdf vào requirements (D96)

### 2026-11-17
- [x] VPS VN100 (`ubuntu@192.168.1.201`, máy `vps-web`, Docker `/srv/apps/vn100`, web chungkhoang.btinvest.vn có mật khẩu): đã ở commit mới nhất + DB tới 16/11 (tự đồng bộ từ GitHub). Chép riêng dòng `DEEPSEEK_API_KEY` vào `/srv/apps/vn100/.env` qua SSH (chmod 600; không chép token Discord/vnstock vì VPS chỉ chạy giao diện), `deploy vn100 --force`: container healthy, app nhận khóa
- [x] Đẩy DB portable mới lên GitHub (giá tới 16/11, BCTC Q3/2026 107 mã, CTCK tới 13/11), quét secret trong DB: sạch
- [x] Đẩy GitHub (tranphixdbt-alt/antigravity-vn100): 8 commit tới D95 + sửa test D62 (BAF đọc kỳ mới nhất); tài khoản rosinante2037-dev có quyền Write

### 2026-11-13
- [x] Sửa lỗi thanh tiến độ "Quét VN100" báo StreamlitAPIException mỗi 5 giây khi đang tải trước FHSC (completed −1 → 0, D95)
- [x] Sửa 3 test FHSC hỏng theo giờ thật (cố định đồng hồ bộ đệm trong test); chạy lại app + Quét VN100 sau khi máy tắt 19:38 làm đợt quét dừng ở 43/100

### 2026-11-12
- [x] vnstock thế hệ 6 — S0: khóa FHSC dùng chung keyring với dự án chứng quyền, gọi thử HTTP 200 (D94)
- [x] vnstock thế hệ 6 — S1: giá FHSC khớp DB 100/100 mã × 60 phiên, 0 ô lệch > 0,5%, có điều chỉnh hồi tố (D94)
- [x] Chuyển từng phần: job giá 07:50 và Quét VN100 tải FHSC trước qua `~/.venv_6x`, VCI dự phòng; nút Tải mới vẫn VCI (D95)

### 2026-11-11
- [x] Lỗi vnai `threading` làm thiếu giá 2–3 mã/sáng: đường tải giá gọi lại ngay 1 lần; nạp bù MCH, VPI phiên 10/11 (D94)
- [x] Kiểm tra vnstock: thế hệ 4 ngừng xác thực 10/11; dựng `~/.venv_6x` với vnstock 6.0.0, lập kế hoạch chuyển (D94)

### 2026-11-05
- [x] Đẩy GitHub `d424ada` (repo ngo-tuankiet/EA_dinhGiaP), đồng bộ tới D93 từ bản máy @1285662; repo tranphixdbt-alt chưa đẩy

### 2026-11-11
- [x] Báo cáo PDF 20 cổ phiếu tích sản 1–3 năm (VN100, 22 trang, độ tin cậy A/B/C) (D93)

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
