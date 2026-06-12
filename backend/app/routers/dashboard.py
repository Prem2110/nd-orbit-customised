from fastapi import APIRouter, HTTPException
from app.schemas import KpiResponse, ProcessGroupResponse
from app.services import hana_service

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/kpis", response_model=KpiResponse)
def get_kpis():
    try:
        return hana_service.get_kpis()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/process-health", response_model=list[ProcessGroupResponse])
def get_process_health():
    try:
        return hana_service.get_process_health()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
