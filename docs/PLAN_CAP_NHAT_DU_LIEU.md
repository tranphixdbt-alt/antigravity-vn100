# Kế hoạch: dữ liệu trên btinvest.vn luôn mới

Viết 26/11/2026 sau khi người dùng báo "nhiều thông tin bị cũ do không cập nhật". Người dùng duyệt "Làm tất cả";
đã làm tại máy, chi tiết D121 trong `DECISIONS.md`. Phần "Kết quả" ở cuối ghi chỗ khác kế hoạch.
Mọi số dưới đây đo trên VPS lúc khoảng 04:30 ngày 26/11/2026, chỉ đọc (DB `/data/vn100_full.db` mở chế độ
`mode=ro`, nhật ký `/app/logs/*.log` trong `vn100-worker`, trang btinvest.vn).

## 1. Hiện trạng từng loại dữ liệu

| Dữ liệu | Web đang hiện | Mới nhất có được | Vì sao cũ |
|---|---|---|---|
| Giá cổ phiếu, VN-Index, dòng tiền 20 phiên, khối ngoại, tự doanh | đến 23/11 | 25/11 | Chỉ tải một lần lúc 07:50 sáng hôm sau (`daily-report`). Từ lúc đóng cửa tới 07:50 hôm sau, web chậm một phiên. Ngày 24/11 sàn không giao dịch (TCBS và FHSC đều không có phiên này), nên không phải lỗi. Lượt 07:50 hôm nay sẽ nạp 25/11. |
| Vĩ mô Việt Nam | CPI đến 30/09 (web đã gắn chữ "cũ"); GDP, bán lẻ, lãi suất điều hành đến 30/06; tăng trưởng tín dụng đến 31/12/2025 | CPI tháng 10, GDP quý 3 đã công bố | Không có job tự chạy. Bốn chuỗi này làm tay qua Chrome (`scripts/refresh_macro_chrome.md`). Lần nạp cuối: CPI 10/10, GDP/bán lẻ/lãi suất 11/07, tín dụng 28/06. |
| ETF | số liệu lúc 09:40 25/11, trong phiên | cuối phiên 25/11 | Báo cáo ETF của `~/cw_scanner` chạy một lần lúc 09:40 mỗi ngày (thiết kế "hai đồng hồ"). |
| Dòng tiền tách khớp lệnh / thỏa thuận (`flow_daily`) | dừng 12/11 | — | Đã biết từ D97: gói `vnstock_data` bị khóa từ 10/11, job tắt, web dùng số gộp từ FHSC. Nhưng Quét VN100 vẫn gọi job cũ nên mỗi thứ Hai và thứ Năm báo "dòng tiền lỗi (mã 4)". |
| BCTC, khuyến nghị CTCK (Quét VN100, thứ Hai và thứ Năm 08:00) | BCTC quý 3/2026 đủ 100 mã; khuyến nghị CTCK có tới 19/11 | — | Chưa cũ, nhưng lần quét 23/11 chỉ lấy đủ 55/100 mã. 45 mã còn lại chỉ lấy được một phần vì máy chủ VCI chặn VPS: 64 lần lỗi 418, 106 lần quá giờ chờ. Nếu tiếp tục như vậy, BCTC quý 4 (cuối tháng 1/2027) có thể không vào đủ. |
| Định giá, xếp hạng VN100 | đợt 23/11, dùng giá đóng cửa 20/11 | đợt 26/11 lúc 08:00 | Đúng lịch thứ Hai và thứ Năm. Đợt định giá cố ý dùng giá phiên trước nên không dính giá giữa phiên. |
| Chứng quyền, phái sinh, sự kiện quyền, TPCP 10 năm, Fed, dầu, USD/VND | mới (25/11, lần quét chứng quyền lúc 14:02) | — | Không có vấn đề. |

Ngoài ra có hai lỗi nhỏ về dữ liệu:

