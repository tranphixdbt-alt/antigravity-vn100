# Hệ thống định giá VN100

Ứng dụng Streamlit định giá cổ phiếu VN100, đọc dữ liệu tài chính/giá lịch sử từ database portable và chỉ gọi API ngoài khi người dùng chủ động cập nhật dữ liệu hoặc sinh báo cáo AI.

## Thư mục đang chạy trên máy này

```text
/Users/macos/Library/CloudStorage/GoogleDrive-tranphixdbt@gmail.com/.shortcut-targets-by-id/18agtU6fpR5TUOQ34MscdIETims-hoTsa/DATA-G/Phi/1 Antigravity/chứng khoán định giá/antigravity-vn100
```

## Cách chạy nhanh trên macOS

1. Cài Python 3.11+ nếu máy chưa có.
2. Tải repo về máy.
3. Nhấp đúp `Chay_Dinh_Gia_VN100.command`.
4. Mở `http://localhost:8502`.

Launcher sẽ tự tạo môi trường Python tại `~/.venv`, cài thư viện từ `requirements.txt`, giải nén `vn100_full.db.gz` thành `vn100_full.db` nếu cần, rồi chạy app.

## Cách chạy bằng terminal

```bash
python3 -m venv ~/.venv
source ~/.venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt
python scripts/ensure_portable_db.py
export DATABASE_URL_READONLY="sqlite:///$PWD/vn100_full.db"
export DATABASE_URL_WRITE="sqlite:///$PWD/vn100_full.db"
python -m streamlit run streamlit_app.py --server.port 8502 --server.headless true
```

## Dữ liệu đi kèm

- `vn100_full.db.gz`: database portable đã nén để đưa lên GitHub.
- Khi chạy lần đầu, file này được giải nén thành `vn100_full.db`.
- `vn100_full.db` không commit trực tiếp vì file lớn hơn 100 MB, GitHub thường chặn file đơn lẻ quá lớn.

## API key

Repo không chứa key thật. Nếu muốn dùng dữ liệu live, Google Sheets/Drive, Discord hoặc DeepSeek, sao chép:

```bash
cp .env.example .env
```

Sau đó điền key trong `.env`.

Các key quan trọng:

- `VNSTOCK_API_KEY`: cập nhật dữ liệu mới từ vnstock.
- `DEEPSEEK_API_KEY`: sinh báo cáo AI khi bấm nút trong app.
- `GOOGLE_SERVICE_ACCOUNT_JSON`, `GOOGLE_SHEET_MASTER_ID`, `GOOGLE_DRIVE_FOLDER_ID`: xuất Google.
- `DISCORD_WEBHOOK_URL`: gửi cảnh báo.

## Đẩy lên GitHub

Vì repo hiện chưa có remote GitHub, tạo repo trống trên GitHub rồi chạy:

```bash
git remote add origin https://github.com/<user>/<repo>.git
git add README.md .env.example .gitignore Chay_Dinh_Gia_VN100.command scripts/ensure_portable_db.py vn100_full.db.gz
git add streamlit_app.py valuation tests config docs requirements.txt requirements-integrations.txt
git status
git commit -m "Đóng gói bản chạy portable VN100"
git push -u origin feat/hieu-chuan-dinh-gia-vn100
```

Trước khi commit, luôn kiểm tra `git status` để chắc `.env`, `venv/`, `build/`, `dist/`, `backups/`, `logs/` và `*.db` không bị đưa lên.

## Kiểm tra nhanh dữ liệu portable

```bash
python scripts/ensure_portable_db.py
sqlite3 vn100_full.db "select count(*) from tickers where is_vn100=1;"
sqlite3 vn100_full.db "select count(distinct ticker) from financials_quarterly;"
sqlite3 vn100_full.db "select count(distinct ticker) from prices_daily;"
```

Kỳ vọng hiện tại:

- `tickers is_vn100`: 101
- `financials_quarterly`: 102 mã
- `prices_daily`: 102 mã
- routing/valuation output: 101/101 mã VN100
- consensus CTCK: 101/101 mã VN100 có ít nhất 1 dòng truy vết
