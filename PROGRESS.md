# PROGRESS — việc đã làm / còn chờ

> Quy ước: xong một việc → chuyển xuống "Đã xong", đánh `[x]`, ghi ngày và số quyết định (Dxx — chi tiết kỹ thuật
> trong `DECISIONS.md`). Việc mới hoặc việc chờ người dùng → thêm vào "Đang chờ". Mỗi dòng ngắn gọn, một việc.

## Đang chờ

- [x] D124: chặn phiên khối ngoại FHSC trả trống cả rổ, vá 23/11 từ Vietcap, Ếch có công cụ khối ngoại từng mã và mua/bán ròng nhiều nhất.
- [x] D123: số gom/xả theo ngành đang chọn, khối cảnh báo trong tab Chứng quyền, siết điều kiện cảnh báo CW (cw_scanner `1197631`).
- [x] Rà soát trước bàn giao (D122): lưu ý dữ liệu thu vào nút tam giác, màu tăng giảm ở trang Hôm nay, VN-Index/VN30 và VN100 tăng giảm mạnh nhất trong phiên (Vietcap, `/api/truc-tiep`), sửa thẻ VN-Index hiện điểm giữa phiên, job `ban-tin-vi-mo` 07:30 viết lại bản tin vĩ mô AI.
- [x] Dữ liệu luôn mới (D121, `docs/PLAN_CAP_NHAT_DU_LIEU.md`): đã lên VPS 26/11 10:50 (`a2f7eb9`, chứng quyền `ec6b127`). Sao lưu `/data/backup-before-d121-20261126.db`; `scheduler.py` cũ giữ ở `/srv/apps/vn100/scheduler.py.bak-20261126-truoc-d121` và `/srv/apps/chungquyen/scheduler.py.bak-20261126-truoc-etf-chieu`. Đã nạp vĩ mô Cục Thống kê (CPI 10/2026, bán lẻ 7–10/2026, GDP quý III) và, theo người dùng « Ghi theo cục thống kê », GDP quý I/2026 8,15% (DB thiếu) và quý II sửa 8,39% → 8,81%.
- [ ] Kiểm sau 15:45 ngày 26/11: lượt `gia-cuoi-phien` phải ghi đè 32 dòng giá giữa phiên 26/11 mà đợt Quét VN100 sáng nay (còn code cũ) đã ghi (31 mã + VNINDEX). Sáu mã ngoài VN100 trong số đó (GEL, HHS, MML, MSR, TBC, VSH) chỉ được ghi đè ở lần quét sau. Còn lại: chuyển BCTC sang FHSC (kế hoạch riêng)
- [ ] Web hợp nhất btinvest.vn: lát 6: web mới ĐANG CHẠY tại `https://btinvest.vn` từ tối 25/11/2026, đã có Quản trị đầu tiên và sao lưu `web_user.db` 23:00 mỗi ngày (D111, D112). Còn: B6 người dùng thử thật (so số từng mã với web cũ, điện thoại, âm thanh, thông báo); B8 đo trong giờ khớp lệnh và chạy lại 9 test trượt; xem lần sao lưu theo lịch đầu tiên (23:00 ngày 25/11) có `exit=0`; `Dockerfile` trên VPS khác bản sao 4 dòng; nút Back mới chỉ thử trên trình duyệt máy tính và cỡ điện thoại giả lập, chưa thử vuốt lùi trên điện thoại thật
- [ ] Web hợp nhất, cảnh báo: chỉ báo khi web đang mở (người dùng chốt); chưa nghe thử âm thanh và chưa thử thông báo của trình duyệt trên điện thoại thật; mức giá tự đặt đang riêng từng người, Quản trị không xem (mặc định của kế hoạch, chưa hỏi lại) (D108)
- [ ] Web hợp nhất, danh mục: thước và lãi lỗ chưa cùng thời điểm giá (thước theo đợt định giá hoặc lần quét, lãi lỗ theo giá trực tiếp; đã ghi ở chân trang); cổ tức bằng cổ phiếu và chia tách chưa tự điều chỉnh; hợp đồng hết hạn phải tự ghi lệnh đóng (D107)
- [ ] Web hợp nhất: đăng nhập thật với coin chưa thử được ở máy Mac; lát 6 phải kiểm `/me` nhận cookie do ứng dụng gửi lại và đổi Caddy để `/api/*` trả 401 thay vì 302 (D106)
- [ ] Web hợp nhất: các nút thao tác của Quản trị (cập nhật vĩ mô, làm mới tin, định giá lại VN100, sinh báo cáo AI, lưu kịch bản, xuất tệp) để sau khi lên VPS, người dùng chốt 25/11/2026
- [ ] Web hợp nhất: phần phân tích theo giá lúc mở của từng chứng quyền, quỹ, hợp đồng vẫn là trang cũ đặt trong khung (đổi màu, phông); dựng lại theo giao diện mới cần tách số khỏi HTML trong `~/cw_scanner` (D105)
- [ ] Web hợp nhất: chưa có Lướt CW, CW sắp ra mắt, nút quét, trang hướng dẫn của web chứng quyền (D105; danh mục và cảnh báo giá đã có ở D107, D108)
- [ ] Web hợp nhất: hợp đồng tương lai chưa có tiêu chí "nên xem xét", tab Phái sinh chỉ hiện basis; chờ người dùng đặt ngưỡng nếu muốn xếp nhóm (D105)
- [ ] Chạy cả bộ test trên máy Mac 24/11/2026: 1.257 qua, 9 trượt, 4 bỏ qua. 7 test đã rõ tên đều đọc DB thật hoặc số golden (`test_golden_banks` TCB số cổ phiếu lệch 50% so với vốn điều lệ, `test_sotp_holdings` MSN 56.124 so với 57.851, `test_freshness_gate`, `test_extreme_review_gate`, `test_broker_synth`, `test_data_flag_fixes`, `test_golden_consensus`); không test nào dùng tệp của web hợp nhất. Chạy lại 25/11 sau lát 5b: 1.278 qua, vẫn đúng 9 trượt (sau lát 5c: 1.290 qua, vẫn 9 trượt đó); hai test chưa rõ tên lần trước là `test_batch_engine::test_bank_dispatch` và `::test_nonfin_dispatch` (TypeError khi so sánh). Chưa rõ do DB máy Mac cũ hay lỗi thật: cần chạy lại trên VPS (D105)
- [ ] Web hợp nhất: máy Mac ra NOT_RATED cho mọi mã vì DB cũ (cờ STALE_PRICE, STALE_MACRO_RF); muốn thử lát 2 với nhãn thật thì cập nhật DB máy Mac hoặc chạy trên VPS (D102)
- [ ] Web hợp nhất: người dùng chốt "Rẻ x%" của cổ phiếu tính theo biên an toàn hay upside, và cách quy đổi nhãn MUA/NẮM GIỮ/BÁN (`docs/PLAN_WEB_HOP_NHAT.md` mục 9)
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
- [ ] Wyckoff (`docs/PLAN_WYCKOFF_FLOW.md`): tiếp W1 bộ máy cấu trúc → W2a thành phần VN100 theo kỳ → W2 kiểm chứng → W3 giao diện → W4 ghép dòng tiền (D101)
- [ ] Xác minh định nghĩa mua/bán chủ động FHSC: mua + bán ≈ 3,9 × KL khớp (VCB 20/11: 12,6 triệu vs 3,9 triệu), 24/09–22/10 thiếu ~45% mã — chưa dùng cho phân tích tới khi rõ (D101)
- [ ] Thứ 2 23/11: kiểm tra job `active-flow` 07:35 trên VPS thêm phiên 21/11? (không — 21–22/11 cuối tuần; phiên mới đầu tiên 23/11 vào lượt thứ Ba 24/11) (`/app/logs/active-flow.log`) (D101)
- [ ] Thứ 2 23/11: kiểm tra lần chạy tự động đầu tiên data-update + ranking 08:00 trên VPS (`docker logs vn100-worker`, `/app/.vn100_ranking/status.json`); worker giới hạn RAM 640 MB chưa từng chạy xếp hạng; bước dòng tiền trong data-update sẽ lỗi (cần `vnstock_data` đã khóa, D97)

