# DECISIONS.md — Quyết định kỹ thuật dự án antigravity-vn100

> Chỉ giữ chi tiết từ D61 trở đi. D01..D60 nằm ở `docs/archive/DECISIONS_D01-D60.md`
> (mục lục 1 dòng bên dưới). Mục mới thêm vào CUỐI file.

## Mục lục D01..D60 (chi tiết trong archive)

- D20 — Trần ROE bền vững ngân hàng theo TIER chất lượng (15%/20%), không dùng 1 trần cứng
- D21 — RNAV PROXY_MODE: chiết khấu chỉ áp phần đánh giá lại đất, không áp vốn CSH sổ sách
- D22 — Capex dự phóng DCF: median 3 kỳ gần nhất, không median toàn lịch sử
- D23 — Harness hiệu chuẩn + hàng rào chống hồi quy theo nhóm phương pháp
- D24 — Chất lượng dữ liệu đồng thuận: chuẩn hoá tên CTCK, cách ly dữ liệu giả, bật Simplize
- D25 — Sổ đăng ký hiệu chuẩn từng mã: cơ chế "giữ nguyên hay phải sửa"
- D26 — Chứng khoán: đấu nối model RI+P/B, sửa lỗi ROE lệch tử/mẫu số
- D27 — Tách bảo hiểm khỏi chứng khoán: NOT_RATED thay vì số đã kẹp
- D28 — SOTP: từ chối xuất bản số khi proxy không mô tả được doanh nghiệp (NOT_RATED)
- D29 — Ngân hàng: sửa ước lượng ROE bền vững, bỏ hệ thống tier, thêm trần P/B
- D30 — Hợp nhất định nghĩa kịch bản + cho kịch bản biến thiên khối terminal
- D31 — Lưu luận điểm CTCK công khai + bóc tách TẤT ĐỊNH (không LLM)
- D32 — Năm gốc dự phóng: cơ chế đã sẵn sàng, MẶC ĐỊNH VẪN TRAILING
- D33 — Cưỡng chế bằng máy: engine không được biết gì về dữ liệu CTCK
- D23-b — Sự cố hạ tầng: hai cluster PostgreSQL, cluster dữ liệu thật bị chết
- D9 — DCF chặn vốn cổ phần ÂM về 0 + cờ NEGATIVE_EQUITY_VALUE_DCF
- D10 — Cờ review upside cực đoan (UPSIDE/DOWNSIDE_EXTREME_REVIEW) trong valuate()
- D11 — Sửa lỗi tầng xuất Excel (export_100.py): Sector & MOS rỗng
- D13 — Sửa bội số EV/EBITDA gán nhầm cho vận tải/cảng (PVT +302%, HAH +113%)
- D14b — Lỗi hiển thị Excel VCB "1000%": pipeline xuất nhân đôi 100×
- D19 — Backfill lịch sử chuỗi vĩ mô → kích hoạt overlay vi mô ngành
- D18 — Nguồn vĩ mô thay thế + cào qua Chrome (đã có dữ liệu thật)
- D17 — Nguồn vĩ mô: khung nhập CSV (chạy ngay) + scaffold scraper HNX/VBMA
- D16 — Audit dữ liệu 2026-07-11 + Freshness Gate + vĩ mô mỗi lần quét
- D15 — Điều chỉnh Blume cho beta toàn hệ thống (sửa gốc NAB +138%)
- D12 — Tồn đọng CẦN QUYẾT (calibration, chưa tự sửa)
- D8 — UI không hiển thị flags từ valuate() → kết quả bất thường trông như lỗi
- D6 — Land Bank Add-on: cộng giá trị quỹ đất chưa phản ánh BCTC
- D7 — VJC/EV-EBITDAR: KHÔNG triển khai — tiền đề ban đầu sai, đã kiểm chứng dữ liệu
- D1 — DCF blend phụ theo business_nature (P/E vs EV/EBITDA)
- D2 — Tách CK thành nhóm "Securities" MOS 30% (không gộp Bank 20%)
- D3 — Decision Engine: epsilon chống lỗi float ở biên MOS
- D4 — Làm rõ 2 trục: routing.json = method, business_nature = MOS
- D5 — Nhóm cao su & FRT: kết luận sau kiểm chứng thực nghiệm
- D34 — Định nghĩa dữ liệu đầu vào
- D35 — Cầu nối EV → VCSH đầy đủ
- D36 — Chuẩn hóa chu kỳ theo biên
- D37 — Một g vĩnh viễn, fade tăng trưởng về g
- D38 — Ngân hàng
- D39 — CTCK, điện, bội số, beta
- D40 — Khuyến nghị, cổng chặn, vĩ mô, kịch bản
- D41 — Dọn engine trùng
- D42 — Golden test tái lập báo cáo CTCK
- D43 — Làm sạch bội số, chặn kết quả cực đoan, cờ tài sản ngắn hạn
- D44 — Bảng định giá chuẩn Excel, đồng thuận không điều chỉnh quyền lần hai (2026-09-29)
- D45 — DCF: liên doanh theo lợi nhuận, CapEx khớp tăng trưởng (2026-09-30, người dùng duyệt)
- D46 — Chặn công bố khi có sự kiện trọng yếu mô hình chưa phản ánh (2026-10-02, người dùng duyệt)
- D47 — Giả định ngân hàng theo số thực tế (2026-10-02, người dùng duyệt)
- D48 — Số cp sau cổ phiếu thưởng thiếu ngày GDKHQ; quy đổi tay ×0,9033 là sai (2026-10-02)
- D49 — Golden test đối chiếu đồng thuận CTCK toàn VN100 (2026-10-02, người dùng duyệt)
- D50 — Khung "Chỉ số vĩ mô" trên sidebar + rút gọn tin AI (2026-10-10, người dùng duyệt)
- D51 — "Tổng quan thị trường" nhìn 5 giây trên đầu sidebar (2026-10-10, người dùng duyệt thiết kế)
- D52 — Mục VN-Index + "Sắp tới" trong Tổng quan thị trường; bỏ điểm số trụ cột (2026-10-12)
- D53 — Giao diện điện thoại + chạy trên VPS (2026-10-12)
- D54 — Điện thoại: thanh tab đáy kiểu app, nhận diện điện thoại ở server (2026-10-12)
- D55 — Tab VN100 làm lại: xếp hạng theo upside mô hình + 5 mã tích sản (2026-10-12, người dùng chọn)
- D56 — Nhận định nhanh lịch quyền: 3 tiêu chí cổ tức; sửa thanh khoản engine (2026-10-12, người dùng chọn)
- D57 — Ngưỡng cổ tức tốt 3,5%; sửa cộng cổ tức hai lần trong phân tích lịch sử (2026-10-12, người dùng chọn)
- D58 — Gọn cảnh báo trên mọi thiết bị (2026-10-13, người dùng yêu cầu)
- D59 — Kaleido cho ảnh biểu đồ PDF/Word (2026-10-13, người dùng yêu cầu cài)
- D60 — Xuất PDF báo cáo bằng Playwright (2026-10-14, người dùng yêu cầu cài)

---

### D61 — Biên lợi nhuận theo cửa sổ gần đây + chặn nhánh DCF âm (2026-10-15, người dùng duyệt « A+D »)
- **A:** trung vị biên EBIT / EBITDA mid-cycle / ROE CTCK lấy `forecast.margin_window_years: 4` năm gần nhất thay vì
  cả 9 năm (9 năm trộn các gãy cấu trúc: BMP biên 2023+ gấp đôi, VPX/PVD thời lỗ). Trung vị ≤ 0 nhưng năm cuối
  dương → dùng năm cuối. `bank_terminal.credit_cost_spike_multiple` 2,0 → 1,5 (EIB lọt).
- **D:** nhánh DCF âm không pha vào trung bình với bội số → `NEGATIVE_DCF_LEG`, FV = 0, NOT_RATED (BAF, CII, NKG, HSG).
- Đo trên cùng DB (chỉ đổi cấu hình D61): 47/100 mã đổi FV; công bố đổi 2 mã (EIB mở 11.082, HSG chặn).
  So CTCK: gần hơn BMP −35→+2%, GAS +25→−1%, DCM +21→−10%, HT1 +29→+8%; xa hơn HPG −13→−28%, POW +1→−16%,
  PVT +2→+12%. Độ nhạy cửa sổ 3/4/5/6/9 năm: trung vị |lệch| 29–31% (nhiễu) → giữ 4, không dò theo CTCK.
- HPG: cửa sổ rơi vào đáy chu kỳ thép (11,8% vs 13,1–13,5% hai năm gần nhất) — giới hạn mid-cycle theo cửa sổ với
  ngành chu kỳ, ghi must_fix. PVD có giá lần đầu, lệch −26% chưa rõ nguyên nhân → must_fix. HHV +148% lọt ngưỡng
  150% → event hold (bội số BOT thời ramp-up). Chưa duyệt: B (capex), C (bội số), các lỗi dữ liệu nhỏ.
- Lưu ý vận hành: 46 mã giá dừng 09/10 → cờ STALE_PRICE chặn công bố (không do D61), cần chạy cập nhật giá.

### D62 — Lỗi dữ liệu nhỏ, ROIC terminal, bội số TTM + trung vị ngành (2026-10-15, người dùng duyệt « làm tất cả »)
- **Dữ liệu/code:** bỏ năm sơ khai không có LCTT thay vì điền 0 (`INCOMPLETE_YEAR_DROPPED`, chỉ BAF 2018);
  trái phiếu chuyển đổi (phần nợ) cộng vào nợ dài hạn — BAF 513, CII 3.257, SBT 976 tỷ; phần quyền chọn là vốn
  chủ, không cộng. `weight_dcf` lấy theo routing.json thay vì cố định 0,5 (VRE 1,0 → FV 16.193 → 8.906; BWE 1,0;
  VPL 0,6; CII 1,0). Cảnh báo văn bản tự do không còn thành mã cờ rác ("Năm 2018"), văn bản vẫn hiển thị.
- **B:** TV đã đúng Damodaran (tái đầu tư = g/ROIC, mặc định ROIC = WACC theo D49). Sửa: `roic_terminal` người
  dùng nhập bị bỏ qua; ROIC ≤ g báo lỗi `INVALID_ROIC_TERMINAL` thay vì kẹp im lặng. **Chưa làm:** cộng XDCB dở
  dang theo giá sổ vào cầu nối vốn chủ (NKG −5.971 → ~4.837, HSG, HPG +16%) — bộ phân loại an toàn chặn sửa đổi
  làm tăng FV, chờ người dùng xác nhận riêng. Không nới trần doanh thu/vốn (5,0) — ngoài phạm vi duyệt.
- **C:** kỳ TTM ghép giá cuối quý → được tính vào ≥3 quan sát bội số lịch sử; thiếu lịch sử → trung vị bội số
  HIỆN HÀNH nhóm routing.json (`peer_multiples.min_peers: 3`, cờ `MULTIPLE_FROM_PEER_MEDIAN`), hằng số ngành chỉ
  còn là phương án cuối. Không kẹp bội số theo ngành: nhóm routing còn lẫn mô hình (HHV BOT chung nhà thầu → −49%).
- Kết quả (giá cập nhật tới 15/10): công bố 58/100; trung vị |lệch CTCK| 25,7% (n=60, ≥3 CTCK). Đổi lớn: FRT
  34.878 → 58.738 (có giá, ghi must_fix: chuẩn hoá LN trên pha tăng trưởng Long Châu, −65% vs CTCK), MCH +27%,
  CTD −22% (+61% → +26% vs CTCK), BSR −26%, VTP +22%, HHV −20% (vẫn hold).

### D63 — Nghiên cứu chu kỳ ngành thép & HPG (2026-10-18, người dùng duyệt nguồn World Bank + FRED)
- Thêm `www.worldbank.org`, `thedocs.worldbank.org` vào `macro_sources.allowed_domains` (Pink Sheet: quặng sắt,
  than theo tháng từ 1960). FRED đã có sẵn; thêm chuỗi WPU101 (giá thép Mỹ từ 1926) và CPIAUCNS (giảm phát).
  Giá cổ phiếu dài hạn lấy từ gói tài trợ `vnstock_data` (bản community trong vnstock_client giới hạn 8 năm).
- `valuation/analysis/steel_cycle.py` (hàm thuần, có test tính tay): zigzag đỉnh/đáy với trạng thái thời gian thực
  (không nhìn trước), thời lượng pha, Kaplan–Meier cho xác suất pha kết thúc, lợi suất theo trạng thái, tương quan
  trễ, nghiên cứu sự kiện, mùa vụ. `scripts/steel_cycle_report.py` nạp/lưu dữ liệu ở `data/steel_cycle/`, ghi
  `reports/steel_cycle/`. Tham số ở `steel_cycle` trong defaults.yaml (ngưỡng 20% hàng hóa, 35% cổ phiếu).
- Không ghi DB, không đụng mô hình định giá. Kết quả là tần suất lịch sử, không phải khuyến nghị.

### D64 — λ ROE ngân hàng 0,5; ngưỡng hai chân 5,0 (2026-10-20, người dùng quyết — owner phi)
- **Q1:** `bank_terminal.roe_convergence` 1,0 → 0,5: ROE terminal = nửa ROE bền vững riêng, nửa ROE ngành. Đo 18 NH
  (mốc 20/10): EIB −28%, SSB −26%, VPB −22%, MSB −19%, CTG −18%, TPB −16%, SHB −14%, OCB −13%, BID −10%, NAB −9%,
  VIB −8%, VCB/TCB −7%, STB −6%, ACB −4%; LPB +7%, MBB +4%, HDB +3% (ROE riêng > ngành); EVF không đổi. MSB, BID,
  VIB, TPB vào band ở hai mốc golden (gỡ khỏi registry; gỡ hold TPB — upside +74%); MBB ra band +20,7% (20/10).
- **Q2:** `publication_gate.leg_ratio_review` 3,0 → 5,0. Mở công bố: BSI, FTS (không có CTCK), SHB (upside +99,9%,
  CTCK n=1 lệch +5,5%), VCI (−50,7%, n=1, luận điểm D26), FRT (−49,9%, n=13 → hold chờ duyệt).
- **Q3/Q4** (audit nguồn công ty con SOTP qua API vnstock chỉ đọc, không ghi DB; MSN cộng MSR 92,89% và MML 94,3%
  theo thị giá vào holdings) đã được phi cho phép — thực hiện ở bước r4b (D65).
- Kèm theo (phản biện r3): driver NH analyst/kịch bản sửa cộng lên đường đã phai ROE thay vì bỏ dòng cân (đúng dấu);
  một nguồn thuế dài hạn `wacc.marginal_tax_rate`. Ghi chú: /private/tmp/claude-501/upgrade_notes/r4a_decisions_models.md.

### D65 — Audit nguồn công ty con SOTP; MSN cộng MSR/MML theo thị giá (2026-10-20, người dùng quyết — owner phi)
- **Q3:** `scripts/collect_sponsor_data.py` và `scripts/audit_vn100_data.py` nhận VN100 ∪ công ty con khai trong
  `config/sotp_holdings.yaml` (`universe.audit_universe/select_audit_tickers`: whitelist + regex `[A-Z0-9]{3}`);
  audit đầy đủ cũng giữ dòng công ty con; `--finalize-existing` đòi đủ 100 mã VN100 (dòng công ty con là phần
  thêm). Thu cache vnstock/VCI (chỉ đọc) và audit `--tickers` GEL, VSH, TBC, TMP, HHS, MSR, MML: status 100 → 107
  dòng (100 dòng cũ giữ nguyên), 0 xung đột. Không ghi DB. GEX/REE/TCH hết `SOTP_SUBSIDIARY_DATA_ERROR`.
- **Q4:** MSN holdings thêm MSR 92,89% và MML 94,3% (thị giá): FV 92.535 → 126.062đ (20/10, +35,2% CTCK n=6) /
  117.171đ (28/09, +27,2%). Registry MSN `out_of_band_justified` (owner phi); golden MSN kiểm phần lõi (MCH, TCB)
  trong golden_tolerance và phần MSR/MML đúng công thức tính tay.
- GEX, REE, TCH, MSN vẫn chặn `SOTP_HOLDINGS_UNVERIFIED` tới khi phi rà tỷ lệ và điền `reviewed_by`/`as_of`.
  Khi mở: REE −40,5% (n=10), TCH −59% (n=2) / −63% (n=3) là must_fix trong registry. Ghi chú:
  /private/tmp/claude-501/upgrade_notes/r4b_sotp_audit.md, bảng rà soát sotp_review_table.md.

