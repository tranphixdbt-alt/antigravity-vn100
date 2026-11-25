# Kế hoạch: web hợp nhất btinvest.vn

> Bản chốt v0.1, 24/11/2026. Ghi lại 32 câu hỏi-đáp với người dùng trước khi dựng bản mẫu.
> Trạng thái: người dùng đã xác nhận bản chốt; **bản mẫu đầu tiên đã dựng (mục 10), chờ người dùng duyệt.**
> Chưa viết code thật, chưa có quyết định nào ghi vào `DECISIONS.md`.

## 1. Mục tiêu

Gộp `chungkhoan.btinvest.vn` (repo này, Streamlit) và `chungquyen.btinvest.vn` (`~/cw_scanner`, HTML viết tay)
thành một web tại `btinvest.vn`: phân tích cổ phiếu, chứng quyền, ETF, hợp đồng tương lai trong một thể đồng nhất.
Tiêu chí của người dùng: tối giản, nhìn 5 giây là hiểu, bấm vào thì đi sâu dần; trình bày đơn giản trên nền tính
toán lớn, tạo tin tưởng; hiệu ứng mượt; mức thiết kế chuyên nghiệp, không giống web AI sinh ra.

## 2. Ranh giới (không đổi)

- Chỉ làm lại lớp giao diện. **Không đổi công thức, ngưỡng, tiêu chí** của bộ máy định giá cổ phiếu, Black-Scholes
  chứng quyền, chiết khấu NAV/iNAV của ETF, basis phái sinh.
- Web mới không tự đặt ngưỡng mới. Chỗ nào chưa có tiêu chí (xem mục 9) thì chỉ hiện số, không gắn nhãn.
- Hai web cũ chạy song song cho tới khi web mới thay được; sau đó hai địa chỉ cũ chuyển hướng về mục tương ứng.

## 3. Người dùng và quyền

- Bản đầu: đội nhân viên của người dùng. Sau này mở cho khách hàng (vai thứ ba, làm sau).
- Hai vai: **Quản trị** (sửa giả định, ngưỡng, duyệt tài khoản) và **Nhân viên** (xem tất cả, có danh mục và cảnh
  báo riêng, không sửa giả định chung).
- Đăng nhập một lần bằng tài khoản coin như D98, thêm **danh sách email được duyệt**; người ngoài danh sách thấy
  trang "chờ duyệt". Người chưa đăng nhập chỉ thấy trang đăng nhập.

## 4. Cấu trúc

- **Thước định giá** là dấu nhận biết: một thanh có vạch giá hợp lý và chấm giá đang giao dịch, dùng cho cả 4 loại
  (cổ phiếu: thị giá so với giá mục tiêu; chứng quyền: giá chào bán so với giá Black-Scholes; ETF: giá so với iNAV;
  hợp đồng tương lai: giá so với chỉ số).
- **Trang "Hôm nay"**: một dòng về thị trường, rồi 4 nhóm xếp dọc, mỗi nhóm 3 mã đứng đầu kèm thước và "Xem tất cả".
- **Thanh đáy 5 mục** (điện thoại): Hôm nay, Cổ phiếu, Chứng quyền, ETF, Phái sinh. Danh mục, cảnh báo (chuông),
  tài khoản ở góc trên.
- **Trang một mã, 3 tầng**: (1) kết luận một câu + thước; (2) "Vì sao", 3–4 lý do bấm để mở; (3) số liệu, biểu đồ,
  giả định. Có liên kết chéo: cổ phiếu ↔ chứng quyền của mã đó ↔ ETF đang nắm nó.
- **Từ ngữ kết luận** chung cho 4 loại: Nên xem xét / Theo dõi / Bỏ qua; thước ghi "Rẻ x%" hoặc "Đắt x%". Không
  dùng MUA/BÁN ở tầng 1.
- **Danh sách cổ phiếu**: mã đạt cả "Giá trị" (định giá) và "Thời điểm" (dòng tiền) đứng đầu; có bộ lọc xem riêng
  từng phép đọc. Trong lúc Wyckoff chưa kiểm chứng xong (D101), "Thời điểm" dùng dòng tiền đang có (Gom/Xả, khối
  ngoại, tự doanh); để sẵn chỗ cho nhãn pha Wyckoff.
- **Danh mục**: mỗi người một danh mục cho cả 4 loại. Danh mục chứng quyền hiện có chuyển sang tài khoản quản trị.
- **Niềm tin**: mỗi con số kết luận có nút "Tính thế nào" (công thức, số đầu vào, nguồn, thời điểm). Dữ liệu cũ
  hoặc thiếu ghi ngay cạnh con số.
- **Không làm bảng giá trực tiếp.** Trang mã có biểu đồ nến và luôn ghi "số liệu lúc mấy giờ".

## 5. Nhận diện

- Gốc là logo BT Invest: navy làm màu mực, vàng kim là màu nhấn duy nhất (thương hiệu và vạch giá hợp lý trên
  thước), lưới kẻ ô và cây nến làm họa tiết. Font Be Vietnam Pro.
- Sáng mặc định, có chế độ tối dùng navy của logo.
- Màu giá: xanh lá tăng, đỏ giảm, tím trần, xanh lơ sàn; giá tham chiếu bằng màu mực thường (không dùng vàng).
- Số viết kiểu Việt Nam (1.234,5), luôn kèm đơn vị.
- Ếch tay mơ chỉ xuất hiện ở trang hướng dẫn và trang trống, không nằm trên bảng số liệu.
- Giữ luật mục 9 của `AGENTS.md` (không gradient, không emoji trang trí, không bảng màu Tailwind mặc định…).

## 6. Hiệu ứng

- Số chạy tới giá trị mới; chấm trên thước trượt tới vị trí.
- Bấm một dòng thì nở ra thành trang chi tiết, vuốt xuống để quay lại; gạch chỉ tab trượt theo ngón tay.
- Khung xương khi tải; biểu đồ vẽ nét từ trái sang phải lần đầu hiện.
- Hai chỗ trình diễn: trang đăng nhập (lưới kẻ ô chuyển động chậm, bốn cây nến mọc lên) và dòng tóm tắt thị trường
  hiện dần ở lần mở đầu trong ngày.
- Máy tính: mục dưới chuột lớn lên nhẹ (kiểu thanh Dock).
- Dấu "!" ở một số chỗ khó hiểu: máy tính rê chuột là hiện, rê ra là mất; điện thoại bấm mới hiện. Không có chuyến
  dẫn hay gợi ý tự hiện.
- Không dùng: nền chuyển động sau bảng số, thẻ nghiêng 3D, chữ lấp lánh.

## 7. Phạm vi bản đầu

- Có: định giá cổ phiếu, báo cáo tài chính, giả định, so sánh công ty chứng khoán; vĩ mô và tin 24h; dòng tiền
  ngành; xếp hạng VN100 và tích sản; cổ tức và quyền mua; bảng "Nên xem xét" và trang phân tích chứng quyền; ETF so
  với iNAV; basis phái sinh; cảnh báo giá; hướng dẫn có Ếch tay mơ.
- Chưa có (còn ở web cũ): Lướt CW 2–5 phiên, nút quét thủ công.

## 8. Kỹ thuật và thứ tự

- Giao diện mới viết tay bằng HTML/CSS/JS (người dùng chọn, không dùng React). Hiệu ứng tự viết, lấy ý tưởng từ
  21st.dev chứ không lấy thành phần về. Bộ máy Python giữ nguyên phía sau.
- Điện thoại là chính; máy tính là bản mở rộng.
- Bản mẫu duyệt trước khi viết code thật: bản chạy được, 5 màn hình điện thoại (Đăng nhập, Hôm nay, danh sách
  Chứng quyền, trang một chứng quyền, trang một cổ phiếu) và bản máy tính của trang Hôm nay; số liệu chụp từ hai
  web, chưa nối dữ liệu sống.
