#!/usr/bin/env bash
# Cài VN100 lên VPS Linux (systemd) — chạy lại bao nhiêu lần cũng được (idempotent).
#   bash deploy/setup_vps.sh            # cài/cập nhật môi trường + dịch vụ
#   bash deploy/setup_vps.sh --no-app   # không chạy app Streamlit (chỉ báo cáo + bot)
# Cần: Python >= 3.11, sudo (để cài dịch vụ systemd), file .env đã chép tay vào thư mục dự án.
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_USER="${SUDO_USER:-$(id -un)}"
WITH_APP=1
[[ "${1:-}" == "--no-app" ]] && WITH_APP=0
cd "$APP_DIR"

say() { printf '\n==> %s\n' "$*"; }
die() { printf '\n[LỖI] %s\n' "$*" >&2; exit 1; }

say "Thư mục dự án: $APP_DIR (chạy dịch vụ bằng user: $RUN_USER)"

# 1. Python >= 3.11
PY=""
for c in python3.13 python3.12 python3.11 python3; do
  if command -v "$c" >/dev/null && "$c" -c 'import sys; sys.exit(sys.version_info < (3, 11))'; then PY="$c"; break; fi
done
[[ -n "$PY" ]] || die "Cần Python >= 3.11 (Ubuntu 22.04: sudo add-apt-repository ppa:deadsnakes/ppa && sudo apt install python3.12 python3.12-venv)."
say "Dùng $($PY --version)"

# 2. .env — KHÔNG có trên GitHub, phải chép tay (xem docs/DEPLOY_VPS.md)
[[ -f .env ]] || die "Chưa có file .env. Chép từ máy chủ dự án: scp .env <user>@<vps>:$APP_DIR/.env"
chmod 600 .env
missing=()
for k in DISCORD_BOT_TOKEN DISCORD_CHANNEL_ID DISCORD_WEBHOOK_URL; do
  grep -Eq "^${k}=.+" .env || missing+=("$k")
done
[[ ${#missing[@]} -eq 0 ]] || die "File .env thiếu giá trị: ${missing[*]}"
gsa="$(grep -E '^GOOGLE_SERVICE_ACCOUNT_JSON=' .env | tail -1 | cut -d= -f2- || true)"
if [[ -n "$gsa" && "$gsa" == *.json && ! -f "$gsa" ]]; then
  echo "[CẢNH BÁO] GOOGLE_SERVICE_ACCOUNT_JSON trỏ tới '$gsa' (đường dẫn máy Mac?) — chỉ cần nếu dùng Google Sheets/Drive."
fi

# 3. Môi trường Python riêng trong dự án
say "Cài thư viện vào $APP_DIR/.venv"
[[ -x .venv/bin/python ]] || "$PY" -m venv .venv
.venv/bin/pip install -q -U pip
# vnstock_data là gói tài trợ vnstock (cài bằng bộ cài riêng của vnstock) — tách ra để không làm hỏng cả bước cài.
grep -v '^vnstock_data' requirements.txt > /tmp/vn100_requirements.txt
# vnstock/vnai/vnii 4.x lấy từ index của vnstocks.com (bản PyPI có thể khác); --extra-index-url để các gói khác vẫn từ PyPI
.venv/bin/pip install -q --extra-index-url https://vnstocks.com/api/simple -r /tmp/vn100_requirements.txt
if ! .venv/bin/pip install -q "$(grep '^vnstock_data' requirements.txt | cut -d' ' -f1)" 2>/dev/null; then
  echo "[CẢNH BÁO] Chưa cài được vnstock_data (gói tài trợ). Báo cáo vẫn gửi nhưng giá có thể không cập nhật."
  echo "           Cài theo hướng dẫn gói tài trợ vnstock với VNSTOCK_API_KEY trong .env."
fi

# 4. Dữ liệu: giải nén DB nếu chưa có (DB đang chạy trên VPS được GIỮ NGUYÊN khi cập nhật code)
mkdir -p logs backups
.venv/bin/python scripts/ensure_portable_db.py

# 5. Chạy thử báo cáo sáng (không gửi Discord, không cập nhật giá)
say "Chạy thử báo cáo (dry-run)"
.venv/bin/python scripts/daily_report.py --dry-run --no-refresh >/dev/null || die "Báo cáo chạy thử lỗi — xem thông báo phía trên."

# 6. Dịch vụ systemd
say "Cài dịch vụ systemd"
# Bảng flow_daily (D73): migrate tự backup DB, chạy lại không làm gì.
.venv/bin/python scripts/migrate_flow_daily.py --apply || die "Tạo bảng flow_daily lỗi — xem thông báo phía trên."
units=(vn100-discord-bot.service vn100-daily-report.service vn100-daily-report.timer vn100-flow-daily.service vn100-flow-daily.timer vn100-weekly-digest.service vn100-weekly-digest.timer)
[[ $WITH_APP -eq 1 ]] && units+=(vn100-streamlit.service)
for u in "${units[@]}"; do
  sed -e "s#__APP_DIR__#$APP_DIR#g" -e "s#__USER__#$RUN_USER#g" "deploy/systemd/$u" | sudo tee "/etc/systemd/system/$u" >/dev/null
done
sudo systemctl daemon-reload
sudo systemctl enable --now vn100-daily-report.timer
sudo systemctl enable --now vn100-flow-daily.timer
sudo systemctl enable --now vn100-weekly-digest.timer
sudo systemctl enable vn100-discord-bot.service && sudo systemctl restart vn100-discord-bot.service
if [[ $WITH_APP -eq 1 ]]; then
  # Hướng dẫn cũ (trước 10/2026) đặt app là vn100.service ở cổng 8502 → tắt để không chạy 2 bản app.
  if systemctl list-unit-files vn100.service >/dev/null 2>&1 && [[ -f /etc/systemd/system/vn100.service ]]; then
    echo "Tắt dịch vụ cũ vn100.service (cổng 8502, thay bằng vn100-streamlit.service cổng 8506)."
    sudo systemctl disable --now vn100.service || true
  fi
  sudo systemctl enable vn100-streamlit.service && sudo systemctl restart vn100-streamlit.service
  grep -qs "127.0.0.1:8502" /etc/caddy/Caddyfile && echo "⚠️  /etc/caddy/Caddyfile còn trỏ 127.0.0.1:8502 — app đã chuyển sang 8506: sửa rồi chạy sudo systemctl reload caddy."
fi

say "Xong. Trạng thái:"
systemctl --no-pager --lines=0 status vn100-discord-bot.service | head -3 || true
systemctl list-timers --no-pager vn100-daily-report.timer vn100-flow-daily.timer vn100-weekly-digest.timer | head -5 || true
echo "Log: $APP_DIR/logs/  |  Cập nhật code về sau: bash deploy/update_vps.sh"