### D66 — Nâng cấp định giá toàn VN100 (2026-10-19→20, người dùng duyệt gói NH, SOTP chiết khấu 10%, XDCB theo sổ, ghi DB)
- Tổng hợp các bước s1–s7, phản biện fx1–fx3, r3, r4 và fin_a; mỗi sửa có test tái hiện viết trước; chỉ s7 ghi DB.
  Quyết định riêng đã ghi: λ ROE NH 0,5 và ngưỡng hai chân 5,0 (D64); audit công ty con SOTP, MSN cộng MSR/MML
  (D65). Ghi chú chi tiết: /private/tmp/claude-501/upgrade_notes/*.md. Vận hành: manual §11–§14.
- **Lỗi code/dữ liệu & cờ (s1, fx1):** `sector_peer_multiples` lọc theo `sector` (D62-C lần đầu thực sự chạy);
  NH giữ dấu chi phí dự phòng (NAB hết BANK_PBT_MISMATCH), số dư bình quân TTM lấy cùng quý năm trước; chỉ tính
  bội số mà route() dùng; UNEXPLAINED_CURRENT_ASSETS theo tổng mục B01; bỏ năm vi phạm đẳng thức IS chỉ khi nằm
  ngoài mọi cửa sổ mô hình; FILING_BS_INCOMPLETE (PVT, GAS Q2/2026). Thuế = −số nguồn, chia cho LNTT trừ lãi LD/LK
  (BAF 22,7% → 10,2%). as_of quy số cp về cùng gốc giá đã điều chỉnh (hết lookahead HDB, TPB, GMD; gộp các đợt
  cùng ngày: BAF 334 → 365 tr cp). RIGHTS_ISSUE_UNDATED (info) tách khỏi CORPORATE_ACTION_UNDATED. Cổng
  VALUATION_LEGS_DIVERGE (s1 cho DCF; fx2 dùng chung CK/BH/NH); ngưỡng +150%/−60% vào config; thêm 48 mô tả cờ,
  level cờ khớp cổng công bố.
- **CK/BH/EVF (s2, r3a):** EVF nhận diện theo mẫu BCTC TCTD → RI 0,5 + P/B 0,5 (lỗi → 11.235đ, công bố). Chân P/B
  thị trường có kỳ TTM; dưới 3 quan sát thì lấy trung vị P/B nhóm. Beta nhóm bottom-up cho NH, CK
  (`coe_convention.peer_beta_groups`). BH dùng P/B lịch sử riêng. Payout CK/BH lấy từ cổ tức tiền 3 năm (cờ Gordon
  chỉ cảnh báo). fx2/r3a: CK/BH quy đổi ROE bình quân ↔ đầu kỳ; P/B trước đợt quyền mua/riêng lẻ tính pro-forma
  vốn hóa/(VCSH + tiền thu); không ước được thì loại quan sát (chỉ nhóm CK, BH).
- **Ngân hàng (s3, fx2, r3a, r4a, fin_a; λ ở D64):** ROE terminal hội tụ về ROE ngành. Một định nghĩa ROE = LNST /
  VCSH bình quân; RI và P/B hợp lý dùng ROE_T·(1 + g/2). Chi phí tín dụng phai đối xứng từ TTM về trung vị 3 năm.
  Tăng trưởng tín dụng phai về GDP danh nghĩa 8%. ROE năm 3–5 phai về ROE_T (dòng `roe_fade_adjustment`, cờ
  BANK_ROE_FADE_PLUG). Driver do analyst/kịch bản sửa được cộng delta trên driver gốc (`driver_base`). Ràng buộc
  vốn áp đối xứng cho đường gốc và đường sửa. Không làm F4 (cổ tức theo VCSH/TS mục tiêu).
- **DCF/thuế/XDCB (s4, fx2, r3a, r4a):** thuế hiệu dụng = Σthuế/ΣLNTT 3 năm tài chính, kẹp `dcf.effective_tax_band`.
  NOPAT terminal và lá chắn thuế nợ trong WACC dùng thuế biên 20% (một nguồn `wacc.marginal_tax_rate`, ô "Thuế
  terminal" trên UI). Bỏ trần 5,0 của sales-to-capital (giữ sàn 0,3). XDCB dở dang (mã 242) cộng theo giá sổ vào
  vốn chủ và loại khỏi EV hoạt động của bội số (người dùng duyệt, NPV = 0); vượt `dcf.cip_share_review` 0,5 → chặn
  CIP_DOMINATES_VALUE (NKG, HSG, BAF). Chân P/E phụ = P/E trailing × LN TTM; EV/EBITDA mã không chu kỳ dùng EBITDA
  TTM. ΔDR/ΔDT chỉ áp cho SIP. Thêm cờ MINORITY_AT_BOOK_MATERIAL (không đổi FV).
- **SOTP & đổi phương pháp (s5, fx3, r4b; MSR/MML ở D65):** chế độ SOTP_HOLDINGS (`config/sotp_holdings.yaml`):
  FV = [VCSH mẹ + Σ(stake × vốn hóa − giá sổ)] / cp × (1 − 10%), chiết khấu holding do người dùng duyệt. Áp cho
  VIC, MSN, GEX (GEL 70,21% thay look-through VGC), REE, TCH. Chặn tới khi người dùng điền `reviewed_by`/`as_of`
  (UNVERIFIED; quá TTL 180 ngày → STALE); lỗi dữ liệu công ty con chặn mã mẹ (SOTP_SUBSIDIARY_DATA_ERROR). PC1 →
  EV/EBITDA, HDG và VCG → FCFF (đảo D39, không gồm VGC); SIP → FCFF 0,5 + EV/EBITDA 0,5.
- **RNAV kỹ thuật (s6):** proxy chỉ đánh giá lại tồn kho + BĐS đầu tư (cơ sở VHM 410.285 → 15.878 tỷ); giả định
  proxy một nguồn config; thặng dư tính sau thuế phổ thông 20%. AI_RNAV theo đẳng thức NAV (bắt buộc giá sổ ròng,
  chi phí/m², tỷ lệ sở hữu). AI_SOTP hết trừ nợ ròng/CĐKKS hai lần. Land Bank trừ giá sổ và thuế. Mọi mã RNAV vẫn
  VALUATION_PROXY (chặn).
- **Ghi DB (s7, người dùng duyệt):** sao lưu `backups/vn100_full.pre_s7_20261020.db`. `run_ingest` (chỉ upsert, không
  UPDATE/DELETE) cho 18 mã công ty con/liên kết ngoài VN100 với is_vn100 = 0: +30.314 dòng giá, +132.911 dòng BCTC.
  Rổ VN100 vẫn 100 mã; chạy lại lượt 5 không nhân đôi dòng. Ngày GDKHQ: 0 dòng ghi (VSDC chưa có ĐKCC cho 13 đợt).
  PVT: không bổ sung tổng mục BCĐKT (PDF lỗi chứng chỉ TLS, không bỏ kiểm tra để tải).
- **Audit nguồn (s1, fx1, r3b, r4b):** dấu vân tay chỉ băm ô trọng yếu của kỳ ĐÃ đối chiếu (`audited_periods`).
  Kỳ mới → SOURCE_AUDIT_PARTIAL (cảnh báo). Số của kỳ đã đối chiếu bị đổi, hoặc quá `audit.max_unaudited_periods`
  kỳ chưa đối chiếu → SOURCE_AUDIT_STALE (chặn). F2c đo ΔFV xung đột trên bản sao DB trong bộ nhớ: ≤ 1% →
  SOURCE_CONFLICT_IMMATERIAL (DPM, SSI mở công bố). FILING_PRECEDENCE đo trên số thực dùng. `--tickers` gộp vào
  audit đã lưu. Status nay có 107 dòng (100 + 7 công ty con), 0 xung đột ở công ty con.
- **Bảo mật ingest (s7, fx1, r4b):** trước đây mã mới luôn được chèn is_vn100 = 1, nay `run_ingest` mặc định
  `is_vn100=False`. Route `/ingest` kiểm `^[A-Z0-9]{3}$` + whitelist VN100 ∪ công ty con. `universe.audit_universe`
  kiểm regex trước khi gọi API/ghi cache.
- **Hold (`config/event_holds.yaml`):** thêm NAB (sổ liên NH phình, cần RWA), BVH (thiếu Embedded Value), VRE
  (25.468 tỷ TS dài hạn chưa phân loại), POW (TTM chưa đủ 4 quý công suất mới), SIP (TV coi tiền thuê trả trước
  là tiền vĩnh viễn, thiếu quỹ đất), VCG, PC1 (mới mở, lệch > 30% CTCK), FRT (mới mở, −49,9%, n=13), REE, TCH (đặt
  sẵn: −40,5% / −59% khi điền reviewed_by). TPB thêm ở fx3 rồi gỡ ở r4a (upside +73,7%). Giữ PNJ, HHV. Luật hold
  thống nhất: `publication_gate.new_listing_hold_*` (0,40, ≥ 3 CTCK, upside 100%).
- **Bác/không làm:** cổ tức NH theo VCSH/TS mục tiêu (proxy sai cho CAR, cần RWA). Bội số theo số cp tại từng kỳ
  (số cp quỹ, ngày GDKHQ, giá phát hành chưa tin cậy). Loại quan sát trước phát hành cho NH/DCF (không có giá phát
  hành; FV đổi gấp nhiều lần độ méo). Ép driver NH về ROE_T (không có chuẩn CFA/Damodaran). Bảng thuế ưu đãi theo
  mã (cần căn cứ pháp lý). Ước CĐKKS theo thị giá (chưa có phương pháp từ dữ liệu sẵn có). VGC sang EV/EBITDA; BCM
  SOTP; module KCN, chân P/B BĐS, bội số chu kỳ chuẩn hóa (F9), NT2 đời hữu hạn, beta bottom-up phi tài chính
  (ngoài phạm vi). CHP, PPC, PAN không khai holdings (nguồn tỷ lệ cũ hơn 2 năm hoặc không có).
- **Kết quả đo** (100 mã, DB thật, đồng thuận CTCK 19/10): công bố 58 → 61; công bố có n ≥ 3 CTCK trong ±20%:
  21/39 → 29/41; trung vị |lệch| 17,2% → 11,8%. Baseline chạy trên dữ liệu cũ hơn (giá khác ở 91 mã, đồng thuận
  khác ở 19 mã) nên chênh lệch gồm cả trôi dữ liệu. Các mốc giữa: s8 64 / 30 trên 43 / 10,8%; fx4 55 / 26 trên 40 /
  15,0% (sửa công thức ROE NH khi λ = 1, P/B CK, cổng hai chân 3,0, hold VCG/PC1/TPB); r4 sau D64. fin_a không đổi FV Base hay cổng công bố. Không mã công
  bố nào có upside > 100% hoặc FV âm (SHB +99,9% sát ngưỡng); 12 mã công bố n ≥ 3 ngoài band đều có mục registry.
  pytest toàn bộ (fin_b): 981 passed, 4 skipped, gồm test_golden_consensus 3 ca hai mốc.
- **Chờ người dùng:** kịch bản Bull/Bear NH có bước nhảy LN năm 5 → 6 (phản biện r4, major); `reviewed_by`/`as_of`
  cho 5 holder SOTP và stake MSR sau Elmet (0,8787 cùng mẫu số DB); các mục registry owner "claude-de-xuat" (vd
  MBB, REE, PC1, VCG, FRT, SSI, HCM); các ngưỡng đề xuất liệt kê ở manual §14; EIB/OCB/EVF registry data_blocked
  mà engine vẫn công bố.

### D67 — Kịch bản NH: ROE dài hạn theo kịch bản (2026-10-21, người dùng chọn — owner phi)
- **Vấn đề (phản biện r4, major):** Bull/Bear sốc driver cả 5 năm. Cơ chế delta r4a dồn toàn bộ phần sốc vào LN năm 5,
  trong khi RI terminal vẫn theo ROE_T của Base (chỉ ±2 điểm % cố định) → LN năm 5 → 6 nhảy bậc. Vd VPB Bear lỗ năm
  4–5 rồi ROE ~12% vĩnh viễn; CTG Bear LN6/LN5 = 4,61. Docstring "năm 5 = ROE_T, LN6 nối liền" sai ở kịch bản.
- **Chọn phương án (b):** roe5 kịch bản = ROE riêng Base + (roe5 driver đã sốc − roe5 driver Base), qua
  `forecast_bank.driver_roe5`, dùng chung với repo. Với giả định máy đặt, ROE riêng Base chính là roe5 driver nên
  roe5 kịch bản đúng bằng ROE năm 5 của driver đã sốc. Khi analyst nhập ROE bền vững thì giữ mức đó, chỉ dịch phần
  sốc. ROE_T kịch bản hội tụ λ (D64) về ROE ngành. `driver_base` sốc cùng hệ số nên năm 3–5 phai về ROE_T kịch bản,
  năm 5 = ROE_T. Bỏ `sustainable_roe_delta` ±2 điểm % trong `config/scenarios.yaml`.
- **ROE ngành KHÔNG sốc.** Đây là dữ liệu quan sát (trung vị ROE lịch sử của nhóm), làm đích dài hạn cho hội tụ
  Damodaran, không phải driver của NH. Muốn sốc thì phải dùng số cố định (đúng thứ (b) thay thế) hoặc dự phóng lại cả
  nhóm. Hệ quả: λ = 1 thì ROE_T kịch bản = ROE ngành. Kịch bản khi đó chỉ còn tác động qua năm 1–5, COE và g (đảo ca
  s3 "λ = 1 sốc cả đích"). Nếu đọc Bear là stress toàn hệ thống thì vẫn có lý do sốc ROE ngành: mở cho phi.
- **ROE riêng ≤ 0 vẫn dùng** (`bank_own_roe`). Trước đây giá trị này bị thay bằng ROE TTM, nên VPB Bear (roe5 −4,5%)
  sẽ ra ROE_T cao hơn Base. Base 19 TCTD đều > 0 nên không đổi.
- **Cờ mới `BANK_TERMINAL_JUMP` (cảnh báo):** bắn khi |LN6/LN5 − (1 + g)| > `bank_terminal.terminal_jump_flag_tolerance`
  hoặc khi LN5 ≤ 0. Ngưỡng 0,10 do claude đề xuất, chờ phi duyệt. Base 19 TCTD lệch +0,03…+0,07.
- **Đo (DB 20/10, chỉ đọc):** Base trùng từng số ở cả 19 mã. Sau sửa, mọi kịch bản lệch tối đa 0,074 (HDB Bull);
  trước sửa là 7,07 (VPB Bear). Không mã nào bắn cờ. FV Bull −1,3%…−10,5% (bỏ +2 điểm % ROE ngành). FV Bear −21,0%
  (EVF) / −15,8% (VPB)…+9,0% (NAB). Giá trị kỳ vọng 25/50/25 −0,6%…−4,8%. Ghi chú:
  /private/tmp/claude-501/upgrade_notes/d67.md.

### D68 — Mô hình tổng hợp CTCK (BROKER_SYNTH) + cổng rà soát (2026-10-22, owner phi yêu cầu)
- **Vấn đề:** 39 mã bị chặn công bố vì mô hình riêng của hệ thống không định giá được (proxy lệch
  phi lý, vốn chủ/chân âm, CIP lấn át, hai chân vênh, hold sự kiện...). Owner yêu cầu vẫn công bố
  (kèm rà soát), và với các mã mô hình riêng chưa làm được thì bắt chước phương pháp CTCK để ra
  giá, ghi rõ nhãn "mô hình tổng hợp của CTCK" — không bịa công thức, không bịa số.
- **`valuation/engine/models/broker_synth.py` (docs/BROKER_SYNTH.md):** mỗi báo cáo CTCK tính lại
  giá trị vốn chủ tuyệt đối (tỷ đồng) bằng đúng công thức CTCK dùng (RNAV/SOTP/DCF: Σ cấu phần −
  nợ ròng − CĐTS + điều chỉnh, × (1 − chiết khấu); PE/PB/EV_EBITDA: bội số × dự phóng FY+1;
  BLEND: Σ trọng số × chân), cộng/trừ sự kiện vốn sau ngày báo cáo, rồi chia SỐ CP HIỆN TẠI —
  tránh điều chỉnh quyền hai lần (không lấy thẳng giá mục tiêu CTCK in). Giá mục tiêu 12 tháng
  chiết về hôm nay bằng COE (Damodaran: target price ≠ fair value hôm nay). Kiểm nhất quán: tính
  lại tại số cp CTCK dùng lệch giá mục tiêu CTCK đó > `broker_synth.recon_tolerance` (10%) → cờ
  `BROKER_SYNTH_RECON_GAP:<broker>`. Tổng hợp nhiều báo cáo = trung vị có trọng số độ mới (dùng
  lại `calibration.consensus_view.weighted_median`/`recency_weight`), bỏ báo cáo cũ hơn
  `max_report_age_days` (365 ngày).
- **`valuate._apply_publication_gate`:** mã có `config/broker_synth/<MÃ>.yaml` và mô hình riêng bị
  chặn vì đúng nhóm cờ dữ liệu/mô hình (`broker_synth.trigger_flag_prefixes`), hoặc config ghi
  `use_broker_synth: true` → công bố theo BROKER_SYNTH, cờ `BROKER_SYNTHESIZED` (info); FV/cờ mô
  hình riêng giữ lại ở `own_model_fv`/`own_model_flags` để so sánh, không xoá. Mã đang công bố
  bình thường không bị thay.
- **Cổng rà soát `config/valuation_reviews.yaml`:** review `decision: publish` còn hạn
  (`valuation_review.ttl_days`, 180 ngày) và cùng `basis` (own_model/broker_synth) với phương pháp
  đang dùng → gỡ các cờ "rà soát được" (`UPSIDE/DOWNSIDE_EXTREME_REVIEW`, `MATERIAL_EVENT_HOLD`,
  `VALUATION_LEGS_DIVERGE`, `PROXY_IMPLAUSIBLE`, `NOT_RATED`; thêm `VALUATION_PROXY`,
  `CIP_DOMINATES_VALUE` nếu basis=broker_synth; `SOTP_HOLDINGS_UNVERIFIED` nếu review xác nhận
  stakes), gắn cờ `REVIEWED_PUBLISH:<reason>` (info). Cờ lỗi dữ liệu thật (mọi `severity: error` từ
  `run_deterministic_checks`, `SOTP_SUBSIDIARY_DATA_ERROR`, `AI_INPUTS_UNVERIFIED`...) KHÔNG bao
  giờ bị gỡ. `decision: block` luôn chặn, cờ `REVIEW_BLOCKED:<reason>` (error). Không có review thì
  hành vi như cũ.
- **Test tính tay (`tests/test_broker_synth.py`, fixture `tests/fixtures/broker_synth/XYZ.yaml`,
  số liệu bịa có chủ đích cho test):** RNAV (1.000+500−300)×(1−20%)/100tr cp = 9.600đ; phát hành
  20tr cp/200 tỷ sau báo cáo → (960+200)/120×1.000 = 9.666,67 (không điều chỉnh quyền hai lần);
  12m_forward 10.000/1,15 = 8.695,65; recon gap + bỏ báo cáo cũ; BLEND trọng số; cổng review
  gỡ/không gỡ cờ dữ liệu thật/hết hạn/khác basis/block (dùng FPT thật trong DB, chỉ đọc); thay FV
  bằng BROKER_SYNTH khi mô hình riêng bị VALUATION_PROXY, giữ own_model_fv/flags, không thay mã
  đang công bố bình thường. 12 test pass; `tests/test_golden_consensus.py` không bị ảnh hưởng.
- **Chưa làm (do owner khác/agent khác điền sau):** file `config/broker_synth/<MÃ>.yaml` thật cho
  39 mã (đọc PDF CTCK, ghi nguồn file+trang) và `config/valuation_reviews.yaml` thật — engine này
  chỉ đọc, không tạo số liệu. Không tạo file mã thật trong lúc viết engine, chỉ có 1 fixture test.

### D68b — Điền `config/broker_synth/<MÃ>.yaml` cho 25 mã từ báo cáo CTCK đã đọc (2026-10-22)
- **Việc làm:** một agent trước đã đọc PDF 29 mã trong `reports/broker_pdfs/` và tính tay lại giá
  trị hợp lý theo đúng phương pháp CTCK (quy đổi về số CP hiện tại, không lấy thẳng giá mục tiêu —
  xem recon_note từng mã). Tôi chỉ dùng engine BROKER_SYNTH đã có (KHÔNG viết thêm code mới trong
  `valuate.py` — hạ tầng `_apply_publication_gate`/`load_broker_synth` đã làm đúng việc task yêu
  cầu), ghi 25 file `config/broker_synth/<MÃ>.yaml`: BAF, BCM, BVH, CII, DXG, FRT, GEE, GEX, HHV,
  HSG, KBC, KDH, MSN, NKG, NLG, NVL, PC1, PDR, REE, SIP, TCH, VCG, VGC, VHM, VJC.
  Mỗi report dùng `equity_value_bn` (tính ngược = FV tính tay × shares_outstanding hiện tại/1000,
  đã khớp số với `build_company_data` cho từng mã) thay vì chẻ `components` — vì agent trước đã
  làm phần tính tay, số liệu/trang nguồn nằm ở `notes` + `pages` trong từng file; `method: RNAV`
  chỉ là vỏ kỹ thuật dùng đường `equity_value_bn` trực tiếp, phương pháp CTCK thật ghi ở
  `method_family`. `horizon: valuation_date` (không chiết khấu COE thêm) vì agent trước đã nêu rõ
  không áp dụng bước này (ưu tiên tốc độ) khi tính recomputed_fv.
- **KHÔNG tạo file cho:** PNJ (mâu thuẫn với ghi nhớ dự án — khủng hoảng P-Lab, lỗ 2026 dự kiến +
  pha loãng 107% khiến upside tính lại +213% vô lý, xem `memory/pnj-plab-crisis-2026.md` — không
  tự ý ghi đè, cần người duyệt riêng); VRE, TAL (PDF ảnh scan, agent trước không đọc được số liệu,
  `recomputed_fv=0` — không có gì để ghi, giữ NOT_RATED); POW (đã có mô hình riêng DCF, agent
  trước ghi rõ "không thay thế" — giữ nguyên, chỉ bị MATERIAL_EVENT_HOLD).
- **Kết quả chạy lại (`valuate()`, 2026-10-22):** 17/25 mã chuyển `publication_allowed=True` với
  `method=BROKER_SYNTH` (BAF, BCM, CII, DXG, GEE, GEX, HSG, KBC, KDH, MSN, NKG, NLG, NVL, PDR,
  VGC, VHM, VJC — FV khớp đúng recomputed_fv tính tay). **8 mã vẫn NOT_RATED** dù đã có
  BROKER_SYNTH (BVH, FRT, HHV, PC1, REE, SIP, TCH, VCG) — vì `MATERIAL_EVENT_HOLD` từ
  `config/event_holds.yaml` KHÔNG tự động gỡ khi dùng broker_synth (đúng thiết kế `_gate()`: event
  hold cần review người thật qua `config/valuation_reviews.yaml`, không để mô hình CTCK tự động
  đè sự kiện trọng yếu chưa xử lý — xem D68 gốc). Đây là hành vi AN TOÀN đúng chủ định, KHÔNG phải
  lỗi — không viết thêm code để "ép" publication_allowed=True cho 8 mã này, vì sẽ phá cơ chế rà
  soát sự kiện trọng yếu mà hệ thống đã có (và đã từng cứu PNJ khỏi công bố sai, xem trên).
- **Test:** `pytest tests/test_broker_synth.py tests/test_golden_consensus.py` (22 pass, không
  đổi code nên không cần test mới — chỉ thêm data config). Toàn bộ 100 mã VN100
  (`/private/tmp/claude-501/broker_lean_final.json`, chạy lại `valuate()` cho cả 100 mã):
  **công bố trước = 61/100, sau = 78/100** (+17, đúng bằng 17 mã BROKER_SYNTH thắng
  MATERIAL_EVENT_HOLD ở trên). 22 mã còn NOT_RATED: 8 mã BROKER_SYNTH-bị-event-hold nêu trên +
  PNJ/VRE/TAL/POW (giữ nguyên, lý do trên) + DIG/DSE/KDC/KOS/NAB/PAN/SJS/VIC/VPI/VPL (ngoài phạm
  vi — owner chưa đưa báo cáo CTCK cho các mã này, không có gì để điền).
- **Việc còn để ngỏ:** 8 mã MATERIAL_EVENT_HOLD trên cần người dùng tự điền
  `config/valuation_reviews.yaml` (reviewed_by là người thật) nếu muốn công bố — ngoài phạm vi
  agent. PNJ cần xem lại riêng vì mâu thuẫn dữ liệu đã biết. VRE/TAL cần đọc PDF scan (OCR) để có
  số liệu.

### D68c — Sửa 8 lỗi test từ D68/D68b trước khi công bố (2026-10-22, owner Claude)
- **Vi phạm kiến trúc:** `broker_synth.py` import `valuation.calibration.consensus_view`
  (`weighted_median`, `recency_weight`) — vi phạm luật "engine không import dữ liệu đồng thuận
  CTCK" (`tests/test_forward_base.py::test_engine_khong_import_du_lieu_CTCK`). Hai hàm này là toán
  thuần (không đọc bảng `consensus_history`) nên tách sang `valuation/engine/weighted_stats.py`
  (module trung lập), `consensus_view.py` re-export lại để không phải sửa nơi khác đang import.
- **`VALUATION_PROXY` biến mất khỏi `flags` khi chuyển BROKER_SYNTH** (vỡ
  `test_batch_engine.py::test_proxy_flag_propagates`, và làm mất thông tin minh bạch): sửa
  `_apply_publication_gate` nối cờ chẩn đoán của mô hình riêng (`gated["flags"]`, bỏ
  `NOT_RATED`/`DATA_REVIEW_REQUIRED`) vào `flags` cuối SAU khi `_gate()` quyết công bố xong — không
  nối trước, vì `VALUATION_PROXY`/`PROXY_IMPLAUSIBLE` nằm trong `PUBLICATION_BLOCKING_FLAGS`, nối
  trước sẽ bị cổng tự chặn lại lần hai. Đồng bộ `batch.py`: `_NOT_RATEABLE_FLAGS` (kiểm độc lập,
  phòng vệ thừa) chỉ áp khi `method != "BROKER_SYNTH"` — quyết định công bố thật đã nằm ở
  `publication_allowed`.
- **`_apply_publication_gate` sập với mã mock trong unit test** (vd ticker `"HOLDX"` 5 ký tự):
  `load_broker_synth()` cố ý `raise ValueError` cho mã sai định dạng (chống path injection, xem
  `test_broker_synth.py::test_ticker_khong_hop_le` — ĐÚNG, không sửa). Lỗi là gọi hàm đó cho MỌI
  mã kể cả mã giả trong test. Sửa: chỉ gọi `load_broker_synth` khi mã khớp `[A-Z0-9]{3}`, mã khác
  dạng thì bỏ qua BROKER_SYNTH (coi như không có config) thay vì sập `valuate()`.
- **Lỗi nghiêm trọng hơn — `SOTP_HOLDINGS_` trong `trigger_flag_prefixes` vô hiệu hoá cổng chờ rà
  soát:** D68b (và tôi, lúc đầu) đã bật `use_broker_synth: true` cho cả MSN/GEX/REE/TCH — 4 mã này
  **đã có cơ chế SOTP_HOLDINGS đúng** (cổ phần công ty con niêm yết theo thị giá, D65), chỉ đang
  chờ người dùng điền `reviewed_by`/`as_of` sau khi rà tỷ lệ sở hữu
  (`reports/sotp_review_table.md`). Vì `trigger_flag_prefixes` có tiền tố `SOTP_HOLDINGS_`, cờ
  `SOTP_HOLDINGS_UNVERIFIED` (chặn có chủ đích, chờ người) tự kích BROKER_SYNTH — thay một cơ chế
  đã đúng bằng một báo cáo CTCK đơn lẻ kém chính xác hơn, và vô hiệu hoá chính cổng chờ rà soát
  (`tests/test_sotp_holdings.py::test_msn_holdings_mechanism_on_real_db` bắt được: tăng thêm từ
  MSR/MML = 0 thay vì ~25.878đ/cp). **Sửa:** bỏ `SOTP_HOLDINGS_` khỏi `trigger_flag_prefixes`;
  trả `use_broker_synth: false` cho MSN/GEX/REE/TCH (đúng kế hoạch D66/D67 đã báo người dùng — 4
  mã này vẫn chờ rà soát, KHÔNG dùng broker_synth).
- **Test:** toàn bộ `pytest` (1.014 passed, 0 fail, 4 skip — tăng từ 1.006 passed/8 fail của
  D68/D68b). `test_golden_consensus.py` (3 ca, cả 2 mốc) pass.
- **Kết quả cuối (`/private/tmp/claude-501/final_valuation2.json`, chạy lại `valuate()` 100 mã):**
  công bố 76/100 (so baseline tuần này 58/100). BROKER_SYNTH công bố 15 mã: BAF, BCM, CII, DXG,
  GEE, HSG, KBC, KDH, NKG, NLG, NVL, PDR, VGC, VHM, VJC. MSN/GEX/REE/TCH quay lại NOT_RATED (chờ
  rà soát tỷ lệ sở hữu — không phải lỗi, đúng kế hoạch). HHV vẫn NOT_RATED (MATERIAL_EVENT_HOLD từ
  D61, không đổi vì broker_synth không gỡ event hold — đúng thiết kế).

### D68d — Excel ghi đúng nhãn BROKER_SYNTH (2026-10-22, owner Claude)
**Vấn đề:** `scripts/export_valuation_book.py` lấy cột "Phương pháp định giá" từ `value_ticker()["method"]`
(= phương pháp của bảng routing), nên 15 mã BROKER_SYNTH vẫn ghi "RNAV (proxy)"/"DCF/FCFF" trong khi app
ghi "Mô hình tổng hợp CTCK"; cột "Chú ý" lại liệt kê cờ của mô hình riêng ("FV về 0, không công bố")
mâu thuẫn với trạng thái Công bố. Giá trị hợp lý thì không lệch (đối chiếu 100/100 mã, sai khác 0).
**Sửa:** mã BROKER_SYNTH dùng `res["method_label"]`, để trống cột nội tại/tương đối, và tách cờ mô hình
riêng thành một câu "Mô hình riêng không dùng được (...)".

### D69 — Rà mô hình sau D68: giữ ROIC dài hạn = WACC; ngân hàng không có lỗi công thức (2026-10-22, người dùng duyệt « Giữ nguyên »)
**Đo trên 24 mã DCF đã công bố, có ≥2 CTCK** (ảnh DB 22/10):
| ROIC terminal | trong ±15% | trong ±25% | trung vị |lệch| | trung vị lệch có dấu |
|---|---|---|---|---|
| = WACC (giữ) | 11 | 17 | 16,2% | −10,1% |
| (ROIC lịch sử + WACC)/2 | 10 | 16 | 16,4% | −4,8% |
| ROIC lịch sử, trần 30% | 10 | 16 | 15,8% | −3,9% |
Đổi chỉ dời thiên lệch, không tăng tỷ lệ khớp; đẩy NT2/BWE lệch xa hơn → **giữ = WACC** (đóng câu hỏi treo từ D49).
**Ngân hàng (SHB +96%, MBB, TPB):** RI = B0 + ΣPV(RI) + TV với RI6 = (ROE_T đầu kỳ − COE)·B5 — đúng CFA/Damodaran.
Upside cao vì cả 17 NH dùng chung beta ngành (D47) → COE 11,9%, trong khi thị trường trả SHB P/B 0,66x
(ngầm định COE cao hơn nhiều hoặc không tin ROE 16% bền vững). SHB không có CTCK nào trong 180 ngày để đối chiếu;
TPB lệch +12% so với CTCK (trong band). Không sửa — đổi COE riêng từng NH là đổi mô hình, cần duyệt riêng.
**Mã lệch >25% là lý do riêng từng mã, không phải một lỗi chung:** HPG — s2c tính trên vốn đã gồm Dung Quất 2
nên dự phóng còn capex lớn (FCFF âm năm 1–2); GVR/PHR — giá trị đất KCN/đền bù không nằm trong DCF;
BSR/PVD — chuẩn hoá chu kỳ; VTP/MCH — tăng trưởng/ROIC cao, ROIC terminal = WACC; SSI — CTCK chu kỳ thanh khoản.

### D70 — Thử s2c trung vị 5 năm cho HPG: KHÔNG áp dụng (2026-10-22, owner Claude)
Giả thuyết: HPG 2025 chuyển ~64 nghìn tỷ XDCB Dung Quất 2 sang TSCĐ → s2c năm cuối 1,02 (trước đó 1,3–1,5) →
capex dự phóng tính lần hai cho công suất đã xây. Thử trung vị s2c 5 năm: HPG chỉ +2% (20.554 → 21.004, vẫn −35%
so với CTCK); toàn rổ trung vị |lệch| 15,1% → 15,7%, số mã trong ±15% không đổi. Đã hoàn tác.
Lệch HPG chủ yếu do CTCK định giá theo LN dự phóng 2026–27 (công suất mới) trong khi chân bội số dùng EBITDA TTM
và DCF dùng thuế biên 20% cho terminal (thuế hiệu dụng HPG 13%) — đều là quyết định đã duyệt (D61/D64), giữ nguyên.

### D71 — Mã còn lại: Mô hình tổng hợp CTCK nhiều nguồn (TARGET_PRICE) + review ủy quyền (2026-10-23, người dùng yêu cầu)
**Yêu cầu:** « các công ty còn lại áp dụng đúng mô hình CTCK, có so sánh chọn lọc của từng cty phát hành; mã đã định
giá không đụng; tôi tin tưởng các báo cáo của bạn ».
**Làm:**
- `broker_synth.py`: phương pháp `TARGET_PRICE` — vốn chủ = giá mục tiêu × shares_used_mn (test tính tay
  `test_target_price_nhieu_ctck_trung_vi_trong_so`). Giá từ `consensus_history` đã điều chỉnh quyền/cổ tức tại nguồn
  → shares_used = số cp hiện tại (không điều chỉnh lần hai). horizon `12m_forward` → chiết về hôm nay bằng COE.
- "So sánh chọn lọc": mọi CTCK phát hành trong 365 ngày, trung vị có trọng số độ mới (bán rã 180 ngày) — trung vị
  tự loại giá mục tiêu lệch xa số đông; báo cáo PDF đã đọc ở D68b giữ nguyên, không trùng (cùng CTCK + ngày).
- 15 mã: FRT HHV PC1 REE SIP TCH VCG GEX MSN POW VRE BVH PAN TAL VPL (`use_broker_synth: true`).
- `config/valuation_reviews.yaml`: review basis broker_synth cho 15 mã — gỡ MATERIAL_EVENT_HOLD vì mọi hold của các
  mã này ghi rõ "lỗi mô hình riêng, không phải sự kiện doanh nghiệp". reviewed_by ghi "người dùng ủy quyền".
**Không mở:** PNJ (sự kiện thật P-Lab; chưa có giá mục tiêu CTCK lập sau 25/09/2026 — đúng lift_when);
DIG DSE KDC KOS NAB SJS VIC VPI (0 báo cáo CTCK trong 365 ngày).
**Lưu ý chất lượng:** BVH, PAN chỉ 1 báo cáo cũ ~10 tháng; GEX/TAL/VPL 1–3 báo cáo. 15 mã D68 cũ vẫn
`horizon: valuation_date` (không chiết COE) — người dùng yêu cầu không đụng, nên hai nhóm khác quy ước chiết khấu.
**Kết quả (DB 23/10):** công bố 76 → 91/100; 76 mã cũ không đổi do D71 (chênh <1% ở vài mã là do giá cập nhật sáng 23/10).
**Test (23/10):** 1012 pass; còn 3 lỗi `test_golden_banks[TCB]` do DỮ LIỆU — đợt tự cập nhật sáng 23/10 nạp Q3/2026 dở
(TCB chỉ IS+CF 78 dòng, không có BS → không tìm được vốn điều lệ; HT1/MSN 66 dòng cũng thiếu). Không ghi DB khi chưa
được duyệt. Registry: gỡ FRT/PC1/REE/TCH/VCG/VRE (vào band qua D71) và HDB (vào lại band sau giá 23/10);
`test_calibration_registry` đổi mã ví dụ FRT → PVD (FRT không còn mục must_fix).

### D71b — Nạp lại BCTC Q3/2026 dở cho TCB, HT1, MSN (2026-10-23, người dùng duyệt « đồng ý »)
Đợt tự cập nhật sáng 23/10 chỉ nạp IS+CF Q3/2026 (nguồn chưa có BS lúc đó). Sao lưu DB
(`/private/tmp/claude-501/vn100_full.before_q3fix.db`), gọi lại `vnstock_client.get_financials` + `upsert_financials`
(ON CONFLICT DO NOTHING) cho BS/IS/CF: +324 dòng BS (TCB 86, HT1 119, MSN 119); chạy lần 2 không thêm dòng (1.102.968).
`test_golden_banks` 9/9 pass. TCB 40.295 → 41.121đ. Chưa đóng gói lại `vn100_full.db.gz` (làm khi push).
**NT2 (cùng ngày):** nguồn vẫn chưa có CF Q3/2026 của NT2 (BS+IS đã có) → không phải lỗi nạp mà công bố dần. Sửa gốc:
`repo.drop_incomplete_latest_quarters` — quý mới nhất chưa đủ BS+IS+CF thì TTM dừng ở quý đầy đủ gần nhất, cờ
`QUARTER_INCOMPLETE_SKIPPED:<kỳ>` (thông tin). Test tay `test_bo_quy_moi_nhat_chua_du_ba_bao_cao`. NT2 công bố lại 36.205đ.
**Số cp (cùng ngày, lỗi có sẵn lộ ra khi có BS Q3):** `ttm_helper.get_latest_balance` luôn lấy quý mới nhất,
bỏ qua as_of → backtest 28/09 dùng vốn điều lệ BS Q3/2026 (kết thúc 30/09) = lookahead (MSN 1.520 → 1.535 tr cp).
Sửa: (a) tham số as_of — chỉ quý đã quá hạn công bố (`publication_lag_days.quarterly`), chỉ áp khi gọi ngày quá khứ;
(b) lấy quý gần nhất CÓ chỉ tiêu (quý nạp dở không làm mất vốn điều lệ, ca TCB sáng 23/10).
`test_msn_holdings_mechanism_on_real_db` tắt broker_synth (MSN công bố qua BROKER_SYNTH từ D71) để vẫn kiểm cơ chế SOTP.

### D72 — Gói triển khai VPS: báo cáo sáng + bot Discord + app chạy bằng systemd (2026-10-23, người dùng yêu cầu)
**Yêu cầu:** nhân viên tải code từ GitHub lên VPS là chạy như máy Mac (Discord hằng ngày), "bao gồm cả .env".
**Không làm:** commit `.env` — luật bảo mật mục 5 (key Discord/vnstock/DeepSeek lộ vĩnh viễn trong lịch sử git).
`.env` chép một lần bằng `scp`; `setup_vps.sh` dừng với hướng dẫn nếu thiếu, kiểm 3 khóa Discord bắt buộc, chmod 600.
**Làm:** `deploy/setup_vps.sh` (idempotent: .venv, thư viện — vnstock_data tách riêng vì là gói tài trợ, giải nén DB,
dry-run báo cáo, cài systemd), `deploy/update_vps.sh` (git pull + setup; giữ DB VPS, `--reset-db` sao lưu rồi thay),
`deploy/systemd/` (timer 07:50 T2–T6 Asia/Ho_Chi_Minh Persistent=true thay launchd; bot Restart=always; Streamlit
127.0.0.1:8502 như hướng dẫn cũ, tự tắt `vn100.service` cũ). `docs/DEPLOY_VPS.md` gộp hướng dẫn cũ (Caddy/HTTPS/mật
khẩu, kaleido/playwright, ufw) với phần tự động. `requirements.txt` thêm `discord.py` (thiếu — bot không chạy được
ngoài máy Mac). Bot chỉ chạy MỘT nơi: tắt launchd trên Mac sau khi VPS chạy.

### D73 — Tab "Dòng tiền ngành" + dòng tiền khớp/thỏa thuận chính xác (flow_daily) (2026-10-24, người dùng duyệt « đồng ý hết »)
**Yêu cầu:** vào tab nhìn toàn bộ ngành biết khối ngoại/tự doanh mua bán ròng ở đâu; tra từng mã có dấu hiệu gom không;
5 giây ra kết quả, chi tiết bấm mới xem; gồm thỏa thuận lớn; chỉ VN100; có lộ trình học. Kế hoạch: `docs/PLAN_SECTOR_FLOW.md`
(v2.1, 2 vòng workflow khảo sát → 3 phương án → giám khảo → rà soát).
**Làm:** lõi thuần `valuation/analysis/money_flow.py` (không import vnstock/streamlit/ingest), UI `valuation/views/money_flow.py`
+ `money_flow_lessons.py` (L1–L10), tab cuối cả 2 nhánh (nhãn đáy điện thoại "money"); B1: bảng `flow_daily`
(MetaData riêng → `create_all` không tự tạo; chỉ `scripts/migrate_flow_daily.py --apply` tạo sau backup + integrity_check),
`valuation/ingest/flow_client.py` (VCI `iq.vietcap.com.vn` price-history + proprietary-history, nuốt stdout để không lộ
tài khoản/tier), job `scripts/update_flow_daily.py` 18:00 T2–T6 (launchd `vn.antigravity-vn100.flow-daily` / systemd
`vn100-flow-daily.timer`), upsert idempotent, dòng `is_final` không bị ghi đè. Cấu hình `money_flow`, `flow_ingest`.
**Phương pháp (HEURISTIC, chưa backtest):** nhãn tính ở chế độ Loại thỏa thuận; phiếu Ngoại (R_F = ΣF/ΣGTGD ≥ 2% và ≥ 60%
phiên hợp lệ cùng dấu) BẮT BUỘC cho « Dấu hiệu gom/xả », cộng ≥ 1 xác nhận từ Giá-KL (CMF20, CHUẨN StockCharts; loại H=L là
quy ước repo) hoặc Tự doanh (chỉ xác nhận, NULL = thiếu). Có flow_daily → dùng khối ngoại/tự doanh KHỚP LỆNH và GTGD khớp
VCI; không có → đường A suy từ prices_daily (cờ thỏa thuận = max(Fb+Pb, Fs+Ps) > KL khớp, cận dưới). Chế độ Gồm chỉ hiện
tổng tỷ đồng. GTGD điều chỉnh theo thưởng/cổ tức CP có ngày GDKHQ; quyền mua/ngày NULL/gãy điều chỉnh → phiếu ◌.
`small_sector_n` = 3 (≠ `sector_min_members` = 2 của sidebar): ngành 2 mã không vào câu kết luận.
**Golden:** `tests/test_money_flow_golden.py` — khối ngoại FPT ở phiên không thỏa thuận so CafeF GDKhoiNgoai (= khớp lệnh):
mua/bán lệch ≤ 0,65%; flow_daily khớp lệnh so CafeF cả phiên có thỏa thuận (FPT 09/10, 12/10, 15/10; MCH 09/10 +47,5 tỷ).
Đo |Δròng|/(mua+bán), không % trên ròng (ròng ≈ 0 thì không ổn định: FPT 05/10).
**Nguồn mâu thuẫn còn mở (AGENTS §8):** CafeF KLThoaThuan = 0 cho MCH 09/10, trong khi DB/VCI/ASEAN/báo chí có ~64 triệu cp.
**Chưa làm / chờ người dùng:** B2 (mua/bán chủ động ASEAN), lệnh lớn tick, đóng gói `flow_daily` vào `vn100_full.db.gz`,
3 quyết định tài chính: (1) 6 mã sự kiện chỉ có ngày công bố (PC1, SBT, TCB, VPI, VPX, VSC) đang ◌; (2) công thức điều chỉnh
GTGD theo cổ tức tiền (hiện chỉ huy hiệu); (3) ngưỡng huy hiệu thỏa thuận lớn theo KL ở đường exact (hiện GT ≥ 0,5 × ADTV).

### D79 — Báo cáo Word chỉ dựng khi bấm tải (2026-10-25, người dùng duyệt)
**Đo (AppTest + cProfile, lượt chạy lại đã cache):** 19,2 s, trong đó `build_docx_report` 5,9 s (9 bảng `add_table` 5,2 s)
chạy ở MỌI lượt chạy lại của tab Định giá dù không ai tải. **Làm:** `results.docx_on_click` trả hàm cho
`st.download_button(data=callable, on_click="ignore")` — Streamlit chỉ gọi khi bấm, chạy luồng riêng, không chạy lại trang
(ảnh biểu đồ của lượt hiện tại không bị lượt sau ghi đè giữa chừng). Dựng lỗi → RuntimeError vào log (trước: nút ẩn).
Đo lại cùng cách: 5,2 s/lượt (≈ 6 s nhờ bỏ dựng Word, phần còn lại có thể do cache ổ đĩa đã nóng). Lượt đầu (nguội) 51,6 s
chưa xử lý: tab Cổ tức 2,1 s, Tổng quan thị trường 1,8 s, kiểm tra dữ liệu thanh bên ~2 s.

### D78 — Sửa lỗi: ngày dòng tiền bỏ qua flow_daily (2026-10-24, owner Claude, người dùng bảo « tiếp tục »)
**Lỗi:** 23/10 `prices_daily` đã có giá nhưng 0/107 mã có khối ngoại/tự doanh, trong khi `flow_daily` (VCI) có khối ngoại
100/100 mã. `clean_flows` chỉ đếm `prices_daily.f_net_val` nên flow_date lùi về 22/10 → tab tụt 1 phiên dù số chính xác đã
có. **Sửa (nguyên nhân gốc):** `clean_flows(..., exact)` đếm phiên-mã có khối ngoại từ CẢ hai nguồn; `_paths` vốn đã lấy
`fr_net_match_val` khi có. Test tái hiện viết trước khi sửa. **Kết quả 23/10:** 8 gom, 20 xả, 6 Nội gom (HAG, HSG, HT1,
NAB, NKG, TAL), 2 chưa đủ (MWG kín room từ 23/10, REE), 0 phiên thủng; tự doanh 56/100 mã có số chốt ngày 23/10.

### D77 — Nhãn « Nội gom / Nội xả » khi khối ngoại không có chiều (2026-10-24, người dùng chọn tên + ngưỡng)
**Vì sao:** nhãn chỉ Gom/Xả khi Ngoại ±1 → mã do dòng tiền nội dẫn luôn ra Trung tính. **Luật:** Ngoại = 0 (đủ dữ liệu, chưa
đạt ngưỡng), Giá-KL ±1, RVOL ≥ `signal.rvol_min` (1,3) và Tự doanh không ngược chiều → Nội gom / Nội xả (△ ▽, đếm riêng ở
cột ngành « Gom / xả » và câu kết luận). RVOL = KL khớp TB `cmf_window` phiên ÷ KL TB `rvol_base` (60) phiên liền trước,
KL đã nhân hệ số thưởng/cổ tức CP. **Ngưỡng:** không có chuẩn; 1,3 ≈ phân vị 75 RVOL VN100 10/2024–10/2026 (1,28; ~59 nghìn
mã-phiên). Bộ lọc KL là bắt buộc vì |CMF20| ≥ 0,05 đúng ở 84% mã-phiên. **Kết quả 22/10:** 3 Nội gom (HT1 ×2,13, NKG ×2,12,
TAL ×1,74), 0 Nội xả. **Giới hạn:** tên « Nội » do người dùng chọn — nhãn là áp lực giá-KL, KHÔNG phải số mua ròng trong nước
(= −(F + P)); giảm sàn không người mua (KOS) có KL thấp nên không ra Nội xả; chưa backtest (người dùng không làm backtest).

### D76 — CMF20 trên biên độ thực + cột « Độ rộng ngoại » ở bản đồ ngành (2026-10-24, người dùng đề xuất, duyệt « cái nào
đúng thì sửa »)
**CMF:** CMF gốc (StockCharts) chỉ dùng H/L trong phiên → bỏ sót khoảng nhảy giá; phiên trần/sàn trắng bên (H = L) không
xác định nên bị loại, quá 2 phiên thì phiếu Giá-KL ◌. Nay TRH = max(H, C_{t−1}), TRL = min(L, C_{t−1}) như True Range
(Wilder/ATR), cùng ý tưởng Twiggs Money Flow; vẫn cộng 20 phiên, ngưỡng ±0,05 giữ nguyên. Chỉ phiên đứng giá (cao = thấp
= giá phiên trước) bị loại. Dữ liệu 23/10: 3/100 nhãn đổi — KOS Chưa đủ → Trung tính (sàn trắng bên 21 phiên, CMF −1,00;
Ngoại 0 nên chưa thành Xả), PNJ Chưa đủ → Dấu hiệu xả (CMF −0,61), PAN Xả → Trung tính (CMF −0,056 → −0,025); 10 phiếu
Giá-KL đổi; |ΔCMF| trung vị 0,010. **Độ rộng:** `sector_table` thêm breadth_pos/breadth_n = số mã ngoại ròng > 0 / số mã
có số (mỗi mã 1 phiếu) để thấy ngành bị một mã trụ kéo hay cả ngành cùng chiều. **Không làm:** bối cảnh giá theo ATR
(so ret20 với ATR một phiên lệch khung thời gian; bối cảnh không đổi nhãn); nhãn « Nội gom/xả » chờ người dùng chốt
(cần ngưỡng đột biến KL — chưa có chuẩn; với luật F = 0 & Giá-KL ±1 & Tự doanh không ngược thì 33/100 mã sẽ có nhãn).

### D75 — Sắp xếp lại tab money: Thị trường → Ngành → Cổ phiếu → Chi tiết (2026-10-24, người dùng duyệt)
**Vì sao:** bảng ngành đứng cạnh thẻ của một mã, danh sách mã lại nằm dưới bản đồ nhiệt → nhóm và từng mã lẫn lộn; 4 ô
« Đọc thế nào? » chiếm chỗ. **Làm:** « Theo ngành » hết chiều ngang, 2 tab Tổng 20 phiên | Theo ngày (bản đồ nhiệt);
« Theo cổ phiếu »: danh sách trái, thẻ 5 giây phải, công tắc « Xem biểu đồ & chi tiết mã này » dưới thẻ; « Chi tiết mã »
hết chiều ngang, 3 tab Biểu đồ | Bảng phiếu | Phiên thỏa thuận. Hướng dẫn đọc chuyển vào dấu (?) cạnh tiêu đề. Người dùng
chọn GIỮ NGUYÊN mục trong nước suy ra, huy hiệu sự kiện (dù trùng thẻ/biểu đồ) và dòng trạng thái kỹ thuật.

### D74 — Biểu đồ giá & dòng tiền từng mã chuyển về tab "Dòng tiền ngành"; bỏ RSI (2026-10-24, người dùng chọn)
**Yêu cầu:** vào chi tiết từng mã thấy dòng tiền theo ngày thật trực quan; biểu đồ ở tab Định giá chuyển hẳn sang money;
bỏ RSI; MACD giữ là tầng tùy chọn; thêm bản đồ nhiệt Ngành × Ngày và dải 20 phiên trên thẻ mã.
**Làm:** `money_flow.ticker_history` (cùng pipeline với thẻ: clean_flows → flow_daily → GTGD điều chỉnh → cờ thỏa thuận →
chọn đường số; 2 năm, chỉ nạp khi mở chi tiết, cache theo khóa panel + mã) và `sector_daily` (R = Σ ngoại / Σ GTGD phiên-mã
hợp lệ theo ngày, chỉ chế độ Loại). Biểu đồ nhiều tầng chung trục ngày: Giá (nến, MA20/50, ◆ thỏa thuận lớn, ▲ GDKHQ) ·
Khối lượng khớp · Khối ngoại · Tự doanh (cột + lũy kế) · « Ai gom/xả » (3 đường lũy kế ngoại / tự doanh / trong nước suy
ra) · CMF20 · MACD (tùy chọn). Chế độ Loại chỉ vẽ khớp lệnh (thỏa thuận cực lớn như MCH 09/10 −9.641 tỷ làm méo trục —
xem bằng ◆ và bảng); Gồm chồng phần thỏa thuận. Lũy kế tính từ đầu khung, ngày thiếu số không cộng 0 giả. Khung 1T/3T/6T/
1N/2N (`money_flow_chart`). `tradingview_chart.py` rút còn hàm vẽ dùng chung; widget, loader giá và RSI đã xóa.
**Cập nhật cùng ngày (người dùng yêu cầu):** gộp CMF20 vào tầng « Ai gom/xả » — nền CMF20 trục trái, 3 đường lũy kế trục
phải, hai trục đối xứng quanh 0 để đường 0 trùng nhau. Mọi tiêu đề tầng có dấu (?), rê chuột vào hiện giải thích
(`money_flow_lessons.CHART_HELP`), đưa chuột ra thì ẩn. Khung mặc định 1N. App chuẩn hóa về một cổng 8506 (launcher,
`.streamlit/config.toml`, systemd VPS, tài liệu); VPS phải sửa Caddyfile `reverse_proxy 127.0.0.1:8506`.

### D73 — Tab money: bỏ bảng "Phiên ảnh hưởng lớn nhất", thêm cảnh báo ⚠ "Dồn 1 phiên" (2026-10-24, người dùng duyệt)
Bảng xếp top 10 phiên-mã theo |ngoại| + |tự doanh| (tỷ đồng) → chỉ lặp lại mã vốn hóa lớn, "Tỷ trọng" tính trên tổng cả
danh sách nên khó đọc; trùng "Mã chi phối" và huy hiệu thỏa thuận. Thay bằng huy hiệu theo TỪNG mã
(`money_flow.concentration_badge`): |ngoại ròng| phiên lớn nhất ≥ `money_flow.single_session_share` (0,5 — người dùng
duyệt) × Σ|ngoại ròng| từng phiên của cửa sổ, chế độ Loại (bỏ phiên thỏa thuận); bỏ qua khi phiên lớn nhất làm tròn
0,0 tỷ. Không đổi nhãn gom/xả. Dữ liệu 24/10: 3 mã (GVR, PHR, PNJ). Hàm `top_impact` phân tích vẫn giữ (có test),
chỉ bỏ hiển thị. Mọi tiêu đề cột tab money có dòng giải thích khi rê chuột (`money_flow_lessons.COLUMN_HELP`).

### D80 — Gộp tab "Định giá & dự phóng" + "So sánh CTCK" thành "Định giá & CTCK" (2026-10-26, người dùng chọn)
6 → 5 tab khi đã nạp mã: Báo cáo tài chính | **Định giá & CTCK** | Cổ tức & quyền mua | VN100 & tích sản | Dòng tiền ngành.
Tab gộp: giả định (expander) → kết quả định giá → so sánh giá mục tiêu CTCK ngay bên dưới (cùng trả lời "đáng giá bao
nhiêu"); so sánh vẫn ẩn khi `publication_allowed` = False. CSS phụ thuộc chỉ số tab sửa theo: ẩn khối định giá đầu trang
ở tab 3/4/5 (trước 4/5/6), nhãn đáy điện thoại BCTC · Định giá · Cổ tức · VN100 · money. Test CSS lấy chỉ số tab từ
chính `streamlit_app.py` để lần sau đổi tab mà quên CSS thì test đỏ.

### D81 — Vòng học hằng tuần: GĐ 1 nhật ký DeepSeek (2026-10-26, người dùng yêu cầu; kế hoạch docs/PLAN_LEARNING_LOOP.md)
Mỗi báo cáo DeepSeek mới (`verified_summary.generate_verified_summary_cached`, nhánh không dùng cache) ghi thêm
`knowledge/ai_reports/<YYYY-MM>/<MÃ>_<ngày>_<fp8>.md` + 1 dòng `index.jsonl` (`valuation/report/ai_journal.py`):
FV/giá/upside/khuyến nghị, nghi vấn dữ liệu, tổng hợp CTCK, luận điểm/rủi ro — ghi rõ là giả thuyết chưa kiểm chứng.
Idempotent theo fingerprint; 0 lời gọi API thêm; lỗi ghi file chỉ cảnh báo log (không chặn báo cáo đã trả phí).
Backfill 12 báo cáo cũ (cache không có FV/giá → để trống). Người dùng chọn: Claude chạy Chủ nhật trên cloud (routine,
môi trường "chứng khoán"), đọc dữ liệu học trên Google Drive (thư mục dự án đã đồng bộ Drive); cho phép tự đẩy riêng
dữ liệu học mỗi tuần. Nguyên tắc: Claude chỉ đề xuất có số đo, không tự sửa mô hình.
**Bổ sung D81 — routine cloud (2026-10-26):** routine `trig_01R7tohvvnWM5t1jiGx7odZo` (môi trường "chứng khoán",
Chủ nhật 20:00 VN = `0 13 * * 0` UTC, sonnet, chỉ connector Google_Drive — bỏ Claude_Docs/Claude_Code_Remote theo least
privilege), đang TẮT chờ webhook. Thử 3 lần: đọc Drive được (index.jsonl, .md); connector KHÔNG tạo được file ở bất kỳ
đâu (chỉ tạo được thư mục; `update_file` chỉ sửa metadata) → đề xuất gửi qua Discord webhook
`DISCORD_LEARNING_WEBHOOK` (người dùng tự đặt trong cài đặt môi trường cloud, Claude không chạm key) kèm nhãn
`[VN100-LEARNING]`; bot (`scripts/discord_bot.py` + `valuation/services/learning_inbox.py`) chỉ nhận tin webhook đúng
kênh + nhãn, chỉ lưu `<năm>-W<tuần>.md` → `knowledge/proposals/` và `LEARNINGS.md` (giữ bản cũ), UTF-8 ≤ 200 KB.
Còn lại sau thử: thư mục rỗng "VN100 - De xuat hang tuan" trong Drive của rosinante2037 (do lần thử tạo, xóa tay được).
**Bật D81 (2026-10-26 21:42):** webhook lấy từ `learning_webhook.env` (gitignored, người dùng tự dán; routine đọc qua Drive,
chỉ nhận URL `discord.com/api/webhooks/`, không in). Chạy thử đầu-cuối OK: Discord nhận → bot lưu
`knowledge/proposals/2026-W44.md`. Routine BẬT, lần chạy đầu Chủ nhật 01/11/2026 20:00 VN.

### D82 — Bản tóm tắt tuần cho vòng học (GĐ 2–4) + lỗi numpy 2.2.6 tự build trên Python 3.14 (2026-10-26)
`scripts/weekly_learning_digest.py` + `valuation/services/learning_digest.py` (không AI, chỉ đọc DB, ~4 phút) ghi
`knowledge/weekly/<tuần>.md` (~100 dòng) + `_valuation.csv`/`_flow_stats.csv`/`_summary.json`, nối `fv_history.csv`
(chạy lại cùng tuần thay, không nhân đôi) và đệm `flow_backtest_labels.csv` (chỉ tính tuần mới). Nội dung: chất lượng
định giá vs trung vị CTCK theo nhóm (so tuần trước), top lệch, nghi vấn DeepSeek, báo cáo CTCK mới 7 ngày, dòng tiền +
kiểm chứng nhãn tính lùi 91 tuần (as_of; trong mẫu < 01/04/2026 ≤ ngoài mẫu). Lịch: launchd Chủ nhật 18:00
(`deploy/launchd/…weekly-digest.plist`, người dùng tự nạp) / systemd `vn100-weekly-digest.timer` (setup_vps.sh).
**Kết quả kiểm chứng dòng tiền (26/10):** tỷ lệ lợi nhuận 20 phiên vượt trung vị VN100 ≈ 50% ở mọi nhãn; ngoài mẫu
"gom" 54,7%, "xa" 55,0% — nhãn hiện chưa có giá trị dự báo lợi nhuận tương đối (mô tả, không phải tín hiệu).
**Lỗi môi trường (gốc rễ xác minh 26/10, đã sửa):** KHÔNG phải pandas. `~/.venv` (Python 3.14.5) chạy numpy 2.2.6 tự
build từ source (nhánh 2.2 không có wheel cp314), thiếu bản sửa Python 3.14 của numpy (PR #28748, có từ 2.3): numpy coi
biến cục bộ là mảng tạm khi ≥ 256 KiB (32.768 phần tử int64/float64) và ghi kết quả đè lên nó — `y = x + 1.0` trong hàm
làm đổi `x`. Trong pandas trúng `_Unstacker` → `pivot`/`pivot_table`/`unstack`/`crosstab` cho nhãn index SAI/lặp (giá
trị ô vẫn đúng); 30 phép pandas khác (stack, melt, groupby, rolling, rank, merge…) đúng. Python 3.12 + numpy 2.2.6
(wheel, như VPS) và Python 3.14 + numpy 2.3.5/2.5.4 đều đúng. Kẹt ở 2.2.6 vì mọi `vnstock` 4.x cần `vnstock-ezchart>=1.0.2`
ghim `numpy<2.3` → không khai `numpy>=2.3` trong requirements được (ezchart vốn không import được vì thiếu `squarify`,
dự án không dùng). **Sửa:** `pip install --no-deps numpy==2.3.5` trong `~/.venv` (`pip check` báo xung đột ezchart —
chấp nhận); chốt chặn `valuation/__init__.py::_numpy_keeps_locals` → RuntimeError khi import nếu numpy còn lỗi (vd cập
nhật vnstock/installer hạ lại về 2.2.6, hoặc máy portable dùng Python 3.14); test `tests/test_numpy_env.py`
(pivot/pivot_table/unstack 544×100). **Ảnh hưởng số liệu:** so vi sai trên bản sao DB giữa numpy 2.2.6 và 2.5.4 — dòng
tiền, nhãn, `close_matrix`, `label_stats`, dữ liệu xếp hạng giống hệt → kết quả ở trên không bị ảnh hưởng. Chỉ
`market_overview.load_market_data` sai khi `history_days` ≳ 475 (thử 800: ngày cuối thành 27/08/2024); hiện 400 ngày ≈
273×100 = 27.300 ô. Bộ test 1139 passed như nhau trên 2.2.6/2.3.5/2.5.4 (5 lỗi `test_discord_bot_gate` có sẵn từ trước).
`close_matrix` giữ cách dựng numpy. Trùng chỉ mục `load_flow_panel(days≈700)`: thử lại 827 ngày không tái hiện (index
duy nhất trên cả hai bản numpy); vẫn giữ `reset_index` phòng hờ.

### D83 — Thực hiện 3 đề xuất vòng học W44 (2026-10-27, người dùng duyệt cả 3)
Nguyên tắc đo trước, sửa sau. **#1 tín dụng ngân hàng:** bác bỏ — 4 NH bị kẹp (EIB sàn; HDB, MBB, VPB trần 25%), nới
trần 30%/bỏ trần đổi FV ≤ 4,5% (HDB), HDB/MBB đã cao hơn CTCK → giữ dải 5–25%, không sửa code. **#2 BCTC BSI & dòng
tiền:** bác bỏ — CFO+CFI+CFF = Δ tiền 2022–2025 ở BSI, CTD, PC1, CII (PC1 lệch = tỷ giá); BSI dùng mô hình P/B CTCK, không
lỗi; lỗi DeepSeek là của báo cáo cũ 30/08. **#3 trình bày:** sửa `verified_summary._compact_payload`: mỗi dòng BCTC có
`period` ("TTM (4 quý gần nhất, năm …)" / "FY…") + `is_actual`; thêm `quality_metrics_period`, `metric_definitions`
(roe, debt_to_equity, roic + lưu ý khác kỳ với mã cùng ngành), `metric_period` cho mã cùng ngành. Gốc "hai ROE" (MWG
0,2887 vs 0,2331) = TTM vs FY, cùng định nghĩa. Fingerprint bộ đệm DeepSeek đổi (dữ liệu gửi đổi) — chỉ tốn phí khi bấm.
Đo thêm: trung vị |lệch CTCK| 16,9% (1 CTCK) / 18,7% (2) / 11,3% (≥ 3). Kết quả ghi `knowledge/LEARNINGS.md` để routine
tuần không đề xuất lại #1, #2.

### D84 — Kiểm tra cổ tức/quyền mua cả rổ mỗi sáng (2026-10-28, người dùng chọn "Giá + sự kiện 100 mã")
**Gốc:** `corporate_actions` chỉ được làm mới khi có người mở mã trên app (TTL 24h) → TCB cổ tức CP 50% (GDKHQ 29/10)
chưa có trong DB. VNM: VCI chưa có thông báo mới — người dùng chọn chờ VCI. **Sửa:** `daily_report.refresh_all_corporate_actions`
chạy trong `refresh_market()` (sau vĩ mô, dưới DATA_LOCK) cho 100 mã; báo cáo sáng thêm mục "📅 Cổ tức / quyền mua 7
ngày tới" + cảnh báo mã chưa kiểm tra được. Config `daily_report.corporate_actions_refresh`, `ca_pause_seconds`,
`ca_upcoming_days`. **Lỗi tự gây, đã sửa cùng ngày:** `FRESH` (đã kiểm tra trong TTL / lỗi < 30 phút) bị tính là lỗi và
lần thử lại không `force` nên luôn bị chặn → thử lại có `force=True`, `FRESH` không phải lỗi (test tái hiện trước).
**Đo 28/10:** nghỉ 1s → 24/100 timeout iq.vietcap (nửa sau lượt); thử lại nghỉ 2s → còn 5; 6s → 0 → `ca_pause_seconds`
3,0 (báo cáo sáng chậm thêm ~5–8 phút). Kết quả: 100/100 OK, cập nhật thêm 4 sự kiện, mới có PC1 cổ tức CP 15% GDKHQ
04/11. ANV hai dòng cùng ngày 29/10 là hai đợt khác nhau (đợt 2/2025 + đợt 1/2026, mỗi đợt 500đ), không trùng. Mã
BROKER_SYNTH (PC1): `shares_used_mn` cố định nên giá trị vốn không đổi, FV/cp tự pha loãng khi engine nhận số cổ phiếu
sau GDKHQ. **Phát hiện kèm:** job launchd `flow-daily` chạy ở bản sao `/Users/macos/antigravity-vn100` (không phải bản
Drive này) và lỗi FlowRateLimited 27/10 → `flow_daily` bản Drive dừng ở 23/10; hai bản dự án lệch nhau — đang so sánh
để gộp (người dùng duyệt "Claude so sánh rồi đề xuất").
**Bổ sung 28/10 — bản chính:** người dùng chốt bản `/Users/macos/antigravity-vn100` là bản chính (mọi job launchd
đã chạy ở đây từ 26/10), bản Google Drive không đụng tới nữa. Đã chép sang bản máy phần việc 27–28/10 chỉ có ở bản Drive
(D83, D84, chốt chặn numpy, PROGRESS, LEARNINGS; bản cũ lưu ở `backups/truoc_gop_tu_drive_20261028/`); phần giao diện
đang sửa dở ở bản máy (views, streamlit_app) giữ nguyên. DB bản máy thiếu TCB 50% → làm mới lại trên bản máy.

### D85 — Vòng học đọc thư mục Drive riêng `vn100_knowledge` (2026-10-28, người dùng chọn "Thư mục Drive riêng")
**Gốc:** bản chính chuyển về `/Users/macos/antigravity-vn100` (ngoài Google Drive); routine cloud Chủ nhật vẫn đọc
`antigravity-vn100/knowledge/` trên Drive → từ 01/11 sẽ đọc dữ liệu cũ. **Sửa:** `learning_digest.mirror_knowledge(src,
dst)` chép `knowledge/` (chỉ .md/.csv/.jsonl/.json, bỏ file ẩn, bỏ file không đổi, không xóa ở đích) sang
`learning.knowledge_mirror_dir` = `…/chứng khoán định giá/vn100_knowledge/`; `scripts/weekly_learning_digest.py` gọi sau
khi ghi bản tóm tắt (Chủ nhật 18:00); máy không có thư mục cha (VPS) → bỏ qua, có in ra. Đã chép lần đầu 21 file.
Routine `trig_01R7tohvvnWM5t1jiGx7odZo` đổi nguồn sang `vn100_knowledge` (cấm đọc bản cũ); webhook vẫn lấy từ
`antigravity-vn100/learning_webhook.env` — **xóa bản Drive cũ thì vòng học mất webhook**. Test
`test_mirror_knowledge_copies_only_text_and_skips_unchanged`.

### D86 — CORPORATE_ACTION_UNDATED chỉ cảnh báo, không chặn xếp hạng (2026-10-30, người dùng yêu cầu)
- Bỏ cờ khỏi `DATA_FLAGS_EXTRA` (`valuation/views/vn100_ranking.py`): mã có cổ tức CP/thưởng thiếu
  GDKHQ vẫn được xếp hạng; cờ vẫn hiện mức cảnh báo ở tab định giá.
- Rủi ro chấp nhận: nếu sự kiện đã GDKHQ mà chưa có override số cp, giá trị/cp có thể phóng đại theo
  tỷ lệ chia (vd TCB 50%, PC1 15%). Vẫn nên thêm override VSDC vào `config/corporate_actions.yaml`.

### D87 — Mở/đổi mã trên app tự tải mới dữ liệu mã đó (2026-10-30, người dùng yêu cầu)
- `render_select_ticker` tự chạy đúng luồng nút "Tải mới <mã>" (giá + BCTC incremental, báo cáo CTCK)
  một lần cho mỗi mã trong phiên trình duyệt (`_claim_auto_refresh`, đánh dấu trước khi tải để lỗi mạng
  không lặp). Sự kiện quyền (số cp) vẫn làm mới nền như trước. Đổi mã mất thêm ~10–20 giây.

### D88 — Dòng tiền cập nhật đầu phiên + theo nút "Quét VN100" (2026-11-03, người dùng yêu cầu)
- **Lỗi:** tab Dòng tiền dừng ở 30/10. Job 18:00 ngày 02/11 kéo VCI nhưng nguồn chưa công bố phiên 02/11
  (13:00 hôm sau đã có) → luôn trễ 1 phiên; thêm lỗi vnai `threading` UnboundLocalError mất ~4 mã/lượt
  và FlowRateLimited một số tối.
- **Sửa:** (1) lịch flow-daily 08:30 T2–T6 (`deploy/launchd`, `deploy/systemd`); (2) `update_flow_daily.run`
  thử lại 1 lần mỗi mã lỗi không chí mạng (bug vnai reset bộ đếm trước khi lỗi nên lần 2 qua);
  (3) nút "Quét VN100" chạy thêm `scripts/update_flow_daily.py` sau giá/BCTC, kết quả hiện ở dòng trạng thái.

### D89 — Tin công bố doanh nghiệp trong tab Cổ tức & quyền mua (2026-11-04, người dùng chọn)
- **Gốc:** lịch quyền lấy từ VCI events vào chậm hơn tin công bố (FPT tạm ứng cổ tức 1.000 đ/cp, chốt
  30/11, trả 10/12 — HOSE đăng 28/10 — chưa có trong lịch ngày 04/11). Không cào web từng công ty
  (100 cấu trúc, dễ hỏng, phải mở allowlist từng domain); dùng VCI news `mode="detail"` (tin sàn HOSE/HNX
  kèm link PDF chính thức + tin báo chí).
- **Làm:** `valuation/ingest/company_disclosures.py` tải 90 ngày/30 tin, cache JSON `.disclosures/<MÃ>.json`
  TTL 24h, lỗi nguồn giữ bản cũ và chờ 30 phút mới thử lại; tải nền cùng lượt sự kiện quyền + nút "Cập nhật
  sự kiện". `valuation/analysis/company_disclosures.py` phân loại theo từ khóa tiêu đề (người dùng chọn luật
  cố định, không AI), rút số (đ/cp, tỷ lệ, ngày chốt, ngày trả) ghi rõ "máy đọc, đối chiếu bản gốc".
  Tab hiện danh sách bấm mở (`<details>`); tin báo chí chỉ hiện 400 ký tự đầu + link (bản quyền).
- **Cảnh báo (người dùng chọn "hiện cảnh báo", không tự ghi DB):** tin cổ tức tiền/quyền mua ≤45 ngày,
  ngày chốt chưa qua, mà lịch quyền chưa có sự kiện khớp → dòng cảnh báo vàng dưới "Lần chia gần nhất".
- Không đi vào số định giá. Test `tests/test_company_disclosures.py`.

### D90 — Biểu đồ dòng tiền kiểu TradingView bằng Lightweight Charts (2026-11-04, người dùng chọn)
- Thay Plotly ở tab Dòng tiền (chi tiết mã) bằng TradingView Lightweight Charts **v5.2.1** (Apache-2.0),
  file `valuation/views/assets/vendor/lightweight-charts.standalone.production.js` tải từ npm, đã khớp
  sha512 của registry; nhúng thẳng vào HTML nên không gọi CDN lúc chạy. Không thêm gói Python.
- Giữ đủ tầng/dữ liệu cũ: nến + MA20/MA50, "TT" thỏa thuận lớn, mũi tên GDKHQ; khối lượng (+ thỏa thuận
  tím ở chế độ Gồm); khối ngoại/tự doanh ròng (trục trái) + lũy kế (trục phải); CMF20 nền xanh/đỏ +
  3 đường lũy kế (0 hai trục trùng nhau); MACD. Thỏa thuận xếp chồng giả lập barmode="relative"
  (`stacked_deal`). Chú thích từng tầng + giá trị theo con trỏ, dấu (?) giải thích như bản cũ.
- Quay lại Plotly: `money_flow_chart.engine: plotly`. Test `tests/test_lw_chart.py`.

### D91 — Volume profile trên biểu đồ dòng tiền (2026-11-04, người dùng yêu cầu, mặc định tắt)
- `lw_chart.volume_profile`: 24 hàng giá trên khung đang chọn; KL khớp mỗi phiên rải đều trên [thấp, cao];
  nến tăng = xanh, nến giảm = vàng (xấp xỉ từ nến ngày, không có dữ liệu khung nhỏ); POC = hàng lớn nhất;
  vùng giá trị 70% mở rộng từ POC thêm hàng kề lớn hơn. Vẽ bằng primitive Lightweight Charts dưới nến;
  đường POC/VAH/VAL + số dưới biểu đồ. Cố định theo khung, zoom không tính lại. Config
  `money_flow_chart.volume_profile`. Test tính tay trong `tests/test_lw_chart.py`.

### D92 — "Tải mới" một mã: tải nhẹ + song song; dọn thư mục dự án (2026-11-04, người dùng chọn)
- **Đo trước khi sửa (bản sao DB):** mỗi lượt tự tải khi mở/đổi mã 8–13 s, chạy tuần tự ~8 lời gọi mạng:
  giá, khối ngoại, tự doanh, BCTC BS/IS/CF (mỗi lời gọi `Finance(get_all=True)` kéo lại toàn bộ lịch sử,
  cộng ghi DB ≈ 5 s), 2 nguồn CTCK; thêm ~6–8 s import vnstock/vnai ở lượt đầu mỗi tiến trình.
- **Làm:** `run_ingest(..., parallel=True)` gửi mọi lời gọi mạng cùng lúc qua `ThreadPoolExecutor`, ghi DB vẫn
  tuần tự như cũ (kết quả y hệt chạy tuần tự — test). Nút/tự tải trong `select_ticker.py` chạy `run_ingest` song
  song với các nguồn CTCK. Tự tải khi mở mã chỉ kéo BCTC khi `financials_due`: DB chưa có quý gần nhất đã kết
  thúc (`latest_ended_quarter`); bấm "Tải mới" luôn kéo đủ. Bản soát xét/kiểm toán sửa quý cũ đến qua nút này
  và đợt quét VN100. Đợt quét VN100 giữ tuần tự (`parallel=False`) để không vượt 60 request/phút của vnai
  (vượt → ngủ 65 s; đã gặp khi đo dồn dập).
- **Kết quả:** tự tải 1,2–4,5 s (cũ 9,5–12,9 s); bấm nút 5–6 s; mở app tới lúc ra giá mục tiêu (server ấm,
  MBB) 7,5 s so với 12,0 s.
- **Dọn đĩa (người dùng chọn):** `venv/`, `.venv/` (app/launchd dùng `~/.venv`), `dist/`, `build/` chuyển vào
  Thùng rác (`~/.Trash/vn100-*-20261104`); `backups/` dời sang `~/vn100_backups` (17 bản). Thư mục 5,6 GB →
  931 MB. Bản clone GitHub vốn chỉ ~145 MB.
- Test: `tests/test_ingest.py::test_latest_ended_quarter_and_financials_due`,
  `::test_run_ingest_parallel_fetches_concurrently_with_same_result`.

### D93 — Job dòng tiền: chờ rồi thử lại khi vượt hạn mức; giữ lịch 18:00 (2026-11-04, người dùng chọn)
- **Gốc (bản đồ nhiệt Ngành × Ngày dừng ở 02/11):** `flow_daily` chỉ có tới 02/11. Lượt 18:00 ngày 03/11 chạy
  đủ 100 mã nhưng VCI chưa có số của chính ngày 03/11 (mỗi mã 6 dòng, tới 02/11). Lượt 18:11 ngày 04/11 vượt
  hạn mức vnai ngay ở mã đầu (ACB) → `FlowRateLimited` dừng cả job (D73), mất trọn ngày. Thử lúc 21:50 ngày
  04/11: nguồn đã có 03/11, vẫn chưa có 04/11. Đã chạy tay job lúc 21:52 để nạp 03/11.
- **Làm:** `scripts/update_flow_daily.py::fetch_with_wait` — vượt hạn mức thì chờ
  `flow_ingest.rate_limit_wait_sec` (65 s) rồi thử lại chính mã đó, tối đa `rate_limit_retries` (2) lần; hết
  lượt vẫn lỗi mới dừng cả job, mã thoát 5 như D73. Không đặt trong `FlowClient` vì tab Cổ tức (D89) dùng chung
  client và có cơ chế chờ 30 phút riêng.
- **Lịch:** launchd trên máy đang nạp plist cũ 18:00 thứ 2–6; plist trong repo là 08:30 (D88). Người dùng chọn
  giữ 18:00, nên bản đồ nhiệt thường trễ 1 phiên (số khối ngoại của phiên T có vào sáng T+1, lượt 18:00 ngày T+1
  mới lấy được).
- Test: `tests/test_flow_ingest.py::test_rate_limit_waits_then_retries_same_ticker`.

### D94 — vnstock thế hệ 4 ngừng xác thực: vá lỗi thiếu giá, dựng môi trường thế hệ 6 (2026-11-11, người dùng chọn)
- **Kiểm tra:** cài đặt `vnstock` 4.0.7, `vnstock_data` 3.2.8, `vnai` 2.5.9, `vnii` 0.2.5. Trang lịch sử phiên bản
  chính thức ghi thế hệ 4 ngừng xác thực từ 10/11/2026 và đã gỡ đường cài; index dòng cũ không còn bản cho Python
  3.14. Thử thật 11/11: giá (VCI) và khối ngoại (`vnstock_data`) vẫn tải được.
- **Thiếu giá mỗi sáng:** lỗi `vnai` `UnboundLocalError ... 'threading'` làm 2–3 mã/ngày không có giá (10/11: MCH,
  VPI). `vnstock_client._retry_vnai_threading_bug` gọi lại ngay đúng 1 lần (như job dòng tiền D88; chỉ lỗi có
  `'threading'`, lỗi khác vẫn nổi lên). Đã nạp bù MCH, VPI. Test `tests/test_vnstock_client_config.py`.
- **Thế hệ 6 (người dùng chọn chuyển ngay):** `~/.venv_6x` riêng với `vnstock` 6.0.0 + `vnstock-oapi` 0.1.1 (tài khoản
  đã nhận, hạn 14/04/2027). Không có VCI; FHSC bắt buộc cho BCTC và tự doanh, chỉ phục vụ 06:00–21:00. Chưa đổi code
  đọc dữ liệu: kế hoạch từng lát + đối chiếu số trong `docs/PLAN_VNSTOCK_V6.md`, chờ người dùng đăng ký khóa FHSC.

### D93 — Báo cáo PDF "20 cổ phiếu tích sản 1–3 năm" (2026-11-11, người dùng chọn)
- **Bối cảnh:** bộ lọc nghiêm ngặt của xếp hạng tích sản không cho mã nào "đạt chuẩn" (thiếu ngày công
  bố BCTC, chưa có hồ sơ quản trị kiểm chứng). Người dùng chọn: điểm tổng hợp + độ tin cậy, chỉ VN100,
  một bảng chung 20 mã.
- **Cách làm:** `scripts/collect_top_picks.py` (chỉ đọc DB) dựng lại hồ sơ 100 mã bằng `build_ranking_row`
  + `rank_companies`; flow_ratio thiếu thì dùng ngoại ròng khớp lệnh/GTGD 20 phiên (flow_daily).
  `valuation/report/top_picks.py`: điểm = trung bình 2 hồ sơ chuẩn hóa theo độ phủ; loại lỗi/cờ chặn/
  MATERIAL_EVENT_HOLD/upside ≤0 hoặc >100%/thanh khoản thấp; tối đa 4 mã/ngành. Độ tin cậy A/B/C từ
  4 tiêu chí (lệch đồng thuận ≤20%, ≥3 CTCK, không cờ warning trừ SOURCE_AUDIT_PARTIAL, kịch bản
  xấu–tốt ≤40%; P/E, EV/EBITDA một kịch bản không tính đạt). Giá tham chiếu thận trọng = min(mô hình,
  trung vị CTCK); vùng gom = ×(1 − min_mos hồ sơ tăng trưởng 15%).
- `scripts/build_top_picks_pdf.py` → `reports_pdf/top20/Top20_tich_san_VN100_<ngày>.pdf` (22 trang).
  Nhận định định tính ở `reports_pdf/top20/notes_<ngày>.yaml` (không chứa số định giá). Không phải
  khuyến nghị đầu tư. Test `tests/test_top_picks.py`.

### D95 — Chuyển từng phần sang FHSC: job giá và Quét VN100 tải trước qua vnstock thế hệ 6 (2026-11-12, người dùng chọn)
- **Cách làm (người dùng chọn "chuyển từng phần"):** thế hệ 6 không cài chung với vnstock 4.x của app (cùng tên gói),
  nên `scripts/fhsc_fetch.py` chạy bằng python của `~/.venv_6x`, chỉ TẢI giá/khối ngoại/tự doanh và in JSON; ghi DB
  vẫn do code hiện tại ở `~/.venv` (không cài thêm gói, không đụng pandas 3). `valuation/ingest/fhsc_bridge.py`
  gọi script MỘT lần cho cả rổ (khởi động vnstock 6 mất ~4–5 s), đưa về đúng dạng VCI (giá: ngày không múi giờ,
  nghìn đồng, chỉ nhận hồ sơ `v5`; dòng tiền: date), giữ trong bộ đệm có hạn (`cache_ttl_sec`).
  `vnstock_client.get_historical_prices` và `market_client.fetch_foreign_flow/proprietary_flow` lấy bộ đệm trước,
  không có thì VCI như cũ. `run_ingest` ghi `source` (fhsc/vci) vào kết quả — bảng giá chưa có cột nguồn (đổi
  schema cần duyệt riêng).
- **Ai dùng:** job giá 07:50 (`daily_report.refresh_market`, 100 mã + VNINDEX) và Quét VN100 (`weekly_updater`, gồm
  khối ngoại + tự doanh). Báo cáo sáng có dòng "Nguồn giá: FHSC x mã, VCI y mã (lý do)" khi phải dùng VCI. Nút "Tải
  mới"/mở mã vẫn VCI (1–2 s; qua FHSC sẽ thành ~6–8 s vì khởi động tiến trình) cho tới khi dòng 4.x ngừng hẳn.
  Job `flow_daily` vẫn VCI: cần tách khớp/thỏa thuận mà FHSC chưa kiểm (S2).
- **Chặn:** ngoài 06:00–21:00, thiếu `~/.venv_6x`, `fhsc.jobs: false` hoặc `VN100_FHSC_JOBS=0` (conftest đặt cho mọi
  test) → không gọi FHSC. Giãn nhịp 1,4 s/lời gọi, 429 chờ 30 s thử lại 2 lần; lỗi từng mã → mã đó đi VCI.
- Test `tests/test_fhsc_bridge.py`. Chạy thật đầu tiên: job 07:50 ngày 13/11/2026 (đêm 12/11 FHSC ngoài giờ).

### D96 — VPS chạy thay máy Mac: giao diện + lịch job + bot trong Docker (2026-11-18, người dùng duyệt)
- **Vì sao:** máy Mac sẽ không mở thường xuyên. VPS `vps-web` (192.168.1.201, Docker `/srv/apps/vn100`, web
  `chungkhoang.btinvest.vn` có mật khẩu) trước đó chỉ chạy giao diện xem, không có vnstock.
- **Làm:** image thêm vnstock 4 bản miễn phí chép từ Mac (Python thuần; index cũ đã gỡ) + vnstock 6 trong
  `/home/app/.venv_6x` (FHSC). Thêm `vn100-worker` (`scheduler.py`, thư viện chuẩn: 07:50 báo cáo sáng T2–T6, 08:30
  dòng tiền T2–T6, CN 18:00 tóm tắt tuần; chạy bù ≤ 3 giờ; trạng thái `/data/scheduler_state.json`) và `vn100-bot`.
  `.env` đầy đủ chép qua SSH (chmod 600). DB trên VPS là bản chính (`DB_SYNC_FROM_REPO=0`); trạng thái lúc chạy
  (`.vn100_ranking` gồm bộ đệm sponsor, `.daily_report`, …) chép từ Mac vào volume riêng. launchd trên Mac:
  `launchctl bootout` + `disable` (bật lại: `launchctl enable gui/$UID/vn.antigravity-vn100.<tên>`).
- **Lỗi lộ ra & sửa:** `requirements.txt` thiếu `discord-webhook`, `pypdf` (chỉ cài tay trên Mac). VPS 3,9 GB không
  swap treo cứng 18/11 ~00:08 khi chạy thử container cạnh app (mongod coin-check bị OOM từ 23:47) → giới hạn RAM web
  1 GB / worker 640 MB / bot 256 MB, đề nghị chủ máy thêm swap. Bản sao cấu hình: `deploy/docker/`.
- **Còn chờ:** vnstock 6 trên VPS chưa đăng nhập được (tài khoản golden đủ 2 thiết bị Linux) → FHSC chưa dùng được,
  giá/BCTC đi VCI bằng vnstock 4; dòng tiền chờ S2.


### D97 — Khối ngoại/tự doanh gộp từ FHSC vào prices_daily; tắt job flow-daily (2026-11-18, người dùng « làm hết »)
- **Vì sao:** khối ngoại/tự doanh DỪNG từ 12/11: `flow_daily` (khớp/thỏa thuận tách, D73) lấy qua gói tài trợ
  `vnstock_data` đã bị khóa; cột dòng tiền `prices_daily` cũng chỉ được ghi qua gói đó (trừ Quét VN100, D95).
- **Đo (S2, 18/11 07:33, 100 mã × 21 phiên 13/10–10/11):** FHSC chỉ có số GỘP — cả `columns="all"` và JSON gốc
  (`trading/foreign/history`, `proprietary/history`, cả endpoint phiên gần nhất) để `matched`/`put_through` = null.
  So với VCI khớp + thỏa thuận: khối ngoại 2100/2100 ô lệch ≤ 0,1% GTGD (trung vị 0); tự doanh 100% ô có số ở cả hai.
  So với VCI chỉ khớp lệnh: 96,1% (khác ở 91 ô có thỏa thuận). Tự doanh FHSC trống trọn 5 phiên (14/10, 15/10, 22/10,
  26/10, 28/10; 61–76 mã/phiên) nhưng có 546 ô VCI thiếu → độ phủ FHSC ≥ VCI; ô trống giữ NULL (= thiếu, D73).
  `trading/history` (GTGD khớp/thỏa thuận cả thị trường) báo MCH 09/10 thỏa thuận = 0 dù khối ngoại bán 64 triệu cp →
  không dùng để tách khớp/thỏa thuận khối ngoại.
- **Làm:** báo cáo sáng 07:50 tải trước `["prices", "foreign", "prop"]` qua cầu nối FHSC và ghi cột dòng tiền
  `prices_daily` (cùng định nghĩa gộp; `upsert_market_flows` coalesce, không đụng OHLCV) — chỉ khi FHSC chạy (ngoài
  giờ 06:00–21:00 thì bỏ, không gọi gói đã khóa); VNINDEX không có dòng tiền. Tab money tự dùng đường A (suy từ
  `prices_daily`, cờ thỏa thuận cận dưới) cho phiên không có `flow_daily` — không đổi công thức. Job `flow-daily`
  08:30 tắt trong `scheduler.py` VPS. `scripts/backfill_fhsc_flows.py <ngày>` vá một lần các phiên 13/11–17/11.
  Test: `tests/test_daily_report.py` (2 ca: có FHSC → tải dòng tiền trừ VNINDEX; ngoài giờ → không).
- **Lỗi lộ ra khi vá (18/11 12:45) & sửa:** FHSC trả khối ngoại phiên ĐANG giao dịch → vá ghi 98 dòng phiên 18/11 chỉ có
  dòng tiền tạm (tab money sẽ coi là phiên mới nhất). Đã trả phiên 18/11 về đúng bản sao lưu
  `/data/backup-before-flows-20261118.db` (xóa 98 dòng tạm, xóa trắng dòng tiền 2 dòng có sẵn; so khớp = True).
  Sửa gốc: `fhsc_bridge.prefetch` bỏ khối ngoại/tự doanh của phiên hôm nay (lượt sáng hôm sau lấy nhờ đệm 5 ngày);
  áp cho báo cáo sáng, Quét VN100, script vá. Test `test_prefetch_drops_flows_of_unfinished_session`.
  Kết quả vá 13–17/11: khối ngoại 100/100 mã cả 3 phiên; tự doanh 16, 17/11 100/100, 13/11 3/100 (FHSC trống trọn phiên).
- **Giới hạn:** từ 13/11 chế độ « Loại thỏa thuận » chỉ còn đường A (cận dưới, gắn cờ), không còn số khớp lệnh chính
  xác. Muốn lại số tách: cần nguồn có khớp/thỏa thuận theo nhà đầu tư (chờ người dùng chọn).

### D98 — Đăng nhập chung *.btinvest.vn bằng tài khoản coin, bỏ tài khoản admin dùng chung (2026-11-18, người dùng chọn)
- **Vì sao:** người dùng muốn trang đăng nhập riêng + tạo được tài khoản; coin.btinvest.vn (cùng VPS) đã có đăng ký/đăng nhập.
- **Người dùng chọn:** mọi tài khoản coin (đã xác minh email) vào được cả VN100 và chứng quyền; cho sửa coin-check để
  đăng nhập một lần dùng mọi trang.
- **Làm:** Caddy `forward_auth` hỏi coin `/api/v1/auth/me`; trang `/dang-nhap` chung; coin-check đặt cookie
  `Domain=.btinvest.vn` (biến `AUTH_COOKIE_DOMAIN`), nâng giới hạn `/me` 60 → 600 lượt/phút/IP (bị 429 khi thử).
  Chi tiết, rủi ro, quay lui: `deploy/dang-nhap/README.md`. Kiểm: chưa đăng nhập → 302 `/dang-nhap?next=…`, 30 lượt liên
  tiếp không 429, trang đăng nhập hiển thị đúng ở cỡ điện thoại. Chưa kiểm: đăng nhập thật (cần tài khoản của người dùng).
- **Rủi ro:** API coin sập → hai trang không vào được; ai tạo tài khoản coin cũng sửa được danh mục chứng quyền, dùng AI.
- **Đổi tên (18/11, người dùng yêu cầu):** tên chính VN100 là `chungkhoan.btinvest.vn` (đúng chính tả); `chungkhoang.btinvest.vn` (tên dùng 17–18/11) chuyển hướng 301 sang; `.deploy` HEALTH_URL đổi theo.

### D99 — FV của snapshot quy về thang giá hiện tại khi có cổ tức/chia tách sau đợt định giá; nạp TPCP_10Y (2026-11-22, người dùng « sửa cả hai »)
- **Lỗi 1 (thang giá):** báo cáo sáng 20/11 xếp TCB đầu danh sách với upside +99,6%. Đợt 20261027T000935 định giá TCB
  FV 41.121 với giá 33.800 (26/10, trước GDKHQ thưởng 50% ngày 29/10); nguồn giá sau đó điều chỉnh hồi tố cả chuỗi
  (DB nay ghi 26/10 = 22.530) nên `ranking_table` so FV thang cũ với giá 20.600 thang mới. Đúng thang: +33,1%.
  Cùng lỗi ở mọi chỗ dùng `ranking_table` (báo cáo sáng, tab VN100, tab money, tab cổ tức, trợ lý bot).
- **Sửa gốc:** `fv_scale_factor` — k = giá DB tại `price_date` của dòng snapshot ÷ `price` snapshot đã dùng; FV × k
  trước khi tính upside. Dùng chính điều chỉnh hồi tố của nguồn giá nên tự đúng với chia tách/thưởng/cổ tức CP
  (TCB k = 0,6666 ≈ 1/1,5; PC1 0,8694 ≈ 1/1,15); cổ tức tiền theo quy ước điều chỉnh tỷ lệ của nguồn (NT2 cổ tức
  1.000 đ: FV × 0,9586 = 37.684, so với trừ thẳng 1.000 đ = 38.312, lệch 1,6%). |k − 1| ≤ 0,5% coi cùng thang (D94);
  k > 1 + 0,5% hoặc k < 0,2 → không quy đổi, ghi chú « Thang giá lệch đợt định giá … cần rà soát » và loại khỏi danh
  sách (cờ, không kẹp im lặng); thiếu giá ngày đó → giữ cách tính cũ. Ngưỡng: `fv_rescale` trong
  `config/investment_ranking.yaml`. Báo cáo sáng ghi « FV quy đổi ×k do cổ tức/chia tách » cạnh mã được quy đổi; tab
  VN100 ghi danh sách mã quy đổi dưới tiêu đề. Không đổi mô hình định giá, chỉ đổi cách so FV cũ với giá mới.
- **Kiểm:** test tính tay (thưởng 50%: FV 30.000 / giá cũ 15.000 / giá DB 10.000 / giá nay 12.500 → +60%, lỗi cũ +140%),
  ca TCB số thật (+33,06%), ca lệch thang, ca thiếu giá, `snapshot_closes` trên SQLite trong bộ nhớ, dòng báo cáo sáng.
  Chạy thử trên DB + snapshot thật của VPS (container tạm, chỉ đọc, không mạng): 10 mã được quy đổi (NT2, TCB, BMP,
  SIP, BAF, VNM, PC1, ANV, GVR, VPI), 0 mã lệch thang; top 5 mới FPT, TPB, GEX, MBB, DBC (TCB, NT2 ra).
- **Lỗi 2 (TPCP_10Y cũ):** chuỗi dừng ở 19/10 (Mac nạp từ investing.com; sau khi chuyển sang VPS 18/11 không job nào
  nạp). Ngày 23/11 sẽ cũ 35 ngày > 30 → cờ chặn `STALE_MACRO_RF` cho cả 100 mã ở đợt xếp hạng 08:00 → danh sách nghiên
  cứu rỗng, AI bị bỏ qua. Đã nạp 22 điểm 22/10–20/11 (investing.com, 20/11 = 4,568%; đối chiếu worldgovernmentbonds
  4,568% cùng ngày) bằng `scripts.ingest_tpcp_10y` trên DB VPS, sau khi sao lưu `/data/backup-before-tpcp-20261122.db`;
  chạy 2 lần, 2629 → 2651 điểm (idempotent). Hết hạn lại sau 20/12 nếu không nạp tiếp.

### D100 — TPCP_10Y nạp tự động từ worldgovernmentbonds.com, báo Discord khi cũ quá 21 ngày (2026-11-22, phiên trước giao việc)
- **Vì sao:** sau khi chuyển sang VPS (D96) không job nào nạp TPCP_10Y; quá 30 ngày cờ chặn `STALE_MACRO_RF` loại cả
  100 mã khỏi xếp hạng (D99 nạp tay tới 20/11, hết hạn lại sau 20/12).
- **Chọn nguồn (đều trong allowlist, không đăng nhập, không trả phí):**
  - worldgovernmentbonds.com, trang `bond-historical-data/vietnam/10-years/`: chuỗi ngày từ 2016 (3.713 điểm). Khớp
    investing.com (nguồn nạp tay) ở 23 phiên 19/10–20/11: lệch tối đa 0,001 điểm % (17/11, 18/11, 05/11), còn lại trùng.
    robots.txt cho phép mọi bot; trang điều khoản không cấm truy cập tự động. → **chọn**.
  - HNX `trai-phieu/duong-cong-loi-suat.html`: đường cong ƯỚC LƯỢNG (spot/par yield), 10 năm par 4,458% so với 4,568% của
    WGB/investing.com cùng tuần (−11 bp) → khác thước đo, không trộn vào chuỗi; giữ làm đối chiếu.
  - investing.com: ngoài allowlist, chặn tải tự động; tradingeconomics 403.
  - Gọi thẳng API JSON nội bộ của WGB bị bộ phân quyền chặn khi thử (22/11) → không dùng. Job mở chính trang công khai
    bằng Chromium headless (Playwright, đã có trong image VPS) như một lượt xem trình duyệt, đọc biến
    `jsGlobalResult.result.quote` trang tự dựng; trình duyệt chỉ được tải tài nguyên từ host trong allowlist (quảng
    cáo/tracker bị chặn). User-agent mặc định của Playwright (không giả trình duyệt thường).
- **Làm:** `valuation/ingest/tpcp_wgb.py` + `scripts/update_tpcp_10y.py` (`--dry-run`: không ghi, không gửi). Chỉ THÊM
  ngày thường chưa có trong DB, trong 45 ngày gần nhất, trước hôm nay (điểm hôm nay còn đổi); ngày đã có (kể cả
  investing.com) không bao giờ bị ghi đè; giá trị ngoài 0,5–15% → lỗi, không ghi. Ghi qua `upsert_macro_series`
  (`source = worldgovernmentbonds.com`). Điểm mới nhất cũ > 21 ngày → tin Discord (webhook báo cáo sáng) kèm ngày bị
  chặn (điểm cuối + 31 ngày) và lỗi lần nạp nếu có; lỗi tải/parse vẫn kiểm tra tuổi rồi thoát mã 1. Tham số:
  `macro_sources.tpcp_10y_wgb` trong `config/defaults.yaml`.
- **Lịch:** `tpcp-10y` 07:20 T2–T6 trong `vn100-worker`, đứng đầu danh sách `JOBS` (chạy bù vẫn trước báo cáo sáng
  07:50 và xếp hạng 08:00). Bản sao `deploy/docker/scheduler.py` trong repo đồng bộ với VPS (gồm 2 dòng data-update +
  ranking T2/T5 08:00 trước đây chỉ có trên VPS).
- **Giới hạn:** WGB chụp số vài lần mỗi ngày theo giờ UTC; điểm của một ngày là lần chụp cuối, có hôm giữa phiên →
  lệch đóng cửa ~0,1–2 bp. Ngày lễ VN WGB lặp số hôm trước, job vẫn ghi (không phân biệt được với ngày thường).
  Gỡ: `DELETE FROM macro_series WHERE indicator_code='TPCP_10Y' AND source='worldgovernmentbonds.com'`.
- **Kiểm:** `tests/test_tpcp_wgb.py` (21 ca, offline, SQLite trong bộ nhớ): 4,561% → 0,04561; DB 18–20/11, hôm nay
  25/11 → chỉ thêm 23/11 và 24/11; lấp ngày thiếu 19/11; 18/11 investing 4,571% không bị WGB 4,572% ghi đè; chạy lại
  ghi 0; ngưỡng báo tính tay (điểm cuối 20/11: 11/12 cũ 21 ngày chưa báo, 12/12 cũ 22 ngày báo, chặn từ 21/12); lỗi
  tải + chuỗi cũ vẫn báo; host ngoài allowlist bị từ chối trước khi tải. Chạy thử trên Mac (dry-run, Chrome của máy):
  đọc 3.713 điểm, chọn đúng ngày thiếu.
- **Kiểm trên VPS (22/11, sau deploy `02e5770`, sao lưu `/data/backup-before-tpcp-auto-20261122.db`):** dry-run trong
  `vn100-worker` 4 s, chọn 9 ngày thiếu 08/10–21/10 (số khớp trang WGB). Chạy thật lần 1 ghi 9, lần 2 ghi 0; TPCP_10Y
  2651 → 2660 dòng, 0 ngày trùng, các dòng investing.com giữ nguyên. Bộ nhớ anon của container lúc chạy tối đa ~305 MB
  (giới hạn worker 640 MB; job chạy tuần tự, không chồng job khác). Nhánh cảnh báo giả lập hôm nay 12/12 + nguồn lỗi
  (dry-run, không gửi): « TPCP_10Y cũ 22 ngày … chặn từ 21/12/2026 … lỗi: TimeoutError … »; webhook có trong môi trường
  worker. Chưa gửi tin Discord thật. Điểm đầu tiên job tự thêm theo lịch: 23/11, ở lượt 07:20 thứ Ba 24/11.

### D101 — Wyckoff: kế hoạch nâng cấp tab money + W0 lưu mua/bán chủ động FHSC (2026-11-22, người dùng chọn Q1–Q8)
- **Kế hoạch:** `docs/PLAN_WYCKOFF_FLOW.md` v0.2.
  - Thêm cấu trúc Wyckoff (vùng giá, sự kiện SC/ST/Spring/SOS/UTAD/SOW, pha A–E), chỉ dùng nến đã đóng.
  - Dòng tiền theo nhà đầu tư thành bằng chứng "ai đứng sau".
  - Kiểm chứng ngược bắt buộc trước khi vào danh sách lọc/Discord.
- **Người dùng chọn:**
  - Q1: nhãn Wyckoff **thay** nhãn Gom/Xả từ W3.
  - Q2: làm W0 ngay.
  - Q3: **hiện mục tiêu P&F**, kèm "quy ước, không phải dự báo" và tỷ lệ đạt đo được.
  - Q4: ghi cả spring KL thấp lẫn shakeout KL cao.
  - Q5: tiêu chí t ≥ 2 trên 2023–2026.
  - Q6: chỉ FHSC.
  - Q7: thu thập thành phần VN100 theo kỳ trước khi kiểm chứng (W2a).
  - Q8: Claude đề xuất mã golden.
- **W0 — làm:**
  - Cầu nối FHSC thêm loại `active` (`active_flow`), bỏ phiên hôm nay như khối ngoại.
  - Bảng `active_flow_daily` (metadata riêng như `flow_daily`; `scripts/migrate_active_flow.py` backup rồi CREATE).
  - Job `scripts/update_active_flow.py` 07:35 T2–T6 (`scheduler.py` VPS + bản repo).
  - Dòng thiếu số/âm/cả hai bằng 0 bị bỏ và đếm. Phiên đã lưu không ghi đè; số lệch ghi `mismatches`.
  - 7 test (`tests/test_active_flow.py`), có ca tính tay VCB 20/11.
- **Kiểm trên VPS (22/11, commit 503cd4b):**
  - Backup `/data/vn100_full.pre_active_flow_daily_20261122_175532.db`, `quick_check` ok.
  - Lần 1: 100/100 mã, ghi 4.997 dòng (61 phiên 24/08–20/11), bỏ 1.010, 168 s. Lần 2: ghi 0, giữ 4.997, 0 lệch.
  - Bộ nhớ worker ~20 MB.
- **CHƯA DÙNG ĐƯỢC CHO PHÂN TÍCH — hai bất thường của nguồn, đã dừng lại báo người dùng (skill vn-finance-data):**
  1. **Mua + bán chủ động ≠ KL khớp.** Trung vị gấp 3,9 lần `prices_daily.volume` (p5 2,9; p95 10; KOS tới 21.140 lần).
     Đối chiếu ngay tại FHSC: VCB 20/11 `ohlcv` KL 3.894.800 nhưng mua + bán chủ động 12.615.010.
     Tài liệu vnstock 6 chỉ ghi "số liệu nguồn tự tính"; `columns="all"` không có thêm trường.
     → Chưa rõ định nghĩa. Tỷ lệ % mua chủ động có thể vẫn dùng được, nhưng chưa xác minh.
  2. **Thiếu mã 24/09–21/10:** mỗi phiên chỉ 45–63/100 mã; 22/10 không có mã nào.
  - Job vẫn lưu số gốc (FHSC chỉ giữ 61 phiên, bỏ thì mất). Phân tích W4 chỉ dùng sau khi xác minh định nghĩa.
  - **Người dùng chọn giữ job** trong lúc chờ xác minh (22/11/2026, được hỏi « giữ hay tắt »).

### D102 — Web hợp nhất btinvest.vn: kế hoạch 6 lát và lát 1 (tìm mã + dòng tiền thật) (2026-11-24, người dùng « tiến hành »)
- **Vì sao:** người dùng muốn gộp chungkhoan và chungquyen thành một web đồng nhất, giao diện mới, giữ logic cũ.
  32 câu hỏi-đáp, hai bản mẫu và góp ý của họ nằm ở `docs/PLAN_WEB_HOP_NHAT.md` (mục 1–11); kế hoạch xây ở mục 12.
- **Người dùng chọn:** giao diện viết tay HTML/CSS/JS (không React); xây cổ phiếu trước; giữ gần đúng logic và bằng
  chứng của web cũ, chỉ đổi bố trí; API chỉ gọi lại hàm sẵn có, không đổi công thức hay ngưỡng.
- **Lát 1 — làm:**
  - `valuation/services/web_flow.py`: lắp ráp y như `views.money_flow._compute`, `_history`, `_chart_block`, `_card`
    rồi đổi sang JSON (NaN → null). Bộ nhớ đệm trong tiến trình theo `web.cache_seconds` (config mới `web:`).
  - `valuation/api/web_main.py`: app FastAPI **riêng, chỉ có GET** (`/api/ma`, `/api/dong-tien`,
    `/api/co-phieu/{ma}/dong-tien`, `/api/co-phieu/{ma}/bieu-do`), phục vụ luôn thư mục `web/`. Không dùng
    `valuation.api.main` vì app đó có route ghi DB và khởi động job.
  - `web/`: ô tìm mã (theo mã hoặc tên, không dấu), tab Cổ phiếu (tóm tắt, bản đồ ngành, 100 mã có nhãn và ba
    phiếu, lọc theo nhãn và ngành, chế độ Loại/Gồm), trang một mã (thẻ, biểu đồ Lightweight Charts của tab cũ
    nhúng nguyên qua iframe với đủ khung thời gian, tầng, volume profile; bảng phiếu, cửa sổ 5/20/60, phiên thỏa
    thuận). Bốn tab còn lại ghi rõ "chưa nối dữ liệu thật".
  - 8 test `tests/test_web_flow.py` đối chiếu API với `compute_money_flow` trên DB tạm, có ca tính tay cho `clean`,
    kiểm mã lạ/tham số sai và kiểm app chỉ có route đọc. 95 test (web + dòng tiền cũ) qua; ruff, black, mypy sạch.
- **Lỗi tự gây và đã sửa:** `_cached` lồng nhau (ticker_list gọi `_result` trong khi giữ khóa tính) treo test → đổi
  sang `RLock`. Tham số `?ma=` bị `ghiDiaChi` xóa trước khi đọc → đọc trước khi đặt tab.
- **Đo trên máy Mac (DB cũ: giá tới 16/11, dòng tiền tới 12/11):** cả VN100 nạp 0,8 s + tính 1,6 s + upside 0,25 s.
  `build_company_data` + `valuate`: VRE 0,7 s, HPG 0,6 s, VCB 11 s (ngân hàng nạp chậm) → lát 2 cần bộ nhớ đệm.
  Ba mã này ở máy Mac đều ra NOT_RATED/không công bố, khác VPS (VRE: MUA 31.856). Nguyên nhân: DB máy Mac cũ nên
  bộ máy tự gắn cờ `STALE_PRICE`, `STALE_MACRO_RF`, `DATA_REVIEW_REQUIRED`; giá trị hợp lý của VRE vẫn khớp VPS
  (31.852 so với 31.856). Lát 2 thử trên máy Mac sẽ thấy NOT_RATED; số đúng chỉ có khi chạy trên VPS.
- **Chưa làm:** lát 2–6; chưa chạy trên VPS (số sống ở đó); chưa thử trên điện thoại thật; chưa có đăng nhập ở
  bản chạy tại máy (trên VPS dùng lại `forward_auth` của Caddy, D98).
- **Chạy tại máy:** `~/.venv/bin/python -m uvicorn valuation.api.web_main:app --host 127.0.0.1 --port 8600`.

### D103 — Web hợp nhất lát 2: định giá, báo cáo tài chính, công ty chứng khoán, cổ tức, báo cáo AI của một mã (2026-11-24, người dùng « Tiếp 2 »)
- **Làm:**
  - `valuation/services/web_valuation.py`: một lần `build_company_data(mode="TTM", fetch_live=False)` → `valuate`
    cho mỗi mã (đúng đường `select_ticker.py` gọi), giữ trong bộ nhớ đệm của `web_flow`. Các bảng lấy nguyên từ
    `report/report_data.py` (`build_historical_analysis`, `build_appendix_financials`, `build_assumptions_table`,
    `build_wacc_breakdown`, `build_scenarios`, `build_consensus_comparison`); độ nhạy lắp như `views/results.py`
    (trục X là WACC, ngân hàng là COE); cờ qua `describe_flags`; cổ tức qua `load_corporate_actions`; tổng hợp luận
    điểm đọc bảng `consensus_synthesis`.
  - Báo cáo AI: **chỉ đọc bản đã lưu** mới nhất trong `.deepseek_report_cache/` đúng phiên bản schema hiện hành
    (`report_markdown`), không gọi DeepSeek. Bộ đệm của app khóa theo dấu vân tay đầu vào nên bản lấy ra có thể
    cũ hơn số đang hiện; giao diện ghi rõ ngày sinh.
  - 5 route GET mới trong `valuation/api/web_main.py`: `/api/co-phieu/{ma}/dinh-gia`, `/tai-chinh`, `/ctck`,
    `/co-tuc`, `/ai`; mã phải có trong bảng `tickers` (404 nếu không).
  - `web/app.js`: phần "Định giá" trên trang một mã (giá trị hợp lý + thước, nhãn của hệ thống, cờ kèm mô tả) và
    9 mục mở ra: kịch bản, độ nhạy, dự phóng 5 năm, giả định, chi phí vốn, báo cáo tài chính, công ty chứng khoán,
    cổ tức và quyền mua, phân tích AI (bốn mục sau nạp khi mở). Số "9,124.0" của `report_data` đổi sang kiểu
    Việt Nam ở trình duyệt, không đổi giá trị.
- **Không tự quyết thay người dùng:** nhãn hiển thị đúng chữ của bộ máy (MUA/NẮM GIỮ/BÁN, NOT_RATED ghi "Chưa xếp
  hạng"), chưa quy đổi sang "Nên xem xét/Theo dõi/Bỏ qua"; tiêu đề ghi upside của bộ máy, chưa dùng "Rẻ x%". Hai
  việc này chờ người dùng chốt (mục 9 của kế hoạch).
- **Phương pháp không áp dụng:** các hàm dựng bảng bọc bằng `_try` bắt đúng `ValueError`, `ZeroDivisionError`,
  `AttributeError`, `TypeError`, `KeyError` rồi trả `{"ap_dung": false, "ly_do": ...}` để hiện "không áp dụng" kèm
  lý do; lỗi khác vẫn thành HTTP 500. Khi phương pháp là BROKER_SYNTH, giao diện ghi rõ kịch bản và độ nhạy tính
  trên mô hình riêng (VRE: 9.521 đ) còn giá trị hợp lý lấy từ tổng hợp công ty chứng khoán (31.852 đ).
- **Kiểm:** 5 test `tests/test_web_valuation.py` trên DB thật của máy, chặn mạng: API bằng đúng `valuate` và
  `report_data` cho VRE; ca kiểm tay: ô giữa bảng độ nhạy bằng kịch bản Base. 13 test web qua; ruff, black, mypy
  sạch cho các tệp mới. Gọi thử `dinh-gia` và 4 route kia cho VCB (11,8 s lần đầu), SSI, BVH, FPT: đều 200.
  Mở VRE và VCB ở cỡ điện thoại: đủ 10 mục, không lỗi console của trang.
- **Hạn chế:** máy Mac ra "Chưa xếp hạng" cho mọi mã vì DB cũ (D102); chưa có nút đổi TTM/FY, chưa cho sửa giả
  định hay lưu kịch bản (việc ghi, để lát 5); chưa có biểu đồ waterfall FCFF và khoảng định giá ±15% của tab cũ;
  máy Mac không có báo cáo AI nào đúng phiên bản schema nên mục AI chưa được nhìn thấy với nội dung thật.

### D104 — Web hợp nhất lát 3: tab Hôm nay (thị trường, vĩ mô), xếp hạng VN100, lịch quyền (2026-11-24, người dùng « Làm tiếp 3 »)
- **Làm:**
  - `valuation/services/web_market.py`: `market` lắp ráp y như `render_market_overview` (bốn trụ cột, đèn tổng,
    `index_view`, `outlook`, `leaders`, nhãn tin); `macro` dùng `PANEL`, `build_snapshot`, `_fmt_value`,
    `is_stale`, `quick_takes` và bản tin `get_macro_bulletin_cached(force=False)` (chỉ đọc bản lưu, đã bỏ dòng
    TAGS); `ranking` y như `render_vn100_ranking` (`ranking_table` + `snapshot_closes` + `accumulation_picks`,
    bỏ các cột `_HIDDEN`); `upcoming` gọi `load_upcoming_vn100_corporate_actions` với `market_upcoming_days`.
  - 4 route GET: `/api/thi-truong`, `/api/vi-mo`, `/api/xep-hang`, `/api/lich-quyen`.
  - `web/app.js`: tab Hôm nay thật (dải VN-Index, bốn trụ cột mở ra được, kịch bản sắp tới, ngành mạnh/yếu, mã
    có lực bấm được, bảng ngành, mã mạnh nhất, 7 chỉ số vĩ mô, nhận định nhanh, bản tin vĩ mô, lịch quyền nạp
    khi mở) và là tab mở đầu; tab Cổ phiếu thêm công tắc "Dòng tiền / Xếp hạng VN100" (bảng tích sản + bảng 100
    mã, cột Mã bấm được). `clean` đổi `Decimal` thành số (trước đó tiền cổ tức ra chuỗi).
- **Trình bày, không đổi số:** bản tin vĩ mô đã lưu có cờ và emoji đầu mục; giao diện bỏ các ký tự đó (mục 9
  `AGENTS.md`), giữ nguyên chữ.
- **Kiểm:** 5 test `tests/test_web_market.py` trên DB thật, chặn mạng: API bằng đúng các hàm gốc (nhãn và trụ cột,
  `outlook`, mã có lực, từng chỉ số vĩ mô với `_fmt_value`, `quick_takes`, thứ tự bảng xếp hạng, tích sản, lịch
  quyền); ca tính tay cho `Decimal`. 18 test web qua; ruff, black, mypy sạch. Mở ở cỡ điện thoại: Hôm nay đủ các
  khối, lịch quyền 11 dòng, xếp hạng 100 dòng, tích sản 5 dòng.
- **Hạn chế:** chưa có nút "Cập nhật vĩ mô", "Làm mới tin tức", "Định giá lại VN100", "Xuất Excel" (đều là thao
  tác ghi hoặc gọi mạng, để lát 5); trang Hôm nay chưa có chứng quyền, ETF, phái sinh (lát 4).

### D105 — Web hợp nhất lát 4: chứng quyền, ETF, phái sinh qua API chỉ đọc của cw_scanner (2026-11-24, người dùng « Ok tiếp tục »)
- **Vì sao hai dịch vụ:** chứng quyền, ETF, hợp đồng tương lai do repo `~/cw_scanner` tính (file quét, Black-Scholes,
  NAV, basis) bằng `http.server` thuần và venv riêng. Không chép công thức sang đây: web mới gọi sang dịch vụ đó.
- **Làm ở `~/cw_scanner` (chưa commit):**
  - `web_api.py` (mới): `chung_quyen` (danh sách theo đúng thứ tự file quét, số theo nhóm, ngưỡng lấy từ hằng số
    `cw_scanner`, lời giải thích cột lấy từ `W.COT`), `chung_quyen_mot_ma` (dòng quét, 4 tiêu chí, ngày đáo hạn,
    chứng quyền cùng mã cơ sở), `quy_etf` (ba bảng của `trang_etf` ở dạng cột + dòng, cùng thứ tự, kèm cảnh báo
    trung vị cũ), `hop_dong_tuong_lai` (`phai_sinh.lay_du_lieu` + `web_phai_sinh.chi_so_hd`), `trang_cu` (trang
    HTML cũ bỏ thanh menu và nút quét, thêm đoạn script báo chiều cao và chuyển cú bấm liên kết ra ngoài).
  - `web.py`: 9 dòng, nhánh `/api/` trong `do_GET` gọi `web_api.tra_loi`; đang quét thì 503, lỗi lúc tính thì 500
    kèm tên lỗi và in dấu vết ra stderr. Các hàm `trang_*` và mọi công thức không bị sửa.
  - 4 tiêu chí của một dòng quét dựng lại từ cột của file (ô IV − HV trống thì đọc cột Ghi chú IV), cùng ngưỡng
    `MIN_NGAY_CON_LAI`, `MAX_IV_TRU_HV`, `MAX_TANG_DE_HOA_VON`, `MIN_KHOI_LUONG`.
- **Làm ở đây:**
  - `valuation/services/web_cw.py`: `fetch(path)` chỉ GET, chỉ đường dẫn trong danh sách cho phép (regex), địa chỉ
    dịch vụ ở `web.cw_base_url` (mặc định `http://127.0.0.1:8000`), hạn chờ `web.cw_timeout_seconds`. Mã 404 và 503
    của dịch vụ giữ nguyên, lỗi khác thành 502, mất kết nối thành 503; câu báo giữ nguyên văn.
  - `web_main.py`: 7 route GET (`/api/chung-quyen`, `/api/chung-quyen/{ma}`, `/api/chung-quyen/{ma}/trang-cu`,
    `/api/etf`, `/api/etf/{ma}/trang-cu`, `/api/phai-sinh`, `/api/phai-sinh/{ma}/trang-cu`), mã phải đúng mẫu.
  - `web/app.js`, `web/app.css`: ba tab thật thay ba tấm "chưa nối dữ liệu"; tờ chi tiết của chứng quyền, quỹ,
    hợp đồng; ô tìm thêm chứng quyền, quỹ, hợp đồng; mục "Chứng quyền và ETF" ở tab Hôm nay; dấu "!" giải thích
    (lời lấy từ lời giải thích cột của trang cũ); địa chỉ `?ma=` mở được cả bốn loại mã.
  - `.claude/launch.json`: thêm preview `cw-dich-vu` (cổng 8000).
- **Trang phân tích cũ đặt trong khung:** phần định giá lại theo giá trực tiếp, nến, sổ lệnh, IV theo thời gian,
  mức theo kịp, lãi lỗ nếu giữ đến đáo hạn nằm lẫn trong HTML của `trang_chi_tiet` (hơn 400 dòng). Tách số ra JSON
  là viết lại phần điều phối đó, dễ lệch số, nên lát này lấy nguyên trang cũ vào `iframe sandbox="allow-scripts"`.
  Giao diện gán lại 16 biến màu của trang cũ bằng màu của web mới (đọc lúc vẽ, theo chế độ sáng / tối) và phông Be
  Vietnam Pro; biểu đồ nến đọc màu từ các biến đó nên đổi theo. Bấm một dòng trong bảng của trang cũ thì web mới mở
  tờ của mã đó (postMessage, chỉ nhận từ đúng khung đang mở và chỉ đường dẫn đúng mẫu).
- **Trình bày, không đổi số:** thước của chứng quyền = giá mua so với giá hợp lý (± 50% như cổ phiếu); của quỹ =
  giá chào bán so với iNAV (± 5%); của hợp đồng = giá so với chỉ số (± 2%), không tô màu rẻ / đắt vì chưa có giá hợp
  lý cho hợp đồng (`phai_sinh.py` cố ý không tính: chưa có tỷ suất cổ tức q). Tab Phái sinh không xếp nhóm "nên xem
  xét". Chữ "Rẻ 18,4%" lấy nguyên từ `W.dat_re` của trang cũ.
- **Sửa kèm:** `thuoc()` gán lớp `bang` khi lệch gần 0, trùng tên dải navy `.bang` nên thước biến thành thanh
  navy dày (lộ ra ở quỹ E1VFVN30, lệch 0,01%); đổi thành `tt`.
- **Kiểm:** cw_scanner: 12 test `test_web_api.py` (file quét dựng tạm, không gọi mạng): JSON đúng thứ tự và đúng chữ
  với bảng "Tất cả" của trang HTML cũ; ca tính tay 4 tiêu chí (45 ngày < 60 nên trượt đúng 1); số tiêu chí trượt
  0 / 1 / ≥ 2 ra đúng Đánh giá của `danh_gia` trên cả 461 dòng file quét thật 17/11; hợp đồng tương lai tính tay
  (1900 so với 1890: basis 10 điểm, 0,5291%, năm hóa 6,42%, ký quỹ 32,3 triệu); đang quét 503; lỗi mạng 500 và có
  dấu vết; 219 test của cw_scanner qua, ruff và black sạch. Ở đây: 8 test `tests/test_web_cw.py` với dịch vụ giả
  (`httpx.MockTransport`, chặn socket): JSON đi qua nguyên vẹn, mã sai mẫu không gọi dịch vụ, đường dẫn ngoài danh
  sách bị từ chối, mã lỗi và câu báo đúng; 26 test web qua; ruff, black sạch, mypy không lỗi ở tệp mới.
  Trình duyệt (máy tính và cỡ điện thoại, sáng và tối): 26 chứng quyền nên xem xét, lọc và tìm; tờ CVRE2609 có khung
  cao 7.455 px định giá lại lúc 22:44 (950 so với 1.198); bấm dòng CVRE2608 trong khung mở tờ CVRE2608; 21 quỹ;
  8 hợp đồng; tìm "vre" ra cổ phiếu VRE và 11 chứng quyền.
- **Hạn chế:** file quét trên máy Mac là 17/11 (ETF 18/11), web báo "số liệu cũ 7 ngày"; số sống ở VPS. Trang
  trong khung còn ký hiệu ⚠ ℹ của trang cũ. Chưa có Lướt CW, CW sắp ra mắt, cảnh báo giá, danh mục, nút quét,
  trang hướng dẫn. Chưa thử trên điện thoại thật. Chưa commit ở cả hai repo.



### D106 — Web hợp nhất lát 5a: tài khoản được duyệt, hai vai, tệp dữ liệu người dùng riêng (2026-11-25, người dùng « giờ làm 5a »)
- **Người dùng chốt trước khi làm** (`docs/PLAN_WEB_HOP_NHAT.md` mục 13): lát 5 chỉ gồm tài khoản, danh mục, cảnh
  báo; Quản trị duyệt người ngay trên web; danh mục đủ 4 loại có nhập lệnh; danh mục chứng quyền cũ giữ ở web cũ tới
  lúc chuyển hẳn; cảnh báo chỉ báo trong web; lãi lỗ sau phí và thuế như web cũ; **Quản trị xem được lệnh của các
  tài khoản dưới** (hiểu là chỉ xem, không sửa; không xem của Quản trị khác; xác nhận lại khi trình 5b).
- **Vì sao phải tự nhận diện:** đăng nhập chung (D98) là `forward_auth` ở Caddy, chỉ cho qua hay chặn; ứng dụng
  không biết ai đang dùng. Đọc mã coin trên VPS (chỉ đọc, người dùng cho phép 25/11): `GET /api/v1/auth/me` trả
  `{user: {_id, username, email (có thể trống), firstName, lastName, …}, …}`, cookie `access_token`, giới hạn 600
  lượt mỗi phút mỗi IP.
- **Schema mới (người dùng duyệt):** tệp SQLite RIÊNG `web_user.db` (`WEB_USER_DB_URL`), không nằm trong DB định giá
  vì DB định giá có thể bị thay bằng bản đóng gói. Bảng `web_users` (`coin_user_id` duy nhất, `email`, `username`,
  `ten_hien_thi`, `vai`, `trang_thai`, `tao_luc`, `duyet_luc`, `duyet_boi`, `thay_luc`), `web_audit` (ai làm gì, lúc
  nào), `web_meta` (`schema_version` = 1). Tạo bằng `create_all`, chạy lại không tạo trùng. Bảng lệnh và mức giá
  thêm ở 5b, 5c.
- **Làm:**
  - `valuation/db/web_user.py`: ba bảng trên, engine tạo ở lần dùng đầu.
  - `valuation/services/web_auth.py`: lấy cookie `access_token`, hỏi coin `/me` (`WEB_AUTH_ME_URL`), chỉ gửi đúng
    cookie đó; nhớ kết quả 60 giây theo mã băm SHA-256 của cookie. Coin không trả lời, trả lỗi lạ, thiếu cấu hình
    hoặc chế độ lạ: 503, không cho vào. Chế độ `dev` (`WEB_AUTH_MODE=dev`, `WEB_DEV_USER`) cho máy Mac không có
    coin, chỉ nhận yêu cầu đến từ 127.0.0.1 nên sau Caddy trên VPS tự vô hiệu.
  - `valuation/services/web_users.py`: lần đầu thấy thì tạo dòng `cho_duyet`; email hoặc tên đăng nhập có trong
    `WEB_ADMIN_EMAILS` thì là Quản trị đã duyệt (thêm vào danh sách sau cũng được nâng lên); duyệt, khóa, đổi vai có
    nhật ký; không khóa hay hạ vai Quản trị đang hoạt động cuối cùng.
  - `valuation/api/web_deps.py`, `web_user_routes.py`: `GET /api/toi`; Quản trị: `GET /api/tai-khoan`,
    `POST /api/tai-khoan/{id}/duyet`, `/khoa`, `/vai`. Route ghi đòi `Origin` (hoặc `Referer`) trùng tên miền và
    thân JSON.
  - `web_main.py`: 20 route số liệu của lát 1–4 chuyển sang một router có điều kiện "đã đăng nhập và đã duyệt".
    `/api/suc-khoe` và tệp tĩnh của khung web vẫn công khai (không có số liệu).
  - `web/`: màn hình chắn (chờ duyệt, bị khóa, chưa hỏi được máy chủ) che cả web và không nạp số liệu nào phía
    sau; nút tài khoản ở góc trên (tên, vai, đăng xuất); tờ Tài khoản cho Quản trị; `api()` gặp 401 thì về
    `/dang-nhap?next=…`, gặp 403 giữa chừng thì hỏi lại trạng thái.
  - `config/defaults.yaml` mục `web.auth`; `.env.example` thêm 5 biến; `.claude/launch.json` chạy preview ở chế độ
    `dev`.
- **Kiểm:** 12 test `tests/test_web_auth.py` (coin giả, SQLite tạm, chặn socket): chưa đăng nhập 401 ở cả route số
  liệu; người mới chờ duyệt, gọi nhiều lần vẫn một dòng; Quản trị đầu tiên từ `WEB_ADMIN_EMAILS` (email viết hoa,
  tên đăng nhập, thêm sau); duyệt hai lần không thêm nhật ký; nhân viên gọi route Quản trị 403; không `Origin`,
  `Origin` lạ 403, gửi kiểu form 415; coin sập, lỗi lạ, thiếu cấu hình, chế độ lạ đều 503; ca tính tay cho bộ nhớ
  đệm (giây 0 hỏi, giây 59 còn nhớ, giây 60 hỏi lại); chỉ cookie phiên được gửi cho coin; chế độ `dev` từ địa chỉ
  khác 127.0.0.1 bị 403. 26 test số liệu cũ đi qua bằng fixture `web_approved`; 38 test web qua; ruff, black sạch,
  mypy không lỗi ở tệp mới. Trình duyệt: nhân viên mới thấy màn hình chờ duyệt và `/api/xep-hang` trả 403; Quản
  trị duyệt trong tờ Tài khoản; nhân viên vào lại xem được 26 chứng quyền, không có mục Tài khoản, gọi
  `/api/tai-khoan` bị 403; tự khóa Quản trị cuối cùng bị 409.
- **Chưa kiểm, chỉ làm được trên VPS (lát 6):** đăng nhập thật với coin (hình dạng `/me` lấy từ mã nguồn, chưa gọi
  thử); coin có nhận cookie do ứng dụng gửi lại không; Caddy phải trả 401 cho `/api/*` thay vì chuyển hướng 302 để
  giao diện tự về trang đăng nhập.
- **Rủi ro:** người vừa bị khóa ở coin còn vào được tối đa 60 giây; ai có tên trong `WEB_ADMIN_EMAILS` thì dù bị
  khóa trên web vẫn được nâng lại ở lần mở sau (muốn khóa hẳn phải bỏ khỏi danh sách); `web_user.db` cần sao lưu
  trên VPS.


### D107 — Web hợp nhất lát 5b: danh mục 4 loại của từng người, công thức lãi lỗ người dùng duyệt (2026-11-25, người dùng « Làm tiếp »)
- **Người dùng chốt bằng hộp chọn trước khi viết (25/11/2026):**
  1. Cổ phiếu và ETF: « Theo giá chờ mua ». Cùng cách của danh mục chứng quyền cũ: giá vốn bình quân gồm phí mua
     0,15%; lãi nếu bán ngay = (giá chờ mua cao nhất × (1 − 0,15% − 0,1%) − giá vốn) × số lượng; không ai chờ mua thì
     giá khớp gần nhất. Ví dụ đã duyệt: mua 1.000 VRE giá 23.000 → vốn 23.034,5; chờ mua 24.000 → +905.500 đ.
  2. Hợp đồng tương lai: « Sau phí và thuế ». Lãi lỗ nếu đóng ngay = chiều × (giá khớp gần nhất − giá mở bình
     quân) × 100.000 × số HĐ − phí và thuế lúc mở − phí và thuế lúc đóng; phí 8.250 đ mỗi HĐ mỗi lần, thuế mỗi lần
     = 0,1% × giá × 100.000 × 17% ÷ 2 (hằng số của `phai_sinh.py`; cách tính thuế ở đó ghi « chưa đối chiếu văn bản
     BTC », web ghi rõ là giả định). Ví dụ đã duyệt: Long 2 HĐ giá 1.780, hiện 1.790 → ròng +1.906.310 đ.
  3. Quyền xem: « Xem của tất cả mọi người ». Quản trị xem được danh mục của mọi tài khoản, kể cả Quản trị khác;
     chỉ xem, không thêm hay xóa lệnh hộ. (Thay cho cách hiểu « chỉ xem của Nhân viên » ghi ở D106.)
- **Làm ở `~/cw_scanner` (chưa commit):**
  - `vi_the.py` (mới, chỉ tính): chứng quyền gọi nguyên `danh_muc.tinh_vi_the` + `danh_gia_danh_muc` (tín hiệu giữ
    hay bán như trang Danh mục cũ); cổ phiếu, ETF dùng cùng `tinh_vi_the` và `gia_ban_ngay` (giá chờ mua cao nhất);
    hợp đồng tương lai `vi_the_hop_dong` (vị thế ròng theo chỉ số + ngày giao dịch cuối, đóng bớt, đảo chiều) và
    `lai_neu_dong`. Mất mạng ở loại nào thì loại đó chỉ có số đang nắm và giá vốn, kèm câu báo.
  - `web_api.tinh` + nhánh POST `/api/tinh/danh-muc` trong `web.py`: nhận danh sách lệnh, kiểm kiểu từng lệnh, trả
    vị thế đã định giá; `chi_kiem` thì chỉ dựng thử vị thế, không gọi giá. Không đọc `danh_muc.csv`, không ghi
    tệp, không gửi Discord. Bắt buộc thân JSON (415 nếu không), nên trang web lạ không khiến máy chủ gọi bảng giá hộ.
- **Làm ở đây:**
  - `valuation/db/web_user.py`: bảng `web_orders` (`user_id`, `loai` cp/cw/etf/hd, `ma`, `chieu` MUA/BAN,
    `so_luong`, `gia`, `ngay`, `chot_loi`, `cat_lo`, `ghi_chu`, `hop_dong_gd_cuoi`, `ma_yeu_cau` duy nhất theo
    người, `tao_luc`, `xoa_luc`); `schema_version` 1 → 2 (chỉ thêm bảng). Người dùng đã duyệt schema này ở mục 13.
  - `valuation/services/web_portfolio.py`: kiểm đầu vào, mã phải có thật ở đúng loại (cổ phiếu trong `tickers`,
    chứng quyền trong lần quét, quỹ trong kết quả ETF, hợp đồng lấy ngày giao dịch cuối từ dịch vụ), nhờ dịch vụ
    dựng thử vị thế trước khi lưu, xóa mềm, nhật ký `them_lenh` / `xoa_lenh`. Không tự tính con số nào.
  - `web_cw.compute`, 5 route trong `web_user_routes.py`: `GET /api/danh-muc[?nguoi=]`, `GET /api/danh-muc/lenh`,
    `GET /api/danh-muc/nguoi` (Quản trị), `POST /api/danh-muc/lenh`, `POST /api/danh-muc/lenh/{id}/xoa`.
  - `web/`: nút Danh mục ở góc trên; tổng lãi lỗ, 4 nhóm vị thế có thước, tín hiệu chứng quyền, form ghi lệnh,
    sổ lệnh (xóa phải bấm hai lần), ô chọn người cho Quản trị (chỉ xem); Nhân viên thấy dòng « Quản trị xem được
    danh mục này ».
- **Khác bản kế hoạch:** cột `loai` lưu mã ngắn `cp/cw/etf/hd` thay cho `co_phieu/…`; thước của cổ phiếu dùng
  upside của đợt định giá VN100 gần nhất (giá trong DB), của chứng quyền dùng đắt rẻ lúc quét, của ETF dùng chiết
  khấu lúc lập báo cáo: thước và lãi lỗ vì thế không cùng thời điểm giá; chân trang Danh mục ghi rõ điều này.
- **Kiểm:** cw_scanner 11 test `test_vi_the.py` (hai ví dụ đã duyệt; giá bán và lãi khớp `danh_gia_danh_muc` trên
  cùng bảng giá mẫu; Short đóng bớt và đảo chiều; hợp đồng nhận diện bằng ngày giao dịch cuối, hết hạn thì không
  bịa giá; kiểm đầu vào; POST chỉ tính không cần `Origin` còn form ghi cũ vẫn 403); 230 test qua. Ở đây 9 test
  `tests/test_web_portfolio.py` (dịch vụ giả): gửi lại cùng mã yêu cầu không nhân đôi; 16 kiểu lệnh sai không lưu;
  bán quá số đang nắm 422; người khác không xem, không xóa được; Quản trị xem được nhưng xóa hộ 404; xóa mềm có
  nhật ký; dịch vụ sập thì không lưu; 47 test web qua; ruff, black sạch, mypy không lỗi ở tệp mới. Trình duyệt với
  hai dịch vụ thật và giá Vietcap trực tiếp: ghi 4 lệnh đủ 4 loại, tổng +2.757.753 đ tính tay lại khớp từng dòng
  (VRE +506.500; CVRE2609 −164.160; E1VFVN30 +9.145; VN30F1M +2.406.268); bán 400 VRE qua form ra lãi đã chốt
  +282.400 đ; xóa hai bước; Quản trị chọn xem danh mục nhân viên, không có form và nút xóa.
- **Hạn chế:** cổ tức bằng cổ phiếu, chia tách không tự điều chỉnh; hợp đồng đã qua ngày giao dịch cuối phải tự ghi
  lệnh đóng ở giá thanh toán cuối cùng; phí thuế là giả định chung, chưa cho từng người đổi; ngưỡng chốt lời, cắt
  lỗ của cổ phiếu và ETF mới được lưu, chưa sinh cảnh báo (5c); chưa kiểm bước giá cổ phiếu; chưa commit.

### D108 — Web hợp nhất lát 5c: cảnh báo trong web (2026-11-25, người dùng « Tiếp »)
- **Phạm vi người dùng đã chốt từ kế hoạch mục 13:** chỉ báo trong web (chuông, âm thanh, thông báo của trình duyệt
  khi đang mở); không Discord, không lịch chạy nền. Hệ quả: một mức chạm lúc không ai mở web thì không được ghi lại,
  web ghi rõ điều này.
- **Ba nguồn tin, đều do `~/cw_scanner` tính:**
  1. Bất thường đang mua được, chung cho mọi người: chứng quyền rẻ bất thường, ETF dưới iNAV, hợp đồng tương lai đắt
     hoặc rẻ, chứng quyền giảm mạnh. Cùng hàm với trang `/canh-bao` cũ (`web_canh_bao.tinh_canh_bao`).
  2. Mức giá từng người tự đặt: trạng thái bằng `canh_bao_gia.trang_thai_muc` (giá khớp; khớp lẻ thì giá giao dịch
     được đủ 5 triệu), tối đa 50 mức mỗi người như cũ.
  3. Tín hiệu danh mục của người đó: chứng quyền dùng đúng bộ lọc `danh_muc.bat_thuong` của tin Discord cũ; cổ phiếu
     và ETF báo khi lãi, lỗ nếu bán ngay chạm ngưỡng **người đó tự đặt ở lệnh mua** (ô « Báo khi lãi từ / lỗ từ » đã
     có từ 5b). Cùng cách so của chứng quyền, nhưng **không áp ngưỡng mặc định +50% / −30%** của chứng quyền cho cổ
     phiếu và ETF: không đặt ngưỡng thì không báo. Ca tính tay: mua 1.000 cp giá 23.000 (vốn 23.034,5), ngưỡng lãi
     3%, chờ mua 24.000 → 24.000 × 0,9975 / 23.034,5 − 1 = +3,93% → báo; ngưỡng lỗ 4%, chờ mua 22.000 → −4,73% → báo.
     Hợp đồng tương lai không có ngưỡng.
- **Làm ở `~/cw_scanner` (chưa commit):**
  - `web_canh_bao.py`: tách phần dựng tin của `tin_canh_bao` thành `mot_tin`, `tin_thi_truong`, `tin_muc_gia`,
    `tin_giam_manh`, `tin_danh_muc`; `tin_canh_bao` gọi lại đúng các hàm đó, kết quả không đổi (test cũ giữ nguyên).
  - `canh_bao_gia.py`: tách `loi_muc_so_voi_gia` khỏi `them_muc_gia` (kiểm mã có trên bảng giá, mức không lệch quá 10
    lần giá hiện tại); `them_muc_gia` gọi lại, hành vi không đổi.
  - `vi_the.py`: `canh_bao_nguong` (cổ phiếu, ETF) và khóa `bat_thuong` trong kết quả `danh_gia`.
  - `web_api.py`: `GET /api/canh-bao` (đủ bảng, xem được cả ngoài giờ), `GET /api/canh-bao/tin` (ngoài giờ khớp lệnh
    trả ngay, không tải gì), `POST /api/tinh/muc-gia` (chỉ tính; `chi_kiem` để kiểm một mức sắp lưu);
    `/api/tinh/danh-muc` trả thêm `tin`. Mức giá trong `muc_gia.csv` và danh mục trong `danh_muc.csv` của web cũ
    không đi vào web mới. Danh sách chứng quyền giảm mạnh gộp file do lịch 5 phút ghi với các mã đang giảm lúc này.
- **Làm ở đây:**
  - `valuation/db/web_user.py`: bảng `web_price_levels` (`user_id`, `ma`, `chieu` duoi/tren, `muc`, `ghi_chu`,
    `tao_luc`, `xoa_luc`), đúng cột của kế hoạch mục 13; `schema_version` 2 → 3 (chỉ thêm bảng).
  - `valuation/services/web_alerts.py`: lưu, xóa mềm mức giá (nhật ký `them_muc_gia` / `xoa_muc_gia`); đặt lại đúng
    mức đang có thì trả mức đó (bảng không có cột mã yêu cầu); nhờ dịch vụ kiểm trước khi lưu; gộp ba nguồn tin.
    Phần chung nhớ 45 giây cho mọi người và giữ khóa lúc gọi, vì dịch vụ chứng quyền chạy một luồng và mỗi lượt tải cả
    bảng giá; dịch vụ lỗi thì nhớ lỗi 10 giây. Ngoài giờ không gọi giá cho mức giá và danh mục. Không tự tính con số
    nào.
  - `web_cw.py`: thêm hai đường GET và một đường POST vào danh sách cho phép. `config/defaults.yaml`: `web.alerts`.
  - `web_user_routes.py`: `GET /api/canh-bao`, `GET /api/canh-bao/tin`, `GET /api/muc-gia`, `POST /api/muc-gia`,
    `POST /api/muc-gia/{id}/xoa`; `/api/toi` trả thêm `hoi_canh_bao_giay`.
  - `web/`: chuông ở góc trên có số tin chưa xem (số cũng hiện ở tên thẻ trình duyệt); tờ Cảnh báo gồm tin chưa xem,
    bật tắt âm thanh, mức giá tôi đặt (form, xóa bấm hai lần), bốn nhóm bất thường có dấu « ! » giải thích ngưỡng;
    hỏi tin mỗi 60 giây, nhiều thẻ chỉ một thẻ hỏi; « đã báo », « chưa xem », bật tắt âm thanh nhớ trong trình duyệt
    theo từng tài khoản. Lượt hỏi lỗi thì chuông hiện dấu « ! » và tờ Cảnh báo ghi câu lỗi.
- **Quyền xem mức giá (mặc định của kế hoạch, người dùng chưa đổi):** của ai người đó thấy; Quản trị cũng không xem.
- **Kiểm:** cw_scanner thêm 7 test `test_web_api.py` và 2 test `test_vi_the.py` (tin chung trùng tin trang cũ trừ phần
  riêng; ngoài giờ không tải; mức giá và ngưỡng lãi lỗ tính tay; kiểm đầu vào; mất mạng báo 500), 239 test qua. Ở đây
  11 test `tests/test_web_alerts.py` và 1 test thêm ở `test_web_cw.py` (mức giá của ai người đó thấy kể cả với Quản
  trị; quá số mức 422; mã sai mẫu không gọi dịch vụ, không lưu; ngoài giờ không gọi giá; phần chung nhớ và dùng chung;
  lỗi từng phần không làm mất phần khác), 59 test web qua; cả bộ 1.290 qua, vẫn đúng 9 test trượt cũ. Trình duyệt với
  hai dịch vụ thật trong phiên chiều 25/11: 6 tin chung trùng cả mã lẫn chữ với `/canh-bao/tin` của trang cũ cùng lúc
  (4 tin còn lại của trang cũ là danh mục dùng chung, đúng là không sang web mới); mức VRE « lên tới 20.000 » báo đang
  chạm ở 23.300 (cách mức +16,5% = 23.300 / 20.000 − 1); lệnh mua 100 VRE giá 20.000 ngưỡng lãi 5% sinh tin « lãi nếu
  bán ngay +16,0% » (23.300 × 0,9975 / 20.030 − 1 = +16,04%); đặt mức 24,5 cho VPB bị từ chối vì nghi sai đơn vị.
- **Hạn chế:** âm thanh chưa nghe thử được trong trình duyệt nhúng (thông báo của trình duyệt bị chặn ở đó); iPhone
  chỉ cho thông báo khi web được thêm vào màn hình chính; chưa thử điện thoại thật; trên máy Mac không có lịch 5
  phút nên « giờ báo đầu tiên » của chứng quyền giảm mạnh trống; mỗi người có mức giá hoặc lệnh thì mỗi phút thêm
  một đến hai lượt gọi bảng giá ở dịch vụ chứng quyền (cần đo ở lát 6); chưa commit.

### D109 — Web hợp nhất lát 6: kế hoạch đưa lên VPS và phần chuẩn bị tại máy (2026-11-25, người dùng « Tiếp tục công việc »)
- **Trạng thái:** kế hoạch ở mục 14 của `docs/PLAN_WEB_HOP_NHAT.md`, **chưa được duyệt**; chưa vào VPS, chưa commit,
  chưa đẩy. Hộp chọn hỏi địa chỉ đặt web bị người dùng đóng, nên các điểm cần chốt được hỏi lại bằng chữ.
- **Rà (không vào VPS):** `btinvest.vn` đang là trang chờ « Website đang được xây dựng »; mọi tên miền phụ trỏ cùng
  địa chỉ. Dự án định giá deploy bằng cách đẩy `main` lên GitHub (VPS tự dựng lại, khởi động lại ba container cũ);
  dự án chứng quyền deploy bằng `git push vps main`. Vì vậy **đẩy mã chính là deploy**, phải xin duyệt như một bước
  trên VPS. Tệp mới của hai dự án biên dịch được bằng Python 3.12 (VPS), máy Mac chạy 3.14. Web mới ở máy Mac dùng
  207 MB sau hơn 3 giờ.
- **Thiết kế đề xuất:** container thứ tư `btinvest-web` cùng image; ở `btinvest.vn` Caddy **không** dùng
  `forward_auth` mà để ứng dụng tự kiểm đăng nhập ở từng route (nhờ vậy `/api/*` trả 401 như giao diện chờ, việc treo
  từ D106); tệp dữ liệu người dùng ở `/data/web_user/web_user.db`; sao lưu mỗi ngày, giữ 14 bản.
- **Đã làm tại máy (không đụng VPS):**
  - `WEB_CW_BASE_URL` (`valuation/config`, `web_cw.base_url`): địa chỉ dịch vụ chứng quyền khi là container khác; để
    trống thì dùng `web.cw_base_url` như cũ; địa chỉ không bắt đầu bằng `http://` hay `https://` thì báo 503, không gọi.
  - `web_user.session_factory` tự tạo thư mục cha của tệp SQLite (trên VPS `/data/web_user/` chưa có ở lần chạy đầu).
  - `valuation/services/web_backup.py` + `scripts/backup_web_user_db.py`: chép bằng cơ chế sao lưu của SQLite, mở tệp
    gốc chỉ đọc, kiểm `integrity_check` rồi mới thay bản của hôm nay, giữ `web.backup.keep` bản (14), chỉ xóa tệp đúng
    mẫu `web_user-YYYYMMDD.db`. Chạy thử hai lần trên bản chép của dữ liệu thử: một bản, tệp gốc không đổi.
  - Test `test_moi_duong_api_deu_dong_khi_chua_dang_nhap`: duyệt cả 35 cặp phương thức và đường dẫn `/api/` (trừ
    `/api/suc-khoe`), chưa đăng nhập phải 401. Thử gỡ điều kiện tài khoản của nhóm số liệu: test trượt.
- **Lỗi lộ ra và sửa:** ba test « chỉ có route đọc » (`test_web_flow`, `test_web_valuation`, `test_web_market`) kiểm
  rỗng từ lát 5a: FastAPI 0.141 giữ route của `include_router` trong vỏ riêng nên `app.routes` không còn liệt kê
  chúng. Sửa thành kiểm đúng nhóm số liệu `web_main.data` chỉ có GET.
- **Kiểm:** 70 test web qua (59 trước đó + 11 mới); ruff, black sạch trên các tệp đổi; mypy chỉ còn lỗi cũ thiếu stub
  `yaml`. Web tại máy khởi động lại và trả đúng `/api/suc-khoe`, `/api/chung-quyen`, `/api/canh-bao/tin`, `/api/muc-gia`.
- **Hạn chế:** bản sao lưu nằm cùng ổ với tệp gốc, không chống được mất cả ổ; job sao lưu lỗi chỉ ghi vào nhật ký,
  chưa báo đi đâu; bản sao cấu hình trong `deploy/docker/` chưa đổi (đổi khi VPS thật sự đổi); RAM trên VPS chưa đo.

### D110 — Web hợp nhất lát 6: commit tại máy và bước B0 đọc VPS (2026-11-25, người dùng « Đưa thẳng lên btinvest.vn luôn. còn lại theo bạn »)

- **Người dùng chốt:** đặt web mới thẳng ở `btinvest.vn` (không thử ở tên miền phụ); phần còn lại theo đề xuất của
  tôi, tức là commit tại máy ở hai dự án, đọc VPS ở chế độ chỉ đọc, rồi trình các bước ghi. Tôi KHÔNG hiểu câu này
  là cho phép đẩy mã hay sửa VPS ngay: đẩy mã chính là deploy, vẫn xin duyệt.
- **Commit (chưa đẩy):** ở đây `af49a65` (kế hoạch, bản mẫu) và `7d9e8c2` (mã, test, cấu hình, tài liệu D102–D109);
  dự án chứng quyền `f66bc9c`. Commit thẳng trên `main` theo quy ước của dự án (`.agents/AGENT_HANDOFF.md` mục 5).
  Không đưa `valuation/views/.last_ticker.txt`. Quét secret: grep mẫu khóa, email, địa chỉ; không thấy khóa nào.
- **Chạy lại cả bộ test trước khi commit:** ở đây 1.301 qua, vẫn đúng 9 test trượt cũ. Dự án chứng quyền lộ một lỗi
  có sẵn của web cũ: `do_POST` từ chối yêu cầu thiếu `Origin` (403) khi chưa đọc thân, nên lúc đóng kết nối bên gửi
  có lần nhận "connection reset" thay vì câu 403 (test trượt 17/60 lần). Sửa tận gốc ở `web.py`: đọc thân (tối đa
  10.000 byte như cũ) rồi mới từ chối; 0/60 lần trượt, 239 test qua. Kết quả từ chối không đổi.
- **B0 (chỉ đọc, không mở `.env`, che mọi chuỗi dài giống khóa trước khi đưa về máy):** chi tiết và hai đoạn cấu
  hình soạn sẵn ở cuối mục 14 của `docs/PLAN_WEB_HOP_NHAT.md`. Điều đổi so với kế hoạch: (1) VPS nay 12,9 GB RAM có
  swap, còn trống hơn 8 GB, nên RAM không còn là rủi ro lớn nhất, giới hạn `btinvest-web` chốt 768 MB; (2) image đã
  có đủ `fastapi`, `uvicorn`, `httpx`, không sửa `Dockerfile`; (3) lệnh deploy dựng lại MỌI dịch vụ trong compose và
  tự quay về commit trước nếu có container không khỏe trong 240 giây, nên sau B4 `btinvest-web` là một phần điều
  kiện khỏe của mọi lần deploy; (4) `Dockerfile` trên VPS khác bản sao trong `deploy/docker/` 4 dòng (không thuộc
  lát 6, chưa đụng).
- **Thứ tự các bước ghi (chờ duyệt):** B3 người dùng tự thêm `WEB_ADMIN_EMAILS` → B1 đẩy dự án chứng quyền → B2 đẩy
  dự án định giá → B4 thêm container → B5 đổi khối `btinvest.vn` của Caddy; dừng ở bước nào kiểm không đạt.
- **Chưa làm, chưa kiểm:** chưa có bước ghi nào trên VPS; đăng nhập coin thật, điện thoại thật, âm thanh và thông
  báo trình duyệt chưa thử; chưa biết image của dự án chứng quyền có `pytest` để chạy 239 test trong container.

### D111 — Web hợp nhất lát 6: đưa lên VPS, web mới chạy tại btinvest.vn (2026-11-25, người dùng « Chạy ngay »)

- **Người dùng duyệt** sau khi xem kết quả B0: chạy lần lượt bốn bước ghi B1, B2, B4, B5 ngay tối 25/11 (ngoài giờ
  khớp lệnh, không trùng job nào). B3 là việc của người dùng, lúc chạy chưa có.
- **Đã làm, theo đúng thứ tự, kiểm đạt mới sang bước sau** (chi tiết từng phép kiểm ở cuối mục 14 của
  `docs/PLAN_WEB_HOP_NHAT.md`): B1 `git push vps main` ở dự án chứng quyền (`f66bc9c`); B2 `git push origin HEAD:main`
  ở đây (`f55bde0`); B4 thêm container `btinvest-web` vào compose trên VPS (sao lưu tệp cũ, `docker compose config`
  rồi mới thay); B5 thay khối `btinvest.vn` trong Caddyfile (sao lưu, `caddy validate`, nạp lại không khởi động lại).
- **Cách sửa tệp trên VPS:** compose soạn ở máy từ bản sao đã so mã băm trùng với VPS, chép sang, nên
  `deploy/docker/docker-compose.yml` nay trùng mã băm với tệp đang chạy. Caddyfile thay bằng script chạy trên VPS, chỉ
  thay khi tìm thấy đúng một khối `btinvest.vn` còn là trang chờ. Không mở `.env`; chỉ hỏi ứng dụng trong container
  biến `WEB_ADMIN_EMAILS` có giá trị hay không (kết quả: chưa).
- **Kết quả:** `https://btinvest.vn/` ra web mới; chưa đăng nhập thì mọi đường `/api/` trả 401 (trừ `/api/suc-khoe`);
  hai web cũ và `crypto.btinvest.vn` không đổi. Đăng nhập coin thật chạy được với phiên có sẵn trong trình duyệt của
  ứng dụng: phiên hết hạn được trang đăng nhập làm mới, web hiện "Tài khoản đang chờ duyệt", số liệu trả 403.
  `btinvest-web` dùng 160 MB trên 768 MB.
- **Việc tôi tự quyết trong phạm vi được giao:** giới hạn RAM 768 MB thay cho 512 MB dự kiến (máy còn trống hơn 8 GB);
  không đẩy commit ghi kết quả này, vì đẩy là deploy lại cả bốn container mà không đổi mã.
- **Hệ quả cần nhớ:** từ nay mỗi lần đẩy `main` là deploy cả web mới, và lệnh deploy chờ cả `btinvest-web` khỏe; đổi
  `.env` trên VPS thì phải `docker compose up -d --force-recreate btinvest-web`.
- **Chưa làm, chưa kiểm:** B3 (chưa ai là Quản trị nên chưa ai xem được số trên web mới); màn hình số liệu trên VPS
  chưa ai thấy, chưa so số với web cũ; điện thoại thật, âm thanh, thông báo trình duyệt (B6); sao lưu `web_user.db`
  chưa gắn lịch (B7), tức dữ liệu người dùng hiện CHƯA có bản sao lưu nào; đo tải trong giờ khớp lệnh và 9 test trượt
  (B8); `Dockerfile` trên VPS khác bản sao 4 dòng.

### D112 — Web hợp nhất lát 6: sao lưu `web_user.db` theo lịch, Quản trị đầu tiên (2026-11-25, người dùng « Gắn sao lưu »)

- **Người dùng duyệt** bước B7: thêm job sao lưu vào lịch của `vn100-worker`, 23:00 mỗi ngày, giữ 14 bản, chỉ khởi
  động lại worker. Giờ 23:00 do tôi đề xuất: không trùng job nào và sau giờ mọi người nhập lệnh trong ngày.
- **Đã làm:** thêm dòng `("web-user-backup", range(0, 7), "23:00", ["python", "scripts/backup_web_user_db.py"])` và ba
  phép tự kiểm vào `scheduler.py` (cả kiểm tên job không trùng, vì trạng thái lưu theo tên); sao lưu tệp cũ trên VPS,
  chép tệp mới, `--selftest` đạt, `docker compose build`, `docker compose up -d vn100-worker`. Ba container còn lại
  không bị tạo lại.
- **Kiểm:** chạy tay script hai lần trong worker ra đúng một bản `web_user-20261125.db`; bản sao và tệp gốc cùng số
  dòng ở cả năm bảng, `integrity_check` đạt. Worker mới có biến `WEB_USER_DB_URL` (worker cũ tạo trước B4 chưa có).
- **Hạn chế đã biết của lịch:** ô 23:00 sát nửa đêm nên chỉ chạy bù được tới 23:59 (`due` tính ô giờ theo ngày hiện
  tại); worker tắt trong khoảng đó thì hôm ấy không có bản. Job lỗi chỉ để lại `exit=1` trong nhật ký worker, không
  báo đi đâu. Bản sao lưu cùng ổ với tệp gốc.
- **B3 do người dùng tự làm lúc 19:28:** `WEB_ADMIN_EMAILS` có một mục (chỉ hỏi ứng dụng có hay không, không in giá
  trị); tài khoản đang chờ duyệt tự thành Quản trị. Sau đó cả năm tab của web mới ra số thật trên VPS.
- **Chưa kiểm:** lần chạy theo lịch đầu tiên (23:00 ngày 25/11); so số từng mã với web cũ; điện thoại thật, âm thanh,
  thông báo; tải trong giờ khớp lệnh. Hai lỗi nhỏ thấy thêm, chưa sửa: đổi `#tab` trên địa chỉ khi trang đang mở không
  chuyển tab; chưa có favicon.

### D113 — Web hợp nhất: đổi `#tab` trên địa chỉ thì chuyển tab; biểu tượng trang (2026-11-25, người dùng « Sửa và đẩy »)

- **Lỗi 1:** giao diện chỉ đọc phần `#tab` của địa chỉ một lần lúc mở trang, nên gõ tay, bấm liên kết hay mở dấu trang
  sang tab khác khi trang đang mở thì không có gì xảy ra. Sửa ở `web/app.js`: nghe sự kiện `hashchange`, tên trùng một
  trong năm tab thì gọi đúng hàm `datDangXem` mà nút menu vẫn gọi; tên lạ thì giữ nguyên tab. `ghiDiaChi` dùng
  `replaceState` nên không gọi vòng lại sự kiện này.
- **Lỗi 2:** web chưa có biểu tượng trang (`/favicon.ico` trả 404). Thêm `web/favicon.ico` (16, 32, 48) và
  `web/apple-touch-icon.png` (180, phủ kín vì iOS không nhận nền trong suốt), hai thẻ `<link>` trong `web/index.html`.
  Hình vẽ bằng Pillow từ đúng dấu hiệu trên đầu trang (`.hieu-dau`): nền `--navy-dam` #113579, chữ B trắng, chữ T
  `--vang` #e0b04a, phông Be Vietnam Pro ExtraBold của bộ nhận diện, bo góc 20%. Không dùng logo đầy đủ vì nến và chữ
  INVEST nhòe ở cỡ 16 điểm ảnh.
- **Kiểm:** test mới `test_khung_web_va_bieu_tuong_mo_duoc_khi_chua_dang_nhap` (trang chỉ trỏ tới tệp có thật, đúng là
  tệp ảnh, không tạo dòng tài khoản); 71 test web qua. Trình duyệt tại máy: đổi `#etf`, `#phai-sinh`, `#chung-quyen` thì
  tab, tiêu đề và ô nội dung đổi theo, `#khong-co` giữ nguyên; ở cỡ điện thoại ô nội dung trượt sang đúng tab.
- **Thấy thêm, CHƯA sửa vì là đổi cách dùng chứ không phải lỗi:** chuyển tab và mở tờ chi tiết mã chỉ thay địa chỉ tại
  chỗ (`replaceState`), không tạo bước lịch sử, nên nút Back hay vuốt lùi trên điện thoại rời khỏi web thay vì về tab
  trước hoặc đóng tờ. Chờ người dùng chốt muốn Back làm gì.

### D114 — Web hợp nhất: nút Back về tab trước và đóng tờ thay vì rời web (2026-11-25, người dùng « Có. Sửa back »)

- **Trước đó:** chuyển tab và mở tờ chi tiết chỉ sửa địa chỉ của bước hiện tại (`replaceState`). Đo trên btinvest.vn: ba
  lần bấm tab và một lần mở tờ không thêm bước lịch sử nào, nên Back hay vuốt lùi trên điện thoại rời khỏi web.
- **Cách làm (`web/app.js`, chỉ giao diện, không đụng máy chủ):** mỗi bước lịch sử giữ `{tab, loai, ma, sau}`.
  Thêm bước khi chủ động chuyển tab (menu, ô tìm, đổi `#tab`), khi vuốt ngang trên điện thoại đã dừng ở tab khác, và
  khi mở tờ trên một bước tab. Đổi nội dung tờ đang mở chỉ sửa bước của tờ (một tầng tờ: Back đóng hẳn tờ, không
  quay về tờ trước). `popstate` và `hashchange` cùng gọi `theoBuoc` để đưa giao diện về đúng bước vừa tới, kể cả mở
  lại tờ khi Forward. Đóng tờ bằng nút lùi, Esc, bấm ra ngoài hay vuốt xuống thì `history.back()` đúng một bước; bấm
  thêm lần nữa khi đang lùi không lùi tiếp.
- **Ba chỗ tôi tự quyết trong phạm vi được giao:** (1) địa chỉ có sẵn `?ma=` (liên kết chia sẻ) mở tờ mà không thêm
  bước, đóng tờ thì đóng tại chỗ, Back vẫn về nơi người dùng đến từ đó; (2) đang mở tờ mà chọn ở ô tìm một mã thuộc tab
  khác thì tab mới là một bước riêng, để đóng tờ mới vẫn ở lại tab mới; (3) hết phiên đăng nhập thì chuyển sang trang
  đăng nhập bằng `location.replace`, để Back không phải đi qua một bản thừa của web.
- **Lỗi của chính bản sửa, lộ ra khi thử ở cỡ điện thoại và đã sửa trước khi commit:** lúc web tự trượt về tab cũ sau
  Back, bộ đếm "cuộn đã dừng" có lúc tưởng người dùng vừa vuốt và ghi thêm hai bước thừa. Nay web đánh dấu tab đích
  khi tự trượt (`dichCuon`) và chỉ coi là vuốt tay sau khi người dùng chạm vào vùng nội dung. Sửa kèm hai chỗ liên
  quan: tờ đang khép mà mở tờ Danh mục, Cảnh báo, Tài khoản thì tờ mới không bị ẩn theo; khi web tự trượt, tên tab
  không còn nhảy qua các tab ở giữa.
- **Kiểm:** trình duyệt tại máy, 40 bước thao tác ở cỡ máy tính và điện thoại (chuyển tab, vuốt, mở và đóng tờ bằng
  bốn cách, Back, Forward, ô tìm, địa chỉ có `?ma=`, tên tab lạ), đối chiếu số bước lịch sử, địa chỉ, tab và trạng
  thái tờ sau từng bước; console không có lỗi. 71 test web qua (phần Python không đổi).
- **Hạn chế:** chưa có test tự động cho JavaScript của giao diện, nên phần này chỉ được kiểm bằng tay; chưa thử vuốt
  lùi trên điện thoại thật (Safari iOS, Chrome Android).

### D115 — Web hợp nhất: tờ mã rộng 3/5 màn hình, định giá và giá mục tiêu lên đầu (2026-11-25, người dùng nhắn sáu yêu cầu mới)

- **Người dùng yêu cầu** (sau khi xem bản trên máy tính): bảng hiện ra khi bấm mã "nhỏ quá, cho to ra 3/5 màn hình";
  "đưa định giá và giá mục tiêu lên đầu, khoảng 4–5 dòng, sau đó mới tới dòng tiền, làm nổi bật phần so sánh với công
  ty chứng khoán". Kèm bốn việc khác (nút sinh báo cáo AI bản ngắn, trang chủ tách từng phần, biểu tượng Zalo và
  Facebook và liên hệ, góc chat AI con ếch học theo TCBS): ghi ở mục 15 của `docs/PLAN_WEB_HOP_NHAT.md`, hỏi từng câu
  rồi mới làm.
- **Đã làm (`web/app.js`, `web/app.css`; không đụng máy chủ, không đổi số nào):** chi tiết ở mục 15 của kế hoạch. Tờ
  rộng `max(560px, 60vw)`; khối đầu gồm câu giá trị hợp lý so với thị giá, thước, nhãn, và bên cạnh là trung vị công
  ty chứng khoán với dải giá mục tiêu; "So với công ty chứng khoán" thành mục riêng mở sẵn sau biểu đồ.
- **Tôi tự quyết:** "giá mục tiêu" hiểu là giá mục tiêu của công ty chứng khoán (trung vị và khoảng), đặt cạnh giá
  trị hợp lý của mô hình; áp bề rộng mới cho mọi loại tờ vì chung một khung; câu phương pháp dài chuyển xuống phần
  chi tiết để khối đầu gọn.
- **Lỗi lộ ra khi thử và đã sửa:** (1) tên lớp CSS của khối mới (`tt`) trùng với lớp đang dùng cho ký hiệu "trung
  tính", làm ba dòng phiếu giãn cao 155px: đổi thành `dgd`; (2) gõ lại đúng địa chỉ đang mở (có `?ma=`) làm tờ bị
  đóng, do bản sửa nút Back (D114) coi bước không có trạng thái là "đóng tờ": nay giữ tờ khi `?ma=` trên địa chỉ vẫn
  là mã của tờ.
- **Kiểm:** trình duyệt tại máy ở 1440×900 (tờ rộng 864px, đúng 60%) và 375×812; thứ tự các khối, ba dòng phiếu cao
  64–65px, console không lỗi; các luồng Back của D114 chạy lại vẫn đúng. Test Python của web vẫn qua (không đổi máy
  chủ). Số trên máy Mac là số cũ (nhãn "Chưa xếp hạng" do DB cũ), chưa xem với số thật trên VPS.
- **Chưa làm:** bốn việc còn lại; chưa đẩy lên VPS (cả D114 lẫn D115 mới ở máy).

### D116 — Web hợp nhất: nút sinh báo cáo AI bản ngắn trên tờ mã (2026-11-25, người dùng « mọi người được duyệt đều được bấm, giới hạn 5 lần/tk … khoảng 500 từ »)

- **Người dùng chốt** (trả lời câu hỏi có đề xuất của tôi): mọi tài khoản đã duyệt bấm được, mỗi tài khoản 5 lượt mỗi
  ngày, báo cáo khoảng 500 từ, "phân tích tổng quan cả công ty, nhận định về mã đó sâu sắc".
- **Đã làm:** `valuation/services/web_ai_report.py`, hai đường `GET`/`POST /api/co-phieu/{ma}/bao-cao-ai` trong
  `web_user_routes.py`, khối "Báo cáo AI" trên tờ mã, cấu hình `web.ai_report`. Chi tiết ở mục 15 của kế hoạch.
- **Không bịa số:** gói số liệu lấy đúng hàm của bản dài (`run_deterministic_checks`, `collect_consensus_context`,
  `collect_market_context`, `corporate_actions_context`, `_compact_payload`), thêm dòng tiền của tờ mã. Câu lệnh cấm
  số ngoài gói, cấm tự tính phần trăm (Python tính sẵn `tinh_san`: giá tham chiếu ÷ thị giá − 1, cùng định nghĩa upside
  của web), cấm nêu giá trị hợp lý của mô hình khi chưa được công bố. Không có bước Python đối chiếu từng con số trong
  bài với gói dữ liệu (bản dài cũng không có): còn phụ thuộc vào việc AI tuân lệnh.
- **Tôi tự quyết:** bản báo cáo dùng chung theo mã (người sau thấy bản người trước sinh); dữ liệu không đổi thì dùng lại,
  không mất lượt; lỗi không mất lượt; mô hình chọn như bản dài (thường `deepseek-v4-flash`, dữ liệu có lỗi hoặc từ hai
  cảnh báo trở lên thì `deepseek-v4-pro`); lưu bằng tệp và đếm lượt trên `web_audit` để KHÔNG phải đổi schema; giữ mục
  bản dài của web cũ, đổi tên thành "Báo cáo AI bản dài (sinh ở web cũ)".
- **Thử thật tại máy (DB máy Mac cũ, giá đến 16/11):** lần 1 ra 618 từ, AI tự chia ra "upside khoảng 37%", gọi trung vị
  là "trung bình", viết "lớn nhất Việt Nam" và mã cờ STALE_PRICE. Siết câu lệnh (`ngan-v2`), thêm `tinh_san`, bỏ giá trị
  hợp lý của mô hình khỏi gói công ty chứng khoán khi chưa công bố; lần 2 ra 455 từ, dùng đúng 36,9% Python tính và
  gọi đúng trung vị. Mỗi lần khoảng 13.000 token vào, 1.000–1.250 token ra.
- **Lỗi có sẵn lộ ra và đã sửa tận gốc:** `collect_consensus_context` hứa "nguồn web tạm lỗi thì dùng DB và cảnh báo"
  nhưng không bắt lỗi của httpx (không phải OSError), nên trang 24hmoney không vào được làm sập cả lượt sinh báo cáo AI
  (cả bản dài của web cũ). Viết test tái hiện trước (`test_consensus_context_survives_unreachable_broker_site`), rồi bắt
  thêm `httpx.HTTPError` đúng ở chỗ tải trang.
- **Kiểm:** 15 test mới (hạn mức tính tay 4, 3, 2, 1, 0 rồi chặn; mốc 0 giờ Việt Nam; dùng lại không mất lượt; lỗi không
  mất lượt; chặn chưa đăng nhập, chưa duyệt, thiếu Origin, mã lạ, bấm hai lần; lời gọi DeepSeek đúng một lần, không thử
  lại; gói dữ liệu thật áp cổng công bố); hai phép tính tay của tôi trong test ban đầu sai và đã được test bắt. 110 test
  web và báo cáo AI qua; ruff, black, mypy sạch trên tệp mới.
- **Chưa kiểm:** chưa chạy trên VPS (số thật, thư viện và quyền ghi thư mục đệm trong container `btinvest-web`); chưa
  có test tự động cho JavaScript của khối mới.

### D117 — Báo cáo AI bản ngắn: ít số, nói chiều hướng, điều ít người để ý, so với đối thủ (2026-11-25, góp ý của người dùng)

- **Người dùng góp ý** sau khi xem bản thử của D116: "nhận định không cần nhắc các con số quá nhiều. Chỉ nhận định
  nhanh chiều hướng là được, tập trung vào những thứ quan trọng mà ít người nhìn thấy từ công ty này. Và so sánh với
  các đối thủ cùng ngành."
- **Đã sửa (`web_ai_report.py`, câu lệnh `ngan-v3`):** cả bài tối đa 5 con số, còn lại nói bằng chiều hướng; bố cục mới
  kết luận, tổng quan, **Điều ít người để ý** (2–3 ý, mỗi ý phải nói căn cứ, gợi ý chỗ tìm: lợi nhuận và doanh thu đi
  ngược nhau, chất lượng lợi nhuận, dòng tiền kinh doanh so với lợi nhuận, biên, nợ vay, phụ thuộc một mảng, công ty
  chứng khoán nhìn khác nhau, dòng tiền ngược chiều giá, cờ dữ liệu), **So với cùng ngành** (gọi tên đối thủ trong bảng
  cùng ngành của đợt xếp hạng VN100: ROE, tăng trưởng doanh thu, nợ, chuyển đổi tiền, điểm phòng thủ và tích sản; không
  có dữ liệu thì nói thẳng), nhận định nghiêng về đâu, 3 rủi ro. Lưu thêm `so_con_so` trong tệp để theo dõi.
- **Cổng công bố, lỗ hổng tìm thêm:** bảng cùng ngành (lấy từ đợt xếp hạng) của bản dài chép cả giá trị hợp lý và
  upside của chính mã; kết quả chưa công bố thì nay bỏ ở đó nữa (`_hide_model_value`), như đã bỏ ở gói công ty chứng
  khoán. Bản dài của web cũ vẫn gửi các giá trị đó: chưa sửa vì ngoài phạm vi, ghi lại để quyết sau.
- **Thử thật một lần tại máy (VRE, số liệu cũ):** 544 từ, 11 chuỗi số theo cách đếm của máy nhưng phần lớn là năm; số
  tiền và phần trăm chỉ còn "khoảng 37%" (làm tròn từ 36,9% Python tính) và hạng phòng thủ 16. Tôi đối chiếu ba "điều ít
  người để ý" với gói số liệu: lợi nhuận sau thuế FY2025 6.446 tỷ cao hơn EBIT 3.893 tỷ (thu nhập ngoài hoạt động lớn),
  hệ số chuyển đổi tiền −0,51, vay dài hạn 2.523 tỷ (FY2024) lên 6.341 tỷ (TTM) trong khi tiền mặt giảm: đều có căn cứ.
  Bài vẫn dài hơn 500 từ một chút và vẫn tự làm tròn phần trăm.
- **Kiểm:** 17 test của báo cáo AI qua (thêm ca tính tay đếm con số, ca che giá trị mô hình trong bảng cùng ngành, kiểm
  câu lệnh có đủ yêu cầu mới).

### D118 — Web hợp nhất: bốn ô đầu trang chủ; tệp giao diện luôn hỏi lại máy chủ (2026-11-26, người dùng « Đồng ý bốn ô »)

- **Người dùng chọn** đề xuất bốn ô (việc 4 của mục 15): trang chủ "quá đồng nhất", muốn tách nổi bật từng phần.
- **Đã làm (`web/app.js`, `web/app.css`):** `veBonO()` vẽ bốn ô ngay dưới dải VN-Index; mỗi ô dùng đúng con số mở đầu của
  tab tương ứng (không tính số mới), dữ liệu tab nào về thì ô đó hiện. Bấm phần trên của ô thì sang tab (một bước lịch
  sử, Back về trang chủ); bấm mã trong ô thì mở tờ của mã. Bỏ `veHnKhac` và khối "Chứng quyền và ETF" vì trùng số với
  ô (AGENTS.md mục 9: mỗi chỉ số hiện một lần). Phái sinh nạp ngay lúc vào trang thay vì chỉ khi mở tab.
- **Tôi tự quyết:** không thêm màu riêng cho từng loại tài sản (AGENTS.md mục 9: màu chỉ mang nghĩa); tách bằng khung,
  biểu tượng, cỡ chữ của con số. Trên điện thoại ẩn hàng mã trong ô (bốn ô cao 163px thay vì 294px) để còn thấy phần
  bên dưới ngay màn hình đầu.
- **Lỗi lộ ra khi thử và đã sửa tận gốc:** tệp tĩnh (`/`, `app.js`, `app.css`) chỉ có ETag và Last-Modified, không có
  `Cache-Control`, nên trình duyệt tự giữ bản cũ một thời gian (thấy thật: sửa xong vẫn chạy app.js cũ). Sau mỗi lần deploy
  người dùng có thể chạy giao diện cũ với API mới. Viết test trước (`test_khung_web_luon_hoi_lai_may_chu_sau_deploy`),
  rồi cho `StaticFiles` của `web_main.py` gắn `Cache-Control: no-cache` (vẫn có ETag nên hỏi lại chỉ là yêu cầu nhỏ trả
  304). Riêng lần đẩy đầu tiên có tiêu đề này: trình duyệt đã lưu bản cũ (không có tiêu đề) có thể vẫn giữ nó vài giờ,
  tải lại trang là hết.
- **Kiểm:** trình duyệt tại máy ở 1440×900 (bốn ô cùng cao, mỗi ô 262px rộng) và 375×812 (2×2); bấm ô sang tab, Back về
  trang chủ, bấm mã trong ô mở tờ, console không lỗi. 89 test web qua.

### D119 — Web hợp nhất: nút Liên hệ; danh sách dài trong khung cuộn cùng kiểu (2026-11-26, người dùng « Đồng ý, các mã … quá dài, cho hiển thị dạng thanh cuộn cho đồng nhất tất cả dữ liệu »)

- **Liên hệ (người dùng đồng ý đề xuất):** nút điện thoại trên thanh đầu mở thực đơn ba kênh (Zalo, gọi điện, Facebook
  "BT Tài Chính"), cùng ba kênh thành hàng cuối trang chủ. Số và đường dẫn lấy từ trang luyện thi của người dùng, đặt ở
  `web.lien_he` (`config/defaults.yaml`), trả qua `/api/toi` (người chờ duyệt cũng nhận được); giao diện chỉ nhận đường
  dẫn `https://` và `tel:` chỉ có số. Test `test_lien_he_lay_tu_cau_hinh_ke_ca_khi_cho_duyet`.
- **Tôi tự quyết khác đề xuất:** trên điện thoại (dưới 600px) thêm nút này làm ô tìm mã chỉ còn 57px (đo thật), nên ẩn
  nút và đưa "Liên hệ BT Invest" vào thực đơn tài khoản; trên máy tính giữ nút như đã chốt.
- **Khung cuộn:** tôi hiểu "các mã quá dài" là các danh sách mã trong từng tab kéo trang rất dài (danh sách 100 cổ phiếu
  làm tab Cổ phiếu cao khoảng 10.000px). Nay mọi danh sách và bảng dài nằm trong khung cuộn cùng một kiểu (`khung()` và
  `bang(…, true)` trong `web/app.js`, cao `min(560px, 64vh)`, điện thoại `min(460px, 58vh)`): tab Cổ phiếu còn khoảng
  1.700px. Bảng có dòng tiêu đề đứng yên khi cuộn. Chứng quyền bỏ phân trang "Hiện thêm", vẽ đủ cả nhóm trong khung (461
  mã vẽ trong khoảng 230ms ở máy Mac). Hiệu ứng phóng dòng khi rê chuột đổi sang đọc vị trí mọi dòng trước rồi mới ghi,
  bỏ qua dòng không đổi, để vài trăm dòng không làm giật.
- **Không nằm trong khung:** bảng trong tờ chi tiết, Danh mục, Cảnh báo, Tài khoản (đã ngắn hoặc có nút mở rộng). Nếu
  người dùng muốn cả bốn ô ở trang chủ cuộn ngang thì là việc khác: hỏi lại.
- **Kiểm:** trình duyệt tại máy ở 1440×900 và 375×812: thực đơn và hàng liên hệ đúng đường dẫn, khung cuộn ở cả năm tab
  (cao 558px, nội dung 1.247–39.976px), console không lỗi. 90 test web qua.

### D120 — Web hợp nhất: góc chat AI "Hỏi Ếch" dùng số liệu của chính web (2026-11-26, người dùng « Đồng ý »)

- **Người dùng đồng ý đề xuất:** con ếch ở góc dưới bên phải, bấm vào mở khung chat; có câu hỏi gợi ý; Ếch chỉ trả lời
  từ số liệu của web qua trợ lý sẵn có của bot Discord (DeepSeek chọn công cụ, Python lấy số, DeepSeek viết lời); câu
  trả lời ngắn, kèm nút mở đúng mã; mỗi tài khoản 20 câu mỗi ngày; thêm vài phần học từ cách TCBS chia công cụ, tự tính
  từ dữ liệu của web. Không gọi TCBS từ web (lý do ở mục 15 của `docs/PLAN_WEB_HOP_NHAT.md`).
- **Năm công cụ mới** (`valuation/services/web_chat_tools.py`, chỉ đọc, chỉ web dùng; bot Discord giữ nguyên bảy công
  cụ cũ): `market_today` (đúng số của tab Hôm nay: nhãn thị trường, VN-Index, bốn trụ cột, kháng cự và hỗ trợ, ngành
  mạnh yếu, mã có lực); `breadth` (số mã VN100 tăng, giảm, đứng giá từng phiên, tối đa 60 phiên); `index_movers` (mã kéo
  rổ VN100 lên, xuống: đóng góp = tỷ trọng vốn hóa đầu kỳ × tỷ suất giá, vốn hóa = giá điều chỉnh × số cổ phiếu lưu
  hành hiện tại, nên là **ước tính trên rổ VN100**, không phải điểm VN-Index); `technical` (giá so với 6 đường trung
  bình 5–200 phiên, RSI14, MACD, cách đỉnh và đáy 250 phiên, chỉ là mô tả); `peers` (các mã cùng ngành trong đợt xếp
  hạng: ROE, tăng trưởng doanh thu, điểm phòng thủ và tích sản, hạng của mã; mã chưa qua cổng công bố thì không đưa
  upside; cột trống ở cả ngành như nợ xấu ngoài ngân hàng thì bỏ để AI không nhắc).
- **Trợ lý dùng chung (`assistant.py`):** `ask`, `plan_request`, `validate`, `write_answer` nhận thêm bộ công cụ và lời
  dặn trả lời riêng; bỏ trống thì đúng như bot Discord (test cũ của bot vẫn qua). Số gốc của các công cụ mới viết
  kiểu Việt Nam.
- **Dịch vụ và đường API:** `valuation/services/web_chat.py`; `GET /api/hoi-ai` (lượt còn, câu gợi ý) và `POST
  /api/hoi-ai` (tài khoản đã duyệt, gửi từ chính trang, câu hỏi tối đa 300 ký tự). Mỗi người một câu đang chạy một lúc.
  Lượt đếm trên `web_audit` (việc `hoi_ai`, ngày theo giờ Việt Nam), chỉ ghi tên công cụ đã chạy và độ dài câu, **không
  lưu câu hỏi**. Không tính lượt khi AI lỗi (báo 502, không chép thông điệp gốc) hoặc câu ngoài phạm vi (không chạy
  công cụ nào). Không đổi schema. Cấu hình ở `web.chat` của `config/defaults.yaml`.
- **Lời dặn trả lời của web:** một câu kết luận rồi 2–5 gạch, dưới 180 từ; chỉ dùng số trong dữ liệu; ngày kiểu
  16/11/2026; nói rõ "ước tính trên rổ VN100" cho mã kéo rổ; kỹ thuật chỉ là mô tả; không tự khuyên mua bán.
- **Giao diện (`web/app.js`, `web/app.css`):** hình đầu con Ếch tay mơ lấy từ `~/video/luat_ck/video/src/Ech.tsx`. Điện
  thoại: khung chiếm cả màn hình, mở khung là một bước lịch sử nên Back đóng khung; máy tính: khung nổi 400px ở góc,
  không vào lịch sử. Đang mở tờ một cổ phiếu thì thêm hai câu gợi ý về đúng mã đó. Nút "Mở mã" đóng khung rồi mở tờ;
  bấm ếch lại thấy cuộc trò chuyện cũ (chỉ trong trang đang mở, tối đa 40 tin). Phần "Số liệu gốc" gập lại dưới mỗi
  câu trả lời. Enter gửi, trừ khi bộ gõ tiếng Việt đang ghép chữ. Mỗi câu được trả lời riêng, Ếch không nhớ câu trước
  (lời chào nói rõ điều này).
- **Thử thật tại máy với DeepSeek** (4 câu): thị trường hôm nay, mã kéo rổ 20 phiên, so sánh HPG với cùng ngành (2 lần).
  Mọi con số trong câu trả lời khớp số gốc của công cụ. Sửa sau lần thử: ngày đang viết kiểu 2026-11-16; AI kể ra
  những thứ không ai hỏi ("không có tin tức"); gọi thay đổi của cả rổ là "điểm phần trăm"; nhắc nợ xấu cho ngành thép;
  số gốc viết kiểu Anh. Mỗi câu mất khoảng 15–20 giây (hai lượt DeepSeek).
- **Kiểm:** 12 test mới (`tests/test_web_chat.py`: độ rộng, đóng góp vào rổ, kỹ thuật, cùng ngành đều có ca tính tay;
  bộ công cụ của bot không đổi; hạn mức 20 câu, lỗi và câu ngoài phạm vi không mất lượt; chặn quyền; công cụ chạy trên
  DB thật với mạng bị chặn). Trình duyệt tại máy ở 1440×900 (sáng, tối) và 375×812: Back và Forward, nút mở mã, gợi ý
  theo mã đang mở, console không lỗi. 109 test web và trợ lý qua.

### D121 — Dữ liệu luôn mới: giá cuối phiên, chặn phiên chưa chốt, vĩ mô Cục Thống kê, báo dữ liệu cũ (2026-11-26, người dùng « Làm tất cả »)
- **Vì sao:** người dùng thấy "nhiều thông tin bị cũ". Kiểm trên VPS (chỉ đọc, sáng 26/11; kế hoạch
  `docs/PLAN_CAP_NHAT_DU_LIEU.md`): giá chỉ vào DB lúc 07:50 sáng hôm sau (chiều tối web chậm một phiên; ngày 24/11 sàn
  nghỉ, TCBS và FHSC đều không có phiên này, không phải lỗi); CPI, bán lẻ, GDP nạp tay, đứng ở tháng 9, tháng 6, quý 2;
  ETF chỉ chạy 09:40; Quét VN100 23/11 chỉ đủ 55/100 mã (VCI trả 418 64 lần, quá giờ chờ 106 lần); dòng giá MCH 25/11 ghi
  giữa phiên (đóng 133.000, khối lượng 22.200; thật 130.000, 472.904); `ingested_at` của BCTC quý 3 trống cả 22.358 dòng.
- **A. Chặn phiên chưa chốt + lượt cuối phiên:** `valuation/ingest/session_guard.py`: trước `market_session.close`
  (15:00) mọi đường ghi (`pipeline.run_ingest`: job giá, Quét VN100, nút "Tải mới" ở web cũ; `fhsc_bridge.prefetch`) bỏ
  dòng của hôm nay, cả giá lẫn khối ngoại, tự doanh (D97 trước đây chỉ bỏ dòng tiền và bỏ cả sau giờ đóng). Hệ quả: nút
  "Tải mới" của web cũ trong giờ giao dịch không còn hiện giá giữa phiên (người dùng duyệt trong kế hoạch). Job mới
  `gia-cuoi-phien` 15:45 T2–T6 (`scripts/update_close_prices.py` = `refresh_market(corporate_actions=False)`, không gửi
  Discord). Mỗi lượt tải so phiên mới nhất trước/sau (`recheck_session`); báo cáo sáng ghi "Tải lại phiên …: x mã đổi
  giá" khi lượt 15:45 hôm trước chưa chốt số → tự đo ba ngày đầu thay cho bước đo tay trong kế hoạch.
- **B. Vĩ mô Việt Nam:** tradingeconomics chặn mọi lượt tải tự động (403 cả trình duyệt headless) → không lách. Dùng
  nguồn gốc: báo cáo kinh tế – xã hội hằng tháng của Cục Thống kê (`valuation/ingest/nso_reports.py`, httpx, chỉ mở được
  từ IP Việt Nam). Đọc 4 bài mới nhất, tìm đúng ba câu mẫu (CPI so cùng kỳ, bán lẻ so cùng kỳ, GDP quý); không thấy câu
  thì không ghi. Chỉ thêm kỳ chưa có; kỳ đã có mà số khác thì báo `revisions`, không ghi đè. Đối chiếu trên 3 bài thật:
  CPI 9/2026 5,08% và bán lẻ 6/2026 14,8% khớp DB; CPI 10/2026 5,09%, bán lẻ 10/2026 14,7%, GDP quý III 9,95% khớp
  tradingeconomics. Job `vi-mo-vn` 07:25 T2–T6. **Tín dụng (`CREDIT_GROWTH`) không tự nạp:** chuỗi là số cả năm (31/12);
  số lũy kế giữa năm (báo cáo quý III: 10,89% tới 28/9) cho vào cùng chuỗi thì `MacroContext.from_db_momentum` so 10,89%
  với 15,08% cả năm 2024 → sai chiều. Điểm 31/12/2025 vẫn là số mới nhất. **GDP quý II/2026:** DB 8,39% (ước tính đầu),
  Cục Thống kê đã sửa thành 8,81% → chờ người dùng quyết có sửa không.
- **C. Báo dữ liệu cũ, job lỗi:** `valuation/services/freshness_alert.py` + job `kiem-du-lieu-sang` 08:20 và
  `kiem-du-lieu-chieu` 16:10 T2–T6: giá chậm quá `max_lag_weekdays` (1) ngày làm việc, phiên mới nhất thiếu mã (dưới 95),
  vĩ mô cũ hơn ngưỡng theo kỳ số liệu (chỉ thứ Hai) → một tin Discord. Không có lịch nghỉ lễ: Tết sẽ báo nhầm, tin có ghi
  chú. `scheduler.py` gọi `scripts/notify_job_failure.py` khi job thoát mã khác 0 (tin chỉ có tên job, mã, giờ, đường dẫn
  nhật ký; không chép nội dung nhật ký). Quét VN100 thôi gọi job `flow_daily` đã tắt (hết dòng "dòng tiền lỗi (mã 4)").
- **D. ETF:** `~/cw_scanner/chay_etf_tu_dong.sh --no-discord`; lịch `etf-chieu` 15:10 T2–T6 thêm vào
  `/srv/apps/chungquyen/scheduler.py` (chỉ có trên VPS). Web chứng quyền khi đó ghi "Số liệu lúc 15:10" không kèm "trong
  phiên".
- **E. Quét VN100:** `status.json` có `missing` (mã → phần thiếu: giá, dòng tiền, BCTC BS/IS/CF quý/năm) và
  `missing_summary`; job `quet-bu` 20:00 thứ Hai, thứ Năm (`scripts/retry_partial_update.py`) tải lại đúng phần thiếu,
  giãn 3 giây/mã, kết quả `retry.json`, còn thiếu thì thoát mã 1 (báo Discord). `ingested_at` ghi rõ khi thêm BCTC (bảng
  thật không có DEFAULT) và khuyến nghị CTCK 24hmoney/Simplize (dòng cũ trống thì điền lần thấy lại đầu tiên). Chuyển BCTC
  sang FHSC (`docs/PLAN_VNSTOCK_V6.md`) là kế hoạch riêng, chưa làm.
- **Không đổi:** schema, mô hình định giá, ngưỡng định giá. Dữ liệu vĩ mô mới đi vào lớp phủ vĩ mô sẵn có
  (`forecast/drivers.py`) ở đợt định giá kế tiếp, như thiết kế.
- **Kiểm:** test mới `tests/test_session_guard.py` (tái hiện MCH 25/11 10:05; sau 15:00 ghi), `tests/test_nso_reports.py`
  (câu mẫu tháng/quý, tháng 12 đăng năm sau, số âm, dấu chấm hàng nghìn, chữ không ở dạng NFC, chỉ thêm kỳ mới, ngoài
  khoảng thì không ghi, chặn host lạ), `tests/test_freshness_alert.py` (ngày nghỉ giữa tuần không báo, chậm 2 ngày thì
  báo, dòng lạc một mã, vĩ mô theo tuổi kỳ, quét bù chỉ gọi phần thiếu), cập nhật `test_fhsc_bridge`,
  `test_daily_report`, `test_data_update_job`; `scheduler.py --selftest`.
- **Lên VPS 26/11 10:50 và sửa thêm cùng ngày:** người dùng duyệt « Ghi theo cục thống kê »: GDP quý II/2026 sửa 8,39% →
  8,81% và thêm quý I/2026 8,15% (DB thiếu), nguồn câu « cao hơn mức tăng 8,15% của quý I và 8,81% của quý II » trong
  báo cáo quý III. Lượt kiểm chạy bù 10:50 báo "Phiên 26/11 chỉ 25/100 mã có giá" vì đợt Quét VN100 sáng (còn code cũ)
  đã ghi giá giữa phiên cho 31 mã. Sửa theo người dùng « Sửa luôn »: lượt kiểm chỉ lấy phiên ĐÃ CHỐT làm phiên mới
  nhất, còn dòng của phiên chưa chốt thì báo riêng, kể tên mã (`freshness_alert.unfinished_problem`,
  `session_guard.unfinished_session_date(now, close)`). Test tái hiện:
  `test_run_check_reports_unfinished_session_rows_not_missing_tickers`.
