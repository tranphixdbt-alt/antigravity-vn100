# Kế hoạch chuyển dữ liệu sang vnstock thế hệ 6 (D94)

> Lập 11/11/2026 theo lựa chọn của người dùng "Chuyển sang thế hệ 6 ngay". Chưa đổi code đọc dữ liệu nào:
> mọi bước dưới đây chờ khóa nguồn và người dùng duyệt từng lát cắt.

## 1. Vì sao phải chuyển

- Trang lịch sử phiên bản chính thức (vnstocks.com/docs/vnstock-insider-api/lich-su-phien-ban), mục `vnstock_data`:
  "Đường cài này đã gỡ từ ngày 10/11/2026 khi thế hệ 4 ngừng xác thực." Index cài dòng 4.x (`api/simple`) không còn
  trả bản nào cho Python 3.14 — không nâng cấp/cài lại được `vnstock` 4.x, `vnstock_data` 3.x, `vnai`.
- Thử thật 11/11/2026: `vnstock` 4.0.7 (giá VCI) và `vnstock_data` 3.2.8 (khối ngoại) **vẫn trả dữ liệu** — có thể bị
  chặn bất cứ lúc nào. Lỗi `vnai` 2.5.9 `threading` không còn bản sửa để cài (đã vá bằng thử lại 1 lần, D94).

## 2. Hiện trạng thế hệ 6 trên máy

- Môi trường riêng `~/.venv_6x` (Python 3.14.5): `vnstock` 6.0.0, `vnstock-oapi` 0.1.1, pandas 3.1.1, numpy 2.5.4.
  `~/.venv` (app, launchd) giữ nguyên dòng 4.x để rollback.
- `vnstock status`: đã đăng nhập, gói "Tự động hoá cá nhân", hết hạn 14/04/2027; bản 6.0.0 dùng được tới 10/11/2027.
- Thế hệ 6 **không có nguồn mặc định và không có VCI**. Nguồn: `dnse`, `fhsc`, `ssi`, `tcbs`, `fmp` (cần khóa riêng
  của người dùng ở từng nguồn), `binance` (không cần khóa). Các lớp `Quote`, `Listing`, `Company`, `Finance` bị bỏ
  (`ImportError`); tin công bố `company.news` đã ngừng từ thế hệ 5.

## 3. Nguồn cho từng loại dữ liệu dự án cần (`vnstock doc <hàm>`, 11/11/2026)

| Dữ liệu (đang lấy từ VCI) | Hàm thế hệ 6 | Nguồn hỗ trợ |
|---|---|---|
| Giá ngày OHLCV | `Market.equity.ohlcv` | dnse, fhsc, ssi, tcbs |
| Giá trong phiên | `Market.equity.quote` | fhsc, tcbs |
| Khối ngoại | `Market.equity.foreign_flow` | dnse, fhsc, ssi |
| Tự doanh | `Market.equity.proprietary_flow` | **chỉ fhsc** |
| BCTC BS/IS/CF quý, năm | `Fundamental.equity.*` | **chỉ fhsc** |
| Sự kiện quyền một mã | `Reference.company.events` | fhsc, ssi |
| Sự kiện quyền toàn thị trường | `Reference.equity.corporate_actions` | dnse |
| Thành phần chỉ số (VN100) | `Reference.index.members` | **chỉ ssi** (dự án đã có `config/vn100_universe.json`) |
| Tin công bố doanh nghiệp (D89) | — | **không còn** — cần nguồn khác hoặc bỏ |

→ **FHSC là bắt buộc** (BCTC, tự doanh). Khóa: một API Key tạo tại `invest.fhsc.com.vn/tai-khoan`; nguồn chỉ phục
vụ **06:00–21:00** giờ VN (job 07:50 / 08:30 / 18:00 hiện tại nằm trong khung). SSI tùy chọn (thành phần VN100).

## 4. Chỗ phải sửa trong code (17 file)

- Lõi: `valuation/ingest/vnstock_client.py` (Quote/Finance/Company/Listing), `market_client.py` (vnstock_data Market),
  `flow_client.py` (vnstock_data VCI Trading — job `flow_daily`), `corporate_actions.py` (Company events),
  `company_disclosures.py` (VCI news — D89), `sponsor_data.py`, `scrapers/consensus_collector.py` (khuyến nghị VCI).
- Gọi qua lõi: `pipeline.py`, `data_access/repo.py`, `services/ranking_sources.py`, `streamlit_app.py` (giá trực tiếp).
- Script: `sync_vn100_universe.py`, `update_all_data.py`, `steel_cycle_report.py`, `draft_sotp_holdings.py`,
  `repair_duplicate_bs_items.py`.

## 5. Rủi ro toàn vẹn dữ liệu (AGENTS §3.3 — đổi nguồn VCI → FHSC)

1. **Cơ sở điều chỉnh giá**: VCI trả giá đã điều chỉnh hồi tố; phải kiểm FHSC có điều chỉnh không quanh các sự kiện
   đã biết (TCB chia 50% 29/10, HDB 30%, PC1 15%) — lệch cơ sở sẽ gãy chuỗi giá và MA200.
