import os
import re
import certifi
import discord
import httpx
import logging
from valuation.config import settings

# Đảm bảo chứng chỉ SSL sử dụng Certifi bundle để tránh lỗi trên macOS
os.environ["SSL_CERT_FILE"] = certifi.where()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Khởi tạo Discord client
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Đọc token và cấu hình từ Settings
DISCORD_TOKEN = settings.discord_bot_token or os.getenv("DISCORD_BOT_TOKEN")
FASTAPI_URL = "http://localhost:8000"
DEEPSEEK_API_KEY = settings.deepseek_api_key or os.getenv("DEEPSEEK_API_KEY")

# Chỉ định Channel ID kiểm thử
TARGET_CHANNEL_ID = 1504370094787133533

async def get_deepseek_insight(ticker: str, price: float, fv: float, upside: float, flags: list, greeks: dict) -> str:
    """Gọi DeepSeek API để lấy nhận định AI insight"""
    if not DEEPSEEK_API_KEY:
        return "⚠️ Không tìm thấy DEEPSEEK_API_KEY trong cấu hình. Không thể tạo AI Insight."
    
    prompt = (
        f"Bạn là chuyên gia phân tích tài chính cao cấp tại một quỹ đầu tư Việt Nam. "
        f"Hãy đưa ra nhận định chuyên sâu bằng Tiếng Việt (khoảng 3-4 câu, chuyên nghiệp, súc tích) "
        f"về cổ phiếu {ticker} dựa trên các thông số sau:\n"
        f"- Thị giá hiện tại: {price:,.0f} VND\n"
        f"- Giá trị hợp lý ước tính (Blended Fair Value): {fv:,.0f} VND\n"
        f"- Upside tiềm năng: {upside:.1f}%\n"
        f"- Cờ cảnh báo chất lượng dữ liệu/kiểm thử (QC Flags): {', '.join(flags) if flags else 'Không có'}\n"
        f"- Độ nhạy định giá (Greeks): {greeks}\n"
        f"Hãy chỉ rõ cơ hội đầu tư, biên an toàn và các rủi ro đáng chú ý."
    )
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 500
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client_http:
            response = await client_http.post(
                "https://api.deepseek.com/chat/completions",
                headers=headers,
                json=payload
            )
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
            else:
                logger.error(f"DeepSeek API error {response.status_code}: {response.text}")
                return f"⚠️ Lỗi khi gọi DeepSeek API (Mã lỗi: {response.status_code})."
    except Exception as e:
        logger.error(f"DeepSeek exception: {e}")
        return f"⚠️ Lỗi kết nối tới DeepSeek: {str(e)}"

@client.event
async def on_ready():
    logger.info(f"Bot đã đăng nhập thành công dưới tên: {client.user}")


def parse_ticker_from_message(content: str, bot_id: int) -> str:
    """Phân tích tin nhắn để trích xuất mã cổ phiếu bằng nhiều cú pháp khác nhau"""
    content_strip = content.strip()
    if not content_strip:
        return None

    # 1. Hỗ trợ tiền tố truyền thống !revalue <ticker>
    if content_strip.startswith("!revalue"):
        parts = content_strip.split()
        if len(parts) >= 2:
            return parts[1].upper().strip()

    # Danh sách các từ cần bỏ qua để tránh nhận diện nhầm khi chat
    ignored_words = {
        "cho", "toi", "con", "mua", "ban", "giu", "xem", "chay", "lenh", 
        "bot", "vua", "vao", "may", "chu", "dinh", "gia", "check", "ma", 
        "code", "link", "them", "xoa", "sua", "gium", "giup", "dep"
    }

    # 2. Hỗ trợ mention bot (ví dụ: @dinh gia chung khoan chạy fpt, @bot VCB...)
    mention_pattern = f"<@!?{bot_id}>"
    if re.search(mention_pattern, content_strip):
        clean = re.sub(mention_pattern, "", content_strip).lower().strip()
        # Tìm các từ có 3-4 chữ cái
        candidates = re.findall(r"\b[a-zA-Z]{3,4}\b", clean)
        for cand in candidates:
            if cand not in ignored_words:
                return cand.upper()

    # 3. Hỗ trợ từ khóa tiếng Việt/tiếng Anh (ví dụ: "định giá fpt", "dinh gia vcb", "check ctg")
    content_lower = content_strip.lower()
    keywords = ["định giá", "dinh gia", "revalue", "check", "định giá mã", "dinh gia ma"]
    for kw in keywords:
        if kw in content_lower:
            # Ưu tiên tìm từ đứng ngay sau từ khóa
            match = re.search(rf"{kw}\s+(\b[a-zA-Z]{3,4}\b)", content_lower)
            if match:
                return match.group(1).upper()
            
            # Nếu không tìm thấy ngay sau, quét toàn bộ tin nhắn loại trừ các từ bỏ qua
            candidates = re.findall(r"\b[a-zA-Z]{3,4}\b", content_lower)
            for cand in candidates:
                if cand not in ignored_words:
                    return cand.upper()

    # 4. Hỗ trợ gõ trực tiếp mã cổ phiếu (ví dụ: gõ "FPT" hoặc "fpt" hoặc "VCB" trong kênh)
    # Chỉ áp dụng nếu tin nhắn chỉ chứa duy nhất 1 từ dài từ 3 đến 4 chữ cái và không nằm trong từ bỏ qua
    if re.match(r"^[a-zA-Z]{3,4}$", content_strip):
        cand = content_strip.lower()
        if cand not in ignored_words:
            return cand.upper()

    return None