- [ ] KIỂM THỬ 29/10 — giá mục tiêu CTCK không điều chỉnh khi chia cổ phiếu (HDB 30%, TCB 50% từ 29/10, PC1 15% từ 04/11) → trung vị CTCK cao ~30%
- [ ] KIỂM THỬ 29/10 — xếp hạng 27/10 lỗi mạng: 23/100 mã không có FV (VHM, BCM, NLG… dù app định giá được); cần chạy lại
- [ ] KIỂM THỬ 29/10 — "5 mã ứng viên" bỏ qua chốt chặn backend (backend 0 mã đạt); SHB +97,5% không có CTCK nào đứng đầu
- [ ] KIỂM THỬ 29/10 — 1103152/1103194 dòng BCTC thiếu published_at → mọi mã bị chặn "chưa xác minh độ mới"
- [ ] KIỂM THỬ 29/10 — bảng tickers: 16 mã tên giả "Công ty cổ phần VCB", 68 mã ngành là số "8355", 67 mã thiếu sàn
- [ ] KIỂM THỬ 29/10 — cột "Giá trị hợp lý (đ)" hiện 15.112,164 (lẻ phần nghìn đồng); khối ngoại sidebar 22.133 tỷ vs tab money 23.119 tỷ
- [ ] KIỂM THỬ 29/10 — bộ test mất 61 phút (dựng lại dữ liệu mã cùng ngành mỗi lần); tin vĩ mô AI cũ 9 ngày

