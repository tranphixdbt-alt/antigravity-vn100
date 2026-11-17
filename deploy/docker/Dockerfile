# VN100 (Streamlit + job + bot) — file trien khai nam NGOAI repo (repo o ./app, tu cap nhat tu GitHub)
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 TZ=Asia/Ho_Chi_Minh
RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
 && rm -rf /var/lib/apt/lists/* \
 && useradd -m -u 10001 app && mkdir -p /data && chown app:app /data
WORKDIR /app
# Thu vien cua repo (bo dong vnstock 4.x: index cu da go, cai tu vendor/ ben duoi).
COPY app/requirements.txt /tmp/requirements.txt
RUN grep -vE '^(vnstock|vnai|vnii|vnstock_data)\b' /tmp/requirements.txt > /tmp/req.txt \
 && pip install -q -r /tmp/req.txt
# vnstock the he 4 BAN MIEN PHI (gia/BCTC tu VCI) chep tu may Mac ~/.venv (Python thuan; index cu da go 10/11/2026).
# Khong co vnstock_data (goi tai tro the he 4 da bi khoa) -> job dong tien cho FHSC (PLAN_VNSTOCK_V6 S2).
COPY vendor/gen4/ /usr/local/lib/python3.12/site-packages/
RUN pip install -q beautifulsoup4 importlib-metadata openpyxl packaging psutil pydantic pytz requests seaborn \
      tenacity cffi cryptography matplotlib mplfinance cycler \
 && python -c "import vnstock, vnai, vnii; print('vnstock', vnstock.__version__ if hasattr(vnstock,'__version__') else 'ok')"
# vnstock the he 6 cho FHSC: moi truong rieng giong ~/.venv_6x tren Mac (config fhsc.python = ~/.venv_6x/bin/python).
RUN python -m venv /home/app/.venv_6x \
 && /home/app/.venv_6x/bin/pip install -q --extra-index-url https://vnstocks.com/api/packages \
      vnstock==6.0.0 vnstock-oapi==0.1.1 \
 && chown -R app:app /home/app/.venv_6x
COPY --chown=app:app app/ /app/
# App goi ensure_portable_db() voi duong dan co dinh <repo>/vn100_full.db -> tro sang volume /data
RUN chown app:app /app && mkdir -p /app/logs && chown app:app /app/logs \
 && mkdir -p /home/app/.vnstock && chown app:app /home/app/.vnstock \
 && mkdir -p /app/.vn100_ranking /app/.daily_report /app/.data_update /app/.disclosures /app/.assistant /app/.flow_update /app/.deepseek_report_cache && chown app:app /app/.vn100_ranking /app/.daily_report /app/.data_update /app/.disclosures /app/.assistant /app/.flow_update /app/.deepseek_report_cache \
 && ln -sf /data/vn100_full.db /app/vn100_full.db
# patches/vps_hotfix.py (import vnstock luoi) KHONG con can: vnstock da duoc cai o tren.
COPY scheduler.py /opt/vn100/scheduler.py
COPY entrypoint.sh /entrypoint.sh
USER app
EXPOSE 8506
ENTRYPOINT ["/entrypoint.sh"]
