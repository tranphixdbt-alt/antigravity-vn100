import docx
import pandas as pd
from pathlib import Path

ref_dir = Path("docs/reference")
scratch_dir = Path("/Users/macos/.gemini/antigravity/brain/2d90a547-1455-4943-89d5-2a1635daa6cf/scratch")
scratch_dir.mkdir(parents=True, exist_ok=True)

# Parse docx
for file in ref_dir.glob("*.docx"):
    try:
        doc = docx.Document(file)
        text = "\n".join([p.text for p in doc.paragraphs])
        out_file = scratch_dir / f"{file.stem}.txt"
        with open(out_file, "w") as f:
            f.write(text)
        print(f"Parsed {file.name} to {out_file.name}")
    except Exception as e:
        print(f"Error parsing {file.name}: {e}")

# Parse excel structure
for file in ref_dir.glob("*.xlsx"):
    try:
        xl = pd.ExcelFile(file)
        print(f"\n--- EXCEL FILE: {file.name} ---")
        print(f"Sheets: {xl.sheet_names}")
        for sheet in xl.sheet_names[:5]: # just print first 5 sheets
            df = xl.parse(sheet, nrows=2)
            print(f"  Sheet '{sheet}' cols: {list(df.columns)}")
    except Exception as e:
        print(f"Error parsing {file.name}: {e}")

