"""Approval schemas."""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta, timezone


class ApprovalCreate(BaseModel):
    approval_id: str
    device_id: str
    event_id: Optional[str] = None
    session_id: Optional[str] = None
    run_id: Optional[str] = None
    tool_name: Optional[str] = None
    params_summary: Optional[str] = None
    risk_score: Optional[int] = None
    risk_labels: Optional[list[str]] = None
    reason: Optional[str] = None
    requested_at: str
    expires_at: Optional[str] = None  # defaults to requested_at + 120s


class ApprovalRead(BaseModel):
    id: str
    approval_id: str
    device_id: str
    event_id: Optional[str] = None
    session_id: Optional[str] = None
    run_id: Optional[str] = None
    tool_name: Optional[str] = None
    params_summary: Optional[str] = None
    risk_score: Optional[int] = None
    risk_labels_json: Optional[list[str]] = None
    reason: Optional[str] = None
    status: str
    requested_at: str
    expires_at: str
    decided_by: Optional[str] = None
    decided_at: Optional[str] = None
    decision_reason: Optional[str] = None
    created_at: str

    model_config = {"from_attributes": True}


class ApprovalListResponse(BaseModel):
    data: list[ApprovalRead]
    pagination: dict


class ApprovalDecision(BaseModel):
    reason: Optional[str] = None
    quarantine_device: bool = False
    quarantine_session: bool = False


class ApprovalStatusResponse(BaseModel):
    approval_id: str
    status: str
    decision_reason: Optional[str] = None
