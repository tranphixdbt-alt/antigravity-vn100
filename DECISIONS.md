# DECISIONS.md — Quyết định kỹ thuật dự án antigravity-vn100

> Ghi lại theo yêu cầu AGENTS.md. Mỗi mục: quyết định, lý do, file/dòng liên quan.

---

## Sprint: Điều tra lệch định giá vs đồng thuận đa-CTCK (2026-07)

**Bối cảnh:** sau khi nạp consensus đa nguồn (24hmoney + Simplize, 64 CTCK,
2.925 dòng), đối chiếu cho thấy mô hình nội bộ thấp hơn đồng thuận CTCK median
-37% (66/81 mã), lệch nặng nhất ở ngân hàng top-tier, công ty quỹ đất lâu năm,
và cổ phiếu chu kỳ vừa qua đỉnh capex. Điều tra tìm ra 3 nguyên nhân gốc — đều
là 1 tham số cố định áp đặt đồng loạt, xoá mất phân hoá chất lượng mà thị
trường/CTCK định giá.

### D20 — Trần ROE bền vững ngân hàng theo TIER chất lượng (15%/20%), không dùng 1 trần cứng

**Quyết định:** `BankGeneralValuationModel.__init__` — ngân hàng có
`sustainable_roe` lịch sử (median nhiều năm) > `ELITE_ROE_THRESHOLD=0.18` được
trần `ELITE_ROE_CAP=0.20`; còn lại giữ trần cũ `STANDARD_ROE_CAP=0.15`.

**Lý do:** trần cứng 15% cho MỌI ngân hàng (thêm ở commit `e36eb41`, sửa lỗi
"upside phi lý" — sprint 2026-07 đầu dự án) xoá sạch phần bù chất lượng: 11/17
ngân hàng VN100 (VCB 19.6%, ACB 20.9%, MBB 19.9%, HDB 20.9%, VIB 21.5%...) có
ROE bền vững lịch sử > trần, bị ép về ĐÚNG mức ngân hàng trung bình (BID
14.8%, CTG 15.5%) — dù thị trường trả P/B cao hơn hẳn cho nhóm tốt (VCB P/B
thị trường ~2.16x vs ACB ~1.17x, model cũ chỉ phân hoá ~5%). Vì
`Target P/B = (ROE-g)/(COE-g)` cực nhạy ROE, đây là nguyên nhân chính khiến
VCB/ACB/MBB/HDB bị định giá thấp hơn đồng thuận CTCK có hệ thống.

Đối chiếu golden test `TestBankGoldenVcb` (fixture `sustainable_roe=0.20`):
tài liệu hand-calc gốc kỳ vọng P/B≈2.148, FVPS≈69,232 VND — code cũ (trần 15%)
cho ra 1.55/50,002 (lệch 28%, không ai phát hiện vì test đã bị viết lại thành
circular-check thuần công thức, không so với hand-calc). Sau fix: khớp đúng
2.148/69,232 — test đã bổ sung assertion số cứng.

**Tác động thực nghiệm (build_company_data thật, TTM):**
VCB upside -24.8%→+0.8% (SELL→HOLD), ACB +30.8%→+77.2%, MBB→+90.8%,
HDB→+44.9% (đều BUY). BID/CTG gần như không đổi (không thuộc tier elite).

**Files:** `valuation/engine/models/bank_general.py` (dòng ~46-62).
**Test:** `tests/test_valuation_accuracy.py::TestBankGoldenVcb` (assertion mới
đối chiếu trực tiếp hand-calc, không còn circular).

---

### D21 — RNAV PROXY_MODE: chiết khấu chỉ áp phần đánh giá lại đất, không áp vốn CSH sổ sách

**Quyết định:** `RNAVValuationModel.perform_valuation()` nhánh PROXY_MODE —
`rnav_discount` chỉ nhân vào `revaluation_surplus` (phần premium đất/BĐS đầu
tư), KHÔNG nhân vào `total_equity` (đã kiểm toán). Công thức mới:
`nav_equity = equity + revaluation_surplus × (1 - discount)`
(trước: `nav_equity = (equity + revaluation_surplus) × (1 - discount)`).

**Lý do:** `rnav_land_premium=0.20`/`rnav_discount=0.40` là default Pydantic
đồng loạt cho MỌI công ty BĐS/KCN (comment gốc "# analyst nhập" — thiết kế để
chuyên viên tự override, nhưng quét batch 100 mã không ai chỉnh). Với công ty
quỹ đất lâu năm (BCM: đất KCN Bình Dương ghi giá gốc hàng chục năm trước,
inventory+BĐS đầu tư/cp 39,480đ >> equity/cp 21,718đ), công thức cũ chiết khấu
40% lên CẢ vốn CSH đã kiểm toán → FV (17,768đ) THẤP HƠN CẢ giá trị sổ sách
(21,718đ) — phi lý cho công ty có tài sản lõi bị định giá thấp trên sổ sách.

**Tác động thực nghiệm:** BCM FV 17,768→26,455đ (thoát vùng dưới sổ sách, vẫn
SELL vì thị giá 48,700đ quá cao so với NAV thận trọng). KBC 23,158→34,609đ
(SELL→HOLD). PHR/GVR ít đổi hơn (premium/equity nhỏ hơn BCM/KBC).

