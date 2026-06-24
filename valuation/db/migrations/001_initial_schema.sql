-- Danh mục mã
CREATE TABLE tickers (
  ticker        TEXT PRIMARY KEY,
  company_name  TEXT,
  exchange      TEXT,
  sector        TEXT,          -- map sang nhóm định giá (mục 6)
  industry      TEXT,
  is_vn100      BOOLEAN,
  updated_at    TIMESTAMPTZ DEFAULT now()
);

-- BCTC theo quý (đã chuẩn hóa)
CREATE TABLE financials_quarterly (
  ticker        TEXT REFERENCES tickers(ticker),
  fiscal_year   INT,
  fiscal_quarter INT,          -- 1..4, 0 = cả năm
  is_consolidated BOOLEAN,     -- hợp nhất vs công ty mẹ
  is_restated   BOOLEAN,       -- bản điều chỉnh hồi tố
  statement     TEXT,          -- 'BS' | 'IS' | 'CF'
  line_item     TEXT,          -- mã chỉ tiêu chuẩn hóa
  value         NUMERIC,
  currency      TEXT DEFAULT 'VND',
  source        TEXT,          -- 'vnstock' | 'hose_filing'
  ingested_at   TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (ticker, fiscal_year, fiscal_quarter, statement, line_item, is_consolidated, is_restated)
);

-- Giá daily (đã sửa để cho phép NULL đối với các trường vnstock thiếu)
CREATE TABLE prices_daily (
  ticker TEXT, 
  trade_date DATE, 
  open NUMERIC, 
  high NUMERIC, 
  low NUMERIC,
  close NUMERIC, 
  adj_close NUMERIC NULL, 
  volume BIGINT, 
  value NUMERIC NULL,
  foreign_buy NUMERIC NULL, 
  foreign_sell NUMERIC NULL,
  price_unit TEXT DEFAULT 'VND', -- Đơn vị đã được chuẩn hóa về VND tuyệt đối x1000
  PRIMARY KEY (ticker, trade_date)
);

-- Dữ liệu vĩ mô & ngành
CREATE TABLE macro_series (
  series_code TEXT, period DATE, value NUMERIC, source TEXT,
  PRIMARY KEY (series_code, period)
);

CREATE TABLE industry_indicators (
  sector TEXT, indicator_code TEXT, period DATE, value NUMERIC,
  PRIMARY KEY (sector, indicator_code, period)
);

-- Giả định định giá (đồng bộ với Google Sheet)
CREATE TABLE valuation_assumptions (
  ticker TEXT, version INT, edited_by TEXT,  -- 'system' | 'user'
  rev_growth JSONB, margin JSONB, wacc NUMERIC, terminal_growth NUMERIC,
  target_multiple JSONB, scenario TEXT,      -- 'bull'|'base'|'bear'
  created_at TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (ticker, version, scenario)
);

-- Kết quả định giá
CREATE TABLE valuation_outputs (
  ticker TEXT, assumption_version INT, model TEXT,
  scenario TEXT, target_price NUMERIC, current_price NUMERIC,
  upside_pct NUMERIC, rating TEXT, margin_of_safety NUMERIC,
  flags JSONB,                               -- Z/M/F score, red flags
  created_at TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (ticker, assumption_version, model, scenario)
);

-- Trạng thái backfill
CREATE TABLE backfill_status (
  ticker TEXT PRIMARY KEY,
  last_financial_period TEXT,
  last_price_date DATE,
  status TEXT,
  updated_at TIMESTAMPTZ DEFAULT now()
);
