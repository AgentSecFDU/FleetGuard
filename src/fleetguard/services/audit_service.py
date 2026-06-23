"""Audit log service."""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from fleetguard.models.audit_log import AuditLog


async def log_audit(
    db: AsyncSession,
    actor: str,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    detail: dict | None = None,
) -> AuditLog:
    """Write an audit log entry."""
    entry = AuditLog(
        actor=actor,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail_json=detail,
    )
    db.add(entry)
    await db.flush()
    return entry


async def query_audit_logs(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    actor: str | None = None,
    action: str | None = None,
    target_type: str | None = None,
) -> tuple[list[AuditLog], int]:
    """Query audit logs with optional filters."""
    stmt = select(AuditLog)
    count_stmt = select(func.count(AuditLog.id))

    if actor:
        stmt = stmt.where(AuditLog.actor == actor)
        count_stmt = count_stmt.where(AuditLog.actor == actor)
    if action:
        stmt = stmt.where(AuditLog.action == action)
        count_stmt = count_stmt.where(AuditLog.action == action)
    if target_type:
        stmt = stmt.where(AuditLog.target_type == target_type)
        count_stmt = count_stmt.where(AuditLog.target_type == target_type)

    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    entries = list(result.scalars().all())

    return entries, total
