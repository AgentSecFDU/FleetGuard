"""Approval business logic: create, decide, expire."""

from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from agentfleetcontrol.models.approval import Approval
from agentfleetcontrol.schemas.approval import ApprovalCreate
from agentfleetcontrol.config import settings


async def create_approval(db: AsyncSession, req: ApprovalCreate) -> Approval:
    """Create an approval request."""
    requested_at = datetime.fromisoformat(req.requested_at.replace("Z", "+00:00"))
    expires_at = requested_at + timedelta(seconds=settings.approval_timeout_seconds)
    if req.expires_at:
        expires_at = datetime.fromisoformat(req.expires_at.replace("Z", "+00:00"))

    approval = Approval(
        approval_id=req.approval_id,
        device_id=req.device_id,
        event_id=req.event_id,
        session_id=req.session_id,
        run_id=req.run_id,
        tool_name=req.tool_name,
        params_summary=req.params_summary,
        risk_score=req.risk_score,
        risk_labels_json=req.risk_labels,
        reason=req.reason,
        status="pending",
        requested_at=requested_at,
        expires_at=expires_at,
    )
    db.add(approval)
    await db.flush()
    return approval


async def approve_approval(
    db: AsyncSession,
    approval_id: str,
    decided_by: str,
    reason: str | None = None,
) -> Approval:
    """Approve a pending approval."""
    result = await db.execute(select(Approval).where(Approval.approval_id == approval_id))
    approval = result.scalar_one_or_none()
    if not approval:
        raise ValueError(f"Approval {approval_id} not found")
    if approval.status != "pending":
        raise ValueError(f"Approval {approval_id} is already {approval.status}")

    approval.status = "approved"
    approval.decided_by = decided_by
    approval.decided_at = datetime.now(timezone.utc)
    approval.decision_reason = reason
    await db.flush()
    return approval


async def deny_approval(
    db: AsyncSession,
    approval_id: str,
    decided_by: str,
    reason: str | None = None,
    quarantine_device: bool = False,
    quarantine_session: bool = False,
) -> tuple[Approval, bool, bool]:
    """Deny a pending approval. Returns (approval, should_quarantine_device, should_quarantine_session)."""
    result = await db.execute(select(Approval).where(Approval.approval_id == approval_id))
    approval = result.scalar_one_or_none()
    if not approval:
        raise ValueError(f"Approval {approval_id} not found")
    if approval.status != "pending":
        raise ValueError(f"Approval {approval_id} is already {approval.status}")

    approval.status = "denied"
    approval.decided_by = decided_by
    approval.decided_at = datetime.now(timezone.utc)
    approval.decision_reason = reason
    await db.flush()
    return approval, quarantine_device, quarantine_session


async def get_approval_status(db: AsyncSession, approval_id: str) -> str:
    """Get the current status of an approval (for device long-poll)."""
    result = await db.execute(select(Approval).where(Approval.approval_id == approval_id))
    approval = result.scalar_one_or_none()
    if not approval:
        return "not_found"
    # Auto-expire if past expiry
    if approval.status == "pending" and approval.expires_at < datetime.now(timezone.utc):
        approval.status = "expired"
        await db.flush()
    return approval.status


async def get_approval(db: AsyncSession, approval_id: str) -> Approval | None:
    """Get approval by ID."""
    result = await db.execute(select(Approval).where(Approval.approval_id == approval_id))
    return result.scalar_one_or_none()


async def list_approvals(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    device_id: str | None = None,
) -> tuple[list[Approval], int]:
    """List approvals with optional filters. Returns (approvals, total)."""
    stmt = select(Approval)
    count_stmt = select(func.count(Approval.id))

    if status:
        stmt = stmt.where(Approval.status == status)
        count_stmt = count_stmt.where(Approval.status == status)
    if device_id:
        stmt = stmt.where(Approval.device_id == device_id)
        count_stmt = count_stmt.where(Approval.device_id == device_id)

    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(Approval.requested_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    approvals = list(result.scalars().all())

    return approvals, total
