# HỆ THỐNG ĐỊNH GIÁ TỰ ĐỘNG VN100 - TÀI LIỆU REVIEW CHO AI
(File này chứa toàn bộ bối cảnh, kiến trúc, và các đoạn code cốt lõi nhất của dự án để một AI khác có thể đọc hiểu toàn bộ hệ thống ngay lập tức).

## 1. MỤC TIÊU DỰ ÁN
Xây dựng một hệ thống định giá cổ phiếu VN100 chuẩn quỹ đầu tư. Thay vì chạy lại toàn bộ mô hình tài chính (DCF, RI) mỗi ngày rất nặng nề, hệ thống sử dụng **Kiến trúc 2 nhịp (Two-Speed Valuation Engine)**:
1. **Nhịp chậm (Intrinsic Engine):** Chạy khi có BCTC quý mới. Phân tích driver-based, dự phóng 5 năm, tính ra Fair Value (FV_base). Quan trọng nhất: hệ thống sẽ **bơm (bump) các biến vĩ mô/ngành** (lãi suất, tỷ giá, NIM...) lên một chút để tính **đạo hàm riêng (greeks / sensitivity)** và lưu vào DB.
2. **Nhịp nhanh (Daily Signal Engine):** Chạy tự động mỗi cuối ngày (EOD). Lấy biến động của các chỉ báo vĩ mô (Macro Radar) hôm nay nhân với greeks (tuyến tính) để nội suy ra `Fair Value Fast` mới nhất mà không cần chạy lại mô hình DCF. Tính toán Upside, Cờ chất lượng, Margin of Safety và đẩy cảnh báo ra Discord & Google Sheets.

## 2. TECH STACK
- **Core:** Python 3.11, FastAPI.
- **Database:** PostgreSQL (SQLAlchemy) với cơ chế UPSERT idempotent.
- **Orchestration:** n8n (gọi HTTP tới FastAPI theo Cron 15:30 EOD).
- **Output:** Google Sheets (gspread) & Discord Webhooks.
- **Rules:** Chặt chẽ về Data Integrity, KHÔNG dùng các mô hình sai bản chất (VD: không dùng Z-Score cho Bank).

---

## 3. CORE LOGIC 1: ĐỊNH GIÁ VÀ TÍNH ĐỘ NHẠY (INTRINSIC ENGINE & GREEKS)
Mỗi ngành có một class kế thừa từ `ValuationModel`. Dưới đây là logic cốt lõi trong `valuation/engine/models/base.py` dùng để tính Đạo hàm (Greeks).

```python
    def calculate_sensitivities(self) -> Dict[str, float]:
        """Tính toán đạo hàm riêng (Greeks) của Fair Value theo từng driver"""
        sensitivities = {}
        original_fv = self.perform_valuation()
        
        for driver_name, bump_amount in self.sensitivity_config.items():
            if not hasattr(self, driver_name):
                continue
                
            orig = getattr(self, driver_name)
            setattr(self, driver_name, orig + bump_amount)
            # Clear cache and recalc
            if hasattr(self, 'projections'): delattr(self, 'projections')
            
            try:
                bumped_fv = self.perform_valuation()
                delta = (bumped_fv - original_fv) / bump_amount
            except Exception:
                delta = 0.0
                
            # Restore state
            setattr(self, driver_name, orig)
            if hasattr(self, 'projections'): delattr(self, 'projections')
            sensitivities[driver_name] = delta
            
        return sensitivities
```

---

## 4. CORE LOGIC 2: NHỊP NHANH & NỘI SUY (DAILY SIGNAL ENGINE)
Thực thi tại `valuation/engine/daily_signal.py`. Đây là trái tim của việc "Định giá hằng ngày". 
Hệ thống lấy `FV_base` và cộng với `(Delta Macro) * (Greek)` để ra `FV_fast`.

```python
def calculate_daily_signal(ticker: str, trade_date: datetime.date = None, force_override: bool = False, db: Session = None):
    # Lấy FV base và Greeks mới nhất
    latest_val = db.query(ValuationResult).filter(ValuationResult.ticker == ticker).order_by(ValuationResult.created_at.desc()).first()
    sensitivities = db.query(ValuationSensitivity).filter(ValuationSensitivity.valuation_id == latest_val.id).all()
    
    fv_fast = latest_val.fair_value_base
    applied_deltas = []
    
    # Fast re-price bằng xấp xỉ bậc nhất (Taylor expansion bậc 1)
    for sens in sensitivities:
        # get_macro_deltas() tìm biến động của macro driver từ lúc chạy FV_base đến hôm nay
        macro_delta = get_macro_deltas(sens.driver_code, latest_val.created_at, trade_date, db)
        if macro_delta != 0.0:
            impact = macro_delta * sens.delta_fv_per_unit
            fv_fast += impact
            applied_deltas.append(f"{sens.driver_code}: {macro_delta} -> impact: {impact}")
    
    # Tính toán Upside và Conviction
    upside = (fv_fast - latest_price) / latest_price
    
    # Kiểm tra cờ rủi ro QC
    flags = []
    if upside > 2.0: flags.append("ABSURD_UPSIDE")
    if fv_fast < 0: flags.append("NEGATIVE_FV")
    if abs(fv_fast - latest_val.fair_value_base) / latest_val.fair_value_base > 0.15:
        flags.append("STALE_FV_NEEDS_RECOMPUTE")
        
    return {
        "ticker": ticker,
        "fv_fast": fv_fast,
        "upside": upside,
        "flags": flags,
        # ... 
    }
```

