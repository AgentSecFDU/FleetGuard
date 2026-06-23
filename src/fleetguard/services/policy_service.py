"""Policy business logic: CRUD with versioning, publish lifecycle."""

from datetime import datetime, timezone
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from fleetguard.models.policy import Policy


async def create_policy(
    db: AsyncSession,
    policy_id: str,
    name: str,
    yaml_content: str,
    created_by: str,
) -> Policy:
    """Create a new policy (draft status)."""
    policy = Policy(
        policy_id=policy_id,
        name=name,
        version=1,
        yaml_content=yaml_content,
        status="draft",
        created_by=created_by,
    )
    db.add(policy)
    await db.flush()
    return policy


async def update_policy(db: AsyncSession, policy_id: str, yaml_content: str) -> Policy:
    """Update a policy — creates a new version (increments version number)."""
    # Find latest version
    result = await db.execute(
        select(Policy)
        .where(Policy.policy_id == policy_id)
        .order_by(Policy.version.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    if not latest:
        raise ValueError(f"Policy {policy_id} not found")

    new_version = Policy(
        policy_id=policy_id,
        name=latest.name,
        version=latest.version + 1,
        yaml_content=yaml_content,
        status="draft",
        created_by=latest.created_by,
    )
    db.add(new_version)
    await db.flush()
    return new_version


async def publish_policy(db: AsyncSession, policy_id: str) -> Policy:
    """Publish a policy — archives the currently published version, sets the latest draft to published."""
    # Find latest version
    result = await db.execute(
        select(Policy)
        .where(Policy.policy_id == policy_id)
        .order_by(Policy.version.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    if not latest:
        raise ValueError(f"Policy {policy_id} not found")

    # Archive any currently published version
    from sqlalchemy import update
    await db.execute(
        update(Policy)
        .where(Policy.policy_id == policy_id, Policy.status == "published")
        .values(status="archived")
    )

    # Publish latest
    latest.status = "published"
    latest.published_at = datetime.now(timezone.utc)
    await db.flush()
    return latest


async def get_policy(db: AsyncSession, policy_id: str, version: int | None = None) -> Policy | None:
    """Get a policy. If version is None, returns the latest version."""
    stmt = select(Policy).where(Policy.policy_id == policy_id)
    if version:
        stmt = stmt.where(Policy.version == version)
    else:
        stmt = stmt.order_by(Policy.version.desc()).limit(1)

    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_policies(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
) -> tuple[list[Policy], int]:
    """List policies (latest version of each)."""
    # Subquery: get latest version per policy_id
    subq = (
        select(Policy.policy_id, func.max(Policy.version).label("max_version"))
        .group_by(Policy.policy_id)
    )
    if status:
        subq = subq.where(Policy.status == status)

    subq = subq.subquery()

    stmt = (
        select(Policy)
        .join(subq, and_(
            Policy.policy_id == subq.c.policy_id,
            Policy.version == subq.c.max_version,
        ))
        .order_by(Policy.created_at.desc())
    )
    count_stmt = select(func.count()).select_from(subq)

    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(stmt)
    policies = list(result.scalars().all())

    return policies, total


async def get_policy_versions(db: AsyncSession, policy_id: str) -> list[Policy]:
    """Get all versions of a policy."""
    result = await db.execute(
        select(Policy)
        .where(Policy.policy_id == policy_id)
        .order_by(Policy.version.desc())
    )
    return list(result.scalars().all())


async def get_effective_policy_for_device(db: AsyncSession, device) -> str:
    """Get the effective YAML policy content for a device."""
    policy_id = device.policy_id or "default"
    result = await db.execute(
        select(Policy)
        .where(Policy.policy_id == policy_id, Policy.status == "published")
        .order_by(Policy.version.desc())
        .limit(1)
    )
    policy = result.scalar_one_or_none()
    if policy:
        return policy.yaml_content
    # Fallback to filesystem (tries multiple locations)
    from pathlib import Path
    candidates = [
        Path(__file__).parent.parent.parent.parent.parent / "policies" / "default.yaml",  # src/fleetguard -> repo root
        Path("/app/policies/default.yaml"),  # Docker
        Path("policies/default.yaml"),  # local dev from repo root
    ]
    for path in candidates:
        if path.exists():
            return path.read_text()
    return ""
