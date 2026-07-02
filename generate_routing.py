"""Sinh valuation/config/routing.json từ VN100_Phuong_phap_dinh_gia_chi_tiet.xlsx.

NGUỒN SỰ THẬT routing DUY NHẤT. Đọc bằng openpyxl theo CHỈ SỐ CỘT (robust hơn
pandas-by-header: bản pandas cũ đọc lệch cột cho vài mã, vd FPT 'SOTP' bị đọc thành
'DCF'). Bố cục sheet "Chi tiet 100 ma" (từ dòng 4):
  col1=Mã, col2=Nhóm ngành, col3=PP chính, col4=PP phụ, col5=Trọng số, col8=Đã KC.

Chạy: ./venv/bin/python generate_routing.py
"""
import json
import os
import openpyxl

file_path = "../VN100_Phuong_phap_dinh_gia_chi_tiet.xlsx"
out_dir = "valuation/config"
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "routing.json")


def _primary_key(raw: str) -> str:
    """PP chính = phương pháp xuất hiện SỚM NHẤT trong chuỗi (vd 'SOTP / RNAV'→SOTP,
    'RNAV / SOTP'→RNAV, 'DCF/FCFF + EV/EBITDA'→FCFF, 'So sánh P/B'→P/B)."""
    s = (raw or "").strip().lower()
    markers = [
        ("RI", ["residual income", "thu nhập thặng dư"]),
        ("RNAV", ["rnav", "tài sản ròng"]),
        ("SOTP", ["sotp", "từng phần"]),
        ("EV/EBITDA", ["ev/ebitda"]),
        ("P/B", ["p/b"]),
        ("P/E", ["p/e"]),
        ("FCFF", ["dcf", "fcff"]),
    ]
    best, best_pos = "FCFF", 10**9
    for key, subs in markers:
        for sub in subs:
            i = s.find(sub)
            if i != -1 and i < best_pos:
                best_pos, best = i, key
    return best


def _secondary_key(raw: str):
    s = (raw or "").strip().lower()
    if not s or s == "nan":
        return None
    if "residual income" in s or "thu nhập thặng dư" in s:
        return "RI"
    if "rnav" in s or "tài sản ròng" in s:
        return "RNAV"
    if "sotp" in s or "từng phần" in s:
        return "SOTP"
    if "ev/ebitda" in s:
        return "EV/EBITDA"
    if "p/b" in s:
        return "P/B"
    if "p/e" in s:
        return "P/E"
    return None


wb = openpyxl.load_workbook(file_path, data_only=True)
ws = wb["Chi tiet 100 ma"]
routing_data = {}

for r in ws.iter_rows(min_row=4, values_only=True):
    ticker = str(r[1]).strip().upper() if r[1] else ""
    if not ticker or ticker in ("NAN", "MÃ"):
        continue
    sector = str(r[2]).strip() if r[2] else ""
    primary_method = str(r[3]).strip() if r[3] else ""
    secondary_method = str(r[4]).strip() if r[4] else ""
    weights_raw = str(r[5]).strip() if r[5] else ""
    verified = bool(r[8] and "✔" in str(r[8]))

    secondary_key = _secondary_key(secondary_method)
    w_primary = 0.5 if secondary_key else 1.0
    w_secondary = 0.5 if secondary_key else 0.0

    routing_data[ticker] = {
        "sector": sector,
        "primary": _primary_key(primary_method),
        "secondary": secondary_key,
        "weight_primary": w_primary,
        "weight_secondary": w_secondary,
        "verified": verified,
        "raw_primary": primary_method,
        "raw_secondary": secondary_method,
        "raw_weights": weights_raw,
    }

with open(out_path, "w", encoding="utf-8") as f:
    json.dump(routing_data, f, ensure_ascii=False, indent=2)

from collections import Counter
print(f"Generated routing.json with {len(routing_data)} tickers.")
print("primary distinct:", dict(Counter(v["primary"] for v in routing_data.values())))
