"""Policy management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from fleetguard.database import get_db
from fleetguard.deps import get_current_admin
from fleetguard.models.admin_user import AdminUser
from fleetguard.schemas.policy import (
    PolicyCreate, PolicyUpdate, PolicyRead,
    PolicyListResponse, PolicyVersionRead, PolicyPublishResponse,
)
from fleetguard.services.policy_service import (
    create_policy, update_policy, publish_policy,
    get_policy, list_policies, get_policy_versions,
)
from fleetguard.services.audit_service import log_audit
from fleetguard.utils.yaml_parser import validate_policy_yaml

router = APIRouter()


def _policy_to_read(p) -> PolicyRead:
    return PolicyRead(
        id=str(p.id),
        policy_id=p.policy_id,
        name=p.name,
        version=p.version,
        yaml_content=p.yaml_content,
        status=p.status,
        created_by=p.created_by,
        published_at=p.published_at.isoformat() if p.published_at else None,
        created_at=p.created_at.isoformat() if p.created_at else "",
        updated_at=p.updated_at.isoformat() if p.updated_at else "",
    )


@router.post("/validate")
async def validate_policy(req: PolicyCreate, admin: AdminUser = Depends(get_current_admin)):
    """Admin: validate a policy YAML without saving."""
    errors = validate_policy_yaml(req.yaml_content)
    return {"valid": len(errors) == 0, "errors": errors}


@router.get("/", response_model=PolicyListResponse)
async def list_policies_route(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Admin: list policies (latest version of each)."""
    policies, total = await list_policies(db, page=page, page_size=page_size, status=status_filter)
    return PolicyListResponse(
        data=[_policy_to_read(p) for p in policies],
        pagination={"page": page, "page_size": page_size, "total": total},
    )


@router.post("/", response_model=PolicyRead)
async def create_policy_route(
    req: PolicyCreate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Admin: create a new policy."""
    errors = validate_policy_yaml(req.yaml_content)
    if errors:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid policy YAML: {'; '.join(errors)}")

    try:
        policy = await create_policy(db, req.policy_id, req.name, req.yaml_content, admin.username)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    await log_audit(db, actor=admin.username, action="policy.create", target_type="policy", target_id=policy.policy_id)
    return _policy_to_read(policy)


@router.get("/{policy_id}", response_model=PolicyRead)
async def get_policy_route(
    policy_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Admin: get policy detail (latest version)."""
    policy = await get_policy(db, policy_id)
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Policy {policy_id} not found")
    return _policy_to_read(policy)


@router.put("/{policy_id}", response_model=PolicyRead)
async def update_policy_route(
    policy_id: str, req: PolicyUpdate,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Admin: update policy (creates new version)."""
    errors = validate_policy_yaml(req.yaml_content)
    if errors:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid policy YAML: {'; '.join(errors)}")

    try:
        policy = await update_policy(db, policy_id, req.yaml_content)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    await log_audit(db, actor=admin.username, action="policy.update", target_type="policy", target_id=policy_id)
    return _policy_to_read(policy)


@router.post("/{policy_id}/publish", response_model=PolicyPublishResponse)
async def publish_policy_route(
    policy_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Admin: publish a policy."""
    try:
        policy = await publish_policy(db, policy_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    await log_audit(db, actor=admin.username, action="policy.publish", target_type="policy", target_id=policy_id,
                    detail={"version": policy.version})

    return PolicyPublishResponse(
        policy_id=policy.policy_id,
        version=policy.version,
        status=policy.status,
        message=f"Policy {policy_id} v{policy.version} published",
    )


@router.get("/{policy_id}/versions", response_model=list[PolicyVersionRead])
async def get_policy_versions_route(
    policy_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Admin: get version history for a policy."""
    versions = await get_policy_versions(db, policy_id)
    if not versions:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Policy {policy_id} not found")
    return [
        PolicyVersionRead(
            version=v.version,
            status=v.status,
            published_at=v.published_at.isoformat() if v.published_at else None,
            created_at=v.created_at.isoformat() if v.created_at else "",
        )
        for v in versions
    ]
