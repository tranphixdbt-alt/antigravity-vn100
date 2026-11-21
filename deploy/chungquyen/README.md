# Chứng quyền (cw_scanner) trên VPS — bản sao cấu hình triển khai

Bản thật nằm ở `ubuntu@192.168.1.201:/srv/apps/chungquyen` (ngoài repo cw_scanner, vì repo đó của Kiệt và tài khoản
này chỉ có quyền đọc). Sửa ở đây thì chép sang VPS rồi `deploy chungquyen --force`.

- `app/` = git clone `https://github.com/ngo-tuankiet/chung_quyen` (công khai). `deploy@chungquyen.timer` kéo code mới
  mỗi 3 phút. KHÔNG sửa code trong `app/` (bị ghi đè); dữ liệu người dùng nằm cạnh code và đều trong `.gitignore`:
  `.env` (chmod 600), `danh_muc.csv`, `cw_da_biet.txt`, `canh_bao_da_gui.json`, `ket_qua/`, `log.txt`.
  `app/.venv` là liên kết tới `/opt/venv` trong image (các script `.sh` gọi `.venv/bin/python`).
- `chungquyen`: web `http.server` cổng 8000, Caddy `chungquyen.btinvest.vn` (đăng nhập chung bằng tài khoản coin, D98).
- `chungquyen-worker`: `scheduler.py` thay 4 lịch launchd của Mac (`vn.cw-scanner.*`, đã `launchctl disable`).
  Nhật ký: `app/log.txt`. Trạng thái lịch: `app/ket_qua/.lich_vps.json`.
- vnstock 6: đăng nhập lỗi (vượt số thiết bị) thì app tự dùng gói Khách (10 lượt/phút, quét chậm hơn).
- `app/.env` PHẢI có `FHSC_API_KEY` (lịch sử giá cổ phiếu cơ sở và giá ETF lấy qua FHSC = Finhay). Trên Mac khóa nằm
  trong keychain nên `.env` chép sang không có → quét 14:00 và báo cáo ETF lỗi 18–20/11 ("Chưa có khoá: FHSC_API_KEY").
  vnstock-oapi đọc `.env` ở thư mục đang chạy (`/app`). Đã chép từ `/srv/apps/vn100/.env` ngày 21/11.
- Bộ test cw không gọi mạng: sau khi chuyển máy phải thử một lượt gọi thật, ví dụ
  `docker exec -w /app chungquyen-worker .venv/bin/python -c "import cw_scanner as c; print(c.bien_dong_lich_su('FPT')[1])"`.
- Vietcap (`trading.vietcap.com.vn`) bảo trì cuối tuần → mọi API chuyển hướng `maintenance.vietcap.com.vn`, quét lỗi
  `JSONDecodeError` ở `ma_theo_nhom` (không phải lỗi VPS).
- Không chạy container thử cạnh app (RAM); kiểm bằng `docker exec`.