**Chưa sửa (để dành quyết định sau nếu cần):** magnitude premium 20%/discount
40% vẫn giữ nguyên — không tăng premium riêng cho nhóm đất lâu năm (BCM/GVR),
vì cần nghiên cứu tuổi quỹ đất/giá KCN hiện tại vs giá gốc mới định lượng đúng
được. Đây vẫn là proxy thận trọng, không phải NAV chi tiết theo dự án.

**Files:** `valuation/engine/models/rnav.py` (nhánh PROXY_MODE, dòng ~127-142).
**Test:** `tests/test_proxy_models.py`, `tests/test_ai_rnav_sotp.py` (không đổi
số, chỉ qualitative — vẫn pass).

---

### D22 — Capex dự phóng DCF: median 3 kỳ gần nhất, không median toàn lịch sử

**Quyết định:** `build_company_data` (repo.py) — `capex_to_rev` ưu tiên
median của 3 kỳ TÀI CHÍNH GẦN NHẤT (`historical_cf[-3:]`/`historical_is[-3:]`,
kỳ cuối là TTM), fallback về median toàn lịch sử nếu <3 kỳ có dữ liệu hợp lệ.
Cùng cửa sổ với `effective_tax` (đã dùng `historical_is[-3:]` từ trước).

**Lý do:** median toàn lịch sử (có thể 9 kỳ) trộn lẫn giai đoạn xây
dựng/mở rộng công suất (capex/DT cao) với giai đoạn thu hoạch hiện tại (capex/
DT thấp) rồi chiếu CỐ ĐỊNH cho cả 5 năm tới. VD HPG: capex/DT lịch sử dao động
3.2%-49.4% (giai đoạn xây Dung Quất 2), median toàn lịch sử = 14.6% — trong
khi kỳ TTM gần nhất chỉ 3.2% (đúng như tất cả báo cáo CTCK: "Dung Quất 2 đã
hoàn thành, giai đoạn gặt hái bắt đầu"). Model cũ vẫn giả định capex nặng như
thời xây dựng → FCFF bị bóp nghẹt (capex ăn ~86% NOPAT năm 1 dự phóng).

**Lưu ý trung thực:** với HPG cụ thể, 3 kỳ gần nhất VẪN còn 2 năm cao điểm
(25.6%, 16.5%, 3.2% → median 16.5% — cao hơn cả median-9 cũ 14.6%), nên fix
này KHÔNG cải thiện nhiều cho riêng HPG (FV giảm nhẹ 15,923→14,762). Logic vẫn
đúng hướng và có lợi hơn cho các mã khác đã hoàn tất capex-cycle sớm hơn (dữ
liệu 3 kỳ gần nhất phản ánh đúng giai đoạn hiện tại thay vì trộn lẫn quá khứ).

**Files:** `valuation/data_access/repo.py` (dòng ~436-448).
**Test:** full suite 233 passed, 3 skipped — không có golden test riêng cho
capex window (áp dụng chung cho mọi mã phi tài chính, không đổi hành vi cho
DN capex ổn định qua các kỳ).

---

## Sprint: Kiểm tra file Excel xuất VN100 — sửa lỗi export + engine (2026-07)

### D9 — DCF chặn vốn cổ phần ÂM về 0 + cờ NEGATIVE_EQUITY_VALUE_DCF

**Quyết định:** `DCFValuationModel.perform_valuation()` chặn `blended_fvps` về 0
khi < 0 và gắn cờ `NEGATIVE_EQUITY_VALUE_DCF` (nhất quán với EV/EBITDA — C9).

**Lý do:** file Excel người dùng xuất có NKG blended = -6,510 VND (giá cổ phiếu
ÂM — vô lý). Nguyên nhân: NKG thép biên mỏng (~2%) + nợ ròng ~6,371 tỷ > EV từ
DCF → equity value âm; DCF (khác EV/EBITDA) chưa có chặn. Giá không thể âm.

**Files:** `valuation/engine/models/dcf.py`.
**Test:** `tests/test_dcf_negative_clamp.py`.

### D10 — Cờ review upside cực đoan (UPSIDE/DOWNSIDE_EXTREME_REVIEW) trong valuate()

**Quyết định:** `valuate()` gắn cờ khi upside > +150% (UPSIDE_EXTREME_REVIEW)
hoặc < −60% (DOWNSIDE_EXTREME_REVIEW), áp cho CẢ 2 nhánh (bank + phi tài chính;
trước đây nhánh bank trả `flags: []` cứng — cũng vá luôn).

**Lý do:** PVT +302.8%, TNH −99.9%, VIC −93% lọt qua không cờ nào → người dùng
không biết mã nào cần soi lại. Cờ này KHÔNG đổi khuyến nghị, chỉ buộc rà giả định.

**Files:** `valuation/engine/valuate.py` (`_review_flags`), `flag_descriptions.py`.

### D11 — Sửa lỗi tầng xuất Excel (export_100.py): Sector & MOS rỗng

**Quyết định:** sửa `export_100.py`:
- `Sector`: lấy `r.get('group')` (route() trả sector dưới key `group`, KHÔNG
  phải `sector` → trước đây rỗng 100/100 mã). Thêm cột `Business Nature`.
- `MOS Target (%)`: lấy `res['decision']['target_mos']` (KHÔNG phải
  `res['mos_target']` không tồn tại → trước đây 0 cho 100/100 mã).
- `Upside (%)`: bỏ `*100` thừa (valuate đã trả sẵn theo %).

**Lý do:** file Excel xuất ra có cột Sector rỗng toàn bộ và MOS = 0 toàn bộ —
lỗi lấy sai tên key ở tầng xuất, KHÔNG phải lỗi engine (khuyến nghị vẫn đúng vì
Decision Engine dùng target_mos nội bộ chính xác).

### D13 — Sửa bội số EV/EBITDA gán nhầm cho vận tải/cảng (PVT +302%, HAH +113%)

**Quyết định:** EV/EBITDA target ưu tiên lấy theo NHÓM từ routing.json (D14 —
nguồn sự thật ngành) qua map `_GROUP_EV_KEY`, fallback keyword DB sector. Thêm
`sector_ev_ebitda.transport: 6.5` cho vận tải/cảng biển.

**Lý do:** PVT (vận tải dầu khí) & HAH (vận tải container) có ngành DB rộng
"Industrial Goods & Services" → keyword 'industrial' khớp nhầm nhóm KCN
(industrial_zone = 12x). Tàu biển thâm dụng vốn đúng ra ~6x. Sau sửa: PVT dùng
oil_gas 6x (upside +302.8% → +70.1%), HAH dùng transport 6.5x (+112.6% → +9.2%).

**Files:** `valuation/data_access/repo.py` (map nhóm→ev_key, ưu tiên routing
group), `config/defaults.yaml` (thêm transport: 6.5).

### D14b — Lỗi hiển thị Excel VCB "1000%": pipeline xuất nhân đôi 100×

**Quyết định:** `export_100.py` bỏ `*100` ở cột Upside (valuate đã trả sẵn %),
sửa Sector→`group`, MOS→`decision.target_mos`. File `VN100_Valuation_Pro.xlsx`
tạo lại bằng script 1 bước dùng định dạng `0.0"%"` (số % thô + hậu tố %, KHÔNG
nhân 100).

**Lý do:** người dùng thấy VCB > 1000%. Nguyên nhân: pipeline cũ 2 bước
(export_100 nhân `upside*100` → format_excel chia /100 rồi định dạng '0.00%' lại
nhân ×100 khi hiển thị) → phóng đại ~100 lần (upside thật -18.5% hiện thành
~-1850%, hoặc +10% → +1000%). Sau sửa: VCB hiển thị đúng -18.5%; không mã nào
|upside| > 500%.

**Files:** `export_100.py`; file Desktop tạo lại.

### D19 — Backfill lịch sử chuỗi vĩ mô → kích hoạt overlay vi mô ngành

**Quyết định:** backfill lịch sử các chuỗi mà `MacroContext.from_db_momentum`
tiêu thụ (GDP_YOY, CREDIT_GROWTH, STEEL_HRC, CPI_YOY) để tính được momentum
(nay vs ~1 năm trước) — trước đây STEEL_HRC/CPI chỉ 1 điểm nên momentum = 0
(overlay no-op).

**Đã nạp (dữ liệu thật):**
- CRUDE_OIL, STEEL_HRC, USDVND: 32 điểm/chuỗi (tháng, 3 năm) qua yfinance history.
- CPI_YOY: 13 điểm (tháng, 2025-06→2026-06) qua Highcharts tradingeconomics
  (đọc `Highcharts.charts[0].series[0].data` qua Chrome). Chuẩn hóa cuối tháng.

**Kết quả momentum (xác nhận overlay hoạt động):** GDP +0.69pp, tín dụng
+2.79pp, thép HRC **+333 USD/tấn** (trước = 0), CPI +1.12pp. Overlay
revenue_growth (theo GDP) & credit_growth (theo tín dụng) chạy trên số thật.

**Tồn đọng (cần QUYẾT — không tự đặt hệ số):** elasticity biên-thép-theo-HRC
trong `config/elasticities.yaml` vẫn = 0.0 (disabled). DỮ LIỆU đã sẵn (HRC 32
điểm), nhưng HỆ SỐ co giãn là phán đoán tài chính — cần người dùng chốt mức
(vd margin thép +Xpp cho mỗi 100 USD/tấn HRC) trước khi bật.

### D18 — Nguồn vĩ mô thay thế + cào qua Chrome (đã có dữ liệu thật)

**Quyết định:** thay vì HNX/VBMA (khó cào, endpoint không rõ), dùng nguồn dễ
bóc tách hơn, cào qua Chrome MCP (người dùng cấp toàn quyền dùng Chrome):
- **worldgovernmentbonds.com** → đường cong lợi suất TPCP VN đầy đủ (1Y–30Y).
- **tradingeconomics.com/vietnam/indicators** → CPI, lãi suất điều hành, GDP,
  bán lẻ.
Cả 2 render bằng JS (httpx chỉ thấy khung, không có số) → phải chạy JS trong
Chrome. Thêm 2 domain vào allowlist.

**Dữ liệu THẬT đã nạp (2026-07-11):**
- TPCP_10Y = 4.537% @ 10/7 (worldgovernmentbonds) — thay điểm cũ 4.521% @ 26/6.
- CPI_YOY = 4.69%, POLICY_RATE = 4.5%, GDP_YOY = 8.39%, RETAIL_SALES_YOY = 14.8%
  @ Jun/26 (tradingeconomics). → MacroEnvironment.from_db giờ chạy trên số thật
  (lạm phát 4.69%, sát ngưỡng stress 5%).

**KHÔNG bịa:** M2 chỉ có dạng số tuyệt đối (VND Billion), không phải %YoY → CHƯA
ingest M2_YOY (tránh suy diễn sai); CREDIT_GROWTH chờ nguồn SBV. Ghi rõ trong
`scripts/refresh_macro_chrome.md`.

**Quy trình lặp lại:** `scripts/refresh_macro_chrome.md` ghi URL + JS trích số +
lệnh ghi DB. Dữ liệu đổi chậm → refresh tuần/tháng, không cần mỗi lần quét.

**Tồn đọng:** backfill LỊCH SỬ (nhiều năm) các chuỗi này để tính baseline
elasticity overlay vi mô — hiện mới có điểm mới nhất. worldgovernmentbonds/
tradingeconomics có trang lịch sử; cần thêm bước cào chuỗi thời gian.

### D17 — Nguồn vĩ mô: khung nhập CSV (chạy ngay) + scaffold scraper HNX/VBMA

**Bối cảnh:** người dùng chỉ định chuyển TPCP_10Y sang cào HNX/VBMA (chính
thống, miễn phí); CPI/M2/POLICY_RATE thì xây khung nhập để họ tải số liệu chính
thức; backfill lịch sử làm sau (mục 3 sau mục 1-2).

**Đã làm — Khung nhập CSV (mục 1, chạy ngay, không cần mạng):**
`valuation/ingest/import_macro_csv.py` + `scripts/import_macro_csv.py`. Hỗ trợ
CSV WIDE (date,value + --code) và LONG (date,indicator_code,value). Auto-detect
đơn vị: rate dạng % (|v|>1) → chia 100 thành decimal_rate; giá giữ nguyên. Ghi
idempotent qua upsert_macro_series (validate registry, từ chối code lạ). Phủ
CPI_YOY/M2_YOY/POLICY_RATE/RETAIL_SALES_YOY **và** TPCP_10Y (export HNX/VBMA→CSV).

**Đã làm — Scaffold scraper (mục 2):** `valuation/ingest/tpcp_scraper.py`.
Thêm hnx.vn/vbma.org.vn vào `macro_sources.allowed_domains`; domain-guard
`_assert_allowed_host` chặn host ngoài allowlist (chống SSRF, AGENTS.md #5);
fetcher injectable (test offline không chạm mạng); parser `parse_hnx_yield_curve`
linh hoạt tên trường + quy % → decimal; endpoint để trong config
(`tpcp_10y_endpoint`, mặc định RỖNG = chưa bật live).

**CHƯA bật scrape LIVE — lý do (trung thực):** endpoint AJAX thật của HNX
không public/không tra được qua search; trang ASP.NET; môi trường dev không
verify SSL hnx.vn (WebFetch fail "unable to verify first certificate"). Không
hardcode endpoint đoán mò rồi tuyên bố chạy được (vi phạm AGENTS.md #4 "tự kiểm
chứng"). **Cách bật:** xác nhận endpoint bằng DevTools trình duyệt → điền
config → chỉnh parser cho khớp schema thật (đã có test khung) → gọi
`fetch_tpcp_10y` trong pipeline. Trong lúc chờ: dùng CSV import (đường tin cậy).

**Test:** `tests/test_macro_ingest_sources.py` (10 test — chuẩn hóa đơn vị,
từ chối code lạ, domain-guard chặn host lạ, parser bóc 10Y, fetch offline).

### D16 — Audit dữ liệu 2026-07-11 + Freshness Gate + vĩ mô mỗi lần quét

**Phát hiện audit:**
1. 🔴 Giá lệch 5 "thế hệ" (mã cũ nhất 26/6, mới nhất 8/7, chênh 12 ngày) →
   upside giữa các mã KHÔNG so sánh được. Nguyên nhân: các đợt ingest rời rạc.
2. 🔴 DGC thủng giá 15 phiên (1/6→19/6, di chứng bug C8 chưa vá hết vì nằm
   ngoài cửa sổ backfill), REE 1 dòng NULL.
3. 🔴 Vĩ mô mỏng: USDVND/STEEL_HRC/CRUDE_OIL chỉ 1 điểm (26/6); CPI_YOY,
   M2_YOY, POLICY_RATE, RETAIL_SALES_YOY hoàn toàn trống; TPCP_10Y dừng 26/6.
4. 🟡 Lãng phí API: mỗi lần ingest kéo FULL giá từ 2020 (~1,700 dòng/mã).

**Đã sửa:**
- **Ingest incremental** (`pipeline.py::_incremental_price_start`): kéo giá từ
  max(trade_date)−5 ngày (đệm vá NULL, upsert idempotent); mã trống → full
  backfill 2020. Tham số `incremental=False` để ép full khi nghi lịch sử hỏng.
  → refresh 102 mã hết vài phút thay vì hàng chục phút, tiết kiệm ~99% dữ liệu kéo.
- **Đồng bộ giá 1 vintage**: refresh 102/102 mã về 2026-07-10; DGC/REE full
  backfill vá lỗ lịch sử. (REE còn 1 dòng 28/6 chỉ có flow không giá — ngày
  không giao dịch, vô hại, không xóa theo Luật vàng #6.)
- **Freshness Gate** (`data_access/freshness.py`): build_company_data gắn
  `data_flags` (STALE_PRICE >5 ngày, STALE_MACRO_RF >30 ngày) → valuate() trộn
  vào flags → UI/Excel tự khai báo độ tươi. Model Company/CompanyBank thêm
  field `data_flags`.
- **Vĩ mô cập nhật mỗi lần quét**: `MacroEnvironment.from_db(db)` tự dựng từ
  macro_series (CPI_YOY→inflation, TPCP_10Y→rf, POLICY_RATE 2 điểm gần nhất→
  sbv_stance); thiếu series → giá trị trung tính, KHÔNG bịa. Streamlit dùng
  from_db mặc định (analyst chỉnh tay vẫn ưu tiên); export_100.py gọi
  fetch_market_macro (3 call yfinance, idempotent) trước mỗi batch scan.

**Nguồn dữ liệu (uy tín, tiết kiệm):** giá/BCTC = vnstock API (trả phí, đã có);
FX/hàng hóa = yfinance (3 symbol); TPCP_10Y = investing.com CSV; GDP/tín dụng =
GSO/SBV qua CSV. CPI/M2/POLICY_RATE chưa có nguồn tự động — cần bổ sung CSV
GSO/SBV (tồn đọng, xem D17-plan).

**Test:** `tests/test_freshness_gate.py` (6 test). Excel regen: 100 mã cùng
vintage 10/7, 0 cờ STALE.

### D15 — Điều chỉnh Blume cho beta toàn hệ thống (sửa gốc NAB +138%)

**Quyết định (người dùng chốt phương án 1):** mọi beta ước lượng đi qua
`_blume_adjust(raw) = 0.67·raw + 0.33·1.0`, chặn dải [0.6, 1.5]. Áp tại
`estimate_vcb_beta` (cả nhánh DB lẫn live) — một điểm, mọi consumer dùng chung.

**Lý do:** NAB (Nam A Bank) upside +138% do beta thô = 0.593 — thấp nhất nhóm
ngân hàng, phi thực tế cho bank nhỏ. Beta hồi quy bị thiên lệch xuống cho mã
thanh khoản mỏng/mới niêm yết (NAB lên sàn 10/2020). Beta thấp → COE 9.4% quá
thấp → phồng RI & P/B. Điều chỉnh Blume là chuẩn ngành (Bloomberg, Value Line)
sửa sai số ước lượng + hồi quy beta về 1.0.

**Tác động:** NAB 0.593→0.727 (upside +138%→+103%); VCB 0.774→0.849; TCB
1.112→1.075 (beta cao gần như không đổi). Kéo các beta cực đoan về hợp lý, cải
thiện độ chính xác COE cho CẢ 100 mã. Lưu ý: NAB vẫn +103% vì thực sự rẻ (0.92x
book, ROE 16-18%) — phần upside này là thật, không phải lỗi.

**Files:** `valuation/engine/ttm_helper.py` (`_blume_adjust`).
**Test:** `tests/test_blume_beta.py`.

### D12 — Tồn đọng CẦN QUYẾT (calibration, chưa tự sửa)

Rà 100 mã phát hiện phân bố lệch mạnh về SELL (57/100) và 20 mã cờ REVIEW. Ba
nhóm nguyên nhân method-mismatch cần người dùng quyết hướng xử lý:
1. **TNH** (bệnh viện): capex/doanh thu = 72.5% (năm xây viện, một lần) bị ngoại
   suy 5 năm → FCFF âm vĩnh viễn → DCF sập ~0. Cần cap/fade capex như đã làm với
   D&A, HOẶC đổi sang P/E cho y tế.
2. **Nhóm cao su PHR/GVR/DPR**: DCF bỏ sót giá trị quỹ đất → cần nhập Land Bank
   Add-on (D6) hoặc quay lại RNAV.
3. **PVT/HAH/PNJ/NT2 (+100-302%)**: bội số EV/EBITDA hoặc growth có thể quá cao
   cho nhóm này — cần hiệu chỉnh bội số mục tiêu theo dữ liệu ngành thực tế.

---

## Sprint: Hiển thị flags trên UI — vá lỗ hổng minh bạch (2026-07)

### D8 — UI không hiển thị flags từ valuate() → kết quả bất thường trông như lỗi

**Bối cảnh phát hiện:** người dùng chụp màn hình VJC hiện "SELL · Giá MT 0 VND ·
Upside -100%" và hỏi "kiểm tra xem lỗi gì". Đây chính là kết quả ĐÚNG đã biết
từ D7 (equity value âm do đòn bẩy tài chính cao), engine đã gắn cờ
`NEGATIVE_EQUITY_VALUE_EV_EBITDA` — nhưng rà code phát hiện **UI không bao giờ
đọc `_res["flags"]`** ở cả 2 nơi hiển thị chính (`streamlit_app.py` banner đầu
trang, `views/results.py` card "KHUYẾN NGHỊ ĐẦU TƯ"). UI chỉ hiển thị
`company.warnings` (model integrity) và `hard_gates_violations` (Decision
Engine), bỏ sót hoàn toàn cờ định giá của engine → người dùng thấy số bất
thường mà không có lời giải thích, hiểu nhầm là bug.

**Quyết định:** thêm `valuation/engine/flag_descriptions.py` — dịch mọi mã cờ
đang tồn tại trong engine (17 cờ: NEGATIVE_EQUITY_VALUE_EV_EBITDA,
VALUATION_PROXY, LAND_BANK_VALUE_ADDED, DDM_BLEND, SOTP_NAV_FALLBACK,
EBITDA/EARNINGS_NORMALIZED_CYCLICAL, COE_TOO_LOW, IMPLIED_PB_WARNING...) sang
câu giải thích tiếng Việt + mức độ (error/warning/info). Wire vào cả 2 nơi
hiển thị: `streamlit_app.py` (ngay dưới Hard Gates) và `views/results.py`
(ngay dưới card khuyến nghị).

**Lý do:** đây là lỗi thiếu minh bạch, không phải lỗi tính toán — engine đã
đúng và đã gắn cờ đúng từ trước (C9, D7), chỉ là UI không hiển thị. Sửa 1 lần
ở lớp hiển thị dùng chung, áp dụng cho MỌI mã có cờ (không riêng VJC).

**Files:** `valuation/engine/flag_descriptions.py` (mới), `streamlit_app.py`,
`valuation/views/results.py`.
**Test:** `tests/test_flag_descriptions.py` (5 test: cờ đã biết, danh sách
rỗng, cờ lạ có fallback, mọi mô tả có level hợp lệ, các cờ then chốt phải
được document — không rơi vào fallback chung chung).

---

## Sprint: Land Bank Add-on + kết luận VJC EV/EBITDAR (2026-07)

### D6 — Land Bank Add-on: cộng giá trị quỹ đất chưa phản ánh BCTC

**Quyết định:** thêm `Assumptions.land_bank_projects` (mặc định RỖNG) + module
`valuation/engine/land_bank.py::compute_land_bank_value_per_share()`. Cộng
thêm vào `blended_fair_value_per_share` ở `valuate.py` cho MỌI phương pháp phi
tài chính (DCF/EV_EBITDA/PE/RNAV/SOTP) — không ép đổi method. Gắn cờ
`LAND_BANK_VALUE_ADDED` khi có dữ liệu. UI nhập liệu dạng bảng (giống mẫu
rnav_projects/sotp_segments) trong `input_assumptions.py` mục 5, luôn hiện cho
mã phi tài chính.

**Công thức:** mỗi dự án `NPV = diện_tích_ha × 10,000 × giá_đền_bù_VND/m2 ×
tỷ_lệ_sở_hữu / (1+COE)^(năm_thu_tiền − năm_hiện_tại)`. Chiết khấu bằng COE
(CAPM) của chính công ty.

**Lý do:** DN nông nghiệp/cao su/KCN (PHR, DPR, GVR, SIP, SZC...) ghi nhận đất
theo giá gốc trên BCTC — DCF trên dòng tiền cao su/nông nghiệp thuần không bắt
được khoản thu nhập đền bù/chuyển đổi đất một lần. Kiểm chứng: PHR baseline
24,320đ → +100ha giả lập @3tr/m2 → 46,460đ (đúng khớp tính tay 22,140đ/cp).

**KHÔNG bịa số liệu:** mặc định rỗng, add-on = 0 cho mọi mã chưa nhập —
analyst BẮT BUỘC tự nhập diện tích/giá đền bù/năm thu tiền từ báo cáo thật.

**Files:** `valuation/models/financials.py` (field mới), `valuation/engine/land_bank.py`
(mới), `valuation/engine/valuate.py` (wire cộng vào phi tài chính),
`valuation/views/input_assumptions.py` (UI mục 5).
**Test:** `tests/test_land_bank.py` (5 test: rỗng không ảnh hưởng, tính tay
không chiết khấu, sở hữu+chiết khấu, nhiều dự án cộng dồn, wire vào valuate()
qua mock cô lập DB).

---

### D7 — VJC/EV-EBITDAR: KHÔNG triển khai — tiền đề ban đầu sai, đã kiểm chứng dữ liệu

**Quyết định:** KHÔNG xây EV/EBITDAR cho VJC. Giữ nguyên EV/EBITDA hiện tại +
cờ `NEGATIVE_EQUITY_VALUE_EV_EBITDA` (đã có từ C9).

**Lý do (phát hiện khi điều tra trước khi code):** đề xuất ban đầu giả định nợ
VJC là "operating lease chưa vốn hóa" (off-balance-sheet) nên cần cộng ngược
EBITDAR. Kiểm tra dữ liệu thực tế cho thấy **giả định này sai**: VJC có dòng
`finance_lease_assets` + `finance_lease_principal_payments` trên BCTC — nợ
thuê máy bay ĐÃ được vốn hóa (capitalized) vào `total_debt` theo đúng chuẩn kế
toán hiện hành. Hơn nữa, `finance_lease_assets` chỉ ~5,517 tỷ trong khi
`total_debt` là ~68,999 tỷ — phần lớn nợ là vay thông thường, không phải thuê
máy bay. Loại trừ riêng nợ thuê tài chính khỏi net debt cũng không đủ xóa
khoảng cách âm (~35,000 tỷ). Xây EV/EBITDAR ở đây sẽ là **bịa công thức** trên
dữ liệu không hỗ trợ tiền đề — vi phạm AGENTS.md luật vàng #1.

**Kết luận đúng:** VJC thực sự có đòn bẩy tài chính rất cao so với EBITDA
chuẩn hóa; multiple EV/EBITDA 6.0x không đủ bù đắp → equity value âm là kết
quả HỢP LỆ của phương pháp so sánh bội số với đòn bẩy này, không phải lỗi
tính toán. Cờ cảnh báo (đã làm ở C9) là xử lý đúng — minh bạch thay vì che giấu
bằng một công thức không có dữ liệu hỗ trợ.

---

## Sprint: Rà soát nâng cấp Decision Engine + Business Nature (2026-07)

Bối cảnh: người dùng thêm `decision_engine.py` (Dynamic MOS + Hard Gates),
`business_nature` trong router, và chuyển 13 mã SOTP→FCFF trong routing.json.
Rà soát phát hiện & xử lý 5 điểm:

### D1 — DCF blend phụ theo business_nature (P/E vs EV/EBITDA)

**Quyết định:** `dcf.py.perform_valuation` chọn bội số so sánh phụ theo
business_nature: Compounder/Retail → **P/E** (EPS chuẩn hóa median × target_pe);
còn lại → **EV/EBITDA** (như cũ). LNST chuẩn hóa ≤ 0 ở nhánh P/E → fallback về
dcf_fvps (không kéo blend về 0).

**Lý do:** Tài liệu lõi định giá quy định Compounder/Retail dùng DCF+P/E, nhưng
code cũ blend EV/EBITDA cho MỌI mã DCF → méo nặng cho retail biên mỏng
(FRT −82.7%→−63.1%; VNM −1.5%→+4.5%). Nhóm Cyclical/Utility giữ nguyên EV/EBITDA
(kiểm chứng HPG/DGC/PLX/GAS/POW không đổi).

**Files:** `valuation/engine/models/dcf.py` (from_pydantic + perform_valuation).
**Test:** `tests/test_dcf_secondary_blend.py` (chọn đúng bội số theo nature +
fallback khi LNST âm).

### D2 — Tách CK thành nhóm "Securities" MOS 30% (không gộp Bank 20%)

**Quyết định:** Chứng khoán → business_nature `Securities`, MOS 30% (như nhóm
chu kỳ). Bảo hiểm giữ `Bank` (MOS 20%). Phương pháp CK vẫn là P/B (không đổi).

**Lý do:** LNST công ty chứng khoán biến động rất mạnh theo chu kỳ thị trường —
đòi hỏi biên an toàn cao hơn ngân hàng.

**Files:** `sector_router.py` (_SECTOR_TO_NATURE), `decision_engine.py`
(get_target_mos). **Test:** `tests/test_decision_engine.py`.

### D3 — Decision Engine: epsilon chống lỗi float ở biên MOS

**Quyết định:** so sánh ngưỡng dùng epsilon 1e-9 (`upside >= mos - 1e-9`...).

**Lý do:** upside đúng bằng MOS (vd 115/100−1 = 14.999...% do float) bị rớt
xuống HOLD thay vì BUY. **Files:** `decision_engine.py`.

### D4 — Làm rõ 2 trục: routing.json = method, business_nature = MOS

**Quyết định:** ghi rõ trong docstring `sector_router.py`: `primary` (routing.json)
là nguồn DUY NHẤT chọn phương pháp; `business_nature` chỉ đặt MOS + chọn nhánh
blend phụ của DCF. Đổi ngành 1 mã phải kiểm tra cả `primary`.

### D5 — Nhóm cao su & FRT: kết luận sau kiểm chứng thực nghiệm

**Quyết định:** GVR/DPR giữ DCF (kiểm chứng: DCF ≈ SOTP ≈ PE, ~−55%/~0% — DCF
không méo). FRT/PHR được cải thiện qua D1 (FRT nhờ nhánh P/E). PHR vẫn thấp do
thu nhập đền bù đất bất thường — cần dữ liệu quỹ đất (RNAV chi tiết) mới định giá
đúng, KHÔNG ép đổi method để "làm đẹp số" (giới hạn dữ liệu, không phải lỗi code).

**Lý do:** nghi ngờ ban đầu "cao su cần SOTP" chỉ đúng một phần — kiểm chứng số
thật cho thấy chỉ PHR lệch, và lệch do bản chất land-bank không model nào bắt
được nếu thiếu dữ liệu đất.

---

## Sprint: Ingest mã thiếu dữ liệu + sửa bug ghi đè giá (2026-07)

### C7 — Ingest 39 mã thiếu dữ liệu tài chính (CTD + 38 mã khác)

**Quyết định:** Chạy `run_ingest(ticker, ["prices","financials"])` cho 39 mã có
metadata trong bảng `tickers` nhưng 0 dòng ở `financials_quarterly`/`prices_daily`
(CTD, VIC, VHM, MSN, GVR, PVD, KBC, HSG...). Kết quả: 39/39 thành công, phủ
100% (101/101 mã, không tính VNINDEX).

**Lý do:** người dùng báo lỗi "Không có dữ liệu tài chính cho CTD" — điều tra
cho thấy đây không phải bug mà là dữ liệu thật sự chưa được nạp. Ghi upsert
idempotent (ON CONFLICT DO UPDATE), an toàn chạy lại nhiều lần.

**Files:** không đổi code, chỉ ghi dữ liệu qua `valuation/ingest/pipeline.py`.

---

### C8 — Fix bug NGHIÊM TRỌNG: upsert_market_flows() ghi đè OHLCV thành NULL

**Quyết định:** `upsert_market_flows()` trước đây dùng
`update_dict = {c.name: c for c in stmt.excluded if c.name not in ['ticker','trade_date']}`
— lấy TOÀN BỘ cột bảng `PricesDaily` để UPDATE, kể cả open/high/low/close/volume.
Vì record market-flow không chứa các cột này, SQLAlchemy coi là NULL trong
`excluded` row → ON CONFLICT DO UPDATE **ghi đè giá thật đã có bằng NULL**.
Đã sửa: chỉ update đúng `_MARKET_FLOW_COLUMNS` (foreign_*/proprietary_*), không
đụng OHLCV. Đồng thời chuẩn hóa mọi record trong batch insert có ĐỦ cùng bộ
cột (trước đây record thiếu cột không đồng nhất giữa các ngày → lỗi
"INSERT value ... explicitly rendered as boundparameter" khi build multi-row
INSERT).

**Lý do:** vi phạm trực tiếp Luật vàng #6 AGENTS.md ("không phá dữ liệu lịch
sử"). Phát hiện khi điều tra VIC upside -92.9% bất thường: giá 23 ngày gần
nhất (19/6→1/7) bị NULL, chỉ còn giá hôm nay (2/7) sống sót vì dữ liệu khối
ngoại/tự doanh của hôm nay chưa được publish (nên chưa kịp ghi đè).

**Phạm vi:** 7 mã bị ảnh hưởng — VIC, VHM, MSN, GVR, VJC, SSI (23 ngày mỗi mã),
REE (5 ngày). Đã backfill lại toàn bộ từ nguồn vnstock gốc (dữ liệu gốc không
mất, chỉ bị ghi đè trong DB) — xác nhận 0 ngày NULL sau khi backfill.

**Files:** `valuation/ingest/pipeline.py` (`upsert_market_flows`,
`_MARKET_FLOW_COLUMNS`). `valuation/data_access/repo.py::get_latest_price`
(người dùng tự thêm `and row.close is not None` — phòng thủ bổ sung, giữ
nguyên: nếu ngày mới nhất có close NULL, fallback về giá gần nhất có dữ liệu
thay vì crash/trả 0).

---

### C9 — EV/EBITDA: gắn cờ khi equity value âm bị clip về 0

**Quyết định:** `EVEBITDAValuationModel.perform_valuation()` gắn cờ
`NEGATIVE_EQUITY_VALUE_EV_EBITDA` khi `net_debt > EV` (equity value âm, trước
đây âm thầm clip về 0 → hiển thị "upside -100%" gây hiểu lầm công ty vô giá
trị). KHÔNG tự đổi method/multiple (VD: EV/EBITDAR cho hàng không thay vì
EV/EBITDA thường) — đây là quyết định tài chính cần duyệt riêng.

**Lý do:** phát hiện ở VJC (Vietjet) — nợ thuê tài chính máy bay vốn hóa theo
chuẩn kế toán rất lớn so với EV theo multiple 6.0x, khiến equity value âm
35,354 tỷ. Rà toàn bộ 6 mã dùng EV/EBITDA (BSR, HAH, HT1, HVN, PVT, VJC) —
chỉ VJC bị ảnh hưởng, không phải lỗi hệ thống.

**Files:** `valuation/engine/models/ev_ebitda.py`.
**Test:** `tests/test_ev_ebitda.py` (3 test: case đòn bẩy cao có cờ, case bình
thường không cờ oan, ca tính tay EV/EBITDA chuẩn).

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