- Thứ tự xây sau khi duyệt: (1) khung, đăng nhập, Hôm nay, Cổ phiếu; (2) Chứng quyền; (3) ETF và phái sinh.

## 9. Điểm còn mở

- **Phái sinh chưa có tiêu chí "nên xem xét".** Web cũ chỉ có bảng basis. Web mới sẽ hiện basis trên thước, không
  gắn nhãn, cho tới khi người dùng chốt ngưỡng.
- **Lớp nối giao diện với bộ máy Python** (API, nơi đặt mã nguồn, bảng lưu tài khoản được duyệt và danh mục theo
  người): đụng schema và tích hợp, sẽ trình kế hoạch riêng và xin duyệt trước khi làm (`AGENTS.md` mục 4.7).
- **Cảnh báo theo từng người** hiện gửi một kênh Discord chung; cách tách theo người chốt ở bước xây.
- **Từ ngữ khi mở cho khách hàng**: nên hỏi lại pháp lý trước khi vai Khách hàng thấy kết luận.
- **"Rẻ x%" của cổ phiếu** (phát sinh khi dựng bản mẫu): bản mẫu ghi theo biên an toàn, 1 − giá ÷ giá mục tiêu, cùng
  công thức với chứng quyền (VRE: rẻ 26,4%). Web cũ ghi theo mức tăng tới giá mục tiêu (VRE: +35,8%). Cần người
  dùng chốt dùng số nào trên thước.
- **Quy đổi nhãn cổ phiếu** (phát sinh khi dựng bản mẫu): bản mẫu đổi MUA → Nên xem xét, NẮM GIỮ → Theo dõi,
  BÁN → Bỏ qua. Cần người dùng chốt, nhất là với mã đang bị tạm giữ công bố như VRE.

## 10. Bản mẫu đầu tiên (24/11/2026)

- Tệp: `docs/mockup_web_hop_nhat/index.html` (một tệp HTML/CSS/JS viết tay, không thư viện). Bản xuất bản:
  <https://claude.ai/artifact/6QajdXTXaRGeDbaygRSYof> (riêng tư).
- Xem tại máy: cấu hình `mockup-btinvest` trong `.claude/launch.json`, mở `http://localhost:8765/dev.html`
  (`dev.html` bọc `index.html` trong khung giống lúc xuất bản; chỉ sửa `index.html`).
- Có: đăng nhập (lưới kẻ ô trôi, nến mọc), Hôm nay, 4 danh sách (cổ phiếu, chứng quyền, ETF, phái sinh), trang
  chi tiết chứng quyền và cổ phiếu 3 tầng có liên kết chéo, tờ "thị trường vì sao", chế độ tối, dấu "!", bản
  máy tính có thanh bên.
- Số liệu thật, chụp ngày 24/11/2026: 21 chứng quyền nhóm nên xem xét (quét 14:02 23/11), CVRE2609 đầy đủ (kịch
  bản, 50 nến ngày, số đầu vào Black-Scholes), 18 trong 21 ETF, 8 hợp đồng tương lai, 4 cổ phiếu VRE, HDG, POW, MCH
  đọc từ chungkhoan.btinvest.vn. Chưa nối dữ liệu sống; phần chưa nạp ghi rõ "chưa có trong bản mẫu".
- Đã kiểm trong trình duyệt ở cỡ 375×812 và 1280×800, hai chế độ sáng và tối, không lỗi console. **Chưa kiểm
  trên điện thoại thật**: vuốt ngang đổi tab và vuốt xuống đóng tờ chi tiết chưa thử bằng ngón tay.

## 11. Góp ý lần 1 của người dùng và bản mẫu lần 2 (24/11/2026)

Người dùng chê bản đầu: không thấy dòng tiền vào thế nào (bằng chứng, biểu đồ); các tab gom chung nên giống nhau;
thiếu các biểu đồ bằng chứng của web cũ; "gần như xây mới, chưa có những cái hay bên trang cũ".
**Nguyên tắc rút ra: giữ gần đúng logic và nội dung web cũ, chỉ đổi cách bố trí.** Trước khi dựng phải kiểm kê
từng khối của web cũ rồi mới xếp lại, không tự rút gọn.

Đã mang sang ở lần 2 (cùng tệp, cùng đường dẫn xuất bản):

- **Tab cổ phiếu theo đúng tab "Dòng tiền ngành" cũ**: tóm tắt 20 phiên (khối ngoại bán ròng 7.436 tỷ, 10 gom,
  22 xả, tự doanh +1.513 tỷ), bản đồ ngành (10 ngành đầu bảng, bấm để lọc), danh sách mã có nhãn (dấu hiệu gom,
  dấu hiệu xả, trung tính, nội gom, chưa đủ dữ liệu), ba phiếu (khối ngoại, giá-KL, tự doanh) và bối cảnh.
- **Trang một cổ phiếu**: thẻ dòng tiền (nhãn, bối cảnh, cột khối ngoại 20 phiên, ba phiếu kèm bằng chứng, ghi chú
  phiếu ngược chiều) → biểu đồ giá và dòng tiền năm tầng như cũ (nến + MA20/MA50 + khối lượng; khối ngoại ròng và
  lũy kế; tự doanh ròng và lũy kế; ai gom ai xả với nền CMF20), có khung 1 tháng/3 tháng, bật tắt từng tầng, rê
  chuột đọc số → định giá (thước, cảnh báo, so sánh công ty chứng khoán). Số thật của VRE, 60 phiên.
- **Mỗi tab một hàng số riêng**: chứng quyền (IV − HV, hòa vốn, đòn bẩy), ETF (mức thường lệch có vạch trên
  thước, GTGD, chênh mua–bán), phái sinh (basis theo kỳ hạn, năm hóa, KL, ký quỹ).
- Trang chứng quyền: đủ 6 ô số, bảng kịch bản và hai biểu đồ nến (CW và cổ phiếu cơ sở) mở sẵn.

Web cũ có mà bản mẫu **chưa** mang sang:

- Cổ phiếu: bảng phiếu theo phiên, phiên thỏa thuận, volume profile, khung 6 tháng/1 năm/2 năm, chế độ "gồm thỏa
  thuận", dòng tiền theo ngày của ngành, 10 bài học; khoảng định giá so sánh, waterfall FCFF, bản đồ nhiệt độ
  nhạy, dự phóng 5 năm, phân tích kịch bản, báo cáo tài chính, giả định, xếp hạng VN100 và tích sản, cổ tức và
  quyền mua, vĩ mô và tin 24h (mới có ở tờ "thị trường vì sao").
- Chứng quyền: bảng 17 cột đầy đủ, nhóm theo dõi và bỏ qua, nến 1 giờ và 4 giờ, danh sách chứng quyền cùng mã cơ
  sở với đủ cột, danh mục, cảnh báo giá, hướng dẫn. (Lướt CW người dùng đã chọn để sau.)
- ETF: 19 cột đầy đủ và trang từng quỹ (biểu đồ giá và chênh lệch so với NAV).
- Phái sinh: cột ngày giao dịch cuối.

## 12. Kế hoạch xây web thật (24/11/2026, chờ người dùng duyệt)

Người dùng hỏi bản mẫu đã hoàn thiện dữ liệu chưa và yêu cầu "tích hợp đầy đủ tất cả": có ô tìm mã, vào trong có
đủ báo cáo tài chính, định giá công ty chứng khoán, biểu đồ, dòng tiền ngành, phân tích bằng AI.
**Bản mẫu chỉ là bản duyệt bố cục, số chép tay cho vài mã.** Muốn đủ mọi mã thì giao diện phải gọi vào bộ máy thật.

### Hiện trạng đã rà (không sửa gì)

