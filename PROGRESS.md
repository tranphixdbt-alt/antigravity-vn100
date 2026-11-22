# PROGRESS — việc đã làm / còn chờ

> Quy ước: xong một việc → chuyển xuống "Đã xong", đánh `[x]`, ghi ngày và số quyết định (Dxx — chi tiết kỹ thuật
> trong `DECISIONS.md`). Việc mới hoặc việc chờ người dùng → thêm vào "Đang chờ". Mỗi dòng ngắn gọn, một việc.

## Đang chờ

- [ ] VPS: đăng nhập vnstock 6 trong vn100-worker (golden đủ 2 máy Linux → gỡ một thiết bị cũ tại vnstocks.com/account?section=devices). KHÔNG cần cho FHSC (đã chạy bằng `FHSC_API_KEY`), chỉ cần khi làm S3–S7 (D96)
- [ ] Người dùng đăng nhập thử bằng tài khoản coin ở chungkhoang và chungquyen (điện thoại + máy tính); nếu lỗi gửi ảnh (D98)
- [ ] Thứ 2 23/11: kiểm chứng quyền trên VPS chạy đúng — ETF 09:40 và quét 14:00 (`docker logs chungquyen-worker`, `app/log.txt`)
- [ ] Dòng tiền khớp lệnh/thỏa thuận TÁCH (`flow_daily`, chế độ « Loại thỏa thuận » chính xác) không còn nguồn từ 13/11: FHSC chỉ có số gộp; gọi thẳng API Vietcap IQ bị hệ thống chặn (đi vòng gói trả phí) → người dùng chọn nguồn (D97)
- [ ] vnstock thế hệ 6 — S3–S7: BCTC, sự kiện quyền, tin công bố, chuyển môi trường app (`docs/PLAN_VNSTOCK_V6.md`)
- [ ] Trùng số D93: báo cáo PDF tích sản (11/11) dùng lại D93 của job dòng tiền (04/11, đã đẩy GitHub) — đổi báo cáo PDF sang số mới
- [ ] VPS → Google Drive: tự tải `knowledge/` lên Drive khi app/bot chạy trên VPS (để routine cloud đọc được)
- [ ] 5 test vàng lệch dữ liệu thật (04/11, thêm 12/11): TCB cổ phiếu +50% sau chia, ACB chi phí tín dụng TTM và MSN SOTP đổi khi có quý 3, registry đồng thuận 28/09 hết hạn, BAF nợ vay (test lấy quý mới nhất, DB đã có Q3/2026 thay Q2) — cần cập nhật số kỳ vọng
- [ ] PNJ (vụ P-Lab): chờ báo cáo CTCK lập sau 25/09/2026
- [ ] 8 mã chưa có báo cáo CTCK nào: DIG, DSE, KDC, KOS, NAB, SJS, VIC, VPI
- [ ] Bảo mật: kiểm tra ai có quyền thư mục Drive `DATA-G` (`.env` và `learning_webhook.env` nằm trong đó)
- [ ] Xóa thư mục rỗng "VN100 - De xuat hang tuan" trong Drive rosinante2037 (do lần thử tạo)
- [ ] Bản máy: MSN, VTP chưa có giá phiên 28/10 (job sáng 29/10 tự lấy lại — kiểm tra)
- [ ] Routine Chủ nhật 01/11 20:00: kiểm tra đọc được `vn100_knowledge` trên Drive (D85)
- [ ] VNM: chờ VCI đăng thông báo cổ tức mới (người dùng chọn chờ)
- [ ] Thứ 3 24/11: kiểm tra job `tpcp-10y` 07:20 trên VPS thêm điểm 23/11 (`/app/logs/tpcp-10y.log`); thứ 2 23/11 không có điểm mới là đúng (21–22/11 cuối tuần) (D100)
- [ ] Thứ 2 23/11: kiểm tra lần chạy tự động đầu tiên data-update + ranking 08:00 trên VPS (`docker logs vn100-worker`, `/app/.vn100_ranking/status.json`); worker giới hạn RAM 640 MB chưa từng chạy xếp hạng; bước dòng tiền trong data-update sẽ lỗi (cần `vnstock_data` đã khóa, D97)

- [ ] KIỂM THỬ 29/10 — giá mục tiêu CTCK không điều chỉnh khi chia cổ phiếu (HDB 30%, TCB 50% từ 29/10, PC1 15% từ 04/11) → trung vị CTCK cao ~30%
- [ ] KIỂM THỬ 29/10 — xếp hạng 27/10 lỗi mạng: 23/100 mã không có FV (VHM, BCM, NLG… dù app định giá được); cần chạy lại
- [ ] KIỂM THỬ 29/10 — "5 mã ứng viên" bỏ qua chốt chặn backend (backend 0 mã đạt); SHB +97,5% không có CTCK nào đứng đầu
- [ ] KIỂM THỬ 29/10 — 1103152/1103194 dòng BCTC thiếu published_at → mọi mã bị chặn "chưa xác minh độ mới"
- [ ] KIỂM THỬ 29/10 — bảng tickers: 16 mã tên giả "Công ty cổ phần VCB", 68 mã ngành là số "8355", 67 mã thiếu sàn
- [ ] KIỂM THỬ 29/10 — cột "Giá trị hợp lý (đ)" hiện 15.112,164 (lẻ phần nghìn đồng); khối ngoại sidebar 22.133 tỷ vs tab money 23.119 tỷ
- [ ] KIỂM THỬ 29/10 — bộ test mất 61 phút (dựng lại dữ liệu mã cùng ngành mỗi lần); tin vĩ mô AI cũ 9 ngày

