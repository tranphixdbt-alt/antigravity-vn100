# VN100 trên VPS bằng Docker (bản sao — file thật nằm ở `/srv/apps/vn100` trên `vps-web`)

Từ 18/11/2026 VPS `ubuntu@192.168.1.201` (web `chungkhoan.btinvest.vn`, đăng nhập bằng tài khoản coin; tên cũ `chungkhoang` chuyển hướng) chạy thay máy Mac (D96).
Thư mục `/srv/apps/vn100`: `app/` = git clone repo này (tự `deploy vn100` khi `main` đổi, ~3 phút), các file ở đây
nằm NGOÀI repo; bản trong thư mục này chỉ để dựng lại nếu VPS hỏng — sửa ở VPS thì chép lại vào đây.

| Container | Việc |
|---|---|
| `vn100` | Giao diện Streamlit (Caddy gọi `vn100:8506`) |
| `vn100-worker` | `scheduler.py`: báo cáo sáng 07:50 T2–T6, dòng tiền 08:30 T2–T6, tóm tắt tuần CN 18:00 (chạy bù ≤ 3 giờ) |
| `vn100-bot` | Bot Discord (chỉ chạy MỘT nơi — launchd trên Mac đã `launchctl disable`) |

- DB ở volume `vn100_vn100_data` (`/data`), `DB_SYNC_FROM_REPO=0`: VPS là bản chính, không ghi đè bằng `vn100_full.db.gz`.
- Trạng thái lúc chạy (`.vn100_ranking`, `.daily_report`, …) và log, đăng nhập vnstock: volume riêng, sống qua deploy.
- vnstock 4 bản miễn phí chép từ Mac vào `vendor/gen4/` (index cũ đã gỡ); vnstock 6 + vnstock-oapi ở
  `/home/app/.venv_6x` cho FHSC. Không có `vnstock_data` (gói tài trợ thế hệ 4 bị khóa từ 10/11/2026).
- `.env` chép từ Mac qua `scp` (chmod 600), không có trong repo. RAM VPS 3,9 GB không swap (treo 18/11) → giới hạn
  web 1 GB, worker 640 MB, bot 256 MB; KHÔNG chạy `docker compose run` thử song song với app.
- Đăng nhập vnstock 6 / khóa FHSC: chủ tài khoản tự làm trong container (`vnstock login`, `vnstock keys set fhsc`).
