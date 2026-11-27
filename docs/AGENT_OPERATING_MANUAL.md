# Agent Operating Manual — Antigravity VN100

> File này dành cho mọi agent mới vào repo. Mục tiêu là hiểu hệ thống đang chạy
> thật, sửa đúng chỗ, không lặp lại lỗi dữ liệu/định giá đã gặp.

## 1. Đọc theo thứ tự này

1. `AGENTS.md`: luật nền bắt buộc.
2. `.agents/AGENT_HANDOFF.md`: checklist và lỗi đã gặp.
3. `.agents/rules/project-context.md`: trạng thái hiện hành của dự án.
4. File này: cách vận hành/sửa hệ thống thực tế.
5. Skill liên quan đến việc đang làm:
   - Dữ liệu/BCTC/giá/macro: `.agents/skills/financial-data-integrity/SKILL.md`
   - Định giá/model/ranking: `.agents/skills/valuation-models/SKILL.md`
   - Google Sheets 2 chiều: `.agents/skills/google-sheets-two-way/SKILL.md`
   - n8n: `.agents/skills/n8n-orchestration/SKILL.md`

## 2. Hệ thống đang chạy thật

- App chính là Streamlit: `streamlit_app.py`, chạy local cổng `8506`.
- Package nghiệp vụ chính: `valuation/`.
- Database đang dùng là SQLite portable:
  - `vn100_full.db`: file chạy local, không commit.
  - `vn100_full.db.gz`: bản nén được phép commit để khách tải về chạy được.
- Launcher:
  - macOS: `Chay_Dinh_Gia_VN100.command`
  - Windows: `Chay_Dinh_Gia_VN100_Windows.bat`
- `docs/spec.md` mô tả kiến trúc mục tiêu ban đầu. Không mặc định coi FastAPI,
  PostgreSQL hoặc n8n là đường chạy thật nếu người dùng không yêu cầu rõ.

## 3. Lệnh chạy nhanh

```bash
python -m streamlit run streamlit_app.py --server.port 8506 --server.headless true
```

Nếu cần kiểm tra health:

```bash
python3 -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8506/_stcore/health', timeout=5).read().decode())"
```

Khi đóng gói dữ liệu portable:

```bash
python scripts/ensure_portable_db.py
gzip -t vn100_full.db.gz
```

## 4. Luồng dữ liệu chính

- `valuation/data_access/repo.py`: đọc DB, map field BCTC vào model nội bộ.
- `valuation/models/financials.py`: cấu trúc `Company`, kiểm tra model
  integrity.
- `valuation/analysis/`: phân tích/ranking/tích sản.
- `valuation/forecast/` và `valuation/engine/`: dự phóng và định giá.
- `valuation/report/`: báo cáo, AI narrative, DOCX/HTML export.
- `valuation/views/`: UI Streamlit.

Nếu thấy cảnh báo dữ liệu, tìm nguyên nhân từ nguồn/map/taxonomy trước, không
ẩn cảnh báo để giá mục tiêu nhìn đẹp hơn.

## 5. Các lỗi dữ liệu đã gặp

- **CFI/CFF và CapEx:** CFI đã bao gồm CapEx âm. Khi model cũng lưu CapEx riêng,
  `cf_other` phải dùng `_cashflow_other_excluding_capex()` để tránh trừ CapEx hai
  lần. Xem `valuation/data_access/repo.py`.
- **Ticker lọt vào tích sản khi dữ liệu yếu:** ranking dài hạn không được chỉ dựa
  vào upside. Mã có cờ dữ liệu trọng yếu, thiếu BCTC quan trọng, đòn bẩy/cashflow
  không kiểm chứng được phải bị chặn hoặc hạ cấp rõ lý do.
- **Corporate actions bị lặp:** không nhồi toàn bộ lịch sử cổ tức/quyền mua vào
  AI summary. Phần sự kiện chi tiết có tab riêng; AI summary chỉ nhắc sự kiện khi
  nó ảnh hưởng luận điểm đầu tư.
- **Báo cáo AI cũ còn trong cache:** khi đổi cấu trúc prompt/section, phải tăng
  cache version trong `valuation/report/verified_summary.py` và xoá/normalize
  session keys cũ.

## 6. DeepSeek

- Chỉ gọi khi người dùng bấm nút sinh báo cáo/kiểm chứng.
- Mỗi lần bấm tối đa một API call cho toàn bộ narrative liên quan.
- Mở app, đổi mã, đổi tab, refresh Streamlit không được gọi DeepSeek.
- Ranking VN100/tích sản chỉ gọi DeepSeek khi dữ liệu hoặc danh sách thay đổi;
  nếu snapshot chưa đổi thì dùng cache.