2. **Đơn vị**: hồ sơ cột `v5` (mặc định) giữ nến theo nghìn đồng như hiện nay; không bật `v6` khi chưa sửa chỗ nhân 1000.
3. **BCTC**: mã chỉ tiêu FHSC khác `item_id` của VCI → phải ánh xạ lại `config/financial_taxonomy.json`; hợp nhất vs
   công ty mẹ; dòng đặc thù ngân hàng/bảo hiểm/chứng khoán; `published_at` (chống lookahead).
4. **Khối ngoại/tự doanh**: định nghĩa khớp lệnh vs gồm thỏa thuận (xem memory money-flow quirks), số đã chốt trong
   `flow_daily` không được ghi đè (`is_final`).
5. **pandas 3.1** trong `~/.venv_6x`: bộ test hiện chạy trên pandas 2.3.3 — phải chạy lại toàn bộ trên môi trường mới.

## 6. Các bước (mỗi bước một lát dọc, có test + đối chiếu số, chờ duyệt)

| Bước | Việc | Xong khi |
|---|---|---|
| S0 | **Người dùng** đăng ký khóa FHSC (và SSI nếu muốn), tự chạy `~/.venv_6x/bin/vnstock keys set fhsc` rồi `vnstock keys check` trong terminal của mình | `keys check` báo fhsc OK |
| S1 | Giá ngày: lớp đọc mới qua `Market("fhsc")`, đối chiếu 100 mã × 60 phiên với DB (close, KL), kiểm điều chỉnh quanh sự kiện quyền | lệch close ≤ 0,5% mọi ô hoặc giải thích được từng ô |
| S2 | Khối ngoại + tự doanh: đối chiếu với `flow_daily` 20 phiên | lệch ròng ≤ 1% GTGD hoặc giải thích được |
| S3 | BCTC: ánh xạ chỉ tiêu FHSC → taxonomy, đối chiếu DT, LNST, VCSH, tổng tài sản 20 mã × 8 quý (gồm NH, BH, CK) | golden test sai số theo AGENTS §3.8 |
| S4 | Sự kiện quyền: FHSC/SSI events vs `corporate_actions` | không mất sự kiện nào trong 12 tháng |
| S5 | Tin công bố (D89): chọn nguồn thay thế hoặc tắt tính năng | người dùng chọn |
| S6 | Chuyển môi trường: cài đủ `requirements` vào `~/.venv_6x`, chạy toàn bộ test (pandas 3.1), đổi launchd + launcher sang venv mới; `requirements.txt` bỏ `vnstock_data`/`vnai`/`vnii`, thêm `vnstock>=6,<7`, `vnstock-oapi` | test xanh, app + 4 job chạy 2 ngày liền đúng |
| S7 | Rollback: giữ `~/.venv` dòng 4.x tới khi thế hệ 4 ngừng hẳn; quay lại = đổi đường dẫn python trong plist | — |

## 7. Kết quả từng bước

**S0 (12/11/2026) — xong.** Khóa FHSC nằm trong keyring chung của máy (người dùng cất từ dự án chứng quyền
`cw_scanner`); `~/.venv_6x` đọc được ở mọi thư mục, `vnstock keys check fhsc` HTTP 200. Không chép khóa vào file nào.
Gọi thử FPT: giá ngày (hồ sơ `v5`, nghìn đồng), khối ngoại (đồng, **có ngay số trong ngày lúc 22:54** — VCI phải
chờ sáng hôm sau), tự doanh, BCTC quý (bảng dọc mẫu biểu VAS `IS_REVENUE`…/`line_code`, từ 2013, đơn vị đồng; có
cảnh báo `VNSTOCK_VAS_IDENTITY` khi đẳng thức mẫu biểu không khớp).

**S1 (12/11/2026) — đạt.** 100/100 mã × 60 phiên (15/08–11/11, 5.760 ô): **0 ô lệch close > 0,5%**; 299 ô ở 16 mã
lệch 10–80 đồng (≤ 0,3%), mỗi mã chỉ lệch tới đúng ngày trước GDKHQ trong `corporate_actions` (BAF 27/10, PC1 04/11,
VPI 10/11, NVL, TPB, HT1, PHR, DIG) → cả hai nguồn điều chỉnh giá hồi tố, khác làm tròn. TCB qua chia 50% (29/10) lệch
tối đa 0,095%; HDB, SSB, SSI, STB khớp tuyệt đối. Ngày 12/11 lệch tới 2,9% ở 5 mã chỉ vì DB giữ giá giữa phiên.
Hạn mức: ~90 lời gọi ở ~3 lần/giây thì FHSC trả 429 (`VNSTOCK_SOURCE_RATE_LIMITED`) → client mới phải giãn nhịp
(≤ ~45 lời gọi/phút) và chờ-thử lại khi 429. Script: scratchpad `reconcile_prices_fhsc.py`.

