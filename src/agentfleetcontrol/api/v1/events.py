"""Event endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession

from agentfleetcontrol.database import get_db
from agentfleetcontrol.deps import get_current_admin, get_current_device
from agentfleetcontrol.models.admin_user import AdminUser
from agentfleetcontrol.models.device import Device
from agentfleetcontrol.schemas.event import (
    EventBatchUpload, EventBatchResponse, EventRead, EventListResponse,
)
from agentfleetcontrol.services.event_service import ingest_event_batch, query_events, get_event

router = APIRouter()


def _event_to_read(e) -> EventRead:
    return EventRead(
        id=str(e.id),
        event_id=e.event_id,
        event_type=e.event_type,
        timestamp=e.timestamp.isoformat() if e.timestamp else "",
        device_id=e.device_id,
        user_id=e.user_id,
        hostname=e.hostname,
        session_id=e.session_id,
        agent_id=e.agent_id,
        run_id=e.run_id,
        tool_name=e.tool_name,
        tool_category=e.tool_category,
        input_provenance=e.input_provenance,
        params_summary=e.params_summary,
        params_redacted_json=e.params_redacted_json,
        risk_score=e.risk_score,
        risk_labels_json=e.risk_labels_json,
        policy_decision=e.policy_decision,
        policy_id=e.policy_id,
        policy_version=e.policy_version,
        reason=e.reason,
        severity=e.severity,
        content_uploaded=e.content_uploaded,
        created_at=e.created_at.isoformat() if e.created_at else "",
    )


@router.post("/batch", response_model=EventBatchResponse)
async def upload_events_batch(
    req: EventBatchUpload,
    request: Request,
    db: AsyncSession = Depends(get_db),
    device: Device = Depends(get_current_device),
):
    """Device: upload a batch of events."""
    # Verify all events belong to this device
    for evt in req.events:
        if evt.device_id != device.device_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Event device_id {evt.device_id} does not match authenticated device {device.device_id}",
            )

    redis = getattr(request.app.state, "redis", None)
    accepted, rejected, errors = await ingest_event_batch(db, req.events, redis_client=redis)

    return EventBatchResponse(accepted=accepted, rejected=rejected, errors=errors)


@router.get("/", response_model=EventListResponse)
async def list_events(
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    device_id: str | None = Query(None),
    severity: str | None = Query(None),
    event_type: str | None = Query(None),
    tool_name: str | None = Query(None),
    tool_category: str | None = Query(None),
    policy_decision: str | None = Query(None),
    risk_score_min: int | None = Query(None),
    risk_score_max: int | None = Query(None),
    session_id: str | None = Query(None),
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Admin: list events with filters and cursor pagination."""
    events, next_cursor = await query_events(
        db,
        cursor=cursor,
        limit=limit,
        device_id=device_id,
        severity=severity,
        event_type=event_type,
        tool_name=tool_name,
        tool_category=tool_category,
        policy_decision=policy_decision,
        risk_score_min=risk_score_min,
        risk_score_max=risk_score_max,
        session_id=session_id,
        from_date=from_date,
        to_date=to_date,
    )
    return EventListResponse(
        data=[_event_to_read(e) for e in events],
        pagination={"cursor": next_cursor, "limit": limit},
    )


@router.get("/{event_id}", response_model=EventRead)
async def get_event_route(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Admin: get event detail."""
    event = await get_event(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Event {event_id} not found")
    return _event_to_read(event)
