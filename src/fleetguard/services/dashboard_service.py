"""Dashboard aggregation service."""

from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from fleetguard.models.device import Device
from fleetguard.models.event import Event
from fleetguard.models.approval import Approval


async def get_dashboard_summary(db: AsyncSession) -> dict:
    """Get dashboard summary statistics."""
    now = datetime.now(timezone.utc)
    since_24h = now - timedelta(hours=24)

    # Device counts
    online = (await db.execute(
        select(func.count(Device.id)).where(Device.status == "online")
    )).scalar() or 0
    quarantined = (await db.execute(
        select(func.count(Device.id)).where(Device.quarantine == True)
    )).scalar() or 0

    # Event counts
    total_24h = (await db.execute(
        select(func.count(Event.id)).where(Event.created_at >= since_24h)
    )).scalar() or 0
    critical_24h = (await db.execute(
        select(func.count(Event.id)).where(
            and_(Event.created_at >= since_24h, Event.severity == "critical")
        )
    )).scalar() or 0

    # Average risk score
    avg_risk = (await db.execute(
        select(func.avg(Event.risk_score)).where(Event.created_at >= since_24h)
    )).scalar() or 0.0

    # Pending approvals
    pending = (await db.execute(
        select(func.count(Approval.id)).where(Approval.status == "pending")
    )).scalar() or 0

    return {
        "online_devices": online,
        "quarantined_devices": quarantined,
        "total_events_24h": total_24h,
        "critical_events_24h": critical_24h,
        "pending_approvals": pending,
        "avg_risk_score_24h": round(float(avg_risk), 1),
    }


async def get_risk_trends(db: AsyncSession, hours: int = 24) -> list[dict]:
    """Get risk trends grouped by hour."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    # Raw aggregation by hour and severity
    # Use strftime for SQLite, date_trunc for PostgreSQL
    engine_name = db.get_bind().dialect.name
    if engine_name == "sqlite":
        hour_expr = func.strftime("%Y-%m-%dT%H:00:00Z", Event.created_at).label("hour")
    else:
        hour_expr = func.date_trunc("hour", Event.created_at).label("hour")

    result = await db.execute(
        select(
            hour_expr,
            Event.severity,
            func.count(Event.id).label("cnt"),
        )
        .where(Event.created_at >= since)
        .group_by("hour", Event.severity)
        .order_by("hour")
    )
    rows = result.all()

    # Pivot into per-hour dicts
    trends: dict[str, dict] = {}
    for hour, severity, cnt in rows:
        hour_str = hour.strftime("%Y-%m-%dT%H:%M:%SZ")
        if hour_str not in trends:
            trends[hour_str] = {"hour": hour_str, "low": 0, "medium": 0, "high": 0, "critical": 0}
        if severity in trends[hour_str]:
            trends[hour_str][severity] = cnt

    return list(trends.values())


async def get_top_risky_devices(db: AsyncSession, limit: int = 10) -> list[dict]:
    """Get devices with highest average risk scores."""
    result = await db.execute(
        select(
            Event.device_id,
            func.avg(Event.risk_score).label("avg_score"),
            func.count(Event.id).label("total"),
            func.sum(
                case((Event.severity == "critical", 1), else_=0)
            ).label("critical_count"),
        )
        .group_by(Event.device_id)
        .order_by(func.avg(Event.risk_score).desc())
        .limit(limit)
    )
    rows = result.all()

    # Get hostnames
    device_map = {}
    device_result = await db.execute(select(Device))
    for d in device_result.scalars().all():
        device_map[d.device_id] = d

    return [
        {
            "device_id": row.device_id,
            "hostname": device_map.get(row.device_id, Device()).hostname if row.device_id in device_map else "",
            "username": device_map.get(row.device_id, Device()).username if row.device_id in device_map else "",
            "avg_risk_score": round(float(row.avg_score), 1),
            "critical_count": int(row.critical_count or 0),
        }
        for row in rows
    ]


async def get_recent_critical_events(db: AsyncSession, limit: int = 10) -> list[dict]:
    """Get most recent critical events."""
    result = await db.execute(
        select(Event)
        .where(Event.severity == "critical")
        .order_by(Event.created_at.desc())
        .limit(limit)
    )
    events = result.scalars().all()

    return [
        {
            "event_id": e.event_id,
            "device_id": e.device_id,
            "hostname": e.hostname,
            "tool_name": e.tool_name,
            "tool_category": e.tool_category,
            "risk_score": e.risk_score,
            "reason": e.reason,
            "timestamp": e.timestamp.isoformat() if e.timestamp else "",
            "event_type": e.event_type,
        }
        for e in events
    ]