**S2 (12/11/2026, ~23:00) — dở, chạy lại ban ngày.** 3/100 mã (63 ô, 13/10–10/11) rồi FHSC trả `DF000 Vui lòng thử
lại sau` / lỗi upstream / ReadError cho mọi mã còn lại — ngoài khung phục vụ 06:00–21:00. Trên 3 mã: **khối ngoại
FHSC = VCI khớp lệnh + thỏa thuận** (100% ô lệch ≤ 0,1% GTGD; chỉ so với khớp lệnh thì 91,7%), **tự doanh cũng =
khớp + thỏa thuận** (100% ô có số). Hệ quả: `flow_daily` đang tách khớp/thỏa thuận (D73) — FHSC chỉ trả ròng gộp,
cần `columns="all"` để xem có tách không trước khi thay nguồn. Mọi job gọi FHSC phải chạy trong 06:00–21:00.

**S2 chạy lại (13/11/2026, 08:17–08:20) — vẫn dở, chưa có kết quả đầy đủ.** `scripts/reconcile_fhsc_flows.py`:
**0/100 mã** — mọi lời gọi `foreign_flow`/`proprietary_flow` lỗi, script dừng ở `pd.concat` ("No objects to
concatenate") trước khi in danh sách lỗi; không có tỷ lệ khớp mới. Nguyên nhân cùng sự cố FHSC ở đoạn dưới (ReadError
dù đang trong giờ phục vụ). Kết luận 3 mã đêm 12/11 (FHSC = khớp + thỏa thuận) giữ nguyên, chưa được xác nhận trên
cả rổ. Chạy lại khi FHSC kết nối được.

**Lượt chạy thật đầu tiên (13/11/2026) — FHSC 0 mã, VCI 100 mã; dữ liệu vẫn đủ.** Job 07:50: cầu nối chạy đúng giờ
phục vụ nhưng `logs/daily_report.log` 07:52:57 ghi `FHSC: 101 lỗi, dùng VCI cho các mã đó` (100 mã/prices + 1 khóa
nữa, log chỉ in 10 khóa đầu và không in nội dung lỗi). Dự phòng VCI hoạt động: **100/100 mã VN100 có giá đóng cửa
phiên 12/11** trong `prices_daily`; log ngày 13/11 không có "Could not fetch prices" hay ERROR. Thử lại cầu nối lúc
08:16–08:17 (FPT, VCB, 3 lần): đều `NetworkError: Lỗi kết nối: ReadError (code=VNSTOCK_SOURCE_NETWORK, source=fhsc)`
sau ~9–16 s. `vnstock doctor` cùng lúc: vnstocks.com kết nối được, bản 6.0.0, tài khoản còn hạn, "Nguồn fhsc: Sẵn
sàng · khoá lấy từ keyring" → không phải thiếu khóa, thiếu `~/.venv_6x`, 429 hay ngoài giờ; là máy chủ FHSC không
trả dữ liệu (hoặc đường mạng tới FHSC) sáng 13/11. Chưa kiểm được hồ sơ cột vì không có dòng nào về. Việc còn lại:
thử lại trong ngày; cân nhắc cho `fhsc_bridge` ghi nội dung lỗi đầu tiên vào log và dừng sớm khi N mã đầu đều lỗi
mạng (lượt này tốn ~3 phút gọi 100 mã vô ích).

**Chẩn đoán mạng (13/11/2026 ~10:00).** Mọi máy chủ FHSC tự vận hành (`open-api` 124.197.17.162, `invest` và
`fhsc.com.vn` 124.197.17.168) bắt tay TLS xong rồi bị cắt (curl HTTP 000 / ECONNRESET) từ mạng nhà người dùng, từ
trình duyệt của người dùng trên cùng máy, và từ máy chủ nước ngoài (WebFetch). `developers.fhsc.com.vn` (Mintlify/
Cloudflare) vẫn mở. Chưa phân biệt được: FHSC sự cố, hay chặn IP nhà người dùng (bắt đầu ~23:00 12/11, ngay sau đợt
gọi dồn bị 429) cộng chặn IP nước ngoài. Dữ liệu không bị ảnh hưởng nhờ VCI dự phòng.

**Chuyển từng phần (D95, 12/11/2026 — người dùng chọn thay cho chuyển cả app một lần).** Job giá 07:50 và Quét
VN100 tải trước cả rổ qua `scripts/fhsc_fetch.py` (python `~/.venv_6x`) → `valuation/ingest/fhsc_bridge.py` →
client cũ lấy bộ đệm trước, VCI dự phòng; ghi DB giữ nguyên ở `~/.venv`. Còn VCI: nút "Tải mới"/mở mã (tốc độ),
`flow_daily` (chờ S2), BCTC (S3), sự kiện quyền (S4), tin công bố (S5). Khi dòng 4.x ngừng hẳn: chuyển nút "Tải
mới" sang cầu nối (chấp nhận ~6–8 s hoặc làm tiến trình FHSC thường trú), rồi S3–S6.