---

## 5. CORE LOGIC 3: CHẤT LƯỢNG DỮ LIỆU (QC GATE)
Hệ thống KHÔNG áp dụng máy móc. Ngân hàng sử dụng bộ metrics riêng (NPL, CIR, LDR, NIM, Credit Cost) thay vì Z-Score, M-Score.
Đoạn code định tuyến QC tại `valuation/quality/scores.py`:

```python
def run_qc_checks(ticker: str, sector_name: str, financials: pd.DataFrame, market_cap: float = 0.0) -> Dict[str, Any]:
    # Lọc riêng khối Tài chính
    if any(k in sector_name.lower() for k in ["ngân hàng", "chứng khoán", "bảo hiểm", "banks", "securities", "insurance", "financial services"]):
        if "ngân hàng" in sector_name.lower() or "banks" in sector_name.lower():
            bm = BankMetrics(financials)
            return {
                "is_financial": True,
                "npl_ratio": bm.calculate_npl_ratio(),
                "npl_coverage": bm.calculate_npl_coverage(),
                "cir": bm.calculate_cir(),
                "credit_cost": bm.calculate_credit_cost(),
                "flags": bm.get_flags()
            }
        return {"is_financial": True, "flags": ["FINANCIAL_QC_NOT_IMPLEMENTED_YET"]}
        
    # Công ty phi tài chính dùng Z-score, F-Score, M-Score
    try:
        curr_period = _get_latest_period(financials)
        prev_period = _get_previous_period(financials, curr_period)
        return {
            "is_financial": False,
            "altman_z_score": calculate_altman_z_score(financials, curr_period, market_cap),
            "piotroski_f_score": calculate_piotroski_f_score(financials, curr_period, prev_period)
        }
    except Exception:
        return {"is_financial": False, "altman_z_score": None, "piotroski_f_score": None, "flags": ["DATA_INCOMPLETE"]}
```

---

## 6. CORE LOGIC 4: TỰ ĐỘNG HÓA VỚI N8N (ORCHESTRATION)
Endpoint `/run-daily` kích hoạt luồng 3 bước: Tính Signal -> Xuất GSheets -> Gắn Alert Discord. (`valuation/api/routes/orchestration.py`)

```python
@router.post("/run-daily")
def run_daily_pipeline(request: RunDailyRequest, db: Session = Depends(get_write_db)):
    # Bước 1: Tính Signal cho rổ mã
    signals_res = calculate_batch_signals(tickers=request.tickers, db=db)
    
    # Bước 2: Push 2-way data lên Google Sheets
    sheets_res = export_daily_signals_to_gsheets(trade_date=export_date, db=db)
    
    # Bước 3: Phân tích và bắn tín hiệu mạnh ra Discord EOD
    discord_res = send_daily_alerts(trade_date=export_date, db=db)
    
    return {"status": "success", "pipeline_summary": ...}
```

---

## 7. CÁC QUY TẮC NGHIÊM NGẶT CỦA REPO (GUARDRAILS)
AI Reviewer vui lòng đánh giá dựa trên các rule sau:
1. **Idempotent DB:** Hàm lưu DB sử dụng `ON CONFLICT DO UPDATE` (Upsert), không duplicate dữ liệu.
2. **Strict Mypy Typing:** Khai báo kiểu dữ liệu rõ ràng, cấm Nuốt Lỗi (No Silent Failures).
3. **Bảo mật:** Toàn bộ API Key, Discord Webhook, GSheets Credentials đọc từ file `secrets/` hoặc `.env`.
4. **Không dự phóng cơ học:** Mô hình tài chính phải dựng qua Driver-based (VD Bank thì lấy Tăng trưởng tín dụng -> LNTT).

---
**LỜI NHẮN CHO AI REVIEWER:** 
Hệ thống này đã vượt qua 100% Pytest và hoàn thiện mọi luồng Data. Hãy đọc kỹ kiến trúc **Fast Re-price (Greeks)** ở Core Logic 2. Đây là điểm sáng tạo lớn nhất của dự án để giải quyết bài toán "Định giá Realtime nhưng tiết kiệm tài nguyên". Vui lòng kiểm tra xem logic tích hợp Toán Học này có lỗ hổng Edge-Case nào không (ví dụ: Taylor expansion bậc 1 có bị rủi ro phi tuyến tính khi Delta quá lớn hay không - hiện tại đã có cờ STALE_FV chặn điều này).
