import pandas as pd

file_path = "../VN100_Phuong_phap_dinh_gia_chi_tiet.xlsx"
try:
    xl = pd.ExcelFile(file_path)
    for sheet in xl.sheet_names:
        print(f"\n--- Sheet: {sheet} ---")
        df = pd.read_excel(file_path, sheet_name=sheet, header=1) # Assume header is row 1 (0-indexed) or 2
        print("Columns:", df.columns.tolist())
        print("Head (5 rows):\n", df.head(5).to_string())
except Exception as e:
    print(f"Error reading excel: {e}")