## Đã xong

### 2026-11-22
- [x] TPCP_10Y tự động: job `tpcp-10y` 07:20 T2–T6 trên VPS lấy worldgovernmentbonds.com (khớp investing.com ≤ 0,001 điểm %), chỉ thêm ngày thiếu, báo Discord khi cũ > 21 ngày (D100)
- [x] Đồng bộ `deploy/docker/scheduler.py` của repo với VPS (2 dòng data-update + ranking T2/T5 08:00) (D100)
- [x] Upside lệch thang giá sau cổ tức/chia tách: FV snapshot quy về thang giá hiện tại ở mọi chỗ dùng `ranking_table` (TCB +99,6% → +33,1%; 10 mã quy đổi, 0 mã lệch thang trên dữ liệu VPS) (D99)
- [x] TPCP_10Y trên VPS: nạp 22 điểm 22/10–20/11 (investing.com, đối chiếu worldgovernmentbonds; sao lưu `/data/backup-before-tpcp-20261122.db`) → hết cờ STALE_MACRO_RF cho đợt xếp hạng 23/11 (D99)

### 2026-11-18
- [x] VPS chạy thay Mac: vnstock 4 (chép từ Mac) + vnstock 6, `.env` đầy đủ, container lịch job (07:50/08:30/CN 18:00) + bot Discord, trạng thái Mac chép sang volume; launchd Mac đã tắt hẳn; thêm discord-webhook/pypdf vào requirements (D96)
- [x] VPS: khóa FHSC — `vnstock keys set fhsc` không lưu được trong container (NoKeyringError) → chép khóa từ keychain Mac vào `FHSC_API_KEY` trong `/srv/apps/vn100/.env` qua SSH (không in, chmod 600; khóa người dùng dán tay bị FHSC từ chối AUTH_KEY_INVALID), `docker compose up -d`; thử 07:25: FHSC trả giá ACB + VNINDEX tới phiên 17/11 (D96)
- [x] Bỏ khỏi "Đang chờ": lịch flow-daily Mac 18:00 và setup_vps.sh (launchd Mac đã tắt, VPS chạy Docker)
- [x] (21/11) Báo cáo sáng VPS 19/11 và 20/11 chạy đúng, lấy dòng tiền FHSC (D97): `prices_daily` 19/11 khối ngoại + tự doanh 100/100 mã; 18/11 tự doanh trống (FHSC thiếu cả phiên)
- [x] (21/11) Chứng quyền trên VPS: quét 14:00 + báo cáo ETF lỗi 18–20/11 vì `.env` thiếu `FHSC_API_KEY` (Mac để trong keychain; test không gọi mạng nên không bắt được) → chép khóa từ `.env` VN100 trên VPS; thử thật `bien_dong_lich_su` FPT/HPG 250 phiên tới 20/11. Quét lại đầy đủ chưa được: Vietcap bảo trì cuối tuần (302 → maintenance.vietcap.com.vn)
- [x] (18/11 16:23) Tên chính VN100 đổi sang `chungkhoan.btinvest.vn`; `chungkhoang` chuyển hướng 301 (giữ đường dẫn); `.deploy` HEALTH_URL đổi theo (D98)
- [x] Đăng nhập chung bằng tài khoản coin cho chungkhoang + chungquyen (bỏ admin dùng chung); coin-check sửa cookie `.btinvest.vn` + giới hạn `/me` 600/phút (D98, `deploy/dang-nhap/README.md`)
- [x] App chứng quyền chạy trên VPS (12:40): https://chungquyen.btinvest.vn (cùng mật khẩu chungkhoang), web + 4 lịch (`scheduler.py`), dữ liệu chép từ Mac (198 file ket_qua, danh mục khớp md5), 185/185 test cw trong container, `deploy@chungquyen.timer` bật; 4 launchd `vn.cw-scanner.*` trên Mac đã tắt. Sửa code: `~/cw_scanner` → `git push vps main` (chỉ ở mạng nhà)
- [x] Vá khối ngoại/tự doanh 13–17/11 vào DB VPS (sao lưu `/data/backup-before-flows-20261118.db`); lỗi ghi phiên 18/11 dở → trả về bản sao lưu + sửa gốc cầu nối FHSC (D97)
- [x] Điện thoại báo "không bảo mật": gõ `chungkhoan.btinvest.vn` (không "g"; DNS *.btinvest.vn trỏ VPS nhưng chưa có khối Caddy/chứng chỉ → Caddy cắt). Người dùng chọn chuyển hướng: thêm khối Caddy `chungkhoan` → `https://chungkhoang.btinvest.vn` (sao lưu `Caddyfile.bak-chungkhoan-*`); chứng chỉ, 3 trang kiểm lại đúng
- [x] Deploy VN100 4f91eb0 (yfinance, Chromium) OK lúc 08:06
- [x] VPS có swap 2 GB (chủ máy thêm, thấy lúc 07:36)
- [x] S2 vnstock 6 (07:33): FHSC khối ngoại/tự doanh = VCI khớp + thỏa thuận ở 100% ô (100 mã × 21 phiên, ≤ 0,1% GTGD); FHSC không tách khớp/thỏa thuận (D97)
- [x] Báo cáo sáng tải thêm khối ngoại/tự doanh FHSC vào `prices_daily` (test 2 ca); tắt job flow-daily 08:30 trên VPS; script `scripts/backfill_fhsc_flows.py` vá phiên 13/11–17/11 (D97)

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