- **Repo này**: gần như toàn bộ lớp dữ liệu gọi được mà không cần Streamlit.
  - Dòng tiền: `analysis/money_flow.compute_money_flow` trả dict đủ tóm tắt, bảng ngành, nhãn, phiếu, bối cảnh của
    cả 100 mã; `views/lw_chart.build_payload` trả đúng cấu trúc biểu đồ nhiều tầng; `ticker_history`,
    `volume_profile`, `votes_frame`, `block_frame` cũng thuần dữ liệu.
  - Định giá: `data_access/repo.build_company_data` → `engine/valuate.valuate`; độ nhạy và kịch bản ở
    `engine/sensitivity.py`; dự phóng ở `engine/forecast*.py`.
  - Báo cáo tài chính: `company.historical_is/bs`. So sánh công ty chứng khoán:
    `report/report_data.build_consensus_comparison`, bảng `consensus_history`, `consensus_synthesis`.
  - Cổ tức, xếp hạng VN100, tổng quan thị trường, vĩ mô: có hàm thuần dữ liệu (xem báo cáo rà trong phiên).
  - AI: chỉ DeepSeek, kết quả lưu ở `.deepseek_report_cache/`, `.macro_bulletin_cache.json`, bảng
    `consensus_synthesis`. Mỗi lần sinh mới tốn tiền API.
  - Danh sách mã cho ô tìm kiếm: bảng `tickers` (mã, tên, ngành).
  - Đã có `valuation/api/main.py` (FastAPI) nhưng chưa dịch vụ nào chạy nó, và các route hiện có phần lớn là ghi
    hoặc kích hoạt job; web mới cần một nhóm route **chỉ đọc** riêng.
- **`~/cw_scanner`**: mỗi trang trộn dữ liệu và HTML trong một hàm; các hàm nạp và tính bên dưới thì tách được
  (`doc_ket_qua`, `chon_luot`, `etf.doc_ket_qua`, `doc_nav`, `phai_sinh.lay_du_lieu`, `nen_cac_khung`, `dinh_gia`,
  `tinh_canh_bao`). Trang chi tiết gọi giá sống Vietcap/SSI lúc mở trang.
- **Dữ liệu trên máy Mac đã cũ**: giá tới 16/11, dòng tiền tới 12/11, quét chứng quyền 17/11, ETF 18/11. Số sống
  nằm trên VPS (D96). Web thật phải chạy trên VPS; trên Mac chỉ để dựng và thử.
- **VPS**: một image dùng chung cho 3 dịch vụ, `entrypoint.sh` nhận lệnh tùy ý nên thêm được dịch vụ API cùng
  image; đăng nhập qua Caddy `forward_auth` (D98). RAM 3,9 GB không swap, phải đo bộ nhớ trước khi thêm dịch vụ.

### Các lát, mỗi lát chạy được và có test

1. **Tìm mã và dòng tiền thật cho cả 100 mã.** Route chỉ đọc: danh sách mã, tóm tắt và bảng ngành, danh sách
   nhãn và phiếu, thẻ và biểu đồ nhiều tầng của một mã (đủ khung thời gian, bảng phiếu, phiên thỏa thuận, volume
   profile). Giao diện: tách bản mẫu thành trang gọi API, thêm ô tìm kiếm dùng ở mọi tab.
2. **Định giá, báo cáo tài chính, công ty chứng khoán, AI của một mã.** Kết quả `valuate`, cờ cảnh báo, pha
   trộn phương pháp, độ nhạy, kịch bản, dự phóng; bảng IS/BS; từng công ty chứng khoán và phần tổng hợp luận
   điểm; cổ tức; báo cáo AI đã lưu. Sinh AI mới chỉ dành cho Quản trị vì tốn tiền. Phải đo thời gian `valuate`
   một mã và quyết định cách lưu đệm (không thêm bảng khi chưa hỏi).
3. **Thị trường, vĩ mô, xếp hạng VN100, lịch cổ tức.**
4. **Chứng quyền, ETF, phái sinh**: thêm route JSON vào `~/cw_scanner` bằng cách tách phần dữ liệu khỏi phần HTML
   của từng trang, giữ nguyên trang cũ.
5. **Danh mục, cảnh báo, tài khoản được duyệt, hai vai**: cần chỗ lưu theo người dùng, tức là đụng schema; trình
   riêng và xin duyệt.
6. **Đưa lên VPS** tại btinvest.vn: thêm dịch vụ API, cấu hình Caddy, dùng lại đăng nhập; cần quyền vào VPS và
   người dùng duyệt từng bước.

### Tiến độ

- **Lát 1 xong ngày 24/11/2026 (D102)**, chạy tại máy: `valuation/services/web_flow.py`, `valuation/api/web_main.py`,
  `web/` (index.html, app.css, app.js), `tests/test_web_flow.py`, config `web:`. Xem tại máy: preview
  `btinvest-web` hoặc `uvicorn valuation.api.web_main:app --port 8600`, mở `http://localhost:8600/`; mở thẳng
  một mã bằng `?ma=VRE`. Biểu đồ là biểu đồ Lightweight Charts của tab cũ nhúng nguyên, chưa đổi màu theo nhận diện mới.
- Đo cho lát 2: `build_company_data` + `valuate` mất 0,6–0,7 giây với VRE, HPG; 11 giây với VCB (ngân hàng).
  Trên máy Mac cả ba ra NOT_RATED vì DB cũ (cờ `STALE_PRICE`, `STALE_MACRO_RF`); giá trị hợp lý của VRE vẫn khớp
  VPS (31.852 so với 31.856). Nhãn thật chỉ có khi chạy trên VPS hoặc sau khi cập nhật DB máy Mac.

- **Lát 2 xong ngày 24/11/2026 (D103)**, chạy tại máy: `valuation/services/web_valuation.py`, 5 route mới,
  phần "Định giá" trên trang một mã với 9 mục mở ra. Còn thiếu so với tab cũ: nút đổi TTM/FY, sửa giả định và lưu
  kịch bản, biểu đồ waterfall FCFF, khoảng định giá ±15%, sinh báo cáo AI mới.

- **Lát 3 xong ngày 24/11/2026 (D104)**, chạy tại máy: `valuation/services/web_market.py`, 4 route mới, tab Hôm
  nay thật và là tab mở đầu, công tắc "Dòng tiền / Xếp hạng VN100" trong tab Cổ phiếu. Các nút cập nhật vĩ mô,
  làm mới tin, định giá lại VN100, xuất Excel chưa có (thao tác ghi hoặc gọi mạng).
- **Lát 4 xong ngày 24/11/2026 (D105)**, chạy tại máy, cần HAI dịch vụ: dịch vụ chứng quyền (`~/cw_scanner`,
  `web.py` cổng 8000, preview `cw-dich-vu`) và web mới (cổng 8600, preview `btinvest-web`).
  - `~/cw_scanner/web_api.py` (mới) + 9 dòng móc trong `web.py`: `/api/chung-quyen`, `/api/chung-quyen/<mã>`,
    `/api/etf`, `/api/phai-sinh`, `/api/trang-cu/{cw,etf,phai-sinh}/<mã>`. Đọc đúng file kết quả và gọi đúng
    hàm của trang cũ; các hàm `trang_*` không bị sửa.
  - `valuation/services/web_cw.py` + 7 route trong `web_main.py`: cầu nối chỉ GET sang dịch vụ đó
    (`web.cw_base_url`), không tính gì.
  - `web/app.js`: ba tab thật, tờ chi tiết của chứng quyền, quỹ, hợp đồng; ô tìm thêm ba loại mã; mục
    "Chứng quyền và ETF" ở tab Hôm nay; dấu "!" giải thích (rê chuột hiện, điện thoại bấm).
  - **Dựng lại theo giao diện mới:** ba danh sách, phần tóm tắt lúc quét của một chứng quyền (4 tiêu chí, số
    chính), số lúc lập báo cáo của một quỹ, số chính của một hợp đồng.
  - **Vẫn là trang cũ đặt trong khung, chỉ đổi màu và phông:** phần phân tích theo giá lúc mở của từng mã
    (định giá lại, nến 1 giờ, 4 giờ, ngày, sổ lệnh, khớp lệnh, IV theo thời gian, mức theo kịp cổ phiếu cơ sở,
    lãi lỗ nếu giữ đến đáo hạn, giá so với iNAV, basis theo ngày). Tách số khỏi HTML của các trang này là việc
    riêng, chưa làm.
  - **Chưa có:** Lướt CW, CW sắp ra mắt, cảnh báo giá, danh mục, nút quét, trang hướng dẫn (liên kết hướng dẫn
    trong khung mở web chứng quyền cũ ở thẻ mới).
