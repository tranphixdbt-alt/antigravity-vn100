from valuation.db.session import SessionLocalWrite
from sqlalchemy import text

db = SessionLocalWrite()
try:
    db.execute(text('ALTER TABLE prices_daily ADD COLUMN IF NOT EXISTS foreign_buy_vol NUMERIC;'))
    db.execute(text('ALTER TABLE prices_daily ADD COLUMN IF NOT EXISTS foreign_buy_val NUMERIC;'))
    db.execute(text('ALTER TABLE prices_daily ADD COLUMN IF NOT EXISTS foreign_sell_vol NUMERIC;'))
    db.execute(text('ALTER TABLE prices_daily ADD COLUMN IF NOT EXISTS foreign_sell_val NUMERIC;'))
    db.execute(text('ALTER TABLE prices_daily ADD COLUMN IF NOT EXISTS foreign_net_vol NUMERIC;'))
    db.execute(text('ALTER TABLE prices_daily ADD COLUMN IF NOT EXISTS foreign_net_val NUMERIC;'))

    db.execute(text('ALTER TABLE prices_daily ADD COLUMN IF NOT EXISTS proprietary_buy_vol NUMERIC;'))
    db.execute(text('ALTER TABLE prices_daily ADD COLUMN IF NOT EXISTS proprietary_buy_val NUMERIC;'))
    db.execute(text('ALTER TABLE prices_daily ADD COLUMN IF NOT EXISTS proprietary_sell_vol NUMERIC;'))
    db.execute(text('ALTER TABLE prices_daily ADD COLUMN IF NOT EXISTS proprietary_sell_val NUMERIC;'))
    db.execute(text('ALTER TABLE prices_daily ADD COLUMN IF NOT EXISTS proprietary_net_vol NUMERIC;'))
    db.execute(text('ALTER TABLE prices_daily ADD COLUMN IF NOT EXISTS proprietary_net_val NUMERIC;'))
    
    db.commit()
    print("Columns added successfully.")
except Exception as e:
    print(f"Error: {e}")
    db.rollback()
finally:
    db.close()
