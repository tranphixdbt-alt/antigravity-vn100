#!/usr/bin/env bash
# Cập nhật VN100 trên VPS sau khi có code mới trên GitHub.
#   bash deploy/update_vps.sh             # kéo code + cài lại thư viện/dịch vụ, GIỮ DB đang chạy
#   bash deploy/update_vps.sh --reset-db  # như trên + thay DB bằng vn100_full.db.gz mới trong repo
#                                         #   (sao lưu DB cũ vào backups/ trước)
set -euo pipefail
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"

git pull --ff-only

if [[ "${1:-}" == "--reset-db" && -f vn100_full.db ]]; then
  mkdir -p backups
  sudo systemctl stop vn100-discord-bot.service vn100-streamlit.service 2>/dev/null || true
  bak="backups/vn100_full.$(date +%Y%m%d_%H%M%S).db"
  mv vn100_full.db "$bak"
  echo "Đã sao lưu DB cũ: $bak — sẽ giải nén DB mới từ repo."
fi

# Cài đặt idempotent: thư viện mới, dịch vụ mới (nếu có), khởi động lại bot/app.
bash deploy/setup_vps.sh "$@"