- DeepSeek không sửa DB. Nó chỉ nêu nghi vấn/cảnh báo dựa trên dữ liệu Python
  đưa vào.

## 7. Báo cáo AI hiện hành

AI summary trong tab BCTC chỉ nên có các phần:

- Luận điểm đầu tư
- Tổng quan doanh nghiệp
- Bối cảnh ngành
- Kỹ thuật, dòng tiền và vị thế thị trường
- Rủi ro và điểm cần theo dõi

Không tạo section riêng tên "Cổ tức, tăng vốn và quyền cổ đông" trong summary
AI vì phần đó đã có tab dữ liệu chi tiết riêng.

## 8. VN100 ranking và tích sản

- Có hai nhóm khuyến nghị: thận trọng và tăng trưởng.
- Không hạ tiêu chuẩn để đủ 5-7 mã nếu dữ liệu không đạt. Nếu người dùng cho
  phép hạ tiêu chuẩn, phải ghi rõ tiêu chuẩn nào được hạ và rủi ro tăng thêm.
- Cần hiển thị lý do không đạt: thiếu dữ liệu, model integrity, định giá không
  đủ MOS, thanh khoản, chất lượng lợi nhuận, rủi ro ngành/vĩ mô, dòng tiền, nợ.
- Lịch cập nhật mong muốn: thứ Ba 09:30 cho ranking/tích sản; TPCP 10 năm thứ
  Ba 10:00 nếu automation được cài trên host chủ dự án.

### Báo cáo sáng & bot Discord

- `valuation/services/daily_report.py` tái dùng `market_data`/`ranking_table`/`accumulation_picks`
  (tab VN100) và `macro_panel.build_snapshot`; KHÔNG gọi DeepSeek. Cập nhật giá giữ
  `.data_update/worker.lock` để không ghi SQLite song song với "Quét VN100".
- `scripts/discord_bot.py` gọi thẳng `unified_report` (không cần FastAPI), chỉ nhận lệnh của
  mọi thành viên trong `DISCORD_CHANNEL_ID` (hoặc chỉ `DISCORD_OWNER_ID` nếu đặt), chỉ mã `is_vn100`; mã có
  `publication_allowed=False` không hiện FV và không gọi DeepSeek.
- Bot chỉ xử lý tin có @bot. Câu tự do đi qua `valuation/services/assistant.py`: DeepSeek chỉ chọn
  công cụ trong `TOOLS` (đọc DB/RSS), `validate()` kiểm tra lại tham số, lượt 2 viết lời từ dữ liệu.
  Thêm công cụ mới = thêm hàm chỉ đọc vào `TOOLS` + nhánh kiểm tra trong `validate()` + test.
- Lịch chạy bằng launchd `vn.antigravity-vn100.discord-bot` / `.daily-report` (chỉ host chủ).

### Tab "Dòng tiền ngành" (D73)

- Lõi `valuation/analysis/money_flow.py` là hàm thuần (test chặn import vnstock/streamlit/`valuation.ingest`);
  UI `valuation/views/money_flow.py` nhận `db` từ app, cache theo khóa dữ liệu + hash cấu hình. Không gọi mạng khi render.
- Dòng tiền chính xác (khớp/thỏa thuận, room) nằm ở bảng `flow_daily` (MetaData riêng). KHÔNG thêm vào `Base` của
  `valuation/db/models.py`; tạo bảng chỉ bằng `scripts/migrate_flow_daily.py --apply` (tự backup). Job
  `scripts/update_flow_daily.py` chạy 18:00 T2–T6; dòng `is_final` không bị ghi đè. Mã thoát: 0 ổn, 1 lỗi từng mã,
  2 chưa có bảng, 3 đang có job khác, 4 nguồn đổi cấu trúc, 5 bị giới hạn lượt gọi, 6 cấu hình/domain sai.
- Nhãn là HEURISTIC: chữ "Dấu hiệu gom/xả", không "tiền vào/ra", không "nên mua" (`forbidden_phrases` có test).
- Golden khối ngoại: CafeF GDKhoiNgoai chỉ tính KHỚP LỆNH — chỉ so `prices_daily` ở phiên không có thỏa thuận.

## 9. Khi sửa UI

- Tone thương hiệu hiện đang hướng tới xanh tài chính, gần cảm giác VPBank:
  tin cậy, rõ ràng, ít màu rối.
