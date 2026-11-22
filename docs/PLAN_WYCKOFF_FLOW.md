# Kế hoạch nâng cấp tab "Dòng tiền ngành" theo Wyckoff (v0.2 — 22/11/2026, ĐÃ DUYỆT HƯỚNG ĐI)

## Quyết định của người dùng (22/11/2026)

| # | Quyết định | Ảnh hưởng tới kế hoạch |
|---|---|---|
| Q1 | **Thay nhãn cũ**: nhãn Wyckoff thành nhãn chính | Từ W3: thẻ, bảng ngành, danh sách và câu kết luận dùng nhãn cấu trúc Wyckoff. Ba phiếu D73/D77 (Ngoại, Giá-KL, Tự doanh) không còn tạo nhãn; chúng thành chip bằng chứng "Ai đứng sau". Bài L1–L10 viết lại theo nhãn mới. Trước W3 nhãn cũ vẫn chạy |
| Q2 | **Làm W0 ngay**: bảng `active_flow_daily` + job lưu mua/bán chủ động FHSC hằng ngày | Đổi schema có sao lưu; làm trước mọi giai đoạn khác |
| Q3 | **Hiện mục tiêu giá P&F** | Thêm đếm ngang P&F theo phương pháp chuẩn ChartSchool (P&F Price Objectives). Ghi rõ "quy ước Wyckoff, không phải dự báo" và hiện **tỷ lệ đạt mục tiêu đo được ở W2** ngay cạnh con số. `DISCLAIMER` và `forbidden_phrases` sửa tương ứng ở W3 |
| Q4 | **Ghi cả hai**: spring KL thấp và shakeout KL cao | Như §4.1 bước 5 |
| Q5 | **t ≥ 2** | Như §5 |
| Q6 | **Chỉ FHSC** | Bỏ các nguồn TCBS / DNSE / SSI khỏi kế hoạch |
| Q7 | **Thu thập thành phần VN100 theo kỳ trước khi kiểm chứng** | Thêm W2a: bảng thành phần VN100 theo từng kỳ cơ cấu từ thông báo HOSE, và tải OHLCV cho các mã đã rời rổ (đổi schema → duyệt khi làm) |
| Q8 | **Claude đề xuất 3–5 mã golden** | Ở W1: lọc từ dữ liệu, gửi biểu đồ để người dùng duyệt nhãn tham chiếu |

> Mục tiêu người dùng: theo dõi việc **gom hàng → kéo giá → xả hàng** của tổ chức lớn ("cá mập").
> Kế hoạch này chỉ là đề xuất, chưa sửa code. Nền tảng: tab hiện tại (D73–D77, D90–D91, `docs/PLAN_SECTOR_FLOW.md` v2.1).
> Mô tả dữ liệu quá khứ, không phải khuyến nghị, không dự báo giá (giữ `DISCLAIMER`, `forbidden_phrases`).

## 0. Tóm tắt

- Tab hiện tại trả lời câu **"AI mua/bán ròng trong 20 phiên"**: khối ngoại, tự doanh, CMF. Nó **không** trả lời câu Wyckoff: **"giá đang ở GIAI ĐOẠN nào của chu kỳ gom–kéo–xả, và hành vi giá–khối lượng có xác nhận không"**.
- Đề xuất thêm **trục thứ hai, "Cấu trúc Wyckoff"**, độc lập với nhãn Gom/Xả hiện có:
  - Nhận diện vùng tích lũy/phân phối, các sự kiện (SC, ST, Spring, SOS, UTAD, SOW…) và pha A–E.
  - Chỉ dùng nến đã đóng, không nhìn trước.
  - Dòng tiền theo nhà đầu tư trở thành **bằng chứng "ai đứng sau"** cho từng sự kiện.
- Dữ liệu đủ cho phần giá–KL: OHLCV 10/2018 → nay, 92/100 mã có ≥ 5 năm. Dữ liệu theo nhà đầu tư chỉ có khoảng 2 năm (`flow_daily` 24/10/2024 → 12/11/2026, rồi FHSC gộp).
- Có nguồn mới: **mua/bán chủ động** qua FHSC (`active_flow`), nhưng chỉ trả 61 phiên gần nhất nên phải lưu hằng ngày từ bây giờ.
- **Chưa có nghiên cứu bình duyệt nào kiểm chứng ngoài mẫu cho Spring/VSA** (mục 1.4). Vì vậy bắt buộc **kiểm chứng ngược trước khi cho sự kiện vào danh sách lọc hay Discord**, với tiêu chí đặt trước khi đo.

