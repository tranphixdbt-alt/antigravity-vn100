# Chứng quyền (cw_scanner, web http.server + 4 lịch) — file triển khai NẰM NGOÀI repo; repo ở ./app (git clone
# github.com/ngo-tuankiet/chung_quyen, tự cập nhật). Code chạy từ ./app gắn vào /app vì dữ liệu người dùng (danh_muc.csv,
# cw_da_biet.txt, ket_qua/, .env) nằm cạnh code (THU_MUC = thư mục cw_scanner.py) và đều trong .gitignore -> deploy
# (git reset --hard) không xóa. Image chỉ chứa thư viện.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 TZ=Asia/Ho_Chi_Minh
RUN apt-get update && apt-get install -y --no-install-recommends tzdata rsync \
 && rm -rf /var/lib/apt/lists/* \
 && useradd -m -u 1000 app
# uid 1000 = ubuntu trên VPS: container ghi được dữ liệu vào ./app, deploy (ubuntu) vẫn git reset được
COPY app/requirements.txt app/requirements-dev.txt /tmp/
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install -q --extra-index-url https://vnstocks.com/api/packages \
      -r /tmp/requirements.txt -r /tmp/requirements-dev.txt certifi
# Dấu vân tay code: commit mới -> image mới -> deploy tạo lại container (code ở ./app không tự nạp lại khi đang chạy).
# Chỉ chép code (.dockerignore loại .env, dữ liệu người dùng).
COPY app/ /tmp/code/
RUN rm -rf /tmp/code
COPY scheduler.py /opt/cw/scheduler.py
# Điểm gắn volume phải có sẵn và thuộc app: volume mới chép quyền từ đây (thiếu -> root, vnstock/sao lưu không ghi được)
RUN mkdir -p /home/app/.vnstock /home/app/cw_scanner_sao_luu && chown app:app /home/app/.vnstock /home/app/cw_scanner_sao_luu
USER app
WORKDIR /app
EXPOSE 8000