- **MCH có một dòng giá 25/11 ghi giữa phiên.** Dòng này có đóng cửa 133.000 và khối lượng 22.200, trong khi phiên thật đóng ở 130.000 với khối lượng 472.904 (theo TCBS). Thủ phạm là đường tải giá theo yêu cầu (mở mã hoặc nút "Tải mới" ở web cũ): đường này ghi cả phiên đang chạy, và chưa có chỗ nào chặn. Lượt 07:50 hôm nay sẽ tự ghi đè dòng này vì mỗi lần tải lùi lại 5 ngày.
- **Không biết số được nạp lúc nào.** Cột `ingested_at` của BCTC quý 3 trống toàn bộ, còn của khuyến nghị CTCK chỉ có số của tháng 8. Điều này trái luật vàng số 5 (mọi con số phải truy vết được).

## 2. Đề xuất, xếp theo lợi ích so với công sức

### Bước A. Lượt tải giá cuối phiên và chặn ghi phiên chưa chốt (lợi nhất)

- Thêm job `gia-cuoi-phien` chạy thứ Hai đến thứ Sáu, giờ đề xuất 15:45. Job gọi phần tải giá, khối ngoại và tự doanh của `daily_report.refresh_market` (FHSC trước, VCI dự phòng). Job không gửi báo cáo Discord, không định giá lại. Nhờ vậy web có số của phiên ngay chiều hôm đó thay vì đợi tới 07:50 sáng hôm sau.
- Giờ đóng phiên đưa vào `config/defaults.yaml` (ví dụ `market.session_close: "15:00"`). Trước giờ đó, mọi đường ghi giá (FHSC, VCI, nút tải mới) bỏ dòng của hôm nay. Quy tắc D97 hiện bỏ dòng tiền của hôm nay bất kể giờ nào. Sửa thành: chỉ bỏ khi chưa tới giờ đóng phiên.
- Đo trước khi bật: ba ngày liền so số lấy lúc 15:45 với số lấy lúc 07:50 sáng hôm sau, theo từng mã (OHLCV, khối ngoại, tự doanh). Chỉ bật khi khớp, hoặc dời giờ chạy nếu FHSC chốt số muộn hơn.
- Tệp đụng tới: `deploy/docker/scheduler.py` (kèm bản trên VPS), `valuation/services/daily_report.py`, `valuation/ingest/fhsc_bridge.py`, `valuation/ingest/pipeline.py`, `config/defaults.yaml`. Test mới tái hiện lỗi MCH (ghi dòng hôm nay lúc 10:00 thì phải bị bỏ). Thêm một ca cho lượt 15:45.
- Rủi ro: thêm một lượt gọi FHSC mỗi ngày (khoảng 300 lời gọi, vài phút). Đổi `scheduler.py` trên VPS là bước ghi, phải xin duyệt riêng.

### Bước B. Vĩ mô Việt Nam tự cập nhật

- Nạp một lần ngay: CPI tháng 10, GDP quý 3, bán lẻ, lãi suất điều hành, tăng trưởng tín dụng. Ghi qua `upsert_macro_series` (allowlist, idempotent). Sao lưu DB trước khi ghi. Đây là bước ghi trên VPS, cần duyệt.
- Job `vi-mo-vn` mỗi tuần một lần (đề xuất thứ Hai 07:25, trước báo cáo sáng). Job dùng Chromium headless giống job TPCP (D100) để đọc trang tradingeconomics. Ngày ghi vào DB là kỳ số liệu (tháng hoặc quý mà con số thuộc về), không phải ngày tải. Không đọc được kỳ số liệu thì không ghi.
- Báo Discord khi một chuỗi quá hạn: CPI quá 45 ngày sau kỳ, GDP quá 120 ngày, lãi suất điều hành quá 180 ngày không có số mới.
- Tệp đụng tới: `scripts/update_vn_macro.py` (mới), `valuation/ingest/macro_store.py`, `deploy/docker/scheduler.py`, `scripts/refresh_macro_chrome.md`, kèm test có trang mẫu lưu sẵn.

### Bước C. Cảnh báo khi dữ liệu cũ hoặc job lỗi

