# Chứng quyền (cw_scanner) trên VPS — bản sao cấu hình triển khai

Bản thật nằm ở `ubuntu@192.168.1.201:/srv/apps/chungquyen` (ngoài repo cw_scanner, vì repo đó của Kiệt và tài khoản
này chỉ có quyền đọc). Sửa ở đây thì chép sang VPS rồi `deploy chungquyen --force`.

- `app/` = git clone `https://github.com/ngo-tuankiet/chung_quyen` (công khai). `deploy@chungquyen.timer` kéo code mới
  mỗi 3 phút. KHÔNG sửa code trong `app/` (bị ghi đè); dữ liệu người dùng nằm cạnh code và đều trong `.gitignore`:
  `.env` (chmod 600), `danh_muc.csv`, `cw_da_biet.txt`, `canh_bao_da_gui.json`, `ket_qua/`, `log.txt`.
  `app/.venv` là liên kết tới `/opt/venv` trong image (các script `.sh` gọi `.venv/bin/python`).
- `chungquyen`: web `http.server` cổng 8000, Caddy `chungquyen.btinvest.vn` (cùng mật khẩu với chungkhoang).
- `chungquyen-worker`: `scheduler.py` thay 4 lịch launchd của Mac (`vn.cw-scanner.*`, đã `launchctl disable`).
  Nhật ký: `app/log.txt`. Trạng thái lịch: `app/ket_qua/.lich_vps.json`.
- vnstock 6: đăng nhập lỗi (vượt số thiết bị) thì app tự dùng gói Khách (10 lượt/phút, quét chậm hơn).
- Không chạy container thử cạnh app (RAM); kiểm bằng `docker exec`.