- Không dùng text giải thích dài dòng trong UI nếu có thể trình bày bằng tiêu
  đề, thẻ số liệu, bảng, tooltip và trạng thái ngắn.
- UI Streamlit phải nhẹ: tránh animation nặng, tránh gọi API trong render.

## 10. Trước khi báo xong

- Với code Python: chạy test liên quan, `ruff check`, `black --check` nếu khả thi.
- Với dữ liệu: in sample hoặc kiểm tra vài ticker đại diện, nhất là mã từng lỗi.
- Với GitHub: đọc `docs/SECURITY_AND_SECRETS.md` và
  `docs/GITHUB_UPDATE_WORKFLOW.md` trước khi commit/push.

## 11. Cập nhật dữ liệu trong ứng dụng

- `Tải mới <MÃ>` gọi API cho đúng mã đang mở: giá, BCTC quý và nguồn báo cáo
  CTCK. BCTC năm chỉ tải khi mã chưa có lịch sử, nhằm giảm thời gian và lượt gọi.
- `Nạp lại mô hình đã lưu` chỉ đọc DB trên máy, tuyệt đối không gọi API.
- Trạng thái độ mới phải tính theo từng mã và tách rõ giá với báo cáo CTCK.
  Không được dùng ngày mới nhất toàn VN100 để kết luận cho mã đang mở, và không
  hiển thị kiểu "dữ liệu cũ 0 ngày" khi thực tế chỉ báo cáo CTCK đã cũ.
- Mở app không tự quét toàn bộ VN100. Quét 100 mã chỉ chạy khi bấm nút hoặc qua
  lịch trên máy chủ dự án, tránh mỗi máy khách tạo hàng trăm lượt API.
- `run_ingest()` trả `SUCCESS`, `PARTIAL` hoặc `FAILED`. Mọi UI/script gọi hàm
  này phải đọc trạng thái trả về; không được coi là thành công chỉ vì hàm không
  ném exception. Mặc định `is_vn100=False`: mã mới không tự vào rổ (thành viên
  VN100 do `scripts/sync_vn100_universe.py` đặt). Route `/ingest` chỉ nhận mã
  thuộc VN100 ∪ công ty con trong `config/sotp_holdings.yaml`.
- Audit nguồn (`scripts/audit_vn100_data.py`) lưu tập kỳ đã đối chiếu
  (`audited_periods`) và dấu vân tay chỉ của các kỳ đó. Sau khi nạp BCTC kỳ mới,
  mã nhận `SOURCE_AUDIT_PARTIAL:<kỳ>` (cảnh báo, vẫn công bố); số của kỳ ĐÃ đối
  chiếu bị đổi → `SOURCE_AUDIT_STALE` (chặn). Quy trình sau mỗi mùa BCTC: làm mới
  cache nguồn `.vn100_ranking/sponsor/` rồi chạy lại audit để kỳ mới được đối chiếu.
  r3b: một kỳ chỉ vào `audited_periods` khi DB có ô trọng yếu khớp khóa nguồn (cache đi
  trước DB không còn làm STALE nhầm khi DB nạp kỳ đó); quá `audit.max_unaudited_periods`
  (2) kỳ chưa đối chiếu → `SOURCE_AUDIT_STALE:<các kỳ>` (chặn).
- **Quy trình audit sau mỗi mùa BCTC (D66)** — không ghi DB, chỉ ghi file audit/cache:
  1. Nạp giá/BCTC kỳ mới (Quét VN100 hoặc `scripts/update_all_data.py`); `weekly_updater` làm mới cả công ty
     con trong `config/sotp_holdings.yaml` (giá cũ → mã mẹ `SOTP_HOLDINGS_STALE`).
  2. `python scripts/collect_sponsor_data.py --financials` (không `--tickers` = VN100 ∪ công ty con SOTP).
     Cache `.vn100_ranking/sponsor/<MÃ>/` chỉ tải lại khi quá 7 ngày (`collect_sponsor_dataset(ttl_days=7)`),
     nên chạy khi nguồn đã có kỳ mới.
  3. `python scripts/audit_vn100_data.py` (đầy đủ): ghi `data/source_quality_status.json` +
     `.vn100_ranking/sponsor/source_audit.json`; đo ΔFV xung đột (F2c) trên bản sao DB trong bộ nhớ:
     ≤ `audit.source_conflict_fv_materiality_pct` (1%) → `SOURCE_CONFLICT_IMMATERIAL` (cảnh báo), còn lại
     `SOURCE_CONFLICT` (chặn). Chỉ chạy một nhóm mã: `--tickers` (gộp vào audit đã lưu).
  4. Kiểm còn mã nào `SOURCE_AUDIT_PARTIAL`/`STALE`/`SOURCE_CONFLICT`. Mùa Q4 + năm mà chưa audit lại thì
     số kỳ chưa đối chiếu vượt `audit.max_unaudited_periods` → STALE chặn hàng loạt.
  5. Đổi MÔ HÌNH (dữ liệu giữ nguyên) không làm audit cũ hết hạn, nhưng số ΔFV F2c trong status được đo bằng
     mô hình cũ → chạy lại audit, hoặc đo lại ΔFV các mã đang `SOURCE_CONFLICT*`.