- Sau lượt 07:50 và lượt 15:45: nếu ngày giá trong DB cũ hơn phiên giao dịch gần nhất (lịch sàn lấy từ chuỗi VNINDEX của chính nguồn), hoặc có job báo `exit` khác 0, thì gửi một dòng Discord. Gộp luôn việc còn treo: hiện nay job sao lưu `web_user.db` có lỗi thì không ai biết.
- Bỏ lời gọi `flow_daily` khỏi Quét VN100 để thôi báo "dòng tiền lỗi (mã 4)" mỗi thứ Hai và thứ Năm. Nếu muốn giữ để chờ nguồn tách khớp lệnh mới, có thể giữ nhưng ghi rõ là đã tắt.

### Bước D. ETF thêm lượt sau đóng cửa (repo `~/cw_scanner`, có AGENTS.md riêng)

- Chạy `etf.chay(gui=False)` thêm một lần lúc khoảng 15:10. Khi đó web hiện "giá đóng cửa" thay vì "09:40 trong phiên".
- Phải đo hạn mức Finhay trước: Finhay từng chặn sau khoảng 450 lượt liên tiếp vào ngày 12/11.

### Bước E. Quét VN100 bị VCI chặn (kế hoạch riêng, lớn)

- Ngắn hạn: ghi rõ mã nào thiếu phần nào vào `status.json`. Thử lại riêng các mã thiếu lúc 20:00 cùng ngày, giãn nhịp gọi.
- Dài hạn: chuyển BCTC sang FHSC theo `docs/PLAN_VNSTOCK_V6.md` (D94), xong trước mùa BCTC quý 4 (cuối tháng 1/2027). Phải đối chiếu số từng dòng BCTC giữa hai nguồn trước khi đổi.
- Kèm theo: ghi `ingested_at` cho BCTC và khuyến nghị CTCK để truy vết được.

## 3. Thứ tự đề xuất

A, rồi B, rồi C làm trước, mỗi bước là một commit kèm test. Bước nào đụng VPS (đổi `scheduler.py`, nạp vĩ mô vào DB) thì xin duyệt riêng ngay lúc đó. D làm ở repo chứng quyền. E viết kế hoạch riêng.

Kiểm sau 07:50 ngày 26/11: web phải hiện "giá đến 25/11", và dòng MCH 25/11 phải là số đóng cửa thật (130.000).

## 4. Kết quả (26/11/2026, D121)

- A, C, E làm đúng kế hoạch. Bước "đo ba ngày" của A thay bằng phép so tự động: lượt 07:50 so phiên mà lượt 15:45 đã
  ghi và báo trong báo cáo sáng số mã đổi giá, đổi khối ngoại.
- B đổi nguồn: tradingeconomics chặn tải tự động (403, kể cả trình duyệt headless) nên không dùng. Job đọc báo cáo kinh
  tế – xã hội của Cục Thống kê (nguồn gốc của số liệu). Tăng trưởng tín dụng KHÔNG tự nạp: chuỗi lưu số cả năm, điểm
  31/12/2025 vẫn là mới nhất, nên không cũ. Lãi suất điều hành vẫn nạp tay (đổi theo sự kiện).
- D: thêm cờ `--no-discord` cho `chay_etf_tu_dong.sh` ở `~/cw_scanner`; lịch 15:10 nằm ở `/srv/apps/chungquyen/scheduler.py`
  trên VPS (không có trong repo).
- E dài hạn (BCTC sang FHSC) chưa làm.
- Người dùng duyệt « Ghi theo cục thống kê » (26/11): GDP quý II/2026 sửa 8,39% → 8,81%, thêm quý I/2026 8,15% (DB
  thiếu kỳ này), cả hai lấy từ câu « cao hơn mức tăng 8,15% của quý I và 8,81% của quý II » trong báo cáo quý III.
- Lên VPS 26/11 lúc 10:50, sau khi đợt xếp hạng chạy xong. Lượt kiểm dữ liệu chạy bù lúc 10:50 báo đúng một lỗi
  có thật: đợt Quét VN100 sáng nay (08:00–10:05, còn code cũ) đã ghi 32 dòng giá giữa phiên 26/11. Đợt xếp hạng
  không bị ảnh hưởng vì chỉ đọc giá tới phiên trước. Lượt 15:45 sẽ ghi đè các dòng của VN100 và VNINDEX.
