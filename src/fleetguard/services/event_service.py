"""Event business logic: batch insert, risk scoring, querying."""

import json
import base64
from datetime import datetime, timezone
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from fleetguard.models.event import Event
from fleetguard.engine.risk_scorer import get_risk_scorer
from fleetguard.engine.base import RiskContext
from fleetguard.schemas.event import EventCreate


def _score_to_severity(score: int) -> str:
    if score >= 80:
        return "critical"
    elif score >= 60:
        return "high"
    elif score >= 30:
        return "medium"
    return "low"


async def ingest_event_batch(
    db: AsyncSession,
    raw_events: list[EventCreate],
    redis_client=None,
) -> tuple[int, int, list[str]]:
    """Ingest a batch of events: score, insert, and publish high/critical events.

    Returns:
        (accepted_count, rejected_count, error_messages)
    """
    scorer = get_risk_scorer()
    accepted = 0
    rejected = 0
    errors: list[str] = []
    high_critical_events: list[dict] = []

    for raw in raw_events:
        try:
            # Parse timestamp
            ts = datetime.fromisoformat(raw.timestamp.replace("Z", "+00:00"))

            # Build risk context
            ctx = RiskContext(
                event_type=raw.event_type,
                tool_name=raw.tool_name,
                tool_category=raw.tool_category,
                input_provenance=raw.input_provenance,
                params_summary=raw.params_summary,
                params_redacted=raw.params_redacted,
            )

            # Run risk scoring
            risk_score, risk_labels, reasons, severity = await scorer.score(ctx)

            # Merge device-reported risk with server-computed risk
            final_score = max(raw.risk_score, risk_score)
            final_labels = list(set((raw.risk_labels or []) + risk_labels))

            # Determine severity if not already set by scorer
            if not severity or severity == "low":
                severity = _score_to_severity(final_score)

            # Build ORM object
            event = Event(
                event_id=raw.event_id,
                event_type=raw.event_type,
                timestamp=ts,
                device_id=raw.device_id,
                user_id=raw.user_id,
                hostname=raw.hostname,
                session_id=raw.session_id,
                agent_id=raw.agent_id,
                run_id=raw.run_id,
                tool_name=raw.tool_name,
                tool_category=raw.tool_category,
                input_provenance=raw.input_provenance,
                params_summary=raw.params_summary,
                params_redacted_json=raw.params_redacted,
                risk_score=final_score,
                risk_labels_json=final_labels,
                policy_decision=raw.policy_decision,
                policy_id=raw.policy_id,
                policy_version=raw.policy_version,
                reason=raw.reason or "; ".join(reasons),
                severity=severity,
                content_uploaded=raw.content_uploaded,
            )
            db.add(event)
            accepted += 1

            # Collect high/critical for WebSocket broadcast
            if severity in ("high", "critical"):
                high_critical_events.append({
                    "event_id": event.event_id,
                    "device_id": event.device_id,
                    "event_type": event.event_type,
                    "tool_name": event.tool_name,
                    "tool_category": event.tool_category,
                    "risk_score": event.risk_score,
                    "severity": event.severity,
                    "reason": event.reason,
                    "timestamp": raw.timestamp,
                })

        except Exception as e:
            rejected += 1
            errors.append(f"Event {raw.event_id}: {str(e)}")

    await db.flush()

    # Publish high/critical events to Redis for WebSocket broadcast
    if redis_client and high_critical_events:
        for evt in high_critical_events:
            try:
                await redis_client.publish("events:publish", json.dumps(evt, default=str))
            except Exception:
                pass

    return accepted, rejected, errors


async def query_events(
    db: AsyncSession,
    cursor: str | None = None,
    limit: int = 20,
    device_id: str | None = None,
    severity: str | None = None,
    event_type: str | None = None,
    tool_name: str | None = None,
    tool_category: str | None = None,
    policy_decision: str | None = None,
    risk_score_min: int | None = None,
    risk_score_max: int | None = None,
    session_id: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
) -> tuple[list[Event], str | None]:
    """Query events with filters and cursor-based pagination.

    Returns:
        (events, next_cursor | None)
    """
    stmt = select(Event)

    # Filters
    conditions = []
    if device_id:
        conditions.append(Event.device_id == device_id)
    if severity:
        conditions.append(Event.severity == severity)
    if event_type:
        conditions.append(Event.event_type == event_type)
    if tool_name:
        conditions.append(Event.tool_name == tool_name)
    if tool_category:
        conditions.append(Event.tool_category == tool_category)
    if policy_decision:
        conditions.append(Event.policy_decision == policy_decision)
    if risk_score_min is not None:
        conditions.append(Event.risk_score >= risk_score_min)
    if risk_score_max is not None:
        conditions.append(Event.risk_score <= risk_score_max)
    if session_id:
        conditions.append(Event.session_id == session_id)
    if from_date:
        conditions.append(Event.created_at >= datetime.fromisoformat(from_date.replace("Z", "+00:00")))
    if to_date:
        conditions.append(Event.created_at <= datetime.fromisoformat(to_date.replace("Z", "+00:00")))

    # Cursor pagination
    if cursor:
        try:
            cursor_data = json.loads(base64.urlsafe_b64decode(cursor).decode())
            cursor_ts = cursor_data["t"]
            cursor_id = cursor_data["i"]
            conditions.append(
                and_(
                    Event.created_at <= datetime.fromisoformat(cursor_ts.replace("Z", "+00:00")),
                    Event.id != cursor_id,
                )
            )
        except Exception:
            pass

    if conditions:
        stmt = stmt.where(and_(*conditions))

    # Order and limit
    stmt = stmt.order_by(Event.created_at.desc(), Event.id.desc()).limit(limit + 1)

    result = await db.execute(stmt)
    events = list(result.scalars().all())

    # Determine next cursor
    next_cursor = None
    if len(events) > limit:
        events = events[:limit]
        last = events[-1]
        cursor_json = json.dumps({
            "t": last.created_at.isoformat() if last.created_at else "",
            "i": str(last.id),
        })
        next_cursor = base64.urlsafe_b64encode(cursor_json.encode()).decode()

    return events, next_cursor


async def get_event(db: AsyncSession, event_id: str) -> Event | None:
    """Get a single event by event_id."""
    result = await db.execute(select(Event).where(Event.event_id == event_id))
    return result.scalar_one_or_none()