- **Độ mới dữ liệu trên VPS (D121, `docs/PLAN_CAP_NHAT_DU_LIEU.md`):** giá vào DB hai lần mỗi ngày giao dịch,
  07:50 (báo cáo sáng) và 15:45 (`gia-cuoi-phien`), thêm lượt 17:45 (`tu-doanh-toi`, D128) để có tự doanh trong
  ngày. Trước 15:00, mọi đường ghi bỏ dòng của phiên hôm nay (`ingest/session_guard.py`), kể cả nút "Tải mới" ở web
  cũ. Web btinvest.vn hiện phiên đang chạy từ bảng giá Vietcap mà không ghi DB (`web_live.session_bars`,
  `web_flow.with_session`, D128); trình duyệt thấy `phien_db` đổi thì tự nạp lại các tab đọc DB. CPI, bán lẻ, GDP tự nạp 07:25 từ Cục Thống kê
  (`ingest/nso_reports.py`, chỉ thêm kỳ mới, số đã sửa thì báo chứ không ghi đè). Tín dụng vẫn nạp tay, số cả năm.
  `kiem-du-lieu-sang`/`-chieu` (08:20, 16:10) báo Discord khi giá chậm hoặc thiếu mã, vĩ mô cũ (thứ Hai). Job lỗi
  nào cũng báo Discord. Quét VN100 ghi `missing` trong `.data_update/status.json`; `quet-bu` 20:00 T2, T5 tải lại
  phần thiếu (`retry.json`).
- Client VNStock phải đưa `settings.vnstock_api_key` vào biến môi trường của
  tiến trình trước request đầu tiên. Không gọi `setup_api_key()` trong app vì
  hàm đó tạo thêm file chứa key trong thư mục HOME; `.env` vẫn là nơi lưu duy
  nhất của dự án.

## 12. Quy ước mô hình định giá (fx2, 20/10/2026)

- Cổng `VALUATION_LEGS_DIVERGE` dùng chung (`guardrails.legs_diverge`, ngưỡng
  `publication_gate.leg_ratio_review`, khóa cũ `dcf.leg_ratio_review` vẫn đọc được): DCF vs bội số,
  RI vs P/B của CK/BH và NH khi cả hai trọng số > 0. Một chân ≤ 0 hoặc max/min > ngưỡng (5,0 — phi duyệt
  20/10/2026; trước 3,0) → chặn.
- Ngân hàng: MỘT định nghĩa ROE = LNST / VCSH bình quân (roe5, ROE ngành, trung vị lịch sử). RI terminal
  và P/B hợp lý dùng ROE_T·(1 + g/2) (VCSH đầu kỳ ở trạng thái dừng). Dự phóng 3 giai đoạn: năm
  3–5 ROE phai tuyến tính từ driver về ROE_T (`bank_terminal.roe_transition_years`), phần chênh nằm ở dòng
  `roe_fade_adjustment` (cấp LNTT); `forecast_bank_financials(..., fade_to_terminal=False)` = driver thuần.
- DCF: NOPAT terminal theo thuế suất biên `sector_tax_rates.default` (`dcf.terminal_tax_mode: marginal`);
  năm 1–5 giữ thuế hiệu dụng. Tỷ lệ ΔDR/ΔDT chỉ cho mã trong `dcf.deferred_revenue_operating_tickers`.
  CĐKKS > `dcf.minority_book_review` VCSH mẹ → cờ `MINORITY_AT_BOOK_MATERIAL` (không đổi FV).
- EV/EBITDA mã không chu kỳ: bội số trailing × EBITDA TTM; mã chu kỳ giữ EBITDA giữa chu kỳ.
- Kỳ Q4: TTM = FY đủ 4 quý, không bị loại khỏi cửa sổ năm đầy đủ (`CompanyBank.last_period_is_ttm`,
  `CashFlow.is_ttm_period`).
