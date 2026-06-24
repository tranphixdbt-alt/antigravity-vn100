# VN100 Valuation System — gói hướng dẫn cho Antigravity

## Cách đặt vào dự án
1. Đặt toàn bộ nội dung này ở **gốc repo**.
2. `AGENTS.md` (gốc repo) — luật nền, Antigravity đọc tự động (cần Antigravity v1.20.3+).
3. `.agents/skills/*/SKILL.md` — các skill nạp theo nhu cầu (khớp theo trường `description`).
4. `docs/spec.md` — đặc tả kiến trúc, được `AGENTS.md` tham chiếu qua `@docs/spec.md`.
5. Sao chép `.env.example` → `.env` và điền secret thật. **Không commit `.env`.**

## Cách khởi động agent (gợi ý prompt)
- Bắt đầu bằng: `/grill-me` + "Đọc @AGENTS.md và @docs/spec.md. Lập kế hoạch Giai đoạn 0 (hạ tầng) rồi hỏi lại tôi trước khi code."
- Làm theo lộ trình trong `docs/spec.md` mục 13 (Giai đoạn 0 → 6), mỗi giai đoạn một plan riêng.
- Với việc lớn (schema, tích hợp Google/Discord/n8n): yêu cầu agent dừng xin duyệt.

## Thứ tự ưu tiên rule (Antigravity)
AGENTS.md → GEMINI.md → mặc định. File này dùng AGENTS.md cho tính di động (Antigravity/Cursor/Claude Code đều đọc được).

## Nhắc quan trọng
- Mỗi file rule giới hạn 12.000 ký tự.
- Skill chỉ được nạp khi request khớp `description` — giữ description theo công thức: điều kiện kích hoạt + hành động + kết quả.
