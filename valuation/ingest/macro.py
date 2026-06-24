import pandas as pd
from sqlalchemy.orm import Session
from valuation.db.models import MacroSeries
from valuation.db.session import SessionLocalWrite

def ingest_macro_csv(file_path: str, db: Session = None):
    """
    Ingest macro data from a CSV file.
    CSV Format expected: indicator_code, date, value, source
    """
    close_db = False
    if db is None:
        db = SessionLocalWrite()
        close_db = True
        
    try:
        df = pd.read_csv(file_path)
        records = []
        for _, row in df.iterrows():
            date_val = pd.to_datetime(row['date']).date()
            record = MacroSeries(
                indicator_code=row['indicator_code'],
                date=date_val,
                value=float(row['value']),
                source=row.get('source', 'CSV')
            )
            records.append(record)
            
        db.add_all(records)
        db.commit()
        print(f"Successfully ingested {len(records)} macro records from {file_path}")
    except Exception as e:
        db.rollback()
        print(f"Error ingesting macro CSV: {e}")
    finally:
        if close_db:
            db.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        ingest_macro_csv(sys.argv[1])
    else:
        print("Usage: python -m valuation.ingest.macro <path_to_csv>")
