import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from valuation.ingest.vnstock_client import vnstock_client

def main():
    for tk in ["HPG", "SSI"]:
        print(f"\n=== FETCHING LIVE FINANCIALS FOR {tk} FROM VNSTOCK ===")
        try:
            df = vnstock_client.get_financials(tk, "BS")
            print(f"{tk} BS shape: {df.shape}")
            if not df.empty:
                print("Columns:", df.columns)
                # Tìm xem có quý 2/2024 hay 2024-Q2 không
                # vnstock thường trả về các cột là các quý
                q2_cols = [c for c in df.columns if "2024" in str(c) or "Q2" in str(c)]
                print("2024 related columns in BS:", q2_cols)
                print(df.head(10))
        except Exception as e:
            print(f"Error fetching {tk}: {e}")

if __name__ == "__main__":
    main()
