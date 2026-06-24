-- Thêm cột published_at vào financials_quarterly
ALTER TABLE financials_quarterly ADD COLUMN IF NOT EXISTS published_at DATE;

-- Bảng lưu trữ độ nhạy (Greeks) của định giá
CREATE TABLE IF NOT EXISTS valuation_sensitivities (
  ticker TEXT REFERENCES tickers(ticker),
  assumption_version INT,
  driver_code TEXT,
  dFV_ddriver NUMERIC, -- Đạo hàm riêng của FV theo driver
  base_driver_value NUMERIC,
  created_at TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (ticker, assumption_version, driver_code)
);

-- Bảng chỉ báo vĩ mô (Macro Radar)
CREATE TABLE IF NOT EXISTS macro_radar (
  sector TEXT,
  indicator_code TEXT,
  frequency TEXT,        -- 'daily' | 'weekly' | 'monthly' | 'quarterly'
  source TEXT,
  warn_low NUMERIC,
  warn_high NUMERIC,
  mapped_driver TEXT,    -- driver nào trong valuation_sensitivities bị ảnh hưởng
  PRIMARY KEY (sector, indicator_code)
);

-- Bảng Daily Signal (Lưu snapshot định giá mỗi ngày)
CREATE TABLE IF NOT EXISTS daily_signal (
  ticker TEXT REFERENCES tickers(ticker),
  trade_date DATE,
  close_price NUMERIC,
  fair_value_fast NUMERIC,
  upside NUMERIC,
  margin_of_safety NUMERIC,
  conviction_score NUMERIC,
  flags JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (ticker, trade_date)
);

-- Bảng Consensus (Tham khảo giá mục tiêu từ các CTCK)
CREATE TABLE IF NOT EXISTS consensus (
  ticker TEXT REFERENCES tickers(ticker),
  broker TEXT,
  report_date DATE,
  target_price NUMERIC,
  rating TEXT,
  source TEXT,
  PRIMARY KEY (ticker, broker, report_date)
);