- **Còn lại:** lát 5 (tài khoản được duyệt, danh mục, cảnh báo: kế hoạch ở mục 13, chờ duyệt), lát 6 (đưa lên VPS; lúc đó hai dịch vụ
  chạy cạnh nhau và `web.cw_base_url` trỏ vào dịch vụ chứng quyền trên VPS).

### Rủi ro

- Không đổi công thức, ngưỡng; API chỉ gọi hàm sẵn có và test so khớp với kết quả hàm đó.
- Lát 1–3 không ghi DB. Mọi thao tác ghi (lưu kịch bản, danh mục, cảnh báo, sinh AI) để lát 5 hoặc xin duyệt riêng.
- Hai repo, hai dịch vụ: giao diện phải gọi hai nguồn; Caddy tách đường dẫn.
- `valuate` có thể chậm (đợt quét gần nhất khoảng 30 giây mỗi mã, gồm cả bước AI): chưa đo riêng.

## 13. Kế hoạch lát 5: tài khoản được duyệt, danh mục, cảnh báo (25/11/2026, người dùng duyệt « giờ làm 5a »)

> Lát đầu tiên có ghi dữ liệu và có schema mới, nên trình riêng theo mục 4.7 của `AGENTS.md`. Chưa viết dòng code nào.

### Người dùng đã chốt (25/11/2026, hỏi từng câu)

1. **Phạm vi:** lát 5 chỉ gồm tài khoản được duyệt, danh mục và cảnh báo. Các nút thao tác của Quản trị (cập nhật
   vĩ mô, làm mới tin, định giá lại VN100, sinh báo cáo AI mới, lưu kịch bản, xuất tệp) để sau khi lên VPS; trong
   lúc đó dùng ở web cũ.
2. **Duyệt người:** Quản trị duyệt ngay trên web. Người mới thấy trang "chờ duyệt". Email Quản trị đầu tiên người
   dùng tự điền vào `.env` trên máy chủ.
3. **Danh mục:** đủ 4 loại, có nhập lệnh mua bán; hiện vị thế, giá vốn bình quân, lãi lỗ, thước so với giá hợp lý.
   Chứng quyền giữ tín hiệu giữ hay bán của trang Danh mục cũ.
4. **Danh mục chứng quyền đang có:** giữ ở web cũ (bản chính, Discord 5 phút chạy như hiện nay) tới lúc web mới
   thay web cũ; khi đó chép một lần sang tài khoản Quản trị. Danh mục ở web mới bắt đầu trống.
5. **Cách báo:** chỉ báo trong web (chuông, âm thanh, thông báo của trình duyệt khi đang mở). Không thêm Discord,
   không thêm lịch chạy nền.
6. **Lãi lỗ:** sau phí và thuế như web cũ, mức phí thuế ghi cạnh con số.
7. Cho đọc VPS (chỉ đọc) để biết dịch vụ coin trả gì: đã đọc, kết quả ở dưới.
8. Quản trị xem được lệnh của các tài khoản Nhân viên (chốt khi duyệt kế hoạch, xem mục Thiết kế chung).

### Hiện trạng đã rà (không sửa gì)

- **Đăng nhập (D98):** Caddy `forward_auth` hỏi coin `GET /api/v1/auth/me`; 2xx thì cho qua. Hai web không biết ai
  đang dùng. Cookie `access_token` và `refresh_token`, `Domain=.btinvest.vn`. `/me` trả
  `{user: {_id, username, email (có thể trống), firstName, lastName, role, status, …}, permissions, …}`, giới hạn
  600 lượt mỗi phút mỗi IP. Email không bắt buộc ở coin nên khóa nhận diện phải là `user._id`.
- **Danh mục chứng quyền cũ:** `danh_muc.csv` dùng chung (cột `id, ngay, ma_cw, loai, so_luong, gia, chot_loi,
  cat_lo, ghi_chu`). `danh_muc.tinh_vi_the`: giá vốn bình quân đã gồm phí mua, `vốn += SL × giá × (1 + phí)`; lãi
  nếu bán ngay `= (giá bán được × (1 − phí − thuế bán) − giá vốn) × SL`, phí 0,15%, thuế bán 0,1%
  (`cw_scanner.PHI_GIAO_DICH`, `THUE_BAN`). `danh_gia_danh_muc` cho tín hiệu giữ hay bán, gần ngày giao dịch cuối,
  chốt lời, cắt lỗ, lệch so với cổ phiếu cơ sở.
- **Cảnh báo cũ:** trang `/canh-bao` có hai phần: bất thường đang mua được (chứng quyền lệch rẻ, ETF dưới iNAV, hợp
  đồng lệch; chung cho mọi người) và mức giá tự đặt (`muc_gia.csv` dùng chung, tối đa 50 mức, mã chứng quyền, cổ
  phiếu, ETF, hợp đồng). Trang đang mở hỏi `/canh-bao/tin` mỗi 60 giây trong giờ khớp lệnh.
- **Dữ liệu:** DB định giá trên VPS là SQLite và là bản chính (D96); bản ở máy Mac cũ và có thể bị thay bằng bản
  đóng gói `vn100_full.db.gz`. Chưa có bảng nào cho tài khoản, danh mục, cảnh báo. Repo không dùng công cụ
  migration.

### Thiết kế chung

- **Dữ liệu người dùng nằm trong tệp SQLite riêng** (`web_user.db`, đường dẫn ở biến môi trường `WEB_USER_DB_URL`),
  không nằm trong DB định giá. Lý do: DB định giá có thể bị thay bằng bản đóng gói, khi đó danh mục của mọi người
  mất theo. Web mới không ghi gì vào DB định giá trong lát này.
- **Bảng mới** (tạo bằng `create_all`, chạy lại không tạo trùng; có bảng `web_meta` ghi phiên bản schema):
  - `web_users`: `id`, `coin_user_id` (duy nhất), `email`, `username`, `ten_hien_thi`, `vai` (`quan_tri` /
    `nhan_vien`), `trang_thai` (`cho_duyet` / `da_duyet` / `khoa`), `tao_luc`, `duyet_luc`, `duyet_boi`, `thay_luc`.
  - `web_orders`: `id`, `user_id`, `loai` (`co_phieu` / `chung_quyen` / `etf` / `hop_dong`), `ma`, `chieu`, `so_luong`,
    `gia`, `ngay`, `chot_loi`, `cat_lo`, `ghi_chu`, `hop_dong_gd_cuoi` (chỉ hợp đồng tương lai), `ma_yeu_cau` (duy nhất
    theo người, để bấm gửi hai lần không thành hai lệnh), `tao_luc`, `xoa_luc`.
  - `web_price_levels`: `id`, `user_id`, `ma`, `chieu` (`duoi` / `tren`), `muc`, `ghi_chu`, `tao_luc`, `xoa_luc`.
  - `web_audit`: `id`, `luc`, `user_id`, `viec`, `doi_tuong`, `chi_tiet` (ai duyệt ai, ai thêm xóa lệnh nào).