- RNAV AI: dòng tiền dự án (trước tài trợ) chiết khấu bằng WACC
  (`proxy_valuation.rnav_project_discount_rate`).
- Bội số lịch sử nhóm CK/BH loại quan sát trước đợt quyền mua/riêng lẻ (`relative_multiples.
  capital_raise_exclusion_groups`); NH/DCF chưa áp vì thiếu giá phát hành để pro-forma.
- r3a (20/10/2026): (1) lá chắn thuế nợ trong WACC dùng thuế biên (`dcf.wacc_tax_mode: marginal`,
  `wacc.wacc_tax_rate`), cùng nguồn với NOPAT terminal; báo cáo dùng `company_wacc`. (2) `Assumptions.
  terminal_tax_rate` (None = config) đi qua `DCFValuationModel.from_pydantic` và ô "Thuế terminal (vĩnh viễn)"
  trên tab giả định. (3) NH: cờ `BANK_ROE_FADE_PLUG:x%` (% LN năm 5 do dòng cân,
  `bank_terminal.fade_plug_flag_share`); cơ chế "năm theo driver" của r3a đã bỏ ở r4a (xem dưới). (4) CK/BH dùng `forecast_bank.ni_from_avg_roe` /
  `begin_roe_from_avg` (ROE bình quân ↔ đầu kỳ). (5) P/B CK/BH trước phát hành pro-forma vốn hóa / (VCSH + C),
  C = tiền thu LCTT đối chiếu Δ(vốn góp + thặng dư) (`repo.capital_raise_proceeds`,
  `relative_multiples.capital_raise_proforma`); không ước được → loại như fx2.
- r4a (20/10/2026, quyết định phi): ROE terminal NH λ = 0,5 (`bank_terminal.roe_convergence`); ngưỡng hai chân
  5,0. NH: dòng cân phai ROE tính từ driver GỐC (`AssumptionsBank.driver_base`, repo chụp lúc dựng; UI chụp nếu
  thiếu); driver analyst/kịch bản sửa cộng thẳng: LN = LN_phai(gốc) + (LN_driver_sửa − LN_driver_gốc) trên cùng
  trạng thái đầu kỳ — đúng dấu, không bỏ dòng cân (trước: bỏ dòng cân → FV giảm khi tăng NIM ở NH dòng cân dương).
  Hệ quả: kịch bản Bull/Bear NH (`sensitivity`) nay có tác dụng ở năm 3–5 (D67 thay cách áp, xem dưới). fin_a: ràng buộc vốn
  (`min_equity_to_assets`) áp RIÊNG cho đường gốc và đường sửa theo cùng luật một bước (trước: đường gốc chỉ bị kẹp
  khi đường sửa chạm trần → LN nhảy bậc khi kéo tăng trưởng tín dụng qua trần); không sửa driver thì trùng từng số
  (19 TCTD), Bull/Bear đổi ≤ 0,4%. Thuế dài hạn một nguồn
  `wacc.marginal_tax_rate(terminal_tax_rate, tax_rate)`: thuế người dùng nhập, không thì thuế biên (mode
  `marginal`) hoặc thuế hiệu dụng (mode `effective`) — dùng cho NOPAT terminal (dcf) và lá chắn thuế nợ (WACC).
- D67 (21/10/2026, phi chọn phương án b): kịch bản Bull/Bear NH tính lại ROE dài hạn từ driver đã sốc. roe5 kịch
  bản = ROE riêng Base + (`forecast_bank.driver_roe5` sau sốc − trước sốc). ROE_T kịch bản hội tụ λ về ROE ngành, và
  ROE ngành KHÔNG sốc. `driver_base` sốc cùng hệ số nên năm 3–5 phai về ROE_T kịch bản: năm 5 = ROE_T, LN6 nối liền,
  đúng cho máy đặt và mọi kịch bản. Chỉ khi analyst sửa driver thì năm 5 mới lệch ROE_T, đúng bằng phần delta.
  Bỏ `sustainable_roe_delta`. ROE riêng ≤ 0 vẫn dùng, không còn thay bằng ROE TTM. Cờ `BANK_TERMINAL_JUMP`
  (cảnh báo) bắn khi |LN6/LN5 − (1 + g)| > `bank_terminal.terminal_jump_flag_tolerance` hoặc LN5 ≤ 0.

