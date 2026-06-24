import pandas as pd
file = "docs/reference/2026.05.03. data_bank_v1.xlsx"
xl = pd.ExcelFile(file)
print("--- MaCK ---")
df_mack = xl.parse("MaCK")
print(df_mack.head())

print("--- BCTC ---")
df_bctc = xl.parse("BCTC")
print(df_bctc.head())
print(df_bctc.columns.tolist())

print("--- Giá cổ phiếu ---")
df_price = xl.parse("Giá cổ phiếu")
print(df_price.head())
