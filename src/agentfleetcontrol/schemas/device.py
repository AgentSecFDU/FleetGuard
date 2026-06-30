"""Device schemas."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class HeartbeatRequest(BaseModel):
    device_id: str
    status: str = "online"
    current_sessions: int = 0
    active_agent_runs: int = 0
    policy_version: int = 1
    quarantine: bool = False
    last_event_id: Optional[str] = None
    timestamp: str


class DeviceRead(BaseModel):
    id: str
    device_id: str
    hostname: str
    os: str
    os_version: Optional[str] = None
    username: str
    openclaw_version: Optional[str] = None
    plugin_version: Optional[str] = None
    sidecar_version: Optional[str] = None
    status: str
    quarantine: bool
    quarantine_reason: Optional[str] = None
    quarantined_at: Optional[str] = None
    policy_id: Optional[str] = None
    policy_version: int
    current_sessions: int
    active_agent_runs: int
    last_seen_at: Optional[str] = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class DeviceListResponse(BaseModel):
    data: list[DeviceRead]
    pagination: dict


class QuarantineRequest(BaseModel):
    reason: str


class DevicePolicyResponse(BaseModel):
    device_id: str
    policy_id: str
    policy_version: int
    yaml_content: str