## 13. SOTP_HOLDINGS và cổng công bố (fx3, 20/10/2026)

- `repo.resolve_sotp_holdings` chạy `run_deterministic_checks` cho từng công ty con (FV giả = thị giá, chỉ giữ
  lỗi dữ liệu mức error, trừ `STALE_PRICE` đã đi đường `SOTP_HOLDINGS_STALE`). Có lỗi → mã mẹ mang
  `SOTP_SUBSIDIARY_DATA_ERROR:<MÃ CON>(<mã lỗi>)` (chặn). r4b (D65): `collect_sponsor_data.py` và
  `audit_vn100_data.py` nhận VN100 ∪ công ty con trong `config/sotp_holdings.yaml` (`universe.audit_universe`,
  whitelist + regex); chạy mặc định (không `--tickers`) gồm cả công ty con. Thêm công ty con mới vào yaml → chạy
  `collect_sponsor_data.py --tickers <MÃ> --financials` rồi `audit_vn100_data.py --tickers <MÃ>` trước khi mã mẹ
  công bố được.
- `config/sotp_holdings.yaml`: có `reviewed_by` thì bắt buộc `as_of` (YYYY-MM-DD), thiếu/sai → `ValueError` khi
  nạp; mô hình vẫn coi `as_of` hỏng là `SOTP_HOLDINGS_UNVERIFIED` (hạn rà soát không tính được).
- **Cách duyệt `config/sotp_holdings.yaml` (việc của người dùng; agent không tự điền `reviewed_by`):** rà từng
  holding — `stake` là lợi ích kinh tế hiệu quả (trực tiếp + gián tiếp), có `source` https và `source_date`;
  `carrying_value_bn` chỉ cho khoản ghi giá gốc; đọc `known_gaps`. Sửa nếu cần, rồi điền ở cấp mã mẹ
  `reviewed_by: <tên>` và `as_of: YYYY-MM-DD` (ngày đối chiếu xong). Quá `review_ttl_days` (180) so ngày định
  giá → `SOTP_HOLDINGS_STALE` (chặn) → rà lại và đổi `as_of`. Trước khi điền, nếu mã mẹ sẽ mở với lệch vượt ngưỡng
  hold (dưới) thì phải có hold hoặc mục registry đã duyệt (REE, TCH đã đặt hold sẵn). Mã holding không được
  đồng thời là holder; mã mới phải qua collect + audit như trên.
- Cổng `_apply_publication_gate` so theo mã cờ trước dấu `:` (cờ mang chi tiết vẫn chặn).
- `audit_vn100_data.py --tickers` GỘP vào audit đã lưu (giữ dòng/chênh lệch các mã khác, dùng lại `year_from`
  của audit đã lưu; mapping_version đổi → phải audit đầy đủ). Trước fx3 lệnh này ghi đè cả file. r3b: chưa
  có `source_audit.json` (máy mới/bản portable) thì gộp vào `data/source_quality_status.json`; không có cả
  hai → lỗi, yêu cầu audit đầy đủ.
- Mã cờ trong `valuate.PUBLICATION_BLOCKING_FLAGS` và tiền tố `verified_summary.DATA_FLAG_ERROR_PREFIXES`
  phải có level `error` trong `flag_descriptions` (test r3b).
- Golden (`tests/test_golden_consensus.py`) kiểm registry ở hai mốc 28/09 và 20/10/2026; mục registry chỉ
  lỗi thời khi không mốc nào còn ngoài band. Cùng lượt chạy kiểm mọi khóa `defaults.yaml` engine đọc đều có
  trong snapshot `harness._ENGINE_CONFIG_KEYS` (khóa mới phải thêm vào đó). fin_a: snapshot `engine_config` còn
  chụp `config_files_sha256` của `config/sotp_holdings.yaml` và `config/event_holds.yaml` (đổi FV/cổng công bố
  ngoài `defaults.yaml`, kể cả khi chưa commit).
- `config/event_holds.yaml` (D46): mỗi mã có `since` (YYYY-MM-DD), `reason`, `source`, `lift_when` → cờ
  `MATERIAL_EVENT_HOLD` (chặn; số chẩn đoán vẫn tính). So `since` với ngày chạy (`date.today()`), không theo
  `as_of` → mã đang hold không được golden đo ở mốc nào. Gỡ hold = xoá dòng khi điều kiện `lift_when` đạt và
  người dùng duyệt; ghi lý do gỡ ở comment file.