- **Không xóa cứng:** xóa lệnh hay mức giá là ghi `xoa_luc`; dòng vẫn còn để truy vết (luật vàng 6).
- **Riêng tư:** mỗi truy vấn lọc theo `user_id` của người đang đăng nhập. **Người dùng chốt 25/11/2026 (hộp chọn
  khi trình 5b): Quản trị xem được danh mục của TẤT CẢ mọi người, kể cả Quản trị khác; chỉ xem, không thêm hay
  xóa lệnh hộ.** Trang Danh mục của Nhân viên ghi rõ "Quản trị xem được danh mục này". Mức giá tự đặt (5c)
  chưa hỏi: mặc định vẫn riêng.
- **Route ghi nằm ở tệp riêng** (`valuation/api/web_user_routes.py`); `web_main.py` giữ nguyên là chỉ đọc.
- **Chống giả mạo yêu cầu:** route ghi chỉ nhận JSON và chỉ khi `Origin` trùng tên miền của web (như
  `nguon_hop_le` của web chứng quyền). Mã nhập vào phải có trong danh sách mã của đúng loại; số lượng, giá phải dương.

### Ba phần, làm lần lượt, mỗi phần chạy được và có test

**5a. Tài khoản, duyệt, hai vai**

- `valuation/services/web_auth.py`: lấy cookie `access_token` của yêu cầu, hỏi coin `/api/v1/auth/me` (địa chỉ ở
  `WEB_AUTH_ME_URL`, trên VPS là trong mạng Docker), nhớ kết quả 60 giây theo mã băm của cookie để không vượt giới
  hạn 600 lượt mỗi phút. Coin không trả lời thì trả 503, **không cho vào** (đóng khi lỗi).
- Lần đầu thấy một người: tạo dòng `cho_duyet`; nếu email hoặc tên đăng nhập nằm trong `WEB_ADMIN_EMAILS` (`.env`) thì
  là `quan_tri`, `da_duyet`. Người `cho_duyet` hoặc `khoa` chỉ gọi được `/api/toi`; mọi route số liệu của lát 1–4
  thêm điều kiện "đã duyệt".
- Route: `GET /api/toi`; Quản trị: `GET /api/tai-khoan`, `POST /api/tai-khoan/{id}/duyet`, `/khoa`, `/vai`. Không tự
  hạ vai hoặc khóa chính mình khi đó là Quản trị cuối cùng.
- Giao diện: trang "chờ duyệt"; nút tài khoản ở góc trên (tên, vai, đăng xuất về `/dang-nhap?dang-xuat=1`); mục
  Tài khoản cho Quản trị (danh sách, duyệt, khóa, đổi vai).
- **Chạy tại máy Mac:** không có coin, nên có chế độ `WEB_AUTH_MODE=dev` (một người dùng thử lấy từ biến môi
  trường). Chế độ này chỉ bật khi đặt biến rõ ràng và máy chủ chỉ nghe ở 127.0.0.1; mặc định là `coin`.
- Test (coin giả bằng `httpx.MockTransport`): không cookie 401; chờ duyệt 403; Quản trị đầu tiên từ `.env`; duyệt
  hai lần không tạo trùng; nhân viên gọi route Quản trị 403; `Origin` lạ bị từ chối; coin sập 503; nhớ 60 giây thật
  sự giảm số lần hỏi; mỗi việc duyệt có dòng `web_audit`.

**5b. Danh mục 4 loại**

- Route: `GET /api/danh-muc` (vị thế đã định giá), `GET /api/danh-muc/lenh`, `POST /api/danh-muc/lenh`,
  `POST /api/danh-muc/lenh/{id}/xoa`.
- **Vị thế và lãi lỗ dùng đúng cách của `danh_muc.tinh_vi_the`:** giá vốn bình quân đã gồm phí mua; bán quá số đang
  nắm thì báo lỗi, không lưu. Chứng quyền, cổ phiếu, ETF: lãi nếu bán ngay
  `= (giá bán được × (1 − 0,15% − 0,1%) − giá vốn) × số lượng`. Hợp đồng tương lai: lãi lỗ nếu đóng ngay
  `= chiều × (giá hiện tại − giá mở bình quân) × 100.000 × số hợp đồng − phí và thuế` theo hằng số của
  `phai_sinh.py` (`PHI_CTCK_HD`, `PHI_SO_HD`, `PHI_BU_TRU_HD`, `thue_mot_lan`). Hai công thức cho cổ phiếu, ETF và
  hợp đồng là **mới ở web này**: sẽ trình riêng công thức kèm ca tính tay trước khi viết, theo luật vàng 1.
- **Giá hiện tại:** bảng giá Vietcap qua dịch vụ chứng quyền, cùng nguồn với trang Danh mục cũ, cho cả 4 loại; luôn
  ghi "số liệu lúc mấy giờ". Dịch vụ chứng quyền cần thêm một đường **chỉ tính, không ghi tệp** nhận danh sách lệnh
  và trả vị thế đã định giá (gọi lại `tinh_vi_the`, `danh_gia_danh_muc`); `danh_muc.csv` và lịch Discord không bị
  đụng tới.
- **Thước:** cổ phiếu so với giá trị hợp lý của đợt định giá gần nhất; chứng quyền so với giá Black-Scholes; ETF so
  với iNAV; hợp đồng so với chỉ số (không tô rẻ đắt).
- **Hợp đồng tương lai lưu theo ngày giao dịch cuối**, không theo tên `VN30F1M`: tên đó mỗi tháng trỏ sang hợp đồng
  khác, lưu theo tên thì vị thế tháng trước sẽ bị định giá bằng hợp đồng tháng sau.
- Giao diện: nút Danh mục ở góc trên; tổng giá trị và lãi lỗ; 4 nhóm, mỗi vị thế một dòng có thước; form nhập lệnh;
  sổ lệnh; chứng quyền có tín hiệu giữ hay bán như trang cũ.
- Test: ca tính tay cho từng loại; người A không đọc, không xóa được lệnh của người B; thêm cùng một lệnh hai lần
  theo cùng mã yêu cầu không nhân đôi; bán quá số đang nắm bị từ chối; xóa là xóa mềm; vị thế chứng quyền khớp
  `tinh_vi_the` của web cũ trên cùng dữ liệu.

**5c. Cảnh báo**

- Cảnh báo chung (bất thường đang mua được): JSON từ dịch vụ chứng quyền, cùng số với trang `/canh-bao` cũ.
- Mức giá tự đặt theo từng người: `GET /api/muc-gia`, `POST /api/muc-gia`, `POST /api/muc-gia/{id}/xoa`; tối đa 50
  mức mỗi người như cũ; trạng thái đã chạm tính bằng `canh_bao_gia.trang_thai_muc` qua một đường chỉ tính ở dịch
  vụ chứng quyền.
- Tín hiệu của danh mục người đó (từ 5b) gộp vào cùng danh sách.
- Giao diện: chuông ở góc trên có số; hỏi mỗi 60 giây trong giờ khớp lệnh; âm thanh và thông báo trình duyệt khi
  có cảnh báo mới (xin quyền khi người dùng bấm bật); "đã xem" nhớ trong trình duyệt như trang cũ.
- Test: mức giá của ai người đó thấy; quá 50 mức bị từ chối; mã sai mẫu bị từ chối; ngoài giờ không gọi giá.

### Không nằm trong lát 5

Nút thao tác của Quản trị; vai Khách hàng; Discord theo từng người; Lướt CW; CW sắp ra mắt; trang hướng dẫn; dựng lại
trang phân tích từng mã (đang là trang cũ trong khung); chép danh mục chứng quyền cũ (làm lúc chuyển hẳn).

### Rủi ro và điểm chưa kiểm

