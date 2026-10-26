# Kế hoạch tab "Dòng tiền ngành" VN100 (v2.1)

**Trạng thái:** ĐÃ TRIỂN KHAI A1–A3, B1 và golden T17 (24/10/2026, D73). B2 và các mục "Chưa làm" trong D73 còn chờ. Lập ngày 23/10/2026. Bản này **thay cho v1** (v1 chưa có dòng code nào). Số quyết định: **D73** (D72 đã dùng cho "Gói triển khai VPS").

**Cách lập:**
- Workflow 2 vòng, mỗi vòng 11 agent: khảo sát nguồn dữ liệu/DB/chuẩn ngành → 3 phương án → 3 giám khảo → tổng hợp → rà soát.
- Phương án **thẻ từng mã** được chấm cao nhất (92 điểm) nên làm xương sống. Ghép thêm bản đồ ngành và lộ trình học từ 2 phương án còn lại.
- v2.1 = v2 đã sửa toàn bộ 23 điểm rà soát.
- Mọi số mẫu trong bản này lấy từ chạy thử **chỉ đọc** trên DB thật ngày 22/10. Đó là sample, **không phải golden**.

## Quyết định của người dùng (23/10/2026)

| # | Quyết định | Áp dụng ở v2.1 |
|---|---|---|
| 1 | Tên tab **"Dòng tiền ngành"**, nhãn đáy trên điện thoại **"money"** | Giữ nguyên |
| 2 | Mặc định **loại** phiên thỏa thuận | Giữ. Cờ thỏa thuận nay tính theo tổng ngoại + tự doanh (bắt 51 phiên-mã thay vì 24) |
| 3 | Ngưỡng của v1: band 1%, độ rộng 50%, upside 15%/0%, "ít mã" khi n < 3 | v2 không còn trạng thái ✅/❌ theo ngành nên band/độ rộng/upside cũ không dùng nữa. Giữ "ít mã" khi n < 3. Ngưỡng mới cho từng mã xem Q3 |
| 4 | Giữ `sector_min_members` = 2 | Giữ cho sidebar. Tab dùng `small_sector_n` = 3 để ngành 2 mã không lọt vào câu kết luận (ghi rõ lý do lệch ở D73) |
| 5 | MVP không có cột "Gợi ý xem" | Giữ. Upside chỉ là cột phụ |
| 6 | Chấp nhận lệch sidebar 1 phiên | Giữ |
| 7 | Dòng rác 28/06 chỉ lọc ở loader | Giữ |
| 8 | Duyệt sửa ingest dòng tiền (tự kéo mỗi ngày) | Đã duyệt **hướng đi**. Nhưng B1 (§7) phải **tạo bảng mới `flow_daily`** (đổi schema) → cần bạn duyệt riêng ở Q1 bên dưới |
| 9 | Sidebar | Chưa quyết. Mặc định giữ nguyên |

## 0. v1 → v2: giữ gì, đổi gì

| Giữ từ v1 | Đổi ở v2 |
|---|---|
| Lịch phiên theo độ phủ giá; bỏ phiên hôm nay trước `session_close`; `flow_date` = phiên cuối đủ độ phủ khối ngoại (đếm cả `flow_daily` VCI — sửa 24/10/2026, D78); giá cắt về `flow_date`; đếm phiên thủng | Thêm **tự doanh**, **thỏa thuận lớn** và nhãn **từng mã** (v1 chỉ có khối ngoại theo ngành) |
| Cờ toàn vẹn \|net − (mua − bán)\| > tol thì NaN; cờ gãy điều chỉnh; dòng CN 28/06 chỉ lọc ở loader | Cờ thỏa thuận đổi sang **quy tắc tổng F+P**: bắt 51 phiên-mã trong 20 phiên, quy tắc chỉ dùng khối ngoại của v1 bắt 24 |
| Công tắc Gồm/Loại, mặc định Loại; luôn hiện cả 2 tổng VN100 | Tổng VN100 20 phiên ở chế độ Loại là −8.520 tỷ (v1: −8.964) |
| Cache cho cả 2 chế độ; không gọi mạng hay DeepSeek khi render; upside chỉ là cột phụ, không có "Gợi ý xem" | Dùng CMF20 có nhãn (v1 cấm), xử lý riêng phiên H=L |
| Golden khối ngoại so với CafeF, sai số < 2% (T14 cũ) | Golden chỉ chọn phiên **không có thỏa thuận** (ASEAN `put_through` = 0), vì CafeF GDKhoiNgoai chỉ tính **khớp lệnh** (MCH 09/10: CafeF +47,53 tỷ = VCI khớp +47,54 tỷ). Số khối ngoại **không mâu thuẫn** giữa các nguồn |
| Ngành ít mã đưa xuống cuối, có badge | Tên tab "Dòng tiền ngành", nhãn đáy "money"; config `money_flow`; số quyết định **D73** |

**Lỗi giám khảo nêu và cách sửa trong v2:**

| Lỗi | Sửa |
|---|---|
| CTG/KDH ra "Gom" dù khối ngoại bán ròng | **Phủ quyết theo dấu:** Gom cần R_F ≥ 0, Xả cần R_F ≤ 0. Chạy thử: KDH (−2,04%) và CTG (−4,0%) ra Trung tính |
| Huy hiệu thỏa thuận ghi "≥ 9.155 tỷ" | Chỉ KL là cận dưới. Giá trị ghi "**ước ~**", tính bằng cận dưới KL × close |
| Tử số/mẫu số R_P không nhất quán; giả định tự doanh NULL→0 không vững (apply_sponsor_market_cache chỉ ghi khối ngoại cho 03–28/08; ngày 21/10 có 3.175 tỷ GTGD ở dòng NULL) | **NULL = thiếu, không coi là 0** (trừ cờ thỏa thuận, nơi coi NULL = 0 vẫn ra cận dưới an toàn). R_P, tổng ngành và D tính trên **cùng tập phiên có số**, kèm độ phủ |
| Ô "Thỏa thuận −11.943 tỷ" đặt tên sai; cột "Trong nước" chỉ là ảnh gương của 2 cột kia | Bỏ cả hai khỏi màn 5 giây. Ghi đúng tên: "F+P trong các phiên có cờ thỏa thuận". D chỉ hiện ở màn chi tiết |
| Template cài cứng "chuyển nhượng cổ đông", "phía nhận là trong nước" | Template chỉ in số. Diễn giải có nguồn báo chí chỉ nằm trong bài học tĩnh |
| Chip "tiền đang vào" mâu thuẫn bài L4 | Danh sách cụm từ cấm trong config (`forbidden_phrases`), có test |
| Tự doanh chặn được nhãn (FPT ra "Lẫn lộn") | Tự doanh chỉ **xác nhận**: không chặn được, và một mình không tạo được nhãn |
| H=L bị bỏ khỏi CMF nhưng phiếu vẫn được tính | Có > 2 phiên H=L thì phiếu Giá-KL là ◌ và nhãn ra "Chưa đủ dữ liệu", kèm huy hiệu sàn/trần trắng. **D76:** CMF tính trên biên độ thực nên phiên trần/sàn trắng bên được tính (±1); chỉ phiên đứng giá (cao = thấp = giá phiên trước) bị loại |
| Không có cờ tự doanh chưa chốt | Giai đoạn A: tự doanh của phiên hôm nay gắn "tạm" và không vào phiếu. Giai đoạn B: `fetched_at`/`is_final` |
| `expander` vẫn chạy code bên trong; `@st.dialog` tự mở lại; AppTest không giả lập được bấm dòng | Phần chi tiết đặt sau `st.toggle`. Đường chính dùng `selectbox` (test được); bấm dòng bảng chỉ là đường phụ, kiểm tay |
| `create_all` tự tạo bảng mới khi import; COALESCE ghi đè số đã chốt | Bảng mới dùng metadata riêng, chỉ tạo bằng script migration sau khi backup. Dòng `is_final` không bị ghi đè |
| Test so với `leaders()` sai khi có phiên thủng; test ghim số trên DB thật dễ gãy | Test so với sidebar chỉ chạy ở chế độ Gồm, trên fixture không có phiên thủng. Số trên DB thật chỉ in làm sample, không assert |

