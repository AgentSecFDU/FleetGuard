"""Approval endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from agentfleetcontrol.database import get_db
from agentfleetcontrol.deps import get_current_admin, get_current_device
from agentfleetcontrol.models.admin_user import AdminUser
from agentfleetcontrol.models.device import Device
from agentfleetcontrol.schemas.approval import (
    ApprovalCreate, ApprovalRead, ApprovalListResponse,
    ApprovalDecision, ApprovalStatusResponse,
)
from agentfleetcontrol.services.approval_service import (
    create_approval, approve_approval, deny_approval,
    get_approval, list_approvals, get_approval_status,
)
from agentfleetcontrol.services.device_service import quarantine_device as svc_quarantine_device
from agentfleetcontrol.services.audit_service import log_audit

router = APIRouter()


def _approval_to_read(a) -> ApprovalRead:
    return ApprovalRead(
        id=str(a.id),
        approval_id=a.approval_id,
        device_id=a.device_id,
        event_id=a.event_id,
        session_id=a.session_id,
        run_id=a.run_id,
        tool_name=a.tool_name,
        params_summary=a.params_summary,
        risk_score=a.risk_score,
        risk_labels_json=a.risk_labels_json,
        reason=a.reason,
        status=a.status,
        requested_at=a.requested_at.isoformat() if a.requested_at else "",
        expires_at=a.expires_at.isoformat() if a.expires_at else "",
        decided_by=a.decided_by,
        decided_at=a.decided_at.isoformat() if a.decided_at else None,
        decision_reason=a.decision_reason,
        created_at=a.created_at.isoformat() if a.created_at else "",
    )


@router.post("/", response_model=ApprovalRead)
async def create_approval_route(
    req: ApprovalCreate,
    db: AsyncSession = Depends(get_db),
    device: Device = Depends(get_current_device),
):
    """Device: create an approval request."""
    if req.device_id != device.device_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Device ID mismatch")

    approval = await create_approval(db, req)
    return _approval_to_read(approval)


@router.get("/", response_model=ApprovalListResponse)
async def list_approvals_route(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    device_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Admin: list approvals."""
    approvals, total = await list_approvals(
        db, page=page, page_size=page_size, status=status_filter, device_id=device_id,
    )
    return ApprovalListResponse(
        data=[_approval_to_read(a) for a in approvals],
        pagination={"page": page, "page_size": page_size, "total": total},
    )


@router.get("/{approval_id}", response_model=ApprovalRead)
async def get_approval_route(
    approval_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Admin: get approval detail."""
    approval = await get_approval(db, approval_id)
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Approval {approval_id} not found")
    return _approval_to_read(approval)


@router.post("/{approval_id}/approve", response_model=ApprovalRead)
async def approve_route(
    approval_id: str,
    decision: ApprovalDecision,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Admin: approve a pending request."""
    try:
        approval = await approve_approval(db, approval_id, admin.username, decision.reason)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    await log_audit(db, actor=admin.username, action="approval.approve",
                    target_type="approval", target_id=approval_id)
    return _approval_to_read(approval)


@router.post("/{approval_id}/deny", response_model=ApprovalRead)
async def deny_route(
    approval_id: str,
    decision: ApprovalDecision,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Admin: deny a pending request."""
    try:
        approval, quarantine_dev, quarantine_sess = await deny_approval(
            db, approval_id, admin.username, decision.reason,
            decision.quarantine_device, decision.quarantine_session,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    await log_audit(db, actor=admin.username, action="approval.deny",
                    target_type="approval", target_id=approval_id)

    # Handle quarantine if requested
    if quarantine_dev:
        try:
            await svc_quarantine_device(db, approval.device_id,
                                        f"Quarantined after denied approval {approval_id}",
                                        actor=admin.username)
        except ValueError:
            pass

    return _approval_to_read(approval)


@router.get("/{approval_id}/status", response_model=ApprovalStatusResponse)
async def check_approval_status(
    approval_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Device: check approval status (use for long-poll)."""
    approval = await get_approval(db, approval_id)
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Approval {approval_id} not found")

    # Check expiry
    if approval.status == "pending" and approval.expires_at:
        from datetime import datetime, timezone
        if approval.expires_at < datetime.now(timezone.utc):
            approval.status = "expired"
            await db.flush()

    return ApprovalStatusResponse(
        approval_id=approval.approval_id,
        status=approval.status,
        decision_reason=approval.decision_reason,
    )
