from fastapi import APIRouter, HTTPException
from app.schemas import LogDetailResponse
from app.services import hana_service

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("/{log_id}/detail", response_model=LogDetailResponse)
def get_log_detail(log_id: str):
    detail = hana_service.get_log_detail(log_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Log not found")
    return detail