- Mã MỚI mở công bố (vừa hết cờ chặn) mà lệch CTCK > `publication_gate.new_listing_hold_dev` (0,40, cần ≥
  `new_listing_hold_min_brokers` = 3 CTCK) hoặc upside > `new_listing_hold_upside_pct` (100%), với mục registry
  chưa được người dùng duyệt → hold trong `config/event_holds.yaml`, `lift_when` là người dùng duyệt (fin_a thống
  nhất ngưỡng; trước đó fx3 ghi 30%, r4a ghi 40%). Mã còn bị chặn bởi cờ chờ người dùng mà sẽ mở vượt ngưỡng
  (REE, TCH: `SOTP_HOLDINGS_UNVERIFIED`) được đặt hold sẵn để luật tự thực thi lúc mở. Thêm/gỡ hold thì sửa dòng
  dưới (test `test_fin_a_round4_minor` đối chiếu với file). Danh sách hold hiện hành: VCG, PC1, FRT, POW, SIP,
  NAB, BVH, VRE, PNJ, HHV, REE, TCH.
- Mọi cờ mới phải có mô tả trong `valuation/engine/flag_descriptions.py`; `describe_flags` tra theo mã trước `:`.

## 14. Cờ mới của đợt nâng cấp D66 (19–20/10/2026)

Mô tả đầy đủ ở `valuation/engine/flag_descriptions.py`; level dưới đây đọc từ file đó.

- **Chặn công bố:** `VALUATION_LEGS_DIVERGE` (một chân ≤ 0 hoặc max/min > `publication_gate.leg_ratio_review`),
  `CIP_DOMINATES_VALUE` (XDCB dở dang > `dcf.cip_share_review` vốn chủ DCF), `SOTP_HOLDINGS_UNVERIFIED`,
  `SOTP_HOLDINGS_STALE`, `SOTP_SUBSIDIARY_DATA_ERROR`, `LAND_BANK_INPUT_MISSING`, `SOURCE_AUDIT_STALE`,
  `SOURCE_CONFLICT` (ΔFV > 1% hoặc không đo được), cùng `MATERIAL_EVENT_HOLD` cho các hold mới.
- **Cảnh báo (không chặn):** `SOURCE_AUDIT_PARTIAL`, `SOURCE_CONFLICT_IMMATERIAL`, `FILING_PRECEDENCE`,
  `FILING_BS_INCOMPLETE`, `UNEXPLAINED_CURRENT_ASSETS`, `CIP_LINE_MISSING`, `MULTIPLE_FROM_PEER_MEDIAN`,
  `SEC_/INS_PAYOUT_FALLBACK`, `SEC_/INS_PAYOUT_INCONSISTENT`, `INS_NO_MARKET_PB_HISTORY`, `TAX_FALLBACK_EBIT`,
  `BANK_ROE_FADE_PLUG`, `BANK_TERMINAL_JUMP` (D67), `MINORITY_AT_BOOK_MATERIAL`, `RNAV_PROJECT_INPUT_MISSING`, `SOTP_SEGMENT_INPUT_MISSING`,
  `SOTP_HOLDINGS_INCOMPLETE` (quay về proxy nên `VALUATION_PROXY` vẫn chặn).
- **Thông tin:** `INCONSISTENT_YEAR_DROPPED`, `MULTIPLE_PRE_ISSUE_EXCLUDED`, `MULTIPLE_PRE_ISSUE_PROFORMA`,
  `PE_LEG_TTM`, `SOTP_HOLDINGS_MODE`, `SOTP_UNLISTED_AT_BOOK`, `RIGHTS_ISSUE_UNDATED` (tách khỏi
  `CORPORATE_ACTION_UNDATED`, không tính là "Lỗi dữ liệu" ở bảng xếp hạng). Từ D86, `CORPORATE_ACTION_UNDATED`
  cũng chỉ là cảnh báo, không chặn xếp hạng.
- **Lỗi cấu hình (raise, không phải cờ):** `PE_LEG_CYCLICAL_UNSUPPORTED` (mã chu kỳ + P/E phụ), stake/holder
  sai trong `sotp_holdings.yaml`, `reviewed_by` thiếu `as_of`, khóa lạ của `dcf.wacc_tax_mode`.
- Ngưỡng do claude đề xuất, CHƯA được người dùng duyệt (đổi số không cần sửa code): `bank_terminal.
  fade_plug_flag_share` 0,10, `bank_terminal.terminal_jump_flag_tolerance` 0,10 (D67), `audit.max_unaudited_periods` 2, `audit.filing_precedence_max_rel_diff` 0,05 +
  `audit.filing_source_domains`, `dcf.minority_book_review` 0,10, `relative_multiples.capital_raise_min_ratio`
  0,05 / `capital_raise_proceeds_tol` 0,10 / `capital_raise_exclusion_groups`, `publication_gate.
  new_listing_hold_*`.

