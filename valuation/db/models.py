from sqlalchemy import Column, String, Boolean, Integer, Numeric, Date, BigInteger, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
import datetime
from valuation.db.session import Base

class Ticker(Base):
    __tablename__ = "tickers"
    
    ticker = Column(String, primary_key=True)
    company_name = Column(String)
    exchange = Column(String)
    sector = Column(String)
    industry = Column(String)
    is_vn100 = Column(Boolean)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

class FinancialsQuarterly(Base):
    __tablename__ = "financials_quarterly"
    
    ticker = Column(String, ForeignKey("tickers.ticker"), primary_key=True)
    fiscal_year = Column(Integer, primary_key=True)
    fiscal_quarter = Column(Integer, primary_key=True)
    is_consolidated = Column(Boolean, primary_key=True)
    is_restated = Column(Boolean, primary_key=True)
    statement = Column(String, primary_key=True)
    line_item = Column(String, primary_key=True)
    value = Column(Numeric)
    currency = Column(String, default="VND")
    source = Column(String)
    published_at = Column(Date, nullable=True)
    ingested_at = Column(DateTime(timezone=True), server_default=func.now())

class PricesDaily(Base):
    __tablename__ = "prices_daily"
    
    ticker = Column(String, primary_key=True)
    trade_date = Column(Date, primary_key=True)
    open = Column(Numeric)
    high = Column(Numeric)
    low = Column(Numeric)
    close = Column(Numeric)
    adj_close = Column(Numeric, nullable=True)
    volume = Column(BigInteger)
    value = Column(Numeric, nullable=True)
    foreign_buy = Column(Numeric, nullable=True)
    foreign_sell = Column(Numeric, nullable=True)
    price_unit = Column(String, default="VND")

class BackfillStatus(Base):
    __tablename__ = "backfill_status"
    
    ticker = Column(String, primary_key=True)
    last_financial_period = Column(String)
    last_price_date = Column(Date)
    status = Column(String)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ValuationOutput(Base):
    __tablename__ = "valuation_outputs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String, ForeignKey("tickers.ticker"))
    blended_fair_value_per_share = Column(Numeric)
    fair_value_bull = Column(Numeric, nullable=True)
    fair_value_bear = Column(Numeric, nullable=True)
    margin_of_safety = Column(Numeric, nullable=True)
    flags = Column(JSON, nullable=True)
    macro_snapshot = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ValuationSensitivity(Base):
    __tablename__ = "valuation_sensitivities"
    
    ticker = Column(String, ForeignKey("tickers.ticker"), primary_key=True)
    assumption_version = Column(Integer, ForeignKey("valuation_outputs.id"), primary_key=True)
    driver_code = Column(String, primary_key=True)
    dFV_ddriver = Column(Numeric)
    base_driver_value = Column(Numeric)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class MacroSeries(Base):
    __tablename__ = 'macro_series'
    id = Column(Integer, primary_key=True, index=True)
    indicator_code = Column(String(50), index=True)
    date = Column(Date, index=True)
    value = Column(Numeric)
    source = Column(String(50))
    created_at = Column(DateTime, default=datetime.datetime.utcnow, server_default=func.now())

class MacroRadar(Base):
    __tablename__ = "macro_radar"
    
    sector = Column(String, primary_key=True)
    indicator_code = Column(String, primary_key=True)
    frequency = Column(String)
    source = Column(String)
    warn_low = Column(Numeric)
    warn_high = Column(Numeric)
    mapped_driver = Column(String)

class DailySignal(Base):
    __tablename__ = "daily_signal"
    
    ticker = Column(String, ForeignKey("tickers.ticker"), primary_key=True)
    trade_date = Column(Date, primary_key=True)
    close_price = Column(Numeric)
    fair_value_fast = Column(Numeric)
    upside = Column(Numeric)
    margin_of_safety = Column(Numeric)
    conviction_score = Column(Numeric)
    flags = Column(JSON)
    computed_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Consensus(Base):
    __tablename__ = "consensus"
    
    ticker = Column(String, ForeignKey("tickers.ticker"), primary_key=True)
    broker = Column(String, primary_key=True)
    report_date = Column(Date, primary_key=True)
    target_price = Column(Numeric)
    rating = Column(String)
    source = Column(String)
