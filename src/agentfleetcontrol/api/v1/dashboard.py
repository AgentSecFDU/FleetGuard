"""Dashboard aggregation endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from agentfleetcontrol.database import get_db
from agentfleetcontrol.deps import get_current_admin
from agentfleetcontrol.models.admin_user import AdminUser
from agentfleetcontrol.schemas.dashboard import (
    DashboardSummary, RiskTrendPoint, TopRiskyDevice, CriticalEvent,
)
from agentfleetcontrol.services.dashboard_service import (
    get_dashboard_summary, get_risk_trends,
    get_top_risky_devices, get_recent_critical_events,
)

router = APIRouter()


@router.get("/summary", response_model=DashboardSummary)
async def summary(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Admin: get dashboard summary statistics."""
    data = await get_dashboard_summary(db)
    return DashboardSummary(**data)


@router.get("/risk-trends", response_model=list[RiskTrendPoint])
async def risk_trends(
    period: str = Query("24h", pattern="^(24h|7d)$"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Admin: get risk trends over time."""
    hours = 24 if period == "24h" else 168
    data = await get_risk_trends(db, hours=hours)
    return [RiskTrendPoint(**d) for d in data]


@router.get("/top-risky-devices", response_model=list[TopRiskyDevice])
async def top_risky_devices(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Admin: get devices with highest risk scores."""
    data = await get_top_risky_devices(db, limit=limit)
    return [TopRiskyDevice(**d) for d in data]


@router.get("/recent-critical-events", response_model=list[CriticalEvent])
async def recent_critical_events(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Admin: get most recent critical events."""
    data = await get_recent_critical_events(db, limit=limit)
    return [CriticalEvent(**d) for d in data]
