"""Dashboard schemas."""

from pydantic import BaseModel
from typing import Optional


class DashboardSummary(BaseModel):
    online_devices: int = 0
    quarantined_devices: int = 0
    total_events_24h: int = 0
    critical_events_24h: int = 0
    pending_approvals: int = 0
    avg_risk_score_24h: float = 0.0


class RiskTrendPoint(BaseModel):
    hour: str
    low: int = 0
    medium: int = 0
    high: int = 0
    critical: int = 0


class TopRiskyDevice(BaseModel):
    device_id: str
    hostname: str
    username: str
    avg_risk_score: float
    critical_count: int


class CriticalEvent(BaseModel):
    event_id: str
    device_id: str
    hostname: Optional[str] = None
    tool_name: Optional[str] = None
    tool_category: Optional[str] = None
    risk_score: int
    reason: Optional[str] = None
    timestamp: str
    event_type: str