- **Đăng nhập thật chỉ thử được trên VPS** (lát 6). Ở máy Mac chỉ thử với coin giả và chế độ `dev`; hình dạng `/me`
  lấy từ mã nguồn đọc ngày 25/11, chưa gọi thử.
- Coin sập thì web mới không vào được (đã là rủi ro của D98). Nhớ 60 giây nghĩa là người vừa bị khóa ở coin còn vào
  được tối đa 60 giây.
- Thêm một tệp dữ liệu phải sao lưu trên VPS; mất tệp là mất danh mục của cả đội. Lịch sao lưu làm ở lát 6.
- Cổ tức bằng cổ phiếu, chia tách làm đổi số lượng và giá vốn: bản đầu **không tự điều chỉnh**, người dùng nhập
  lệnh điều chỉnh; sẽ ghi rõ trên trang.
- Phí và thuế là mức giả định chung, khác nhau theo công ty chứng khoán; ghi cạnh con số, chưa cho từng người đổi.
- Dịch vụ chứng quyền phải thêm hai đường chỉ tính (vị thế, mức giá): sửa ở repo `~/cw_scanner`, sẽ trình cách làm
  cụ thể khi tới 5b.
- VPS 3,9 GB không swap: thêm tiến trình web mới cần đo RAM ở lát 6.

### Thứ tự và điểm dừng

5a → 5b → 5c. Xong mỗi phần: test, thử trên trình duyệt, ghi `DECISIONS.md` và `PROGRESS.md`, báo lại rồi mới sang
phần sau. Trước 5b dừng một lần để trình công thức lãi lỗ của cổ phiếu, ETF và hợp đồng tương lai.

### Tiến độ lát 5

- **5a xong ngày 25/11/2026 (D106)**, chạy tại máy ở chế độ `dev`: `valuation/db/web_user.py`,
  `valuation/services/web_auth.py`, `web_users.py`, `valuation/api/web_deps.py`, `web_user_routes.py`, phần tài khoản
  trong `web/`, `tests/test_web_auth.py`. Tên cột đúng như bản kế hoạch. Preview `btinvest-web` vào bằng một tài
  khoản Quản trị thử (`quantri@thu.local`); muốn thử vai khác thì đổi `WEB_DEV_USER` trong `.claude/launch.json`.
- Chưa kiểm được ở máy Mac: đăng nhập thật với coin (để lát 6).
- **5b xong ngày 25/11/2026 (D107)**, chạy tại máy với hai dịch vụ và giá Vietcap trực tiếp: `~/cw_scanner/vi_the.py`
  và đường POST chỉ tính `/api/tinh/danh-muc`; ở đây `web_orders`, `valuation/services/web_portfolio.py`, 5 route
  danh mục, giao diện Danh mục, `tests/test_web_portfolio.py`. Ba công thức lãi lỗ và quyền xem người dùng duyệt
  bằng hộp chọn (ghi ở D107).
- **5c xong ngày 25/11/2026 (D108)**, chạy tại máy với hai dịch vụ và giá thật trong phiên chiều: ở
  `~/cw_scanner` thêm `GET /api/canh-bao`, `GET /api/canh-bao/tin`, `POST /api/tinh/muc-gia` và cảnh báo ngưỡng
  lãi lỗ của cổ phiếu, ETF trong `vi_the.py`; ở đây bảng `web_price_levels`, `valuation/services/web_alerts.py`,
  5 route, chuông và tờ Cảnh báo trong `web/`, `tests/test_web_alerts.py`. Khác bản kế hoạch: « đã chạm lúc mấy
  giờ » không có (web cũ có nhờ lịch 5 phút; web mới không có lịch nền nên chỉ biết « đang chạm »); đặt lại
  đúng mức đang có thì trả mức đó thay cho cột mã yêu cầu; phần chung được nhớ 45 giây dùng cho mọi người.
- **Lát 5 xong cả ba phần.** Kế tiếp: lát 6 (đưa lên VPS), xin duyệt từng bước.

## 14. Kế hoạch lát 6: đưa web mới lên VPS tại btinvest.vn (25/11/2026)

> Lát đầu tiên đụng máy chủ đang chạy thật (mục 4.7 và 8 của `AGENTS.md`): mỗi bước GHI trên VPS xin duyệt.
> **Trạng thái tối 25/11/2026:** người dùng trả lời "Đưa thẳng lên btinvest.vn luôn. còn lại theo bạn": đặt web mới
> thẳng ở `btinvest.vn`, phần còn lại theo đề xuất (commit tại máy, đọc VPS chỉ đọc, rồi trình các bước ghi). Đã
> commit tại máy ở hai dự án (chưa đẩy) và xong B0; kết quả B0 và hai đoạn cấu hình soạn sẵn ở cuối mục này.
> **Chưa có bước ghi nào trên VPS.**

### Đích của lát 6

Web mới chạy thật tại `https://btinvest.vn`, đăng nhập bằng tài khoản coin, số liệu sống của VPS. Hai web cũ
(`chungkhoan.btinvest.vn`, `chungquyen.btinvest.vn`) **giữ nguyên, chạy song song**; chuyển hẳn là việc sau.

### Hiện trạng đã rà (đọc bản sao cấu hình trong `deploy/` và hỏi từ ngoài, không vào VPS)

- **btinvest.vn** đang là trang chờ "Website đang được xây dựng" (tệp ngày 17/11); `www` chuyển hướng về đó. Mọi
  tên miền phụ `*.btinvest.vn` đều trỏ về cùng địa chỉ, nên thêm tên miền phụ không phải sửa DNS.
- **Dự án định giá trên VPS** (`/srv/apps/vn100`): `app/` là bản git của repo này, tự deploy khoảng 3 phút sau khi
  `main` trên GitHub đổi (dựng lại image `vn100:local`, tạo lại ba container). `docker-compose.yml`, `Dockerfile`,
  `entrypoint.sh`, `scheduler.py`, `.env` nằm ngoài repo; `entrypoint.sh` nhận lệnh tùy ý nên chạy được dịch vụ thứ
  tư cùng image. **Đẩy lên GitHub chính là deploy.**
- **Dự án chứng quyền trên VPS** (`/srv/apps/chungquyen`): mã vào bằng `git push vps main` từ máy Mac (chỉ ở mạng
  nhà), deploy tự chạy trong 3 phút. Container `chungquyen` nghe cổng 8000 trong mạng Docker `web`. Bản ở máy đang
  bằng bản trên VPS (chưa có phần `web_api.py`, `vi_the.py` của lát 4–5).
- **Đăng nhập (D98):** Caddy `forward_auth` hỏi coin (`coin-check-api-1:8090`), chưa đăng nhập thì 302 về
  `/dang-nhap`. Web mới tự hỏi coin `/me` bằng cookie phiên và tự trả 401; giao diện gặp 401 thì chuyển sang
  `/dang-nhap?next=…` (`web/app.js`).
- **RAM** (số lúc viết kế hoạch, đã cũ: xem "Kết quả B0" ở cuối mục): VPS 3,9 GB không swap, từng treo 18/11. Giới hạn đang đặt: web định giá 1.024 MB, worker 640 MB, bot
  256 MB, web chứng quyền 384 MB, worker chứng quyền 768 MB, cộng coin và Caddy. Web mới ở máy Mac dùng 207 MB sau
  hơn 3 giờ chạy thử.
- **Python:** VPS chạy 3.12, máy Mac 3.14. Toàn bộ tệp mới của hai dự án biên dịch được bằng Python 3.12.
- **Lúc viết chưa biết, B0 đã trả lời (cuối mục):** nội dung thật của đoạn `(coin_login)` và khối `btinvest.vn` trong
  `/srv/web/conf/Caddyfile`; RAM đang dùng thật; `docker-compose.yml` thật có khác bản sao trong repo không.

