import os
import time
import hashlib
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Bản tin vĩ mô được lưu ra file kèm timestamp để tồn tại QUA CÁC LẦN RESTART app
# (st.cache_data chỉ nằm trong RAM, mất khi restart → tốn token gọi lại AI mỗi lần).
_MACRO_CACHE_FILE = Path(__file__).resolve().parents[2] / ".macro_bulletin_cache.json"


def get_macro_bulletin_cached(force: bool = False) -> str:
    """Đọc thường không gọi mạng/AI; chỉ nút làm mới kiểm tra tin thay đổi."""
    now = time.time()
    data = {}
    if _MACRO_CACHE_FILE.exists():
        try:
            data = json.loads(_MACRO_CACHE_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"Không đọc được cache bản tin vĩ mô: {e}")

    if not force:
        return data.get("text") or "Chưa có bản tin vĩ mô được lưu."

    news_text = fetch_rss_news()
    if not news_text:
        if data.get("text"):
            return data["text"]
        return "⚠️ Không thể lấy được bản tin Vĩ mô lúc này. Vui lòng thử lại sau."
    source_hash = hashlib.sha256(news_text.encode("utf-8")).hexdigest()
    if data.get("text") and data.get("source_hash") == source_hash:
        data["checked_at"] = now
        try:
            _MACRO_CACHE_FILE.write_text(
                json.dumps(data, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as e:
            logger.warning(f"Không gia hạn được cache bản tin vĩ mô: {e}")
        return data["text"]

    text = generate_macro_bulletin(news_text=news_text)

    # Chỉ lưu khi tạo thành công (không lưu thông báo lỗi để lần sau còn thử lại)
    if text and not text.startswith("⚠️"):
        try:
            _MACRO_CACHE_FILE.write_text(
                json.dumps(
                    {"ts": now, "text": text, "source_hash": source_hash},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning(f"Không ghi được cache bản tin vĩ mô: {e}")
    return text


def get_macro_cache_age_hours() -> float | None:
    """Tuổi (giờ) của bản tin đang lưu; None nếu chưa có."""
    if not _MACRO_CACHE_FILE.exists():
        return None
    try:
        data = json.loads(_MACRO_CACHE_FILE.read_text(encoding="utf-8"))
        return (time.time() - float(data.get("ts", 0))) / 3600.0
    except Exception:
        return None

def fetch_rss_news():
    urls = [
        "https://cafef.vn/vi-mo-dau-tu.rss",
        "https://cafef.vn/tai-chinh-quoc-te.rss"
    ]
    news_items = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    for url in urls:
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, "xml")
                items = soup.find_all("item")
                # Lấy 10 tin mới nhất mỗi nguồn
                for item in items[:10]:
                    title = item.find("title").text if item.find("title") else ""
                    description = item.find("description").text if item.find("description") else ""
                    
                    # Clean CDATA and HTML from description if any
                    desc_soup = BeautifulSoup(description, "html.parser")
                    clean_desc = desc_soup.get_text(separator=" ").strip()
                    
                    if title:
                        news_items.append(f"Tiêu đề: {title}\nNội dung tóm tắt: {clean_desc}")
        except Exception as e:
            logger.error(f"Error fetching RSS {url}: {e}")
            
    return "\n\n".join(news_items)

def get_openai_client() -> OpenAI | None:
    """Trả client AI; None nếu chưa cấu hình API key.

    Trả None thay vì để OpenAI(api_key=None) ném OpenAIError: bản tin vĩ mô chỉ là
    tính năng phụ, thiếu key thì tắt riêng nó, KHÔNG được kéo sập cả app định giá.
    """
    from valuation.config import settings
    api_key = settings.deepseek_api_key or os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY") # fallback
    if not api_key:
        return None
    if api_key.startswith("sk-"):
        # if using deepseek
        return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    return OpenAI(api_key=api_key)

def generate_macro_bulletin(news_text: str | None = None) -> str:
    # Kiểm tra key TRƯỚC khi tải RSS để khỏi tốn request mạng vô ích.
    client = get_openai_client()
    if client is None:
        return (
            "⚠️ Chưa cấu hình API key cho AI (`DEEPSEEK_API_KEY` hoặc `OPENAI_API_KEY` "
            "trong `.env`). Bản tin vĩ mô tạm nghỉ — các chức năng định giá khác vẫn "
            "chạy bình thường."
        )

    news_text = news_text or fetch_rss_news()
    if not news_text:
        return "⚠️ Không thể lấy được bản tin Vĩ mô lúc này. Vui lòng thử lại sau."

    prompt = f"""Bạn là một chuyên gia kinh tế vĩ mô và chiến lược gia thị trường chứng khoán.
Dưới đây là các tin tức vĩ mô mới nhất được tổng hợp từ báo chí trong 24h qua:

{news_text}

Nhiệm vụ của bạn:
Viết 1 BẢNG TIN VĨ MÔ & NHẬN ĐỊNH THỊ TRƯỜNG siêu ngắn gọn, súc tích (đọc lướt trong 30 giây), format bằng Markdown.
Bắt buộc gồm đúng 4 phần sau (KHÔNG dùng Markdown cho thẻ H3, chỉ dùng in đậm cho tiêu đề):

**🇻🇳 VĨ MÔ VIỆT NAM**
- (2-3 gạch đầu dòng về các sự kiện/chỉ số quan trọng nhất trong nước)

**🌍 VĨ MÔ THẾ GIỚI**
- (1-2 gạch đầu dòng về chính sách FED, tỷ giá, hàng hóa hoặc sự kiện quốc tế quan trọng)

**💡 NHẬN ĐỊNH THỊ TRƯỜNG**
- (1-2 câu chốt: Dòng tiền có thể phản ứng thế nào? Tốt hay xấu cho VN-Index hoặc nhóm ngành nào?)

**🎲 PHÂN TÍCH DÒNG TIỀN VN-INDEX (LÝ THUYẾT TRÒ CHƠI & NHÀ CÁI)**
- (Đúng 5 dòng phân tích trực diện, súc tích về hành vi dòng tiền, ý đồ của nhà cái (market maker) và sự giằng co tâm lý đám đông theo lý thuyết trò chơi).

LƯU Ý: Không được bịa đặt thông tin, chỉ lấy từ nội dung được cung cấp ở trên và suy luận logic. Viết thẳng vào vấn đề, không nói dài dòng.
"""

    try:
        response = client.chat.completions.create(
            # "deepseek-chat" (không phải "deepseek-v4-flash" — model suy luận,
            # tốn token "suy nghĩ" ngẫu nhiên, đôi khi cắt cụt nội dung trước khi
            # kịp trả lời; xem valuation/analysis/ai_insight.py).
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a top-tier macroeconomic analyst."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Lỗi AI macro_news: {e}")
        return f"⚠️ Lỗi khi gọi AI tổng hợp tin tức: {e}"
