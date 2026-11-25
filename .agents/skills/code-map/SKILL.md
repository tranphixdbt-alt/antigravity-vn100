---
name: code-map
description: Bản đồ code của antigravity-vn100 — package nào làm gì, file config nào điều khiển gì, và "muốn sửa X thì mở file Y". Đọc ĐẦU TIÊN khi nhận việc code trong repo này (model định giá, ingest, tab Streamlit, báo cáo, ranking, dòng tiền, Discord, lịch chạy), để mở đúng file thay vì grep cả repo. Lệnh chạy, luồng dữ liệu, lỗi đã gặp: docs/AGENT_OPERATING_MANUAL.md và .agents/AGENT_HANDOFF.md.
---

# Bản đồ code — antigravity-vn100

Bản chạy thật: **`~/antigravity-vn100`** (từ 26/10/2026; bản trên Google Drive chỉ là bản sao cho người khác, đừng sửa/chạy ở đó).
Thứ tự đọc, lệnh chạy, luồng dữ liệu: `.agents/AGENT_HANDOFF.md` → `docs/AGENT_OPERATING_MANUAL.md`. Quyết định: `DECISIONS.md` (D/C/B, tới D82).
Bản đồ viết 26/10/2026; thấy lệch với code thì tin code và sửa lại bản đồ.

## Lõi định giá (một đường cho UI, batch, Excel)
`data_access/repo.build_company_data` → `engine/valuate.valuate`:
ngân hàng `forecast_bank` → `sensitivity.run_valuation_engine` (`models/bank_general.py`) → `blend`;
phi tài chính `batch._dispatch_nonfin` → `engine/models/<model>.py` (dcf, ev_ebitda, pe/pb_relative, rnav, sotp, securities, insurance,
`broker_synth.py` = mô hình tổng hợp CTCK D68/D71); rồi cờ, `decision_engine` (MOS, NOT_RATED), cổng công bố (`config/valuation_reviews.yaml`).
`calibration/` chỉ đo lệch vs CTCK — engine cấm import (D33).

## Package (`valuation/`)
| Thư mục | Làm gì |
|---|---|
| `ingest/` | Lấy và ghi dữ liệu: `pipeline.py` (upsert), `vnstock_client.py`, `flow_client.py` (dòng tiền), `corporate_actions*.py`, `sponsor_data.py`, `universe.py`, `taxonomy.py`, `macro*.py`, `fred_fetcher.py`, `scrapers/` |
| `data_access/` | DB → object: `repo.py`, `investment_snapshot.py`, `corporate_actions.py`, `freshness*.py`, `units.py` |
| `engine/` | Định giá: `valuate.py`, `batch.py`, `decision_engine.py`, `sector_router.py`, `coe.py`, `wacc.py`, `ttm_helper.py`, `sensitivity.py`, `guardrails.py`, `flag_descriptions.py`, `weighted_stats.py`, `models/` |
| `analysis/` | `investment_ranking.py` (VN100 hai chiến lược), `money_flow.py`, `steel_cycle.py`, `macro_radar.py`, `technical_chart.py` |
| `services/` | Việc chạy nền: `daily_report.py`, `investment_job.py`, `data_update_job.py`, `learning_digest.py`, `learning_inbox.py`, `assistant.py`, `ranking_*.py` |
| `views/` | Tab Streamlit: `select_ticker`, `results`, `consensus_compare`, `vn100_ranking`, `money_flow`, `market_overview`, `macro_panel`, `corporate_actions`, `theme` … |
| `report/` | Báo cáo: `report_data.py` (số), `template.html`, `build_pdf.py`, `build_docx.py`, `verified_summary.py`, `ai_journal.py` |
| `calibration/`, `quality/`, `output/`, `api/`, `db/` | Hiệu chuẩn CTCK; điểm QC; Discord/Drive/Sheets; FastAPI; schema + session |

Config chính (`config/`): `defaults.yaml`, `scenarios.yaml`, `valuation_reviews.yaml`, `calibration_registry.yaml`, `investment_ranking.yaml`,
`sotp_holdings.yaml`, `broker_synth/<MÃ>.yaml`, `corporate_actions.yaml`, `event_holds.yaml`, `analyst_notes.yaml`; routing mã → phương pháp:
`valuation/config/routing.json`. Dữ liệu tích lũy: `knowledge/`, `data/`, `reports/`, `logs/`.

## Chạy tự động (launchd, `~/Library/LaunchAgents/vn.antigravity-vn100.*.plist`, `~/.venv/bin/python`, thư mục làm việc = `~/antigravity-vn100`; không đặt dự án trong ~/Desktop: macOS chặn launchd đọc Desktop)
`discord-bot` (`scripts/discord_bot.py`), `daily-report` (`scripts/daily_report.py`), `flow-daily` (`scripts/update_flow_daily.py`, 18:00 T2–T6),
`weekly-digest` (`scripts/weekly_learning_digest.py`). App: `sh scripts/run_app.sh` (cổng 8506; tự tắt mọi Streamlit VN100 khác trước khi chạy).

## Muốn sửa X thì mở đâu
| Việc | Mở |
|---|---|
| Mô hình của một ngành/mã | `routing.json` → `engine/models/<model>.py` → `batch._dispatch_nonfin` (ngân hàng: `sensitivity.run_valuation_engine`) |
| Giả định đầu vào (ROE, biên, capex, thuế, bội số) | `data_access/repo.py` + `config/defaults.yaml` |
| Có công bố giá mục tiêu hay không | `config/valuation_reviews.yaml`, `engine/valuate.py` |
| Ranking VN100 / tích sản | `analysis/investment_ranking.py`, `config/investment_ranking.yaml`, `scripts/update_vn100_ranking.py` |
| Dòng tiền ngành | `ingest/flow_client.py`, `analysis/money_flow.py`, `views/money_flow.py` |
| Báo cáo sáng / Discord | `services/daily_report.py`, `scripts/discord_bot.py` |
| Cờ cảnh báo mới | nơi sinh cờ + mô tả ở `engine/flag_descriptions.py` |
| Web hợp nhất `btinvest.vn` (FastAPI + HTML viết tay, chạy thật trên VPS) | `api/web_main.py` (số liệu, chỉ GET), `api/web_user_routes.py` + `api/web_deps.py` (tài khoản, danh mục, mức giá), `services/web_*.py` (góc chat `web_chat*.py` dùng chung `services/assistant.py` với bot Discord), `db/web_user.py` (tệp `web_user.db` riêng), `web/` (giao diện), `tests/test_web_*.py`; kế hoạch và trạng thái: `docs/PLAN_WEB_HOP_NHAT.md`; vận hành: `docs/AGENT_OPERATING_MANUAL.md` mục 15 |

Bẫy dữ liệu và luật định giá: skill `financial-data-integrity`, `valuation-models`; luật chung: `vn-finance-data`, `vn-valuation-rules`.