### Thiết kế

1. **Container thứ tư `btinvest-web`** trong `/srv/apps/vn100/docker-compose.yml`, cùng image, lệnh
   `python -m uvicorn valuation.api.web_main:app --host 0.0.0.0 --port 8600`, một tiến trình (bộ nhớ đệm nằm trong
   tiến trình). Đọc DB định giá ở chế độ chỉ đọc như hiện nay. Giới hạn RAM 768 MB (chốt sau B0; đề xuất ban đầu 512 MB). Kiểm sống
   bằng `/api/suc-khoe`. Biến môi trường đặt ngay trong compose vì không phải bí mật: `WEB_AUTH_MODE=coin`,
   `WEB_AUTH_ME_URL=http://coin-check-api-1:8090/api/v1/auth/me`, `WEB_USER_DB_URL=sqlite:////data/web_user/web_user.db`,
   `WEB_CW_BASE_URL=http://chungquyen:8000`. Riêng `WEB_USER_DB_URL` đặt ở phần dùng chung của compose, vì job sao
   lưu chạy trong `vn100-worker` phải thấy đúng tệp đó.
2. **Tệp dữ liệu người dùng** nằm ở `/data/web_user/web_user.db` trong volume `/data` (sống qua deploy), tách tệp với
   DB định giá; `entrypoint.sh` chỉ thay `vn100_full.db` nên không đụng tới.
3. **Caddy cho `btinvest.vn`:** `/api/v1/auth/*` sang coin, `/dang-nhap` là trang đăng nhập chung, còn lại sang
   `btinvest-web:8600`. **Không dùng `forward_auth` cho tên miền này**: ứng dụng tự kiểm đăng nhập và quyền ở từng
   route, nên `/api/*` trả 401 đúng như giao diện chờ (việc còn treo từ D106). Khung web tĩnh (HTML, CSS, JS, không
   có số liệu) ai cũng tải được, giống các đường dẫn công khai của hai web cũ. Vì Caddy không còn chặn hộ, thêm một
   test duyệt **mọi** route `/api/` của ứng dụng: chưa đăng nhập thì phải 401, trừ `/api/suc-khoe`.
4. **Dịch vụ chứng quyền:** đẩy phần lát 4–5 (`web_api.py`, `vi_the.py` và các chỗ tách hàm) lên VPS. Các đường
   `/api/*` mới cũng mở ở `chungquyen.btinvest.vn` sau lớp đăng nhập coin như mọi trang của web đó; chúng chỉ đọc
   và chỉ tính, không ghi `danh_muc.csv` hay `muc_gia.csv`.
5. **Sao lưu `web_user.db`:** script dùng cơ chế sao lưu của SQLite (chép nhất quán khi đang có người dùng), kiểm
   `integrity_check`, giữ 14 bản gần nhất trong `/data/web_user/sao_luu/`; chạy mỗi ngày bằng một dòng trong
   `scheduler.py` của `vn100-worker`. Bản sao lưu nằm cùng volume: chống được xóa nhầm và hỏng tệp, **không** chống
   được mất cả ổ; chép ra ngoài máy là việc riêng, chưa có.
6. **Quản trị đầu tiên:** người dùng tự thêm dòng `WEB_ADMIN_EMAILS=…` vào `/srv/apps/vn100/.env` (đã chốt ở lát 5).

### Việc làm tại máy trước, không đụng VPS

- **Xong 25/11/2026 (D109):** biến `WEB_CW_BASE_URL` (để trống thì dùng `web.cw_base_url` trong config như hiện
  nay); tự tạo thư mục cha của tệp dữ liệu người dùng; test chặn cả 35 đường `/api/` khi chưa đăng nhập; script sao
  lưu `scripts/backup_web_user_db.py` (chạy hai lần trong ngày không tạo hai bản, giữ đúng số bản, bản sao đọc lại
  đủ dòng). 70 test web qua.
- **Xong tối 25/11/2026:** quét secret (máy không có `gitleaks`: grep các mẫu khóa, email, soát danh sách tệp; không
  thấy khóa nào), chạy lại cả bộ test (ở đây 1.301 qua, vẫn đúng 9 test trượt cũ; dự án chứng quyền 239 qua), rồi
  commit từng tệp: ở đây `af49a65` (kế hoạch, bản mẫu) và `7d9e8c2` (mã, test, cấu hình, tài liệu); dự án chứng
  quyền `f66bc9c`. Chưa đẩy. Lúc chạy lại bộ test dự án chứng quyền lộ một lỗi có sẵn của web cũ: từ chối POST
  thiếu `Origin` khi chưa đọc thân, bên gửi có lần nhận "connection reset" thay vì câu 403 (test trượt 17/60 lần);
  đã sửa ở `web.py` (đọc thân rồi mới từ chối, 0/60 lần trượt), nằm trong `f66bc9c`.
- **Làm cùng lúc với bước tương ứng trên VPS**, để bản sao luôn đúng với máy thật: cập nhật `deploy/docker/`
  (compose ở B4, scheduler ở B7, README) và chép đoạn Caddy đã dùng ở B5.

### Các bước trên VPS, mỗi bước dừng xin duyệt

| Bước | Việc | Ghi hay đọc | Kiểm sau bước |
|---|---|---|---|
| B0 | Đọc Caddyfile, compose thật, `docker ps`, `docker stats`, `free -m` | Chỉ đọc | **Xong 25/11**: chốt đoạn Caddy và giới hạn RAM (cuối mục) |
| B1 | `git push vps main` ở dự án chứng quyền, ngoài giờ khớp lệnh | Ghi | Web chứng quyền cũ vẫn chạy; `/api/chung-quyen` trả JSON; 239 test trong container |
| B2 | `git push origin main` ở dự án định giá (VPS tự dựng lại và khởi động lại ba container cũ) | Ghi | Ba container cũ khỏe; web định giá cũ mở được |
| B3 | Người dùng tự thêm `WEB_ADMIN_EMAILS` vào `.env` trên VPS | Người dùng làm | Không in giá trị |
| B4 | Sao lưu rồi sửa compose trên VPS, `docker compose up -d btinvest-web` | Ghi | Kiểm sống, RAM, `/api/toi` trả 401 khi gọi trong mạng Docker |
| B5 | Sao lưu rồi sửa khối `btinvest.vn` trong Caddyfile, `caddy validate`, tải lại | Ghi | `https://btinvest.vn/` ra khung web; `/api/toi` trả 401; hai web cũ không đổi |
| B6 | Người dùng đăng nhập thật trên máy tính và điện thoại, duyệt tài khoản thử | Người dùng làm | Số của vài mã khớp web cũ; chuông, âm thanh, thông báo |
| B7 | Thêm dòng sao lưu vào `scheduler.py` trên VPS | Ghi | Chạy tay một lần, có bản sao, chạy lại không nhân đôi |
| B8 | Đo trong giờ khớp lệnh phiên kế tiếp | Chỉ đọc | Thời gian trả tin cảnh báo, RAM của `btinvest-web` và `chungquyen` |

Chạy lại 9 test đang trượt ở máy Mac trong container trên VPS thuộc B8 (chỉ 9 test đó, không chạy cả bộ vì RAM).

### Quay lui

- Web mới: `docker compose stop btinvest-web`, chép lại bản sao lưu Caddyfile rồi tải lại Caddy: `btinvest.vn` về
  trang chờ. `web_user.db` còn nguyên trong volume.
- Mã: hai web cũ không gọi tệp mới nào của web hợp nhất. Ở dự án chứng quyền có ba tệp cũ bị sửa (`web.py`,
  `web_canh_bao.py`, `canh_bao_gia.py`): nếu web cũ lỗi sau B1 thì `git revert` rồi đẩy lại.

### Rủi ro

