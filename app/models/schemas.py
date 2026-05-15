from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DataSourceInput(BaseModel):
    name: str
    last_synced_at: Optional[str] = None
    max_age_hours: float = 6.0


class SubmitDecisionRequest(BaseModel):
    agent_id: str
    action_type: str
    description: str
    payload: dict = Field(default_factory=dict)
    context: str = ""
    data_sources: list[DataSourceInput] = Field(default_factory=list)


class SubmitDecisionResponse(BaseModel):
    decision_id: str
    status: str
    message: str
    submitted_at: str


class AuditTrailResponse(BaseModel):
    decision_id: str
    events: list[dict]