## 15. Web hợp nhất btinvest.vn (chạy thật trên VPS từ 25/11/2026, D102–D111)

- **Là gì:** web gộp cổ phiếu, chứng quyền, ETF, hợp đồng tương lai tại `https://btinvest.vn`, chạy SONG SONG với
  hai web cũ (`chungkhoan.btinvest.vn` là Streamlit của repo này, `chungquyen.btinvest.vn` là repo `~/cw_scanner`).
  Quyết định của người dùng, kế hoạch 6 lát và phần còn dở: `docs/PLAN_WEB_HOP_NHAT.md`.
- **Mã:** ứng dụng FastAPI `valuation/api/web_main.py` (nhóm số liệu chỉ có GET) + `web_user_routes.py` (tài khoản,
  danh mục, mức giá); giao diện viết tay trong `web/` (không React). Số chứng quyền, ETF, hợp đồng tương lai và phép
  tính danh mục lấy từ dịch vụ chứng quyền qua `services/web_cw.py` (chỉ các đường dẫn trong danh sách cho phép).
  Không có công thức định giá nào viết lại ở đây: mọi số lấy từ bộ máy có sẵn.
- **Chạy tại máy:** hai preview trong `.claude/launch.json`: `cw-dich-vu` (cổng 8000, repo `~/cw_scanner`) và
  `btinvest-web` (cổng 8600, `WEB_AUTH_MODE=dev`). Sửa Python xong phải khởi động lại preview (uvicorn không tự nạp).
- **Trên VPS:** container `btinvest-web` trong `/srv/apps/vn100/docker-compose.yml` (bản sao: `deploy/docker/`), cùng
  image với ba container cũ nên **đẩy `main` lên GitHub là deploy cả web này**. Đăng nhập bằng tài khoản coin; ở
  tên miền này Caddy không chặn hộ, ứng dụng tự trả 401. Thêm route `/api/` mới thì test
  `test_moi_duong_api_deu_dong_khi_chua_dang_nhap` phải còn qua.
- **Dữ liệu người dùng:** tệp SQLite riêng `/data/web_user/web_user.db` (tài khoản, lệnh, mức giá), không nằm trong DB
  định giá, không commit. Tài khoản mới ở trạng thái chờ duyệt; Quản trị đầu tiên lấy từ `WEB_ADMIN_EMAILS` trong
  `.env` trên VPS (chủ máy tự điền, đã có từ 25/11/2026). Sao lưu: `scripts/backup_web_user_db.py` chạy 23:00 mỗi
  ngày trong `vn100-worker` (job `web-user-backup` của `scheduler.py`, D112), giữ 14 bản ở `/data/web_user/sao_luu/`,
  cùng ổ với tệp gốc nên không chống được mất cả ổ; job lỗi chỉ để lại dòng `exit=1` trong nhật ký worker.
- **Báo cáo AI bản ngắn (D116):** `services/web_ai_report.py`, nút trên tờ mã; mỗi tài khoản 5 lượt sinh mới mỗi
  ngày (`web.ai_report` trong `config/defaults.yaml`), đếm trên `web_audit`; bản lưu ở
  `.deepseek_report_cache/ban_ngan/`. Đổi câu lệnh cho AI thì tăng `PROMPT_VERSION` để bản cũ không bị dùng lại.
- **Góc chat "Hỏi Ếch" (D120):** `services/web_chat.py` (lượt, lời dặn trả lời) và `services/web_chat_tools.py`
  (bộ công cụ `WEB_TOOLS` = bảy công cụ của bot + năm công cụ của web), đường `/api/hoi-ai`; mỗi tài khoản 20 câu
  mỗi ngày (`web.chat`), đếm trên `web_audit` việc `hoi_ai`. Sửa `assistant.py` thì chạy cả `tests/test_assistant.py`
  (bot Discord) lẫn `tests/test_web_chat.py`; thêm công cụ cho web thì thêm vào `WEB_TOOLS`, nhánh kiểm tham số ở
  `assistant.validate` và dòng số gốc ở `assistant.render_sources`.
- **Dự án chứng quyền** nhận mã bằng `git push vps main` từ máy Mac (chỉ ở mạng nhà); VPS tự deploy trong 3 phút.