- **RAM** từng là rủi ro lớn nhất; B0 cho thấy máy đã lên 12,9 GB có swap, còn trống hơn 8 GB, nên không phải hạ
  giới hạn dịch vụ nào. Vẫn đo lại RAM của `btinvest-web` sau B4 và trong giờ khớp lệnh (B8).
- **Mọi lần deploy sau B4 đều chờ `btinvest-web` khỏe:** container này không lên được trong 240 giây thì lệnh deploy
  tự quay về commit trước cho cả dự án định giá. Kiểm sống chỉ gọi `/api/suc-khoe`.
- B2 khởi động lại web định giá, worker và bot đang chạy (như mọi lần đẩy mã); tránh giờ job sáng 07:20–09:30.
- B1 khởi động lại web và worker chứng quyền; tránh giờ khớp lệnh vì lịch 5 phút đang chạy.
- Coin sập thì web mới cũng không vào được (đóng khi lỗi), như hai web cũ.
- Mọi yêu cầu hỏi coin `/me` của web mới đi từ một địa chỉ (container), giới hạn 600 lượt mỗi phút: đã nhớ kết
  quả 60 giây mỗi phiên, đủ cho vài trăm người cùng lúc.
- Dịch vụ chứng quyền một luồng: nhiều người cùng mở tờ chi tiết (tải giá trực tiếp, có lúc hơn 10 giây) sẽ xếp
  hàng. Đo ở B8; chưa sửa trong lát này.

### Không nằm trong lát 6

Tắt hai web cũ và chép danh mục chứng quyền cũ sang (chuyển hẳn); các nút thao tác của Quản trị; dựng lại trang
phân tích từng chứng quyền, quỹ, hợp đồng; Lướt CW, CW sắp ra mắt, nút quét, trang hướng dẫn; sao lưu ra ngoài máy.

### Kết quả B0 (đọc VPS lúc 19:02–19:20 ngày 25/11/2026, chỉ đọc, không mở `.env`)

- **RAM không còn là rủi ro lớn nhất.** Máy nay có 12.897 MB RAM và 2.047 MB swap, 16 nhân (bật lại 3 ngày trước);
  còn trống dùng được 8.401 MB. Mười hai container đang dùng khoảng 3,9 GB, lớn nhất là `coin-check-mongo-1`
  2,1 GB. Câu "VPS 3,9 GB không swap" trong ghi chú của compose đã cũ. Giới hạn cho `btinvest-web` chốt **768 MB**
  (ở máy Mac dùng 207 MB; web định giá Streamlit đang dùng 290 MB trên giới hạn 1.024 MB).
- **Image đã có đủ thư viện:** trong container `vn100` có `fastapi 0.141.1` (đúng bản ở máy Mac), `uvicorn 0.52.4`,
  `httpx 0.28.1`, `sqlalchemy 2.0.52`, `pydantic-settings 2.15.0`, Python 3.12.16. Không phải sửa `Dockerfile`.
- **`/data` ghi được** bằng người dùng `app` (uid 10001) của container: `web_user.db` tự tạo được ở lần chạy đầu.
- **Bản sao cấu hình:** `docker-compose.yml`, `entrypoint.sh`, `scheduler.py` trên VPS trùng bản sao trong
  `deploy/docker/`. Riêng `Dockerfile` trên VPS **khác** bản sao (còn 4 dòng: liên kết tệp bản tin vĩ mô sang
  `/data` và bước chạy `patches/vps_hotfix.py`); không thuộc lát 6, chưa đụng, cần người dùng chốt bản nào đúng.
- **Lệnh deploy** (`/usr/local/bin/deploy`, hẹn giờ 3 phút cho cả hai dự án): `docker compose build` rồi
  `up -d --remove-orphans` cho MỌI dịch vụ trong compose; chờ tới 240 giây cho mọi container chạy và khỏe, kèm gọi
  thử `https://chungkhoan.btinvest.vn/_stcore/health`; không đạt thì tự quay về commit trước và báo Discord. Hệ
  quả: sau B4, `btinvest-web` nằm trong điều kiện khỏe của mọi lần deploy sau này, nên kiểm sống của nó phải nhẹ
  và chắc (`/api/suc-khoe`, không đụng DB hay dịch vụ ngoài).
- **Dự án chứng quyền:** `app/` trên VPS kéo từ `repo.git` cùng máy; cả hai đang ở `5498c12`, máy Mac hơn đúng
  một commit `f66bc9c`.
- **Caddy** chạy trong container `web-caddy-1`, thư mục `/srv/web/conf` gắn chỉ đọc vào `/etc/caddy`, trang tĩnh ở
  `/srv/web/sites` gắn vào `/srv`. `Caddyfile` thuộc root: sửa bằng `sudo` (tài khoản `ubuntu` có sudo không hỏi
  mật khẩu). Khối `btinvest.vn` hiện chỉ có `root * /srv/btinvest` và `file_server`.
- **Kiểm `Origin` chạy đúng sau Caddy:** `same_origin` so `Origin` với tiêu đề `Host`, mà Caddy giữ nguyên `Host`
  khi chuyển tiếp, nên các nút ghi (duyệt người, lệnh, mức giá) không bị từ chối nhầm.
- Giờ chạy job: `vn100-worker` chỉ có job buổi sáng (07:20–08:00, chạy bù tới 3 giờ sau) và chủ nhật 18:00; đẩy mã buổi tối ngày thường
  không cắt ngang job nào.

**Đoạn thêm vào `/srv/apps/vn100/docker-compose.yml` ở B4** (và một dòng `WEB_USER_DB_URL` trong phần `&env` dùng chung):

```yaml
    # x-vn100 → environment (&env), thêm:
    WEB_USER_DB_URL: sqlite:////data/web_user/web_user.db   # tep du lieu nguoi dung cua web hop nhat, song qua deploy

  btinvest-web:               # web hop nhat btinvest.vn (FastAPI, docs/PLAN_WEB_HOP_NHAT.md muc 14)
    <<: *vn100
    container_name: btinvest-web
    command: ["python", "-m", "uvicorn", "valuation.api.web_main:app", "--host", "0.0.0.0", "--port", "8600"]
    environment:
      <<: *env
      WEB_AUTH_MODE: coin
      WEB_AUTH_ME_URL: http://coin-check-api-1:8090/api/v1/auth/me
      WEB_CW_BASE_URL: http://chungquyen:8000
    mem_limit: 768m
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8600/api/suc-khoe',timeout=5).status==200 else 1)"]
      interval: 30s
      timeout: 10s
      start_period: 60s
      retries: 3
```

**Khối `btinvest.vn` mới trong `/srv/web/conf/Caddyfile` ở B5** (thay khối trang chờ; `www` và các tên miền khác giữ nguyên):

```
btinvest.vn {
	import access_log
	encode zstd gzip
	header {
		Strict-Transport-Security "max-age=31536000"
		X-Content-Type-Options "nosniff"
		X-Frame-Options "SAMEORIGIN"
		Referrer-Policy "strict-origin-when-cross-origin"
		-Server
	}
	# Web hop nhat (FastAPI, container btinvest-web:8600). KHONG dung coin_login: ung dung tu hoi coin /me va tu tra
	# 401 o tung duong /api/ (test test_moi_duong_api_deu_dong_khi_chua_dang_nhap); giao dien gap 401 thi sang /dang-nhap.
	handle /api/v1/auth/* {
		reverse_proxy coin-check-api-1:8090
	}
	handle /dang-nhap {
		root * /srv/dang-nhap
		rewrite * /index.html
		file_server
	}
	handle {
		reverse_proxy btinvest-web:8600 {
			lb_try_duration 30s
		}
	}
}
```

Thứ tự chạy sau khi được duyệt: B3 (người dùng) → B1 → B2 → B4 → B5; dừng ngay ở bước nào kiểm không đạt.
