"""Event schemas."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class EventCreate(BaseModel):
    """Schema for a single event uploaded by a device."""
    event_id: str
    event_type: str
    timestamp: str
    device_id: str
    user_id: Optional[str] = None
    hostname: Optional[str] = None
    session_id: Optional[str] = None
    agent_id: Optional[str] = None
    run_id: Optional[str] = None
    tool_name: Optional[str] = None
    tool_category: Optional[str] = None
    input_provenance: Optional[str] = None
    params_summary: Optional[str] = None
    params_redacted: Optional[dict] = None
    risk_score: int = 0
    risk_labels: Optional[list[str]] = None
    policy_decision: Optional[str] = None
    policy_id: Optional[str] = None
    policy_version: Optional[int] = None
    reason: Optional[str] = None
    content_uploaded: bool = False


class EventBatchUpload(BaseModel):
    """Batch of events to upload."""
    events: list[EventCreate] = Field(..., min_length=1, max_length=1000)


class EventBatchResponse(BaseModel):
    accepted: int
    rejected: int
    errors: list[str] = []


class EventRead(BaseModel):
    id: str
    event_id: str
    event_type: str
    timestamp: str
    device_id: str
    user_id: Optional[str] = None
    hostname: Optional[str] = None
    session_id: Optional[str] = None
    agent_id: Optional[str] = None
    run_id: Optional[str] = None
    tool_name: Optional[str] = None
    tool_category: Optional[str] = None
    input_provenance: Optional[str] = None
    params_summary: Optional[str] = None
    params_redacted_json: Optional[dict] = None
    risk_score: int
    risk_labels_json: Optional[list[str]] = None
    policy_decision: Optional[str] = None
    policy_id: Optional[str] = None
    policy_version: Optional[int] = None
    reason: Optional[str] = None
    severity: Optional[str] = None
    content_uploaded: bool = False
    created_at: str

    model_config = {"from_attributes": True}


class EventListResponse(BaseModel):
    data: list[EventRead]
    pagination: dict


class EventFilterParams(BaseModel):
    cursor: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)
    device_id: Optional[str] = None
    severity: Optional[str] = None
    event_type: Optional[str] = None
    tool_name: Optional[str] = None
    tool_category: Optional[str] = None
    policy_decision: Optional[str] = None
    risk_score_min: Optional[int] = None
    risk_score_max: Optional[int] = None
    session_id: Optional[str] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None
