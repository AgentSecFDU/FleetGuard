"""Audit log endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from fleetguard.database import get_db
from fleetguard.deps import get_current_admin
from fleetguard.models.admin_user import AdminUser
from fleetguard.services.audit_service import query_audit_logs
from fleetguard.schemas.common import PaginatedResponse

router = APIRouter()


@router.get("/")
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    actor: str | None = None,
    action: str | None = None,
    target_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Admin: list audit logs."""
    entries, total = await query_audit_logs(
        db, page=page, page_size=page_size,
        actor=actor, action=action, target_type=target_type,
    )

    data = [
        {
            "id": str(e.id),
            "actor": e.actor,
            "action": e.action,
            "target_type": e.target_type,
            "target_id": e.target_id,
            "detail_json": e.detail_json,
            "created_at": e.created_at.isoformat() if e.created_at else "",
        }
        for e in entries
    ]

    return PaginatedResponse(
        data=data,
        pagination={"page": page, "page_size": page_size, "total": total},
    )
