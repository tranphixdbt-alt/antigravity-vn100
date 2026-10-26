# Cài VN100 lên VPS (chạy thay máy Mac)

Sau khi cài, VPS tự làm đúng như máy Mac:

| Dịch vụ | Việc | Lịch |
|---|---|---|
| `vn100-daily-report.timer` | Báo cáo sáng lên Discord (webhook), cập nhật giá + vĩ mô | 07:50 thứ 2–6, giờ Việt Nam; VPS khởi động lại sau 07:50 thì chạy bù |
| `vn100-discord-bot.service` | Bot Discord trả lời khi được @ trong kênh | Chạy liên tục, tự khởi động lại khi lỗi/khởi động máy |
| `vn100-streamlit.service` | App định giá (tuỳ chọn) | Chạy liên tục, chỉ nghe `127.0.0.1:8506`; mở ra ngoài qua Caddy có mật khẩu (mục dưới) |

Yêu cầu: Ubuntu 24.04 (Python 3.12 sẵn; dự án cần ≥ 3.11), 2 GB RAM trở lên, quyền `sudo`, git. Nên chạy bằng user
thường (vd `sudo adduser vn100`), không chạy bằng root.

## Lần đầu (một lần)

1. Tải code:
   ```bash
   git clone https://github.com/tranphixdbt-alt/antigravity-vn100.git ~/vn100   # repo riêng tư: cần deploy key hoặc gh auth trên VPS
   cd ~/vn100
   ```
2. **Chép file `.env` từ máy Mac lên VPS** — file này chứa key thật nên KHÔNG BAO GIỜ có trên GitHub.
   Chạy trên máy Mac (trong thư mục dự án):
   ```bash
   scp .env <user>@<ip-vps>:~/vn100/.env
   ```
   Nếu `.env` có `GOOGLE_SERVICE_ACCOUNT_JSON` (đường dẫn file JSON trên Mac) và cần Google Sheets/Drive:
   chép thêm file JSON đó lên VPS rồi sửa đường dẫn trong `.env` của VPS.
3. Cài đặt:
   ```bash
   bash deploy/setup_vps.sh            # hoặc --no-app nếu không cần app Streamlit
   ```
   Script tự: tạo `.venv`, cài thư viện, giải nén `vn100_full.db.gz`, chạy thử báo cáo (không gửi), cài và bật 3 dịch vụ.
4. **Tắt dịch vụ trên máy Mac** để Discord không nhận báo cáo/bot trả lời hai lần:
   ```bash
   launchctl unload ~/Library/LaunchAgents/vn.antigravity-vn100.daily-report.plist
   launchctl unload ~/Library/LaunchAgents/vn.antigravity-vn100.discord-bot.plist
   ```
   (Bot Discord chỉ được chạy MỘT nơi — hai bot cùng token sẽ tranh nhau kết nối.)

## Mỗi lần có code mới trên GitHub

```bash
cd ~/vn100
bash deploy/update_vps.sh
```

Kéo code, cài thư viện mới, khởi động lại bot/app. **DB trên VPS được giữ nguyên** (giá cập nhật hằng ngày trên VPS
không mất). Khi chủ dự án báo "có DB mới" (sửa dữ liệu, thêm báo cáo CTCK...):

```bash
bash deploy/update_vps.sh --reset-db   # sao lưu DB cũ vào backups/ rồi dùng vn100_full.db.gz mới
```

## Kiểm tra

```bash
systemctl status vn100-discord-bot          # bot
systemctl list-timers vn100-daily-report    # lần chạy báo cáo kế tiếp
sudo systemctl start vn100-daily-report     # gửi báo cáo ngay (thử)
tail -f ~/vn100/logs/daily_report.log ~/vn100/logs/discord_bot.log
```

## Mở app trên điện thoại (HTTPS + mật khẩu)

> **Không mở app ra Internet khi chưa có mật khẩu.** App không có đăng nhập riêng: ai có link đều bấm được nút gọi
> DeepSeek (tốn tiền), quét vnstock và ghi DB.

Cần một tên miền trỏ bản ghi A về IP VPS. Cài Caddy (tự lấy HTTPS, tự chuyển websocket mà Streamlit cần):

```bash
sudo apt install -y caddy
caddy hash-password          # nhập mật khẩu, copy chuỗi hash
```

`/etc/caddy/Caddyfile`:

```
vn100.<tên-miền> {
    basic_auth {
        phi <chuỗi-hash>
    }
    reverse_proxy 127.0.0.1:8506
}
```

```bash
sudo systemctl reload caddy
sudo ufw allow 22/tcp && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw enable   # KHÔNG mở 8506
```

Dùng nginx thay Caddy thì bắt buộc `proxy_http_version 1.1;`, `proxy_set_header Upgrade $http_upgrade;`,
`proxy_set_header Connection "upgrade";`, `proxy_read_timeout 86400;` — thiếu sẽ treo "Connecting…".
Chưa có tên miền: xem tạm bằng SSH tunnel `ssh -L 8506:127.0.0.1:8506 <user>@<ip-vps>` rồi mở http://localhost:8506.

Kiểm tra trên điện thoại: có nút « Chọn mã · Vĩ mô » góc trên trái; 5 tab hiện đủ, không kéo ngang cả trang; bảng
xếp hạng kéo ngang được, cột Mã đứng yên. (`streamlit==1.55.0` được ghim vì CSS điện thoại phụ thuộc bản này.)

## Xuất PDF/Word có biểu đồ (tuỳ chọn, một lần)

```bash
.venv/bin/kaleido_get_chrome                               # ảnh biểu đồ Plotly trong PDF/Word
.venv/bin/playwright install --with-deps chromium          # nút xuất PDF báo cáo
```

Thiếu thì app vẫn chạy; PDF/Word không kèm biểu đồ / nút PDF trả trang thay thế.

## Lưu ý

- `vnstock_data` là gói tài trợ vnstock, cài bằng bộ cài riêng của vnstock với `VNSTOCK_API_KEY`. Thiếu gói này báo
  cáo vẫn gửi nhưng giá có thể không cập nhật (setup sẽ cảnh báo).
- DeepSeek chỉ gọi khi bấm nút trên app — dịch vụ tự động không tốn phí AI. Nên đặt hạn mức chi tiêu thấp trên DeepSeek.
- `.env` giữ `DATABASE_URL_*=sqlite:///vn100_full.db` (đường dẫn tương đối) được — mọi dịch vụ chạy trong thư mục dự án.
- Lịch "Quét VN100" (xếp hạng) chỉ chạy ở MỘT nơi (Mac hoặc VPS) — chạy cả hai thì tốn API gấp đôi và hai DB lệch nhau.
- Dịch vụ cũ `vn100.service` (hướng dẫn trước 10/2026, cổng 8502 cũ) được `setup_vps.sh` tự tắt và thay bằng
  `vn100-streamlit.service`.
- Từ 24/10/2026 app chạy cổng 8506 (trước là 8502). VPS đã cài theo bản cũ: sửa `/etc/caddy/Caddyfile` thành
  `reverse_proxy 127.0.0.1:8506` rồi `sudo systemctl reload caddy` (`setup_vps.sh` sẽ cảnh báo nếu còn 8502).
- Không chép `.env` qua Zalo/email/GitHub; dùng `scp` hoặc gõ tay trên VPS. Lộ key → đổi key ngay (Discord Developer
  Portal, vnstock, DeepSeek).
