from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List
from valuation.ingest.pipeline import run_ingest

router = APIRouter(prefix="/ingest", tags=["Ingestion"])

class IngestRequest(BaseModel):
    ticker: str
    data_types: List[str] = ["prices", "financials"]

@router.post("/")
async def trigger_ingest(req: IngestRequest, background_tasks: BackgroundTasks):
    try:
        # Nếu muốn gọi đồng bộ thì bỏ background_tasks
        # nhưng ở đây nên chạy nền để không timeout nếu BCTC lớn
        background_tasks.add_task(run_ingest, req.ticker, req.data_types)
        return {"message": f"Ingestion triggered for {req.ticker}", "data_types": req.data_types}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