## Đã xong

### 2026-11-24
- [x] Web hợp nhất btinvest.vn: 32 câu hỏi-đáp, hai bản mẫu, kế hoạch 6 lát (`docs/PLAN_WEB_HOP_NHAT.md`) (D102)
- [x] Web hợp nhất lát 1: API chỉ đọc + giao diện thật cho tìm mã và dòng tiền 100 mã, chạy tại máy cổng 8600; 8 test mới, 95 test qua (D102)
- [x] Web hợp nhất lát 2: định giá, kịch bản, độ nhạy, dự phóng, giả định, WACC, báo cáo tài chính, công ty chứng khoán, cổ tức, báo cáo AI đã lưu của từng mã; 5 test mới, thử VRE, VCB, SSI, BVH, FPT (D103)
- [x] Web hợp nhất lát 3: tab Hôm nay (thị trường, vĩ mô, bản tin, lịch quyền 90 ngày) và xếp hạng VN100 + tích sản trong tab Cổ phiếu; 5 test mới, 18 test web qua (D104)
- [x] Web hợp nhất lát 7, góc chat AI "Hỏi Ếch" (26/11/2026): con ếch góc dưới bên phải mở khung chat, câu gợi ý, trả lời ngắn từ số liệu của web kèm nút mở mã, 20 câu mỗi tài khoản mỗi ngày; 5 công cụ mới học theo cách TCBS chia (thị trường hôm nay, độ rộng, mã kéo rổ VN100 ước tính, tín hiệu kỹ thuật, so với cùng ngành); bot Discord không đổi; 12 test mới, thử thật 4 câu với DeepSeek (D120)
- [x] Web hợp nhất lát 7: D114–D120 đã đẩy lên btinvest.vn (`4899f04`, deploy 03:45 26/11/2026, bốn container khỏe, hỏi thật Ếch một câu trên web)
- [x] Web hợp nhất lát 7, liên hệ và khung cuộn (26/11/2026): nút Liên hệ (Zalo, gọi điện, Facebook) trên thanh đầu, trong thực đơn tài khoản ở điện thoại và cuối trang chủ, lấy từ `web.lien_he`; mọi danh sách và bảng dài của các tab trong khung cuộn cùng kiểu, chứng quyền hiện đủ trong khung thay cho nút Hiện thêm; 1 test mới (D119)
- [x] Web hợp nhất lát 7, bốn ô đầu trang chủ (26/11/2026): Cổ phiếu, Chứng quyền, ETF, Phái sinh, mỗi ô một con số chính và vài mã bấm được, bấm vào sang tab; bỏ khối trùng số; sửa kèm lỗi tệp giao diện thiếu `Cache-Control: no-cache` làm trình duyệt chạy mã cũ sau deploy (1 test mới) (D118)
- [x] Web hợp nhất lát 7, cách viết báo cáo AI theo góp ý (25/11/2026): ít số, nói chiều hướng, thêm "Điều ít người để ý" và "So với cùng ngành" có tên đối thủ; che giá trị của mô hình cả trong bảng cùng ngành khi chưa công bố; thử thật một lần tại máy (544 từ, các nhận định đối chiếu lại đúng với gói số liệu) (D117)
- [x] Web hợp nhất lát 7, nút sinh báo cáo AI bản ngắn (25/11/2026): mọi tài khoản đã duyệt bấm được, 5 lượt mỗi ngày, khoảng 500 từ (tổng quan công ty, nhận định về mã, 3 rủi ro); cùng gói số liệu đã kiểm của bản dài; dữ liệu không đổi thì dùng lại không mất lượt; 15 test mới; thử thật hai lần với DeepSeek tại máy (618 từ rồi 455 từ sau khi siết câu lệnh). Sửa kèm lỗi có sẵn: trang 24hmoney không vào được làm sập lượt sinh báo cáo AI bản dài (D116)
- [x] Web hợp nhất lát 7, tờ mã (25/11/2026): tờ chi tiết rộng 3/5 màn hình; định giá và giá mục tiêu (trung vị công ty chứng khoán) lên đầu, rồi dòng tiền; "So với công ty chứng khoán" thành mục riêng mở sẵn; chỉ đổi bố trí, không đổi số; thử trên trình duyệt tại máy (D115)
- [x] Web hợp nhất, nút Back (25/11/2026): chuyển tab, vuốt sang tab khác và mở tờ chi tiết nay là bước lịch sử, Back đóng tờ rồi về tab trước thay vì rời web; đóng tờ bằng nút thì lùi đúng một bước; địa chỉ có sẵn `?ma=` vẫn đóng tại chỗ; thử trên trình duyệt ở cỡ máy tính và điện thoại, chưa có test tự động cho phần JavaScript (D114)
- [x] Web hợp nhất, hai lỗi nhỏ thấy sau khi lên VPS (25/11/2026): đổi `#tab` trên địa chỉ khi trang đang mở nay chuyển tab (tên lạ thì giữ nguyên); có biểu tượng trang vẽ từ dấu hiệu BT của web (`favicon.ico`, `apple-touch-icon.png`); 1 test mới, 71 test web qua (D113)
- [x] Web hợp nhất lát 6, sao lưu và Quản trị đầu tiên (25/11/2026): người dùng tự đặt `WEB_ADMIN_EMAILS`; job `web-user-backup` 23:00 mỗi ngày trong `vn100-worker`, chạy tay hai lần ra một bản đọc lại đủ dòng; cả năm tab của web mới ra số thật trên VPS (D112)
- [x] Web hợp nhất lát 6, đưa lên VPS (25/11/2026): commit và đẩy mã hai dự án, container `btinvest-web` (768 MB, đang dùng 160 MB), khối Caddy mới cho `btinvest.vn`; hai web cũ không đổi; đăng nhập coin thật chạy được, tài khoản mới ở trạng thái chờ duyệt và bị khóa số liệu; 239 test chứng quyền qua trong container (D110, D111)
- [x] Web hợp nhất lát 6, phần chuẩn bị tại máy (25/11/2026): biến `WEB_CW_BASE_URL`, tự tạo thư mục của tệp dữ liệu người dùng, script sao lưu `web_user.db` (giữ 14 bản), test chặn cả 35 đường `/api/` khi chưa đăng nhập; sửa ba test « chỉ có route đọc » kiểm rỗng; 11 test mới, 70 test web qua; chưa đụng VPS (D109)
- [x] Web hợp nhất lát 5c (25/11/2026): cảnh báo trong web: chuông có số, tờ Cảnh báo (tin chưa xem, mức giá tôi đặt, bốn nhóm bất thường đang mua được), hỏi tin mỗi phút trong giờ khớp lệnh; bảng `web_price_levels`, 5 route; ngưỡng lãi lỗ tự đặt của cổ phiếu và ETF nay sinh tin; 9 test mới ở cw_scanner (239 qua), 12 test mới ở đây (59 test web qua); phần chung trùng tin trang cũ khi so cùng lúc (D108)
- [x] Web hợp nhất lát 5b (25/11/2026): danh mục 4 loại của từng người (bảng `web_orders`, 5 route, giao diện Danh mục); vị thế và lãi lỗ do `~/cw_scanner/vi_the.py` tính theo ba công thức người dùng duyệt; Quản trị xem được danh mục của mọi người, chỉ xem; 11 test mới ở cw_scanner (230 qua), 9 test mới ở đây (47 test web qua) (D107)
- [x] Web hợp nhất lát 5a (25/11/2026): tài khoản được duyệt và hai vai; tệp dữ liệu người dùng riêng `web_user.db` (3 bảng); mọi route số liệu đòi đã đăng nhập và đã duyệt; màn hình chờ duyệt, nút tài khoản, tờ Tài khoản cho Quản trị; 12 test mới, 38 test web qua (D106)
- [x] Web hợp nhất lát 4 (24/11/2026): tab Chứng quyền (461 mã lần quét 17/11), ETF (21 quỹ), Phái sinh (8 hợp đồng, giá Vietcap trực tiếp) với số thật qua `~/cw_scanner/web_api.py` và cầu nối `web_cw.py`; tờ chi tiết nhúng trang phân tích cũ; ô tìm đủ bốn loại mã; dấu "!"; 12 test mới ở cw_scanner (219 qua), 8 test mới ở đây (26 test web qua) (D105)

### 2026-11-22
- [x] Kế hoạch Wyckoff cho tab money (nghiên cứu có nguồn, đọc code, đo dữ liệu) + 8 quyết định của người dùng (D101)
- [x] W0: bảng `active_flow_daily` + job `active-flow` 07:35 T2–T6 trên VPS; nạp lần đầu 4.997 dòng (100 mã × 61 phiên), chạy lại không trùng (D101)
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