@client.event
async def on_message(message):
    # Tránh trường hợp bot tự trả lời chính mình
    if message.author == client.user:
        return

    # Phân tích xem tin nhắn có chứa mã cổ phiếu yêu cầu định giá không
    ticker = parse_ticker_from_message(message.content, client.user.id)
    if not ticker:
        return
        
    temp_msg = await message.channel.send(f"⏳ Đang thực hiện định giá và phân tích AI cho cổ phiếu **{ticker}**...")
    
    try:
        # Gọi FastAPI Endpoint để định giá
        api_endpoint = f"{FASTAPI_URL}/revalue/valuation/revalue/{ticker}"
        async with httpx.AsyncClient(timeout=30.0) as client_http:
            response = await client_http.post(api_endpoint)
            
        if response.status_code != 200:
            await temp_msg.delete()
            await message.channel.send(f"❌ Lỗi khi định giá {ticker} từ hệ thống (Mã lỗi API: {response.status_code})")
            return
            
        res = response.json()
        curr_price = res.get("current_price", 0.0)
        valuation_data = res.get("valuation", {})
        blended_fv = valuation_data.get("blended_fair_value_per_share", 0.0)
        greeks = res.get("greeks", {})
        qc_data = res.get("qc", {})
        qc_flags = qc_data.get("flags", [])
        
        # Tính upside
        upside = 0.0
        if curr_price > 0:
            upside = ((blended_fv - curr_price) / curr_price) * 100
            
        # Gọi DeepSeek lấy insight
        ai_insight = await get_deepseek_insight(ticker, curr_price, blended_fv, upside, qc_flags, greeks)
        
        # Tạo Discord Embed
        color = 0x00FF00 if upside > 0 else 0xFF0000
        embed = discord.Embed(
            title=f"📊 Báo cáo định giá chi tiết: {ticker}",
            description=f"Thời gian định giá: {os.popen('date').read().strip()}",
            color=color
        )
        
        embed.add_field(name="💵 Thị giá hiện tại", value=f"{curr_price:,.0f} VND", inline=True)
        embed.add_field(name="🎯 Định giá Hợp lý (Blended FV)", value=f"{blended_fv:,.0f} VND", inline=True)
        embed.add_field(name="📈 Upside tiềm năng", value=f"{upside:+.1f}%", inline=True)
        
        # QC Flags
        flags_str = ", ".join([f"`{f}`" for f in qc_flags]) if qc_flags else "✅ Sạch (Không có cảnh báo)"
        embed.add_field(name="🚨 Cảnh báo chất lượng (QC Flags)", value=flags_str, inline=False)
        
        # Sensitivities (Greeks)
        greeks_str = ""
        for k, v in greeks.items():
            if v is not None:
                greeks_str += f"- **dFV/d({k})**: `{v:+.4f}`\n"
        if not greeks_str:
            greeks_str = "Không có độ nhạy"
        embed.add_field(name="📊 Độ nhạy Định giá (Greeks)", value=greeks_str, inline=False)
        
        # AI Insight
        embed.add_field(name="💡 AI Insight (DeepSeek-Chat)", value=ai_insight, inline=False)
        
        embed.set_footer(text="Hệ thống định giá tự động VN100 | Quỹ đầu tư AI")
        
        await temp_msg.delete()
        await message.channel.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error processing command for {ticker}: {e}")
        await temp_msg.delete()
        await message.channel.send(f"❌ Có lỗi xảy ra trong quá trình xử lý lệnh: {str(e)}")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        logger.error("Vui lòng cấu hình DISCORD_BOT_TOKEN trong file .env hoặc biến môi trường.")
    else:
        client.run(DISCORD_TOKEN)
