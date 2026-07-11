import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List
from valuation.ingest.pipeline import run_ingest
from valuation.output.discord_alerter import notify_discord

router = APIRouter(prefix="/ingest", tags=["Ingestion"])
logger = logging.getLogger(__name__)

class IngestRequest(BaseModel):
    ticker: str
    data_types: List[str] = ["prices", "financials"]
    channel_id: int | None = None  # Kênh Discord nơi user gõ lệnh (để báo cáo trả về đúng chỗ)


def _run_ingest_job(ticker: str, data_types: List[str], channel_id=None):
    try:
        run_ingest(ticker, data_types)
        notify_discord(
            embed_title=f"✅ Ingest hoàn tất: {ticker}",
            embed_desc=f"Đã cập nhật dữ liệu: {', '.join(data_types)}",
            color="00FF00",
            channel_id=channel_id,
        )
    except Exception as e:
        logger.error(f"Ingest failed for {ticker}: {e}")
        notify_discord(
            embed_title=f"❌ Ingest thất bại: {ticker}",
            embed_desc=f"Lỗi: {e}",
            color="FF0000",
            channel_id=channel_id,
        )


@router.post("/")
async def trigger_ingest(req: IngestRequest, background_tasks: BackgroundTasks):
    try:
        # Nếu muốn gọi đồng bộ thì bỏ background_tasks
        # nhưng ở đây nên chạy nền để không timeout nếu BCTC lớn
        background_tasks.add_task(_run_ingest_job, req.ticker, req.data_types, req.channel_id)
        return {"message": f"Ingestion triggered for {req.ticker}", "data_types": req.data_types}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
