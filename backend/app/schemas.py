from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class KpiResponse(BaseModel):
    in_progress: int = 0
    total_incidents: int = 0
    pending_approval: int = 0
    fix_failed: int = 0
    auto_fixed: int = 0
    failed_messages: int = 0
    auto_fix_rate: float = 0.0
    avg_resolution_minutes: float = 0.0
    rca_coverage: float = 0.0


class ScenarioItem(BaseModel):
    id: str
    name: str
    status: str
    time: str
    icon: str = "activity"


class ProcessGroupResponse(BaseModel):
    id: str
    name: str
    route: str
    status: str
    error_count: int
    warning_count: int
    scenarios: List[ScenarioItem]


class FlowStep(BaseModel):
    label: str
    step: str
    status: str


class TimelineEvent(BaseModel):
    status: str
    event: str
    description: str
    time: str


class ErrorDetail(BaseModel):
    heading: str
    code: str


class LogDetailResponse(BaseModel):
    id: str
    title: str
    process: str
    status: str
    incident_id: str
    time: str
    source: str
    destination: str
    flow: List[FlowStep]
    timeline: List[TimelineEvent]
    error: Optional[ErrorDetail] = None
    recommendations: List[str]


class IngestionStatusResponse(BaseModel):
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_fetched: int = 0
    total_classified: int = 0
    error: Optional[str] = None