## 1. Wyckoff vận hành thế nào

### 1.1 Lõi phương pháp
- **Composite Man** là công cụ tư duy: coi diễn biến giá như kế hoạch gom, kéo, xả của một "nhà vận hành" lớn.
  [ChartSchool — The Wyckoff Method: A Tutorial](https://chartschool.stockcharts.com/table-of-contents/market-analysis/wyckoff-analysis-articles/the-wyckoff-method-a-tutorial) · [Wyckoff Analytics](https://www.wyckoffanalytics.com/wyckoff-method/)
- **Ba quy luật** (cùng nguồn):
  1. **Cung–cầu** quyết định hướng giá.
  2. **Nhân–quả**: độ rộng vùng giá (nguyên nhân) quyết định biên độ nhịp sau. Wyckoff đo bằng đếm ngang P&F.
  3. **Nỗ lực–kết quả**: khối lượng (nỗ lực) phải tương xứng với biến động giá (kết quả). Phân kỳ giữa hai thứ báo trước khả năng đổi hướng.
- **Bốn pha thị trường:** tích lũy → tăng giá → phân phối → giảm giá.
  [ChartSchool — Wyckoff stock analysis](https://chartschool.stockcharts.com/table-of-contents/market-analysis/wyckoff-analysis-articles/wyckoff-stock-analysis)

### 1.2 Sơ đồ tích lũy (theo tutorial ChartSchool)

| Pha | Sự kiện | Hành vi giá – khối lượng |
|---|---|---|
| A — dừng xu hướng giảm | PS (hỗ trợ sơ bộ) | KL tăng, biên độ nến mở rộng |
| | SC (bán tháo cao trào) | Biên độ rộng, bán nặng, thường đóng cửa xa đáy |
| | AR (hồi tự động) | Đỉnh AR là **trần vùng** |
| | ST (kiểm tra thứ cấp) | Về gần vùng SC với KL và biên độ **giảm rõ** |
| B — xây "nguyên nhân" | Dao động trong vùng | KL ở các nhịp giảm thu hẹp dần |
| C — rũ bỏ | Spring / shakeout | Thủng đáy vùng rồi quay lại vào vùng. ChartSchool: spring KL thấp là dấu hiệu sẵn sàng tăng |
| | Test | Đáy cao hơn, KL thấp hơn |
| D — cầu chiếm ưu thế | SOS (dấu hiệu sức mạnh) | Tăng với biên độ rộng, KL tương đối cao |
| | LPS (điểm hỗ trợ cuối) | Điều chỉnh với biên độ và KL giảm |
| | BU | Lùi về kháng cự cũ, biên độ hẹp, KL thấp. JAC là ẩn dụ cho SOS, không phải sự kiện riêng |
| E — rời vùng | Xu hướng tăng | — |

**Phân phối** đối xứng: PSY → BC (KL và biên độ tăng mạnh) → AR (đáy AR là **sàn vùng**) → ST → **UTAD** (vượt kháng cự rồi đóng cửa lại trong vùng) → **SOW** (xuống tới hoặc thủng sàn, biên độ và KL tăng) → LPSY (hồi yếu, biên độ hẹp).

### 1.3 Bổ trợ: VSA và Weis Wave
- **VSA (Tom Williams)**, qua nguồn thứ cấp [ATAS](https://atas.net/volume-analysis/basics-of-volume-analysis/vsa-and-cluster-analysis-no-demand-and-no-supply/):
  - *No demand*: nến tăng, biên độ hẹp hoặc trung bình, đóng cửa quanh giữa nến, KL thấp hơn 2 nến trước.
  - *No supply*: dạng đối xứng.
- **Weis Wave** (David Weis, *Trades About to Happen*): cộng dồn KL theo từng sóng giá; sóng kết thúc khi giá đảo chiều vượt ngưỡng R. "Shortening of thrust" là các sóng cùng chiều ngắn dần, KL giảm.

### 1.4 Mã hóa được gì, giới hạn ở đâu (quan trọng)
- **Có công thức chuẩn:** CLV, ADL, CMF, OBV (ChartSchool). App đã có CMF trên biên độ thực (D76) và OBV.
- **Chỉ có mô tả định tính:** SC, BC, ST. **Không có ngưỡng chuẩn** kiểu "KL ≥ k × trung bình". Mọi ngưỡng ở đây là quy ước của repo và phải gắn nhãn HEURISTIC.
- **Ngưỡng của người thực hành** (không phải chuẩn):
  - Spring dùng hỗ trợ = đáy thấp nhất của 15 nến ([Wyckoff Analytics 6/2025](https://www.wyckoffanalytics.com/identifying-wyckoff-springs-with-algorithmic-trading-strategies/)).
  - Máy trạng thái RANGE → SPRING → SOS với KL > 1,2 × KL trung bình vùng ([MQL5 6/2026](https://www.mql5.com/en/articles/22628)).
  - Cả hai đều **không công bố backtest**. Hai nguồn **mâu thuẫn** về KL của spring: Wyckoff Analytics muốn KL vào khi thủng, ChartSchool coi spring KL thấp là tích cực.
- **Không tìm thấy nghiên cứu bình duyệt nào kiểm chứng ngoài mẫu cho Spring/VSA**; [Quantified Strategies](https://www.quantifiedstrategies.com/wyckoff-trading-strategy/) cũng nói vậy.
  - Gần nhất là bằng chứng gián tiếp: KL bất thường cao đi kèm giá tăng tháng sau ([Gervais, Kaniel, Mingelgrin 2001](https://ideas.repec.org/a/bla/jfinan/v56y2001i3p877-919.html)); giao dịch đầu cơ làm lợi suất tiếp diễn, phòng hộ làm đảo chiều ([Llorente et al. 2002](https://www.nber.org/papers/w8312)).
  - Với quy tắc kỹ thuật nói chung, chỉ 4/18 thị trường mới nổi còn vượt trội sau phí 20bp ([Springer 2023](https://link.springer.com/article/10.1007/s11408-023-00433-2)).
- **Bẫy nhìn lại (hindsight):** đáy SC và đỉnh AR chỉ biết sau khi đã xảy ra. Bruce Fraser: sau PS–SC–AR–ST mới chỉ kết luận được *đà giảm đã dừng*, "too early … to call this Accumulation" ([StockCharts](https://articles.stockcharts.com/article/articles-wyckoff-2015-05-the-stopping-of-a-downtrend)). Vì vậy app chỉ được gọi là **"giả thuyết tích lũy"**, và mọi sự kiện ghi theo **ngày xác nhận**, không theo ngày xảy ra.

### 1.5 "Cá mập" ở Việt Nam: dòng tiền theo nhà đầu tư nói được gì
- **Khối ngoại** giao dịch theo kiểu *positive feedback* và gây tác động giá chủ yếu trong ngày ([Richards 2005](https://econpapers.repec.org/RePEc:cup:jfinqa:v:40:y:2005:i:01:p:1-27_00)).
- **Ở HOSE:**
  - Khối ngoại theo đà và có dấu hiệu chọn được thời điểm ([Vo 2017, IRFA](https://ideas.repec.org/a/eee/finana/v52y2017icp88-93.html)).
  - Ở cổ phiếu ngân hàng, khối ngoại mua bất thường đi kèm lợi suất bất thường dương và bền; bán bất thường chỉ làm giá giảm ngắn rồi hồi ([Dang et al. 2025](https://publisher.unimas.my/ojs/index.php/IJBS/article/view/9543)).
- **Nhưng khối ngoại không mặc nhiên là "smart money":** ở Hàn Quốc họ mua đắt hơn 21bp, bán rẻ hơn 16bp ([Choe, Kho, Stulz 2005](https://econpapers.repec.org/RePEc:oup:rfinst:v:18:y:2005:i:3:p:795-829)).
- **Tự doanh:** chưa tìm được nghiên cứu học thuật. Phòng hộ chứng quyền làm số tự doanh ròng phản ánh nghiệp vụ phòng hộ, không phải nhận định. Thiết kế hiện tại để tự doanh "chỉ xác nhận" là đúng hướng.
- **"Trong nước suy ra" D = −(F + P)** gộp cả cá nhân lẫn tổ chức trong nước. App **không tách được quỹ nội hay "đội lái"** từ dữ liệu ngày. Phần này phải nói rõ trên giao diện.

## 2. Tab hiện tại làm gì (đọc từ code)

- **Thành phần:**
  - `valuation/analysis/money_flow.py`: hàm thuần, có test.
  - `valuation/views/money_flow.py`: giao diện.
  - `lw_chart.py`: biểu đồ Lightweight Charts.
  - `money_flow_lessons.py`: bài học L1–L10.
- **Ba phiếu trong 20 phiên** (`votes`, ngưỡng ở `config/defaults.yaml → money_flow.signal`):
  - **Ngoại** (chính): R_F = ΣF / ΣGTGD ≥ 2% và ≥ 60% phiên cùng dấu.
  - **Giá-KL**: CMF20 trên biên độ thực ±0,05.
  - **Tự doanh** (phụ): ±0,5%.
- **Nhãn** (`label`): Dấu hiệu gom / Dấu hiệu xả / Nội gom / Nội xả (RVOL ≥ 1,3, D77) / Trung tính / Chưa đủ dữ liệu.
- **Huy hiệu:**
  - Thỏa thuận lớn: đường A là cận dưới; đường chính xác dừng từ 13/11.
  - "Dồn 1 phiên", GDKHQ, kín room, phiên cơ cấu ETF, gãy điều chỉnh.
- **Màn ngành:** bản đồ nhiệt R_F, độ rộng ngoại, đếm nhãn, câu kết luận.
- **Màn chi tiết:** tầng Giá (+ volume profile D91), Khối lượng, Khối ngoại, Tự doanh, "Ai gom/xả" (nền CMF + lũy kế F, P, D), MACD.

**Khoảng trống so với Wyckoff:**

| # | Wyckoff cần | Tab hiện có | Hệ quả |
|---|---|---|---|
| 1 | Bối cảnh: tích lũy chỉ có nghĩa **sau** xu hướng giảm, **trong** một vùng giá | Cửa sổ trượt 20 phiên, không biết giá đang ở đâu | "Dấu hiệu gom" ở đỉnh sóng và ở đáy vùng trông như nhau |
| 2 | Vùng giá (hỗ trợ/kháng cự từ SC/AR) | Không có | Không có mốc để nhận Spring, UTAD, SOS, SOW |
| 3 | Sự kiện SC, ST, Spring, SOS, LPS, BC, UTAD, SOW, LPSY | Không có | Không trả lời "đang ở pha nào" |
| 4 | Nỗ lực–kết quả từng nến, hấp thụ cung | Chỉ RVOL 20/60 và CMF tổng | Không thấy phiên "KL lớn mà giá không giảm" ở đáy vùng |
| 5 | KL theo sóng (Weis) | Không có | Không thấy cung cạn dần |
| 6 | Bằng chứng "ai" tại từng sự kiện | Phiếu tổng 20 phiên | Không biết ngoại mua đúng phiên Spring hay mua ở đỉnh |
| 7 | Kiểm chứng | Nhãn là HEURISTIC, chưa backtest (`PLAN_SECTOR_FLOW` §10 #9) | Không biết nhãn có giá trị dự báo hay không |

## 3. Dữ liệu: có gì, thiếu gì (đo trên DB VPS 22/11/2026)

| Dữ liệu | Độ sâu | Dùng cho | Ghi chú |
|---|---|---|---|
| OHLCV điều chỉnh (`prices_daily`) | 29/10/2018 → nay; 92/100 mã ≥ 5 năm | Lớp Cấu trúc + kiểm chứng ngược | KL danh nghĩa → dùng `factor` hiện có (§4.2 PLAN_SECTOR_FLOW) |
| Ngoại / tự doanh khớp + thỏa thuận tách (`flow_daily`) | 24/10/2024 → 12/11/2026 | Lớp "Ai đứng sau", kiểm chứng ~2 năm | Đã dừng (`vnstock_data` bị khóa, D97) |
| Ngoại / tự doanh gộp FHSC (`prices_daily`) | 13/11/2026 → nay, hằng ngày | Tiếp nối | **Gãy định nghĩa** so với `flow_daily` (gộp ≠ khớp) → phải gắn cờ chỗ nối |
| **Mua/bán chủ động** FHSC `Market().equity(m).active_flow()` | Chỉ 61 phiên gần nhất (thử VCB: 24/08 → 20/11; `start` không kéo dài được) | Hấp thụ cung/cầu, delta chủ động | Phải **lưu hằng ngày** → bảng mới (đổi schema) |
| Giao dịch nội bộ FHSC `insider_deal()` | Có dữ liệu (VCB 2 giao dịch) | Huy hiệu "nội bộ mua/bán trong vùng" | `start_date`/`end_date` đang NaT → cần kiểm chất lượng trước khi dùng |
| Thỏa thuận chính xác, cung–cầu theo NĐT, sổ lệnh lịch sử | Nguồn TCBS / DNSE / SSI trong vnstock 6 | Dò lệnh lớn | Cần tài khoản API của các CTCK đó (chỉ có khóa FHSC) → câu hỏi Q6 |
| Thành phần VN100 theo thời điểm | Không có | Chống survivorship | Kiểm chứng sẽ lạc quan → ghi rõ (Q7) |

## 4. Thiết kế nâng cấp

### 4.1 Lớp 1 — "Cấu trúc Wyckoff" (giá–KL, hàm thuần mới `valuation/analysis/wyckoff.py`)

Mọi ngưỡng đặt trong `config/defaults.yaml → wyckoff`, gắn nhãn HEURISTIC, dùng **phân vị của chính mã** thay cho số cứng. Mỗi sự kiện ghi `event_date` (ngày xảy ra) **và** `confirmed_date` (ngày đủ nến để xác nhận). Kiểm chứng và giao diện chỉ dùng `confirmed_date`.

1. **Bối cảnh xu hướng trước:**
   - Lợi suất N phiên trước vùng (vd 60) thuộc nhóm thấp: điều kiện cần để gọi là giả thuyết tích lũy.
   - Đối xứng cho phân phối.
2. **Phiên cao trào (ứng viên SC/BC):**
   - KL điều chỉnh ≥ phân vị cao của 250 phiên trước (vd p95), True Range ≥ phân vị cao (vd p90), xảy ra sau xu hướng ở bước 1.
   - SC ưu tiên phiên đóng cửa xa đáy (CLV biên độ thực > 0), đúng mô tả ChartSchool.
3. **AR và vùng giá:** AR là đỉnh cao nhất trong K phiên sau SC; chỉ "chốt" sau K phiên, nên có độ trễ nhưng không nhìn trước. Vùng giá = [đáy SC, đỉnh AR]; phân phối đối xứng.
4. **ST:** giá về trong dung sai quanh đáy SC với KL < KL SC × r và True Range nhỏ hơn.
5. **Spring / shakeout:**
   - Đáy < hỗ trợ − dung sai, đóng cửa quay lại ≥ hỗ trợ trong 0–2 phiên.
   - **Ghi cả hai loại**: spring KL thấp và shakeout KL cao. Hai nguồn mâu thuẫn, nên để kiểm chứng quyết định (Q4).
   - **Test** = đáy cao hơn đáy spring, KL thấp hơn.
6. **SOS / LPS / BU:**
   - SOS: đóng cửa > kháng cự với True Range ≥ phân vị khá và KL ≥ 1,2 × KL trung bình vùng (quy ước MQL5).
   - LPS: trong 8 phiên sau, điều chỉnh giữ trên kháng cự cũ với KL thấp.
7. **Phân phối:**
   - BC → AR → ST.
   - **UTAD**: đỉnh > kháng cự + dung sai, đóng cửa lại trong vùng.
   - **SOW**: đóng cửa < hỗ trợ, biên độ và KL tăng.
   - **LPSY**: hồi biên độ hẹp, KL thấp.
8. **Máy trạng thái pha A → E** cho mỗi vùng, kèm **điều kiện vô hiệu** in ra màn hình:
   - Tích lũy vô hiệu khi đóng cửa < đáy spring (hoặc đáy SC) quá dung sai trong n phiên.
   - Phân phối vô hiệu khi đóng cửa > đỉnh UTAD.
   - Pha A chỉ được ghi "**đà giảm đã dừng**", không ghi "tích lũy" (theo Fraser).
9. **Nỗ lực–kết quả từng phiên:**
   - Tính z-score KL so với z-score |biến động| hoặc True Range trong vùng.
   - Phiên "nỗ lực lớn – kết quả nhỏ" ở nửa dưới vùng là **ứng viên hấp thụ cung**; ở nửa trên là **ứng viên hấp thụ cầu**.
10. **Weis Wave:** KL cộng dồn theo sóng, R = k × ATR. Đánh dấu chuỗi sóng giảm ngắn dần với KL giảm ("cung cạn").
11. **No demand / No supply** theo định nghĩa VSA (mục 1.3), chỉ làm huy hiệu.
12. **Đặc thù Việt Nam:**
    - Nến trần/sàn (H = L hoặc chạm biên ±7%/±10%) làm CLV ≈ ±1 một cách cơ học → đánh dấu riêng, không dùng làm bằng chứng nỗ lực–kết quả.
    - Phiên cơ cấu ETF (`etf_review_dates`) tạo cao trào KL giả → không tính là SC/BC.
    - KL điều chỉnh theo thưởng/cổ tức CP qua `factor` hiện có; quyền mua → ◌.

### 4.2 Lớp 2 — "Ai đứng sau" tại từng sự kiện

- Trong mỗi vùng và tại từng sự kiện, gắn bằng chứng:
  - Ngoại F, tự doanh P (chỉ xác nhận), trong nước suy ra D.
  - **Delta chủ động** = KL mua chủ động − KL bán chủ động (FHSC).
  - Thỏa thuận lớn (đường A); nội bộ mua/bán (sau khi kiểm chất lượng).
- **Mẫu hình đáng chú ý** (mô tả, không khuyến nghị):
  - **Hấp thụ ở đáy vùng:** delta chủ động âm mạnh, KL cao, nhưng giá giữ hỗ trợ; ngoại hoặc D mua ròng.
  - **Spring có người đỡ:** ngoại mua ròng đúng phiên hoặc 1–2 phiên sau spring.
  - **SOS có cầu thật:** delta chủ động dương, ngoại không bán ròng.
  - **UTAD/SOW có người xả:** ngoại bán ròng hoặc thỏa thuận lớn bên bán, delta âm.
- Ba phiếu hiện tại (D73/D77) **giữ nguyên**. Trục Cấu trúc thêm ngữ cảnh cho phiếu, không thay phiếu. Ví dụ "Dấu hiệu gom" khi giá đang ở pha C/D là đáng chú ý hơn khi giá đã ở pha E.

### 4.3 Hiển thị trong tab "Dòng tiền ngành"
- **Biểu đồ chi tiết** (`lw_chart.py`), thêm tầng "Wyckoff":
  - Hộp vùng giá (hỗ trợ/kháng cự).
  - Mốc sự kiện bằng markers của Lightweight Charts: SC, AR, ST, SP, T, SOS, LPS, BC, UT, UTAD, SOW, LPSY.
  - Dải màu pha A–E.
  - Tầng phụ Weis Wave (mặc định tắt trên điện thoại).
- **Thẻ 5 giây:** thêm một dòng, ví dụ "Cấu trúc: giả thuyết tích lũy · pha C · Spring 18/11 (KL thấp) · vô hiệu nếu đóng cửa < 22.300 · ngoại +1,2 tỷ tại spring".
- **Bảng ngành:** đếm số mã theo cấu trúc (tích lũy giả thuyết / phân phối giả thuyết / tăng / giảm / chưa rõ).
- **Danh sách mã:** bộ lọc "sự kiện mới trong 5 phiên" và "sự kiện có xác nhận dòng tiền".
- **Bài học mới:** L11 (3 quy luật), L12 (sơ đồ tích lũy/phân phối), L13 (nỗ lực–kết quả, hấp thụ), mỗi bài có ví dụ sinh từ dữ liệu như L1–L10.
- **Discord:** chỉ khi kiểm chứng đạt (mục 5). Cần duyệt tích hợp riêng.
- **Mục tiêu giá P&F** (Q3, người dùng chọn hiện):
  - Đếm ngang trên biểu đồ P&F (ô theo % giá, đảo chiều 3 ô) tại đường LPS/Spring, theo ChartSchool P&F Price Objectives.
  - Hiện kèm "quy ước Wyckoff, không phải dự báo" và tỷ lệ đạt mục tiêu đo được ở W2.

## 5. Kiểm chứng trước khi bật (tiêu chí đặt TRƯỚC khi đo)

- **Mẫu:**
  - OHLCV 2019–2026, các mã hiện thuộc VN100. Có survivorship (Q7) nên kết quả mang tính lạc quan.
  - Lớp dòng tiền chỉ có khoảng 2 năm, nên đo **giá trị gia tăng** của "sự kiện có xác nhận dòng tiền" so với "không xác nhận".
- **Phương pháp:**
  - Event study ([MacKinlay 1997](https://econpapers.repec.org/RePEc:aea:jeclit:v:35:y:1997:i:1:p:13-39)).
  - Lợi suất 5/20/60 phiên sau `confirmed_date`, trừ VN-Index và trừ nền vô điều kiện của chính mã.
  - t-stat theo cụm ngày (các mã cùng ngày tương quan mạnh).
  - Chuỗi ngày chạm trần/sàn cộng dồn.
- **Walk-forward:** chốt ngưỡng trên 2019–2022, đo trên 2023–2026, không chỉnh ngưỡng sau khi thấy kết quả.
- **Chống data snooping:**
  - Giới hạn số cấu hình thử và ghi lại **mọi** cấu hình đã thử (tinh thần [Sullivan, Timmermann, White 1999](https://econpapers.repec.org/RePEc:bla:jfinan:v:54:y:1999:i:5:p:1647-1691), [PBO — Bailey et al.](https://papers.ssrn.com/abstract=2326253)).
  - Nhãn chồng lấn thì dùng purged split.
- **Tiêu chí đề xuất (Q5, người dùng chốt trước khi chạy):**
  - Spring/SOS hiện ở danh sách lọc khi lợi suất vượt trội 20 phiên > 0 với t ≥ 2 trên giai đoạn kiểm tra **và** tỷ lệ thắng > nền.
  - UTAD/SOW đối xứng.
  - Không đạt thì sự kiện **chỉ là chú thích trên biểu đồ**, không vào danh sách lọc hay Discord. Ghi số đo vào `DECISIONS.md` dù đạt hay không.
- **Golden test:** chuỗi tổng hợp dựng tay cho từng sự kiện (tính tay được), và 3–5 mã thật do người dùng chọn cùng xem biểu đồ để chốt nhãn tham chiếu.

## 6. Lộ trình

| Giai đoạn | Việc | File đụng | Cần duyệt |
|---|---|---|---|
| **W0 — Dữ liệu** | Job lưu `active_flow` hằng ngày cho 100 mã (~100 lời gọi, FHSC ≤ 43/phút → ~3 phút, trong khung 06:00–21:00); bảng mới `active_flow_daily`; cờ nối `flow_daily` → FHSC gộp; kiểm chất lượng `insider_deal` | `valuation/ingest/`, `scripts/`, `valuation/db/models.py`, `scheduler.py` VPS | **Đổi schema** (Q2), sao lưu DB |
| **W1 — Bộ máy Cấu trúc** | `valuation/analysis/wyckoff.py`: vùng giá, cao trào, sự kiện, máy trạng thái, nỗ lực–kết quả, Weis; config `wyckoff`; test tổng hợp tính tay | `valuation/analysis/`, `config/defaults.yaml`, `tests/` | Ngưỡng ban đầu |
| **W2a — Thành phần VN100 theo kỳ** (Q7) | Bảng thành phần VN100 theo từng kỳ cơ cấu (thông báo HOSE) từ 2019; tải OHLCV cho mã đã rời rổ | `valuation/ingest/`, `scripts/`, `valuation/db/` | Đổi schema, nguồn HOSE |
| **W2 — Kiểm chứng** | `scripts/backtest_wyckoff_events.py`, báo cáo vào `knowledge/`, quyết định D10x | `scripts/`, `knowledge/`, `DECISIONS.md` | Tiêu chí Q5 (trước khi chạy) |
| **W3 — Giao diện** | Tầng Wyckoff trên biểu đồ, dòng trên thẻ, đếm ở bảng ngành, bộ lọc, L11–L13 | `valuation/views/money_flow.py`, `lw_chart.py`, `money_flow_lessons.py` | Xem thử trên máy tính + điện thoại |
| **W4 — Ghép "Ai đứng sau"** | Bằng chứng F/P/D/delta/thỏa thuận tại sự kiện; delta chủ động chỉ bật khi đã tích lũy ≥ 60 phiên | `money_flow.py` (analysis + view) | — |
| W5 — Tùy chọn | Discord: sự kiện mới đạt kiểm chứng; công cụ bot `money_flow(mã)` (PLAN_SECTOR_FLOW §10 #12) | `daily_report.py`, bot | Duyệt tích hợp |

Thứ tự: **W0 nên chạy ngay** (mỗi ngày chậm là mất một ngày dữ liệu mua/bán chủ động không lấy lại được). W1 → W2 trước W3, để giao diện chỉ hiện những gì đã đo.

## 7. Rủi ro
- **Chủ quan và nhìn lại:** cùng một biểu đồ, hai người đọc Wyckoff khác nhau. Giảm bằng `confirmed_date`, điều kiện vô hiệu và chữ "giả thuyết".
- **Quá khớp ngưỡng:** nhiều tham số (N, K, phân vị, dung sai). Giảm bằng walk-forward, ghi mọi cấu hình đã thử, ưu tiên phân vị hơn số cứng.
- **Nguồn:**
  - `active_flow` chỉ 61 phiên, nên lớp delta chưa kiểm chứng được trong vài tháng đầu.
  - `insider_deal` thiếu ngày.
  - `flow_daily` đã dừng.
  - Nguồn TCBS/DNSE/SSI cần tài khoản khác.
- **Diễn giải sai "cá mập":**
  - Khối ngoại không luôn đúng (Choe et al.).
  - Tự doanh có thể chỉ là phòng hộ chứng quyền.
  - D gộp cá nhân và tổ chức trong nước.
- **Biên độ ±7%:** nến trần/sàn, chuỗi chạm biên làm sai lệch VSA và lợi suất.
- **Giao diện quá tải trên điện thoại:** tầng Wyckoff và Weis mặc định tắt trên điện thoại, chỉ hiện dòng trên thẻ.

## 8. Câu hỏi đã hỏi (đã trả lời ngày 22/11/2026, xem bảng đầu file)

| # | Câu hỏi | Đề xuất mặc định |
|---|---|---|
| **Q1** | Thêm **trục Cấu trúc Wyckoff riêng**, giữ nguyên nhãn Gom/Xả hiện có (D73/D77)? Hay thay nhãn cũ bằng nhãn Wyckoff? | **Thêm trục riêng**, không đụng nhãn cũ |
| **Q2** | Tạo bảng mới `active_flow_daily` và job lưu mua/bán chủ động FHSC hằng ngày (**đổi schema**, có sao lưu)? | **Có, làm ngay (W0)** |
| **Q3** | Không hiện mục tiêu giá theo đếm P&F (vì app không dự báo giá), chỉ hiện độ rộng và thời gian vùng? | **Không hiện mục tiêu** |
| **Q4** | Spring: ghi cả spring KL thấp và shakeout KL cao, để kiểm chứng quyết định loại nào có giá trị? | **Ghi cả hai** |
| **Q5** | Tiêu chí cho sự kiện vào danh sách lọc/Discord: lợi suất vượt trội 20 phiên > 0, t ≥ 2 (cụm ngày) trên 2023–2026, tỷ lệ thắng > nền; không đạt thì chỉ chú thích biểu đồ | **Đồng ý** (hoặc bạn đặt ngưỡng khác TRƯỚC khi đo) |
| **Q6** | Bạn có tài khoản API ở TCBS / DNSE / SSI để lấy thỏa thuận chính xác, cung–cầu theo nhà đầu tư, sổ lệnh lịch sử không? | Mặc định **chỉ FHSC** |
| **Q7** | Chấp nhận kiểm chứng trên danh sách VN100 hiện tại (có survivorship, ghi rõ), hay thu thập thành phần VN100 theo từng kỳ trước? | **Chấp nhận ở v1**, ghi rõ hạn chế |
| **Q8** | Chọn 3–5 mã bạn đã từng quan sát rõ giai đoạn gom/xả để làm golden test cùng xem biểu đồ? | Bạn chọn; nếu không, tôi đề xuất từ dữ liệu để bạn duyệt |
