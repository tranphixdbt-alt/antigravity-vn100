# VN100 trên VPS bằng Docker (bản sao — file thật nằm ở `/srv/apps/vn100` trên `vps-web`)

Từ 18/11/2026 VPS `ubuntu@192.168.1.201` (web `chungkhoan.btinvest.vn`, đăng nhập bằng tài khoản coin; tên cũ `chungkhoang` chuyển hướng) chạy thay máy Mac (D96).
Thư mục `/srv/apps/vn100`: `app/` = git clone repo này (tự `deploy vn100` khi `main` đổi, ~3 phút), các file ở đây
nằm NGOÀI repo; bản trong thư mục này chỉ để dựng lại nếu VPS hỏng — sửa ở VPS thì chép lại vào đây.

| Container | Việc |
|---|---|
| `vn100` | Giao diện Streamlit (Caddy gọi `vn100:8506`) |
| `vn100-worker` | `scheduler.py`: TPCP_10Y 07:20 T2–T6 (D100), báo cáo sáng 07:50 T2–T6, cập nhật dữ liệu + xếp hạng 08:00 T2 và T5, tóm tắt tuần CN 18:00 (dòng tiền 08:30 tắt từ D97; chạy bù ≤ 3 giờ) |
| `vn100-bot` | Bot Discord (chỉ chạy MỘT nơi — launchd trên Mac đã `launchctl disable`) |
| `btinvest-web` | Web hợp nhất `https://btinvest.vn` từ 25/11/2026 (D111): FastAPI `valuation.api.web_main` cổng 8600, một tiến trình, giới hạn 768 MB. Caddy gọi `btinvest-web:8600` và KHÔNG chặn hộ: ứng dụng tự hỏi coin `/me`, tự trả 401 |

- DB ở volume `vn100_vn100_data` (`/data`), `DB_SYNC_FROM_REPO=0`: VPS là bản chính, không ghi đè bằng `vn100_full.db.gz`.
- Trạng thái lúc chạy (`.vn100_ranking`, `.daily_report`, …) và log, đăng nhập vnstock: volume riêng, sống qua deploy.
- vnstock 4 bản miễn phí chép từ Mac vào `vendor/gen4/` (index cũ đã gỡ); vnstock 6 + vnstock-oapi ở
  `/home/app/.venv_6x` cho FHSC. Không có `vnstock_data` (gói tài trợ thế hệ 4 bị khóa từ 10/11/2026).
- `.env` chép từ Mac qua `scp` (chmod 600), không có trong repo. Giới hạn: web 1 GB, worker 640 MB, bot 256 MB, web
  hợp nhất 768 MB. Máy từng chỉ có 3,9 GB không swap (treo 18/11); đo 25/11/2026 là 12,9 GB RAM và 2 GB swap. Ghi
  chú "3,9 GB" còn trong compose đã cũ.
- Web hợp nhất (`btinvest-web`): dữ liệu người dùng ở `/data/web_user/web_user.db` (biến `WEB_USER_DB_URL` đặt ở phần
  dùng chung của compose), tách khỏi DB định giá. `WEB_ADMIN_EMAILS` chỉ nằm trong `.env` trên VPS, do chủ máy tự
  điền; đổi xong phải `docker compose up -d --force-recreate btinvest-web`. Lệnh `deploy` chờ MỌI container khỏe
  trong 240 giây, nên container này không lên được thì cả lần deploy tự quay về commit trước.
- Quay lui web hợp nhất: `docker compose stop btinvest-web`, rồi
  `sudo cp -p /srv/web/conf/Caddyfile.bak-btinvest-web-20261125-1921 /srv/web/conf/Caddyfile` và
  `docker exec web-caddy-1 caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile` (btinvest.vn về trang
  chờ ở `/srv/web/sites/btinvest`). Compose trước khi thêm: `docker-compose.yml.bak-20261125-truoc-btinvest-web`.
- `Dockerfile` trên VPS đang khác bản sao ở đây 4 dòng (liên kết tệp bản tin vĩ mô sang `/data`, bước chạy
  `patches/vps_hotfix.py`); thấy lúc đọc VPS 25/11/2026, chưa đối chiếu bản nào đúng.
- Đăng nhập vnstock 6 / khóa FHSC: chủ tài khoản tự làm trong container (`vnstock login`, `vnstock keys set fhsc`).
