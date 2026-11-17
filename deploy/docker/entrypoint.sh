#!/bin/sh
# 1) DB song trong volume /data (khong mat khi deploy).
# 2) DONG BO DU LIEU TU REPO: khi vn100_full.db.gz trong repo doi (Mac day du lieu moi len GitHub),
#    giai nen lai, giu 3 ban sao luu DB cu. Tat bang DB_SYNC_FROM_REPO=0 (khi VPS tu cap nhat du lieu).
#    Tu 18/11/2026 VPS la ban chinh -> compose dat DB_SYNC_FROM_REPO=0 (chi giai nen khi /data chua co DB).
# 3) Co tham so -> chay lenh do (vn100-worker: lich job, vn100-bot: bot Discord); khong co -> giao dien Streamlit.
set -e
GZ=/app/vn100_full.db.gz; DB=/data/vn100_full.db; MARK=/data/.db_gz_sha256
NEW=$(sha256sum "$GZ" | cut -d' ' -f1)
if [ ! -s "$DB" ] || { [ "${DB_SYNC_FROM_REPO:-1}" = 1 ] && [ "$(cat "$MARK" 2>/dev/null)" != "$NEW" ]; }; then
  if [ -s "$DB" ]; then
    cp "$DB" "/data/backup-$(date +%Y%m%d-%H%M%S).db"
    ls -1t /data/backup-*.db 2>/dev/null | tail -n +4 | xargs -r rm -f
  fi
  echo "Giai nen $GZ -> $DB (sha ${NEW%"${NEW#????????????}"})"
  python - <<'PY'
import gzip, os, shutil, sqlite3
src, tmp, dst = "/app/vn100_full.db.gz", "/data/vn100_full.db.tmp", "/data/vn100_full.db"
with gzip.open(src, "rb") as s, open(tmp, "wb") as t:
    shutil.copyfileobj(s, t)
ok = sqlite3.connect(tmp).execute("PRAGMA integrity_check").fetchone()[0]
assert ok == "ok", ok
os.replace(tmp, dst)
PY
  echo "$NEW" > "$MARK"
fi
export DATABASE_URL_READONLY="sqlite:///$DB" DATABASE_URL_WRITE="sqlite:///$DB"
if [ "$#" -gt 0 ]; then
  exec "$@"
fi
exec python -m streamlit run streamlit_app.py \
  --server.address 0.0.0.0 --server.port 8506 --server.headless true \
  --server.fileWatcherType none --browser.gatherUsageStats false