## 1. Mục tiêu và lời hứa 5 giây

- **Câu hỏi cần trả lời:** (a) Trong VN100, khối ngoại và tự doanh đang mua/bán ròng ngành nào? (b) Mã X có **dấu hiệu đang được gom** hay không? (c) Nếu muốn hiểu sâu, đọc từ đâu?
- **Đây không phải khuyến nghị, không dự báo.** UI ghi "mua/bán ròng", không ghi "tiền vào/ra". Lý do: mỗi lệnh luôn có một người mua và một người bán.
- **Màn đầu, desktop xem được không cần cuộn:**

| Hàng | Nội dung |
|---|---|
| 1. Dải trạng thái | "Giá đến 23/10 · Dòng tiền đến 22/10 (ngoại 100/100 mã, tự doanh x mã) · 20 phiên · [Loại \| Gồm] thỏa thuận · 0 phiên thủng · chỉ cập nhật khi bấm Quét VN100 · cấu hình `money_flow` #hash (D73)" (truy vết theo AGENTS #5) |
| 2. Một câu kết luận (1 dòng, ~25 chữ, template số, không AI) + câu miễn trừ cố định | Mẫu 22/10: "20 phiên, đã loại thỏa thuận: ngoại bán ròng 8.520 tỷ · mua mạnh Dầu khí, Xây dựng · bán mạnh Bán lẻ, Công nghệ · 4 dấu hiệu gom · 23 dấu hiệu xả". Câu miễn trừ: "Mô tả dữ liệu quá khứ, không phải khuyến nghị, không dự báo giá." Chi tiết (tổng có thỏa thuận −22.133 tỷ; tự doanh +1.050 tỷ kèm độ phủ) đặt ở dòng phụ chữ nhỏ |
| 3. **Theo ngành** (hết chiều ngang): 2 tab « Tổng 20 phiên » (bản đồ ngành §3, bấm dòng lọc danh sách) · « Theo ngày » (bản đồ nhiệt) | |
| 4. **Theo cổ phiếu**: trái ~60% lọc + danh sách mã (bấm dòng đổi thẻ) | Phải ~40%: **ô tra mã** (selectbox chỉ gồm VN100, mặc định là mã ở sidebar) + **thẻ mã 5 giây** (§4) + công tắc « Xem biểu đồ & chi tiết mã này » |
| 5. **Chi tiết mã** (hết chiều ngang, chỉ khi bật công tắc): 3 tab Biểu đồ · Bảng phiếu (+ trong nước suy ra) · Phiên thỏa thuận (+ huy hiệu) | |

- **Điện thoại:** cùng thứ tự Thị trường → Ngành → Cổ phiếu → Chi tiết; bản đồ ngành rút gọn (cột Ngành ghim, 3 cột), bảng đầy đủ và danh sách mã nằm trong `phone_collapsible`. (Sắp xếp lại 24/10/2026, người dùng duyệt.)

## 2. Các dòng tiền

| Dòng tiền | Nguồn | Có NGAY? | Cần ingest | Độ sâu lịch sử (số thật) |
|---|---|---|---|---|
| Khối ngoại tổng (khớp + thỏa thuận) | `prices_daily.foreign_*` (vnstock VCI foreign_flow) | Có | Không | 100/100 mã từ 20/05/2026 (~110 phiên); 81 mã từ 10/02; đến 22/10 (ngày 23/10: 0 mã) |
| Khối ngoại loại thỏa thuận (xấp xỉ: bỏ **cả** phiên có cờ) | Suy từ `prices_daily` | Có | Không | Như trên. Chỉ là cận dưới; có 487 mã-phiên/60 phiên ở vùng mập mờ |
| Khối ngoại **chỉ khớp lệnh**, chính xác | VCI `Trading.price_history(get_all=True)`: `fr_*_matched/_deal/_total` | Không | B1 | ≥ 01/2014 (đã thử FPT 01/2014). MCH 09/10: khớp +47,54 tỷ, thỏa thuận −9.641,19 tỷ |
| Tự doanh tổng | `prices_daily.proprietary_*` | Có (độ phủ thấp) | Không | Có từ 21/06/2019, nhưng độ phủ mã-phiên < 9% trước 01/2026; 28% tháng 01; 58% tháng 02; 65–72% từ 03/2026; 52–93 mã mỗi phiên. **NULL = thiếu** |
| Tự doanh tách khớp/thỏa thuận + giờ chốt | VCI `prop_trade`: `total_match_*`, `total_deal_*`, `update_date` (16:20–17:15) | Không | B1 | ≥ 01/2021 |
| **Thỏa thuận lớn** (cận dưới KL) | Suy: max(Fb+Pb, Fs+Ps) − KL khớp | Có | Không | Như khối ngoại. Giả định ngoại và tự doanh không trùng người |
| Thỏa thuận chính xác (KL/GT, bên nào làm, cả nội↔nội) | VCI `deal_volume/deal_value`, `fr_*_deal` | Không | B1 | ≥ 01/2014. **Không** dùng KBS put_through (trả rỗng); CafeF KLThoaThuan = 0 cho MCH 09/10: **chưa giải thích được, phải báo người dùng**, không dùng làm nguồn thỏa thuận |
| Trong nước suy ra (ròng) D = −(F+P) | Đẳng thức người mua = người bán | Có, chỉ ở màn chi tiết | Không | Chỉ tính trên phiên có cả F lẫn P |
| Giá-KL ẩn danh (CMF20; OBV chỉ minh họa) | `prices_daily` OHLC (điều chỉnh) + volume (KL khớp, khớp CafeF) | Có | Không | 120 phiên 06/05–23/10 đã kiểm: 0 NULL; có 36 phiên H=L |
| Mua/bán **chủ động** (proxy mất cân bằng lệnh) | ASEAN `Insight.trading_history` (route [Experimental], không bị vnai đếm quota) | Không | B2 | Cắt cứng 497 phiên (24/10/2024–22/10/2026). GT dùng được khoảng 2 năm; KL chỉ dùng được từ khoảng Q2/2026 |
| Room/sở hữu ngoại (cổng kín room) | VCI `fr_total_room`, `fr_current_room`, `fr_owned_percentage` | Không | B1 | ≥ 01/2014 (MCH 16,05% → 11,13%) |
| GTGD khớp danh nghĩa | VCI `matched_value` (cột `value` trong DB đang trống) | Không | B1 | ≥ 01/2014 |
| Lệnh lớn theo cỡ lệnh | KBS `Quote.intraday` (tick có chiều mua/bán) | Không | C (sau) | **Chỉ có phiên hiện tại**; lịch sử chỉ tích lũy từ ngày job bắt đầu chạy |
| Nội bộ / cổ đông lớn | VCI `insider_deal` | Không | C (sau) | Chưa gọi thử |
| Phiên cơ cấu ETF ngoại | `money_flow.etf_review_dates` do người dùng nhập | Có (danh sách rỗng) | Không | — |

## 3. Màn hình ngành

**Phần 5 giây: bản đồ ngành** (`st.dataframe` + pandas Styler, ghim cột Ngành).

| Cột | Định nghĩa |
|---|---|
| Ngành · n | Theo `market_overview.sector_map()` (22 ngành), không dùng `tickers.sector` (trộn nhãn Anh/Việt) |
| **Ngoại 20p** | ΣF_net (tỷ, kèm ▲/▼) và R_F = ΣF/ΣGTGD. **Màu** theo R_F, cắt ở ±`heat_clip` (5%); chữ trong ô vẫn ghi số thật |
| **Tự doanh 20p** | ΣP và R_P trên các phiên **có số**, kèm độ phủ (GTGD có số / GTGD ngành). Phủ < 75% thì để mờ (mẫu: Cảng 39%, KCN 47%, Dệt may 25%, Nước 0%) |
| Mã gom / xả | Đếm nhãn từng mã (§4), ví dụ "1 ▲ · 7 ▼ / 18" |
| Mã chi phối | Mã có \|F\| lớn nhất kèm tỷ trọng \|F_i\|/Σ\|F\| (vd Bán lẻ −14,3% trong khi 0 mã xả) |
| RS20 | median_ngành(ret20_i − median VN100), chỉ hiện chữ |
| Cờ | "đổi dấu Gồm/Loại" · "ít mã" (n < 3) · "dòng tiền thủng" |

- **Sắp xếp:** theo R_F ở chế độ đang chọn. Ngành có n < `small_sector_n` (3) xuống nhóm cuối và **không** vào câu kết luận. Nếu không tách, Du lịch +11,9% và Hóa chất +8,9% sẽ đứng đầu bảng.
- **Mẫu 22/10 (Loại):** Dầu khí +406 tỷ (+2,6%), Thép +93 (+1,0%). Ngân hàng: ngoại −3.504 (−5,1%) nhưng tự doanh +1.097 (+1,6%, phủ 99%). Công nghệ −1.049 (−13,8%), Bán lẻ −1.697 (−14,3%).
- **Không đưa vào bản đồ:** cột "Trong nước" (ảnh gương của −(F+P)), cột thỏa thuận có dấu, trạng thái ✅/❌ của v1. Một màn chỉ dùng một thước đo, nên không có hai dấu ngược nhau trên cùng dòng.
- **Bấm vào ngành:** dùng selectbox "Lọc ngành" (đường chính, test được) hoặc bấm dòng (`on_select`, kiểm tay). Kết quả là danh sách mã của ngành (§4) và bảng "Phiên ảnh hưởng lớn nhất": top N phiên-mã theo \|F\|+\|P\|, có cận dưới KL thỏa thuận, dạng giao dịch và tỷ trọng \|net\|/Σ\|net\|.
- **Hướng dẫn đọc (dấu (?) cạnh tiêu đề bảng; trước 24/10/2026 là expander « Đọc thế nào? »):**
  - Màu là ròng so với GTGD của chính ngành.
  - Một mã lớn có thể kéo cả ngành, nên xem thêm cột "Mã chi phối" và cột gom/xả.
  - Ngân hàng bán ròng có thể do kín room (chưa có dữ liệu FOL tới B1).
  - Khối ngoại thường mua theo đà (Richards 2005).
  - Sidebar tính chế độ Gồm và không cắt cửa sổ theo lịch phiên, nên có thể lệch dấu với tab ở chế độ Loại.

## 4. Màn hình từng mã

### 4.1 Thẻ 5 giây

Dòng 1 là nhãn kèm hậu tố bối cảnh; dòng 2 là 3 chip có số; dòng 3 là huy hiệu sự kiện; dòng 4 là 1 câu lý do sinh từ template. Màu luôn đi kèm ký hiệu ▲ ▼ 0 ◌.

| Mã (22/10, mẫu) | Thẻ |
|---|---|
| FPT | **Dấu hiệu xả · giá đang giảm (−12,1%)** · Ngoại ▼ −15,4% GTGD, 16/20 phiên bán · Giá-KL ▼ CMF20 −0,54 · Tự doanh ▲ +1,2% (phụ, có thể là phòng hộ CW/ETF) |
| DCM | **Dấu hiệu gom · giá đi ngang (+3,7%)** · Ngoại ▲ +15,7%, 16/20 phiên · Giá-KL ▲ +0,21 · Tự doanh ▼ (không chặn) |
| KDH | **Trung tính** · Giá-KL ▲ +0,18, Tự doanh ▲ +6,4%, nhưng phiếu Ngoại không phải +1 (ngoại bán ròng 2,0% GTGD). Cửa sổ có đợt thưởng 10%, nên tính lại ở A2 sau khi điều chỉnh GTGD |
| MCH | **Trung tính** · Ngoại 0 (−0,9%) · Giá-KL ▲ +0,46 · Tự doanh ▼ −12,4% · huy hiệu "Thỏa thuận lớn 09/10: KL ≥ 64,0 triệu cp, GT ước ~9.155 tỷ, ngoại bán" |
| KOS | **Chưa đủ dữ liệu** · 20/20 phiên H=L (sàn/trần trắng), ret20 −76% — sau D76: Trung tính, Giá-KL ▼ CMF20 −1,00 (sàn trắng bên 21 phiên), Ngoại 0 |
| PNJ | **Chưa đủ dữ liệu** · 4 phiên H=L · Ngoại ▼ −34,3% GTGD (vẫn hiện chip để không bị đọc thành trung tính) — sau D76: Dấu hiệu xả (CMF20 −0,61) |

### 4.2 Quy tắc nhãn (HEURISTIC của repo, chưa backtest)

**Thiết lập:**
- **Cửa sổ:** W = 20 phiên dòng tiền tính tới `flow_date`; giá cắt về `flow_date`.
- **Nhãn luôn tính ở chế độ Loại:** phiên-mã có cờ thỏa thuận bị bỏ khỏi cả tử số lẫn mẫu số.
- **Chế độ Gồm** chỉ hiện **tổng tuyệt đối (tỷ)**: không tỷ lệ, không tô màu, không bỏ phiếu. Lý do: khi Gồm, tử số có cả thỏa thuận còn mẫu số GTGD chỉ có khớp lệnh. Ví dụ MCH: −9.594 tỷ chia cho khoảng 115 tỷ GTGD thì vô nghĩa. Thay cho cờ "nhãn khác khi Gồm" là huy hiệu "cửa sổ có n phiên thỏa thuận, F ±x tỷ".
- **Phiên thủng** = phiên có giá nhưng F NULL. Phiên bị loại vì thỏa thuận **không** tính là thủng. Phải có ≥ `min_valid_sessions` (15) phiên hợp lệ. Tỷ lệ "phiên cùng dấu" lấy mẫu số là **số phiên hợp lệ**.
- **GTGD = close × volume, có điều chỉnh** (sửa lệch do giá điều chỉnh hồi tố, KL danh nghĩa):
  - Phiên trước GDKHQ của BONUS_SHARE/STOCK_DIVIDEND có `ex_right_date`: close × (1 + `exercise_ratio`).
  - Quyền mua, `ex_right_date` NULL, hoặc cờ gãy điều chỉnh trong cửa sổ: phiếu Ngoại và Tự doanh là ◌, kèm huy hiệu.
  - Cửa sổ hiện tại có 5 mã dính trường hợp này: TPB 15%, GMD 50%, KDH 10%, HDB 5% + 25%, NVL quyền mua.

| Phiếu | Vai trò | Đo | +1 | −1 | ◌ (không tính) |
|---|---|---|---|---|---|
| Ngoại | Chính | R_F = ΣF_net / ΣGTGD trên phiên hợp lệ | R_F ≥ `foreign_band` (0,02) **và** ≥ 60% phiên hợp lệ có F_net > 0 | Đối xứng | Không có số ngoại; số phiên thủng > `max_flow_gaps`; phiên hợp lệ < `min_valid_sessions`; hoặc dính sự kiện cổ phiếu chưa điều chỉnh được |
| Giá-KL | Xác nhận | CMF20 trên biên độ thực (D76: TRH = max(H, C_{t−1}), TRL = min(L, C_{t−1}), ý tưởng Twiggs Money Flow); phiên đứng giá bị loại khỏi cả tử lẫn mẫu (quy ước của repo) | CMF ≥ +0,05 | CMF ≤ −0,05 | Số phiên đứng giá > `cmf_max_flat` (2) |
| Tự doanh | Phụ (chỉ xác nhận) | R_P = ΣP / ΣGTGD trên **cùng tập phiên có số** | R_P ≥ 0,005 và ≥ 60% phiên có số cùng dấu | Đối xứng | Số phiên có số < 75% phiên hợp lệ; phiên hôm nay luôn bị loại vì chưa chốt |

**Nhãn**, xét theo thứ tự:

1. Ngoại hoặc Giá-KL là ◌ → **Chưa đủ dữ liệu**, kèm lý do.
2. **Phiếu Ngoại = +1** và có thêm ≥ 1 phiếu +1 (Giá-KL hoặc Tự doanh), không phiếu nào là −1 → **Dấu hiệu gom**.
3. **Phiếu Ngoại = −1** và có thêm ≥ 1 phiếu −1, không phiếu nào là +1 → **Dấu hiệu xả**.
4. **(D77) Phiếu Ngoại = 0**, Giá-KL ±1, KL khớp đột biến (RVOL = KL TB 20 phiên ÷ KL TB 60 phiên liền trước, đã điều
   chỉnh cổ phiếu thưởng/cổ tức CP, ≥ `rvol_min` 1,3) và Tự doanh không ngược chiều → **Nội gom △ / Nội xả ▽**. Là áp lực
   giá-KL khi khối ngoại đứng ngoài, không phải số mua ròng trong nước (= −(F + P)); đếm riêng ở bảng ngành và câu kết luận.
5. Còn lại → **Trung tính**, kèm lý do "lẫn lộn" (các phiếu ngược dấu) hoặc "chưa đủ mạnh".

*Vì sao bắt buộc phiếu Ngoại (đề xuất mặc định, xem Q3):* CMF và tự doanh đều hay đi theo đà giá (tự doanh phòng hộ CW thường mua khi giá tăng). Cho (0, +, +) ra Gom là đếm trùng một nguồn thông tin, trái nguyên tắc multicollinearity. Ở phiên 22/10, cả 4 mã gom đều có Ngoại = +1, nên phân bố Gom không đổi; số Xả sẽ tính lại ở A2.

**Hệ quả:**
- (0, +, +) → Trung tính (không đếm trùng), trừ khi KL đột biến → Nội gom (D77, người dùng chọn 24/10/2026).
- Tự doanh không chặn được nhãn: (−, −, P+) vẫn là Xả (FPT); (+, +, P−) vẫn là Gom (DCM).
- Tự doanh một mình không tạo được nhãn: (0, 0, +) là Trung tính.
- Không có điểm tổng hợp, không có xác suất.
- D = −(F+P) không phải phiếu vì phụ thuộc tuyến tính vào F và P.
- Thỏa thuận, kín room, ETF, GDKHQ chỉ là huy hiệu, không bỏ phiếu.

**Hậu tố bối cảnh** (không đổi nhãn, **chỉ mô tả giá**): \|ret20\| ≤ 5% là "giá đi ngang"; > 5% là "giá đã tăng x%"; < −5% là "giá đã giảm x%". Cách này tránh câu vô lý kiểu "Dấu hiệu xả · mua theo đà".

**Ngoài ra:**
- **Giữ nhãn từ dd/mm:** tính lại nhãn ở 10 `flow_date` gần nhất.
- **Huy hiệu thỏa thuận trong cửa sổ:** "n phiên thỏa thuận, F ±x tỷ" (thay cờ "nhãn khác khi Gồm").

**Chạy thử 22/10 (band 2%):**
- Nhãn: 4 Gom (DCM giá đi ngang; FRT, NT2, VPL giá đã tăng) · 23 Xả · 71 Trung tính (17 lẫn lộn; 5 mã có ≥ 2 phiếu cùng chiều nhưng bị chặn) · 2 Chưa đủ (KOS, PNJ).
- Phiếu: Ngoại +10 / 0: 51 / −39. Tự doanh ◌ ở 45 mã.
- Độ nhạy: band 1% ra 5 Gom (thêm VCG) và 24 Xả; band 3% ra 4 Gom và 22 Xả.

### 4.3 Danh sách và phần chi tiết

- **Danh sách 100 mã:** lọc theo Ngành và Nhãn. Cột gồm Mã · Ngành · Nhãn · 3 chip · Bối cảnh · Ngoại 20p · TD 20p · CMF20 · ret20 · Giữ nhãn từ · Cờ. Bấm một dòng thì ghi `session_state['flow_ticker']` qua callback, thẻ ở trên đổi theo; không dùng dialog.
- **"Xem chi tiết"** đặt sau `st.toggle`, nên chỉ tính khi bật:
  - (a) Bảng phiếu: giá trị đo, ngưỡng config, số phiên cùng dấu, độ phủ.
  - (b) Plotly 2 hàng: giá, cột F/P theo ngày (phiên thỏa thuận tô viền), đường lũy kế F và P.
  - (c) CMF20 và OBV, ghi rõ OBV chỉ để minh họa, chỉ xem độ dốc.
  - (d) Các phiên thỏa thuận trong 60 phiên: ngày, KL mua/bán của ngoại và tự doanh, cận dưới KL, **GT ước ~**, dạng giao dịch (ngoại↔ngoại khi min/max(Fb, Fs) ≥ 0,8).
  - (e) D = −(F+P) ở chế độ Loại, chỉ trên phiên có cả F lẫn P, kèm 3 điều kiện để đúng.
  - (f) GDKHQ (`ex_right_date` NULL thì ghi "ngày chưa rõ"), H=L, gãy điều chỉnh, phiên ETF.

## 5. Lộ trình học trong app

**Nơi hiển thị:**
- Tooltip `help` ở từng tiêu đề cột.
- Dấu (?) cạnh tiêu đề mỗi khối (rê chuột hiện hướng dẫn, đưa ra thì ẩn); tiêu đề từng tầng biểu đồ cũng có (?).
- Expander "Học từ cơ bản (10 bài)" ở cuối tab. Mỗi bài 3–5 dòng tĩnh và 1 dòng "Ví dụ từ dữ liệu" sinh bằng template; DB thiếu dữ liệu thì dùng câu dự phòng. Không gọi mạng hay AI.

| Bài | Nội dung ngắn | Ví dụ |
|---|---|---|
| L1 Thanh khoản | GTGD, ADTV20, biên độ ±7% HOSE, T+2, lô 100 (bản trích quy chế HOSE của MBS) | GTGD 20 phiên của mã đang xem |
| L2 Khớp lệnh và thỏa thuận | Thỏa thuận ≥ 20.000 cp, không tạo giá đóng cửa. Vì sao có công tắc Loại/Gồm | MCH 09/10: ngoại bán 64,3 triệu cp, khớp chỉ 0,8 triệu; sở hữu ngoại 16,05% → 11,16%. Báo Mekong ASEAN xác nhận là thỏa thuận (dẫn URL trong bài tĩnh). CafeF bảng khối ngoại chỉ tính khớp lệnh, nên ngày đó ghi +47,5 tỷ |
| L3 Các nhóm nhà đầu tư | Cá nhân ~82%, ngoại ~10–12% thanh khoản HOSE (số tham khảo, có ngày); room/FOL; tự doanh phòng hộ CW (TT 107/2016) hoặc lập quỹ ETF (TT 229/2012) | HDB 02/10: tự doanh mua 56,8 triệu cp |
| L4 "Mua ròng" là gì | Ngoại + tự doanh + trong nước = 0, nên app không dùng chữ "tiền vào" | Trên các phiên có **cả** số ngoại lẫn tự doanh (ghi độ phủ): ngoại + tự doanh + trong nước suy ra = 0 |
| L5 Mua ròng ≠ giá sẽ tăng | Khối ngoại mua theo đà (Richards 2005; Froot, O'Connell & Seasholes 2001); bằng chứng ở VN yếu, có hành vi bầy đàn | Spearman giữa ngoại 20 phiên và ret20 ≈ 0,27 |
| L6 Dòng tiền ẩn danh qua giá-KL | OBV, A/D, CMF; vì sao chỉ giữ 1 phiếu (multicollinearity) | CMF20 của mã đang xem; KOS sàn trắng bên: trước D76 CMF không xác định, sau D76 = −1,00 |
| L7 Gom hàng theo Wyckoff | Đi ngang sau xu hướng giảm + Effort vs Result; các pha chỉ thấy khi nhìn lại nên app không tự gán pha | Lý do hậu tố chỉ mô tả giá ("đi ngang", "đã tăng x%") |
| L8 Ngành và luân chuyển | Cách đọc bản đồ, mã chi phối, ngành ít mã, RS20. RRG chỉ là khung tham khảo, không phải hệ thống giao dịch | Ngành dẫn và ngành bị bán nhất tại `flow_date` |
| L9 Kết hợp định giá | FV chưa golden; upside chỉ là cột phụ; value và momentum tương quan âm (Asness et al. 2013), nên "rẻ + bị bán" là vùng chờ xác nhận | Upside của mã kèm nguồn đợt xếp hạng |
| L10 Quản trị rủi ro | Số cp = vốn × % rủi ro / (giá vào − giá stop), làm tròn lô 100 (quy ước của app; HOSE có khớp lô lẻ); stop theo cấu trúc giá hoặc ATR (StockCharts). Có máy tính dùng số người dùng tự nhập | 50.000.000 × 2% / 5.000 = 200 cp |

**Không hứa:** không có chữ "Mua/Bán" làm nhãn, không có "điểm vào", "hiệu quả nhất", tỷ lệ thắng, xác suất hay dự báo. Không tự gán pha Wyckoff. Không gợi ý giá vào hay giá stop.

## 6. Chỉ báo

| Tên | Công thức | Loại |
|---|---|---|
| Cờ thỏa thuận | max(Fb_vol + Pb_vol, Fs_vol + Ps_vol) > volume (P NULL = 0 chỉ ở đây); cận dưới KL = phần vượt; GT **ước** = cận dưới × VWAP danh nghĩa của phía áp đảo (vd MCH: foreign_sell_val/foreign_sell_vol = 149.997 → ~9.600 tỷ; thực tế 9.641). Không có VWAP thì dùng close | Suy luận, cận dưới; giả định ngoại và tự doanh không trùng người |
| Thỏa thuận lớn (huy hiệu) | GT ước ≥ `big_block_adtv_share` (0,5) × GTGD bình quân 20 phiên. B1: deal_volume / KL thỏa thuận bình quân 20 phiên | HEURISTIC, theo cách xếp hạng của VND (ptVolTotalVolAvg20D) |
| F_N, P_N | Σnet qua N phiên dòng tiền tới `flow_date` (chế độ Loại bỏ phiên có cờ); P chỉ cộng phiên có số | Dữ liệu gốc |
| R_F, R_P | Σnet / ΣGTGD trên **cùng tập** (mã, phiên) | HEURISTIC (D56); chuẩn học thuật chia cho vốn hóa (Richards 2005), để §10 |
| Độ phủ tự doanh | GTGD (hoặc số phiên) có P không NULL / tổng | Chất lượng dữ liệu |
| D trong nước suy ra | −(F+P) trên phiên có cả F lẫn P | Đẳng thức người mua = người bán (Fisher; Chordia, Roll & Subrahmanyam 2002) |
| CMF20 | MFM = ((C−L) − (H−C))/(H−L); CMF = Σ(MFM·V)/ΣV; H=L bị loại | **CHUẨN** StockCharts (±0,05 là ngưỡng ví dụ của nguồn). Việc loại phiên H=L là **quy ước repo**, không phải chuẩn |
| OBV (chỉ ở chi tiết) | OBV_t = OBV_{t−1} + sign(ΔC)·V | **CHUẨN** StockCharts; không làm phiếu |
| ret20, RS20 | C_t/C_{t−20} − 1; median_ngành(ret20 − median VN100) | **CHUẨN** ROC / price relative |
| Phiếu, nhãn, hậu tố, phủ quyết | §4.2 | HEURISTIC (đếm phiếu theo nhóm thông tin độc lập, ChartSchool multicollinearity; Wyckoff) |
| Dạng ngoại↔ngoại | Phiên có cờ và min/max(Fb_vol, Fs_vol) ≥ 0,8 | HEURISTIC |
| Cờ gãy điều chỉnh | \|VWAP_ngoại/close − 1\| > 0,08 trong ≥ 3 phiên liên tiếp | HEURISTIC (v1) |
| Khối lượng vị thế | floor(vốn × % rủi ro / (giá vào − stop) / 100) × 100 | **CHUẨN** StockCharts position sizing |
| B2: Chủ động ròng A20 | Σ(active_buy_val − active_sell_val) / Σmatched_value, chỉ dùng dòng qua cổng chất lượng | Proxy (Chordia 2002); sai số phân loại kiểu Lee-Ready khoảng 20–25% |

## 7. Kiến trúc, ingest và cache

**Giai đoạn A (không đổi schema, không gọi mạng):**

| File | Việc |
|---|---|
| `valuation/analysis/money_flow.py` (mới) | Hàm thuần: `clean_flows`, `block_flags`, `cmf`, `votes`, `label`, `label_history`, `context`, `badges`, `sector_table`, `implied_domestic`, `top_impact`, `conclusion`, `position_size`. Không import streamlit hay vnstock |
| `valuation/views/money_flow.py` (mới) | `load_flow_panel(db)`: 1 SELECT `prices_daily` JOIN `tickers.is_vn100` (OHLCV + 12 cột F/P) trong `history_days`, cộng `corporate_actions.ex_right_date` và `ranking_store.latest_snapshot`. Hàm **nhận `db` từ app**, giống `market_overview.load_market_data(db, cfg)`; không dùng `SessionLocalRead`, vì module đó chạy `create_all` khi import và đọc URL khác engine của app. `compute_money_flow(key)` bọc `@st.cache_data`, trả kết quả **cả 2 chế độ**. `render_money_flow(ticker: str \| None)` |
| `valuation/views/money_flow_lessons.py` (mới) | L1–L10 và các khung "Đọc thế nào?" (văn bản tĩnh + template) |
| `streamlit_app.py` | Thêm tab "Dòng tiền ngành" ở cuối cả 2 nhánh (nhánh chưa chọn mã: 1 → 2 tab), truyền `company.ticker` |
| `valuation/views/assets/workspace.css` | Thêm `:nth-of-type(6)` vào quy tắc ẩn (~dòng 161); nhãn đáy điện thoại **"money"** cho tab 6 và nhánh 2 tab (~dòng 296–310) |
| `config/defaults.yaml` | Khối `money_flow` (dưới đây) |
| `tests/test_money_flow.py`, `tests/test_money_flow_tab.py`, `tests/golden/money_flow_cafef.json` (mới) | §8 |
| `docs/PLAN_SECTOR_FLOW.md` (thay bằng v2), `DECISIONS.md` (D73), `docs/AGENT_OPERATING_MANUAL.md`, `.agents/rules/project-context.md` | Phương pháp, danh sách tab |
| **Không sửa** | `market_overview.py` (chỉ import `sector_map`, `_vi`, `_chg`), `pipeline.py`, `market_client.py`, `prices_daily`, `daily_report.py`, `assistant.py` |

- **Cache:** khóa = (ngày giá cuối, `flow_date`, số dòng, `run_id` snapshot, hash config `money_flow` + `market_overview`). Render chỉ chọn chế độ và định dạng. Mục tiêu: < 1 giây khi cache lạnh, < 0,3 giây khi ấm (đo ở A3).
- **Cấm import trong module money_flow:** `vnstock`, `vnstock_data`, `vnii`, `vnai`, `valuation.ingest`. Các gói này gọi mạng và in tên tài khoản kèm tier. Kiểm bằng test tĩnh và AppTest chỉ render `render_money_flow`, so **phần chênh** của `sys.modules`.
- **Lỗ rò có sẵn, việc riêng:** nhánh có chọn mã đã import vnstock khi render (`streamlit_app.py:420` → `views/corporate_actions.py:29` → `ingest/corporate_actions.py:17`).

```yaml
money_flow:                       # HEURISTIC trừ dòng ghi CHUẨN — chờ duyệt D73
  window: 20
  windows_show: [5, 20, 60]
  exclude_block_default: true
  session_close: "15:00"
  prop_settle_time: "17:30"       # tự doanh chốt ~16:20–17:15
  max_flow_gaps: 0
  net_identity_rel_tol: 0.001
  ca_break_tol: 0.08
  ca_break_min_sessions: 3
  small_sector_n: 3               # ≠ market_overview.sector_min_members (2): ngành 2 mã không vào câu kết luận (D73)
  heat_clip: 0.05
  prop_sector_min_value_cov: 0.75 # độ phủ tự doanh của NGÀNH, tính theo GTGD
  big_block_adtv_share: 0.5
  cross_foreign_ratio: 0.8
  top_impact_n: 10
  golden_flow_tol: 0.02
  lot_size: 100                   # quy chế HOSE
  hose_put_through_min_shares: 20000   # chỉ dùng trong bài học
  etf_review_dates: []
  forbidden_phrases: ["khuyến nghị mua", "nên mua", "nên bán", "điểm vào", "điểm mua", "hiệu quả nhất", "tiền vào", "tiền ra"]
  signal:
    foreign_band: 0.02
    same_sign_share: 0.6
    prop_band: 0.005
    prop_min_session_cov: 0.75    # độ phủ tự doanh của MÃ, tính theo số phiên
    min_valid_sessions: 15
    cmf_window: 20
    cmf_band: 0.05                # CHUẨN: ngưỡng ví dụ StockCharts
    cmf_max_flat: 2
    sideways_band: 0.05
    label_history: 10
# Dùng lại: market_overview.{history_days, min_coverage, sector_min_members}
```

**Giai đoạn B (DỪNG XIN DUYỆT trước: đổi schema, gọi mạng, tốn quota):**

| Thành phần | Thiết kế |
|---|---|
| Bảng `flow_daily` | PK (ticker, trade_date, source). Cột: `fetched_at`, `is_final`, `batch_id`, `matched_vol/val`, `deal_vol/val`, `fr_{buy,sell,net}_{match,deal}_{vol,val}`, `fr_total_room`, `fr_current_room`, `fr_owned_pct`, `prop_{buy,sell,net}_{match,deal}_{vol,val}`, `active_buy/sell_{val,vol}`, `quality_flags`. **Không** đụng `prices_daily` |
| Chặn tự tạo bảng | Model đặt trong `valuation/db/flow_models.py` với metadata riêng, nên `init_db()` (session.py:53–55) và `streamlit_app.py:105` (cũng chạy `create_all`) không tạo. Chỉ `scripts/migrate_flow_daily.py` tạo, sau khi backup DB. UI kiểm bảng có tồn tại bằng `sqlalchemy.inspect`, không bọc try/except. Đưa bảng vào `vn100_full.db.gz` / `ensure_portable_db` và bước migration trên VPS |
| Client | `valuation/ingest/flow_client.py` gọi thẳng explorer: VCI `price_history(resolution='1D', get_all=True)`, VCI `prop_trade`, (B2) ASEAN `trading_history`. Không qua tầng UI chuẩn hóa strict, vì tầng đó làm mất cột khớp/thỏa thuận và bỏ kwarg lạ |
| Kiểm khi nạp | Đủ cột bắt buộc, thiếu thì raise. Đẳng thức total = matched + deal. ASEAN `total_value` (triệu VND) × 1e6. Cổng chất lượng: (mua CĐ + bán CĐ)/GT khớp ≤ 1 + tol; KL CĐ = 0 thì chỉ dùng GT; NaN để thủng, không thay bằng 0 |
| Ghi idempotent | Chưa có thì INSERT. Có dòng chưa final thì UPDATE. **Dòng `is_final` không bị ghi đè**: số lệch ghi log để người dùng duyệt. Rollback theo `batch_id` |
| Job | `scripts/update_flow_daily.py`, chạy như tiến trình riêng (launchd/systemd timer như D72) sau 17:30 giờ VN. Whitelist VN100 + regex mã, allowlist nguồn trong config. Throttle theo quota vnai (mặc định 20/phút, 1.200/giờ, 28.800/ngày). Chạy tiếp được: bỏ qua (mã, ngày) đã final. `is_final` = `fetched_at` (giờ VN) ≥ `trade_date` + `prop_settle_time`; dòng backfill coi là final. Domain nguồn (VCI, ASEAN) thêm vào allowlist trong config. Nuốt stdout lúc import để log không có tên tài khoản. Ghim `vnstock_data==3.2.8` (bản đang cài; đã có 3.3.1) |
| Quota | Hằng ngày khoảng 200 lần gọi VCI (~10 phút ở 20/phút) + 100 POST ASEAN (không bị đếm). Backfill: VCI `price_history` 2 năm ~100 lần (730 dòng ≤ 1.000, 1 trang); `prop_trade` ~100 lần (chưa thử gọi 2 năm một lần); ASEAN 100 lần (497 phiên) |
| UI khi có `flow_daily` | Phiếu Ngoại dùng `fr_net_match` (không còn phải loại cả phiên); huy hiệu thỏa thuận chính xác kèm bên tham gia; mã kín room thì phiếu Ngoại là "không áp dụng"; GTGD lấy `matched_value`. B2: A20 thay CMF làm phiếu Giá-KL khi qua cổng chất lượng và golden, **không bao giờ đếm cả hai**. Không có dòng thì quay về đường A, có ghi nguồn |

## 8. Lộ trình triển khai

| Giai đoạn | Việc | Test tính tay | Xong khi |
|---|---|---|---|
| **P0** | Người dùng trả lời §11; ghi D73; thay `docs/PLAN_SECTOR_FLOW.md` | — | Có quyết định |
| **A1** Loader và làm sạch (0,5 ngày) | Config, `load_flow_panel`, `clean_flows`, lịch phiên, `flow_date`, chặn phiên dở, phiên thủng, `block_flags`, cờ H=L, GDKHQ, gãy điều chỉnh | T1–T3 | Pass. Sample DB: 51 phiên-mã có cờ / 20 phiên; MCH 09/10 cận dưới ≈ 64,0 triệu cp; dòng 28/06 bị loại |
| **A2** Phiếu, nhãn, ngành (0,5–1 ngày) | `votes`, `label`, `label_history`, `context`, `badges`, `sector_table`, `implied_domestic`, `top_impact`, `conclusion`, `position_size` | T4–T15, T18 | Pass. In bảng 22 ngành ở 2 chế độ và phân bố nhãn để người dùng xem (khớp prototype: Loại F −8.520, P +1.050; 4/23/71/2) |
| **A3** UI (1 ngày) | Dải trạng thái, câu kết luận, bản đồ ngành, ô tra mã + thẻ, danh sách, chi tiết sau toggle, bài học, CSS tab 6 | T16 | Pass. Kiểm tay desktop và 375px, sáng và tối, bấm dòng bảng; đo thời gian |
| **A4** Golden và hoàn thiện (0,5 ngày) | T17 qua phiên Chrome của người dùng (chỉ đọc); ruff/black/mypy; pytest toàn bộ; quét secret; docs | T17 | **Chưa pass T17 thì không tuyên bố xong** (luật #8) |
| **B1** (duyệt riêng) Ingest VCI (1–1,5 ngày) | `flow_models`, migration + backup, `flow_client` VCI, job, backfill 2 năm, UI ưu tiên `flow_daily` | TB1–TB4, TB6, TB7 | Chạy lại 2 lần không nhân đôi; golden MCH/FPT pass; log sạch |
| **B2** (duyệt riêng) Ingest ASEAN (1 ngày) | Chuẩn hóa đơn vị, cổng chất lượng, backfill 497 phiên rồi chụp hằng ngày, phiếu A20 | TB5, TB8 | Golden chủ động pass; nguồn đổi schema thì fail rõ ràng |
| **C** (sau) | Job tick lệnh lớn, `insider_deal`, Discord | — | Mỗi việc duyệt riêng |

| # | Test (fixture dựng tay; số DB thật chỉ in làm sample) |
|---|---|
| T1 | Dòng CN bị loại; net ≠ mua − bán vượt tol thì NaN; mua = bán = 0 thì net = 0 (không phải NaN) |
| T2 | Fb 600k + Pb 500k = 1,1 triệu > V 1,0 triệu → cờ True, cận dưới 100k (quy tắc chỉ dùng khối ngoại ra False). MCH dựng tay: Fs 64.300.671, V 804.200 → True. Pb NULL tính là 0 **chỉ** trong cờ |
| T3 | Phiên cuối thiếu F thì `flow_date` lùi 1 phiên; phiên hôm nay trước 15:00 bị bỏ; có 1 phiên thủng thì báo và phiếu Ngoại ◌; P của phiên hôm nay gắn "tạm" và không vào phiếu |
| T4 | GTGD 100 tỷ × 20 phiên. (a) 14 phiên +6, 6 phiên −1 → R = 78/2.000 = 3,9%, 14 ≥ 12 → +1. (b) 13 phiên +2, 7 phiên −1 → 0,95% → 0. (c) R = 4% nhưng 11 phiên dương → 0. (d) đối xứng → −1 |
| T5 | Từ (a), thay phiên cũ nhất bằng 1 phiên có cờ, F = −9.000 tỷ (vẫn 20 phiên). **Loại:** 19 phiên hợp lệ, R = 72/1.900 ≈ 3,8%, 13/19 phiên dương ≥ 60% → +1. **Gồm:** chỉ hiện tổng −8.922 tỷ, không có phiếu hay màu; có huy hiệu "1 phiên thỏa thuận". Có 21 phiên thì W = 20 không kéo phiên thứ 21 vào |
| T6 | P +1 tỷ ở 15 phiên có số, 5 phiên NULL, GTGD 100 tỷ/phiên → R_P = 15/1.500 = 1% (**không phải** 15/2.000). Phủ 14/20 → ◌ |
| T7 | (10, 8, 10, V100) → MFM +1; (10, 8, 8, V100) → −1; (10, 8, 9,5, V200) → +0,5. CMF = (100 − 100 + 100)/400 = 0,25. Thêm 1 phiên H=L → CMF không đổi, flat = 1. 3 phiên H=L → ◌ và huy hiệu |
| T8 | (F, A, P): (+,+,◌) Gom; (+,0,+) Gom; (0,+,+) với R_F +0,5% → Gom; (0,+,+) với R_F −0,5% → Trung tính (phủ quyết); (0,0,+) Trung tính; (+,−,+) lẫn lộn; (−,−,+) Xả; (+,+,−) Gom; (◌,+,+) Chưa đủ; A ◌ → Chưa đủ; đúng bằng band → đạt |
| T9 | ret20 +6% → "giá đã tăng 6%"; +2% → "giá đi ngang"; đúng ±5% → "giá đi ngang"; −8% → "giá đã giảm 8%". Hậu tố không đổi nhãn và không bao giờ chứa "mua" |
| T10 | Ngành 2 mã × 3 phiên: F, R_F, P, độ phủ, đếm nhãn, mã chi phối. n < 3 xuống cuối và không vào câu kết luận. R = −201% → màu cắt ở −5%, chữ vẫn là số thật |
| T11 | Cận dưới 50k cp × VWAP danh nghĩa 10.000 = 0,5 tỷ (có VWAP thì không dùng close điều chỉnh), ADTV 1 tỷ → có huy hiệu; chuỗi chứa "ước ~", không chứa "≥ … tỷ". Fb = Fs = 7,95 triệu → ngoại↔ngoại; Fb 1 triệu / Fs 23 triệu → không |
| T12 | F −100, P +30 → D +70; P NULL → D NaN |
| T13 | Câu kết luận và lý do: định dạng số kiểu VN, không có "nan"/"None", không có cụm từ trong `forbidden_phrases` ("mua ròng" được phép). Chỉ quét template sinh động, **không** quét bài học tĩnh (L4 cố ý nhắc "tiền vào"). Không ngành nào thỏa điều kiện thì có câu trạng thái rỗng |
| T14 | Chuỗi nhãn dựng tay đổi ở phiên 7 → "giữ nhãn từ" đúng ngày đó |
| T15 | 50.000.000 × 2% / 5.000 = 200 cp; 100.000.000 × 1% / 3.000 = 333,3 → 300; stop ≥ giá vào → báo lỗi |
| T16 | AppTest, SQLite tạm, chặn socket, **chỉ render `render_money_flow`**: tab cuối "Dòng tiền ngành" (nhánh chưa chọn mã có 2 tab); có dải trạng thái, câu kết luận, miễn trừ, bản đồ; selectbox chọn FPT ra thẻ; mã ngoài VN100 bị từ chối; phần chênh của `sys.modules` không có vnstock, vnstock_data, vnii, vnai. Thêm test tĩnh: module money_flow không import `valuation.ingest`. Selectbox đồng bộ với mã ở sidebar qua callback |
| T17 | **Golden:** khối ngoại FPT ở các phiên `put_through` = 0 (05/10, 19/10, 20/10, 22/10; 22/10: DB −264,19 = ASEAN) so với CafeF GDKhoiNgoai (= khớp lệnh), lệch < `golden_flow_tol`; tự doanh FPT khớp tuyệt đối. Fixture ghi URL, ngày truy cập và "CafeF = khớp lệnh". **Không** dùng các phiên FPT 09/10, 12/10, 15/10 vì có thỏa thuận (1.314.285 / 935.000 / 127.240 cp) |
| T18 | Chế độ Gồm, fixture ≥ 50 phiên giá (`leaders()` bỏ mã quá ngắn), không có phiên thủng: dấu F20 ngành = dấu `leaders().sec.flow` |
| T19 | GTGD điều chỉnh: thưởng 50% có `ex_right_date` ở phiên 10, close 52.000 → phiên 1–9 tính 78.000 × KL. Quyền mua, hoặc `ex_right_date` NULL trong cửa sổ → phiếu Ngoại và Tự doanh ◌ kèm huy hiệu |
| T20 | Phiên F NULL = thủng; phiên bị loại vì thỏa thuận ≠ thủng; 14 phiên hợp lệ < 15 → phiếu Ngoại ◌ |
| T21 | Chế độ Gồm: không trả tỷ lệ, màu hay phiếu; nhãn giống hệt chế độ Loại |
| TB1 | Fixture VCI MCH 09/10: deal_volume 64.274.571; fr_net deal −9.641,19 tỷ; matched +47,54; total −9.593,65 (= DB); total = matched + deal, sai số 0 |
| TB2 | Upsert 2 lần không nhân đôi; dòng `is_final` không bị ghi đè; số lệch được ghi log |
| TB3 | `init_db()` không tạo `flow_daily`; script migration tạo bảng sau khi backup |
| TB4 | Thiếu cột bắt buộc → raise |
| TB5 | ASEAN `total_value` 139.741,01 triệu → VND; tỷ lệ chủ động 1,24 → cổng loại; NaN giữ NaN; KL CĐ = 0 → chỉ dùng GT |
| TB6 | Golden MCH 09/10: VCI + sở hữu ngoại 16,05% → 11,13% + báo chí. FPT 1–2 ngày so với CafeF |
| TB7 | Log không chứa key, tên chủ tài khoản, tier |
| TB8 | Golden chủ động: 2–3 cặp mã-ngày so với một nguồn ngoài thứ hai (web/app CTCK qua phiên trình duyệt của người dùng) |

## 9. Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Nhãn là HEURISTIC, chưa backtest: khối ngoại đủ 100 mã chỉ ~110 phiên; 1 snapshot thành phần VN100 (survivorship); nghiên cứu ở VN không cho thấy dòng tiền ngoại dự báo được giá | Miễn trừ cố định, không điểm tổng hợp, không tỷ lệ thắng; backtest để §10 |
| 71/100 mã ra Trung tính, người dùng có thể nghĩ app hỏng | Ghi lý do ("lẫn lộn" / "chưa đủ mạnh"); bài L5 giải thích; đó là kết quả thật (CMF tương quan với F+P chỉ 0,17) |
| CMF tương quan 0,56 với ret20, nên có thể chỉ lặp lại đà giá | Bắt buộc phiếu Ngoại cho Gom/Xả; CMF chỉ xác nhận; hậu tố ghi mức tăng giá |
| Quy tắc tổng F+P và D sai nếu CTCK có vốn ngoại > 50% bị tính vào cả 2 nhóm | Ghi nhãn "suy ra"; D chỉ ở màn chi tiết; golden theo nhóm nhà đầu tư để §10 |
| Cờ thỏa thuận chỉ là cận dưới (487 mã-phiên mập mờ / 60 phiên); chế độ Loại bỏ cả phần khớp của phiên | B1 sửa triệt để |
| Tự doanh: 45/100 mã ◌; động cơ có thể là phòng hộ CW/ETF | Phiếu phụ, chỉ xác nhận; hiện độ phủ |
| Giai đoạn A không biết thời điểm lấy tự doanh (`prices_daily` không có `updated_at`), nên Quét lúc 16:00 rồi xem hôm sau vẫn là số dở | Chỉ chặn được phiên hôm nay; B1 có `fetched_at`/`is_final` |
| Kín room chưa có dữ liệu, nên ngân hàng dễ bị đọc là xả | Ghi rõ trong "Đọc thế nào?"; B1 có cổng kín room |
| Giá điều chỉnh hồi tố + KL danh nghĩa: 28 mã có sự kiện / 60 phiên; 20 bản ghi `ex_right_date` NULL | Huy hiệu GDKHQ và "ngày chưa rõ"; B1 có `matched_value` |
| Nhãn nhấp nháy quanh ngưỡng | "Giữ nhãn từ"; hysteresis để §10 |
| Dòng tiền chỉ cập nhật khi bấm Quét (23/10: 0 mã) | Tách ngày giá khỏi ngày dòng tiền; đếm phiên thủng; B1 có job tự chạy |
| Số khối ngoại **không** mâu thuẫn: CafeF GDKhoiNgoai chỉ tính khớp lệnh. Còn một điểm chưa giải thích: CafeF KLThoaThuan = 0 cho MCH 09/10, trong khi DB/VCI/ASEAN/báo chí đều có thỏa thuận ~64 triệu cp | Báo người dùng (AGENTS §8); golden chỉ dùng phiên không có thỏa thuận; không dùng CafeF làm nguồn thỏa thuận |
| Import vnstock_data/vnii gọi mạng và lộ tên tài khoản | T16 chặn; job nuốt stdout lúc import |
| ASEAN [Experimental], đơn vị lẫn lộn, chất lượng mới kiểm 2 mã (MCH, FPT) | Tách duyệt B2; cổng chất lượng; golden TB8; fail rõ ràng |
| vnstock_data bị obfuscate, API có thể đổi | Ghim version; test schema |
| Bị đọc thành khuyến nghị | `forbidden_phrases` + T13 |
| CSS gắn theo vị trí tab | Kiểm 320–375px ở A3 |

## 10. Gợi ý phát triển thêm

| # | Ý tưởng | Điều kiện |
|---|---|---|
| 1 | Job tự kéo dòng tiền (hết phiên thủng); B1 làm luôn việc này | Duyệt ingest |
| 2 | Báo cáo sáng Discord: dải đếm + 3 ngành mỗi phía + mã đổi nhãn; cảnh báo đổi nhãn cho danh mục theo dõi | Duyệt tích hợp |
| 3 | Bản đồ luân chuyển xấp xỉ: X = RS20, Y = ΔRS20 qua 5 phiên, ghi "không phải JdK RRG" | — |
| 4 | Lệnh lớn từ tick KBS sau giờ đóng cửa (300–500+ lần gọi/ngày, chỉ tích lũy từ ngày chạy), nhãn proxy, chỉ ở màn chi tiết | Duyệt riêng |
| 5 | Huy hiệu nội bộ / cổ đông lớn (`insider_deal`) | Duyệt riêng |
| 6 | Chuẩn hóa theo vốn hóa (bps, Richards 2005) | — |
| 7 | Golden theo nhóm nhà đầu tư (HOSE / CafeF TradingReport) để kiểm D và kiểm trùng ngoại với tự doanh | — |
| 8 | Hysteresis / "giữ nhãn N phiên" | Thêm ngưỡng vào config |
| 9 | Backtest nhãn khi có ≥ 2 năm `flow_daily` và lịch sử thành phần VN100 | Đủ dữ liệu |
| 10 | Ma trận Dòng tiền × Upside khi snapshot FV được đồng bộ và có golden | — |
| 11 | Heatmap room và premium thỏa thuận cho ngân hàng | Sau B1 |
| 12 | Công cụ `@bot money_flow(mã)` trả đúng thẻ 5 giây | Duyệt |

## 11. Câu hỏi cần người dùng quyết

| # | Câu hỏi | Đề xuất mặc định |
|---|---|---|
| **1** | **Làm B1 (kéo dữ liệu thỏa thuận và khối ngoại khớp lệnh chính xác từ VCI vào bảng mới `flow_daily`) TRƯỚC giai đoạn A2?** Bạn hỏi thẳng về "dòng tiền lớn qua thỏa thuận". Không có B1 thì app không thấy thỏa thuận giữa hai bên trong nước (MCH 14/10: 1,395 triệu cp), và khoảng nửa số quy tắc ước lượng của A chỉ tồn tại để bù chỗ thiếu này. B1 cần khoảng 100 lần gọi API, **đổi schema** (bảng mới, có backup), và chạy job mỗi ngày | **Có**: A1 → B1 → A2 → A3 → A4. B2 (mua/bán chủ động, nguồn ASEAN [Experimental]) duyệt riêng sau |
| 2 | Đổi tên nhãn thành **"Dấu hiệu gom / Dấu hiệu xả"** (thay "Đang gom/xả", để không nói quá dữ liệu)? | Có |
| 3 | Bắt buộc **phiếu khối ngoại** mới được gắn Gom/Xả (CMF và tự doanh chỉ xác nhận)? | Có |
| 4 | Ngưỡng từng mã: ngoại ±2% GTGD và ≥ 60% phiên cùng dấu; tự doanh ±0,5% và phủ ≥ 75%; CMF ±0,05; ≥ 15 phiên hợp lệ; ≤ 2 phiên H=L; đi ngang ±5% | Có. Độ nhạy: band 1% → 5 gom/24 xả; 2% → 4/23; 3% → 4/22 |
| 5 | Tự doanh NULL = **thiếu** (không coi là 0), mọi con số tự doanh đều kèm độ phủ? | Có |
| 6 | 4 nhãn (Dấu hiệu gom / Trung tính / Dấu hiệu xả / Chưa đủ dữ liệu); chế độ Gồm thỏa thuận chỉ hiện tổng tỷ đồng? | Có |
| 7 | Phần "trong nước suy ra" chỉ ở màn chi tiết; có máy tính khối lượng vị thế ở bài L10 (dùng số bạn tự nhập)? | Có |
| 8 | Ghi nhận: CafeF KLThoaThuan = 0 cho MCH 09/10 là điểm chưa giải thích được; app lấy thỏa thuận theo VCI/ASEAN | Có |

Chưa kiểm:
- AppTest với `st.dataframe` `on_select` và Styler trên điện thoại (sẽ kiểm tay ở A3).
- Số trên DB thật mới chạy cho một ngày (22/10).
- Gọi `prop_trade` 2 năm trong một lần gọi.
- Kết luận "CafeF = khớp lệnh" dựa trên 1 phiên MCH và 3 phiên FPT.
- Dữ liệu ASEAN mới thử với FPT và MCH.
