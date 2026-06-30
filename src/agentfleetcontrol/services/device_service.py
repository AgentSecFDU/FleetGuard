"""Device business logic: enrollment, heartbeat, quarantine lifecycle."""

from datetime import datetime, timezone
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from agentfleetcontrol.models.device import Device
from agentfleetcontrol.models.enrollment_token import EnrollmentToken
from agentfleetcontrol.utils.crypto import hash_token, hash_password
from agentfleetcontrol.utils.id_generator import generate_device_api_token
from agentfleetcontrol.config import settings


async def enroll_device(
    db: AsyncSession,
    enrollment_token_raw: str,
    device_id: str,
    hostname: str,
    os: str,
    username: str,
    os_version: str | None = None,
    openclaw_version: str | None = None,
    plugin_version: str | None = None,
    sidecar_version: str | None = None,
) -> tuple[Device, str]:
    """Enroll a new device. Returns (device, raw_device_token)."""

    # Validate enrollment token
    from agentfleetcontrol.utils.crypto import verify_token
    stmt = select(EnrollmentToken).where(
        EnrollmentToken.used == False,
        EnrollmentToken.expires_at > datetime.now(timezone.utc),
    )
    result = await db.execute(stmt)
    tokens = result.scalars().all()

    matched_token = None
    for t in tokens:
        if verify_token(enrollment_token_raw, t.token_hash):
            matched_token = t
            break

    if not matched_token:
        raise ValueError("Invalid or expired enrollment token")

    # Check device_id uniqueness
    existing = await db.execute(select(Device).where(Device.device_id == device_id))
    if existing.scalar_one_or_none():
        raise ValueError(f"Device {device_id} already registered")

    # Generate device API token
    raw_token, _ = generate_device_api_token()
    token_hash = hash_token(raw_token)

    # Create device
    device = Device(
        device_id=device_id,
        hostname=hostname,
        os=os,
        os_version=os_version,
        username=username,
        openclaw_version=openclaw_version,
        plugin_version=plugin_version,
        sidecar_version=sidecar_version,
        status="online",
        device_token_hash=token_hash,
        policy_id="default",
        policy_version=1,
        last_seen_at=datetime.now(timezone.utc),
    )
    db.add(device)

    # Mark enrollment token as used
    matched_token.used = True
    matched_token.used_by_device = device_id

    await db.flush()
    return device, raw_token


async def process_heartbeat(
    db: AsyncSession,
    device_id: str,
    status: str = "online",
    current_sessions: int = 0,
    active_agent_runs: int = 0,
    policy_version: int = 1,
    quarantine: bool = False,
    last_event_id: str | None = None,
) -> Device:
    """Process a device heartbeat. Returns the updated device."""
    result = await db.execute(select(Device).where(Device.device_id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise ValueError(f"Device {device_id} not found")

    device.status = status
    device.current_sessions = current_sessions
    device.active_agent_runs = active_agent_runs
    device.policy_version = policy_version
    device.last_seen_at = datetime.now(timezone.utc)

    if quarantine and not device.quarantine:
        device.quarantine = True
        device.status = "quarantined"
        device.quarantined_at = datetime.now(timezone.utc)
        device.quarantine_reason = "Reported by device"

    await db.flush()
    return device


async def quarantine_device(db: AsyncSession, device_id: str, reason: str, actor: str = "admin") -> Device:
    """Quarantine a device."""
    result = await db.execute(select(Device).where(Device.device_id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise ValueError(f"Device {device_id} not found")

    device.quarantine = True
    device.quarantine_reason = reason
    device.quarantined_at = datetime.now(timezone.utc)
    device.status = "quarantined"
    device.policy_id = "lockdown"

    await db.flush()
    return device


async def unquarantine_device(db: AsyncSession, device_id: str, actor: str = "admin") -> Device:
    """Remove quarantine from a device."""
    result = await db.execute(select(Device).where(Device.device_id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise ValueError(f"Device {device_id} not found")

    device.quarantine = False
    device.quarantine_reason = None
    device.quarantined_at = None
    device.status = "online"
    device.policy_id = "default"

    await db.flush()
    return device


async def get_device(db: AsyncSession, device_id: str) -> Device | None:
    """Get a device by ID."""
    result = await db.execute(select(Device).where(Device.device_id == device_id))
    return result.scalar_one_or_none()


async def list_devices(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    quarantine: bool | None = None,
    search: str | None = None,
) -> tuple[list[Device], int]:
    """List devices with optional filters. Returns (devices, total_count)."""
    stmt = select(Device)
    count_stmt = select(func.count(Device.id))

    if status:
        stmt = stmt.where(Device.status == status)
        count_stmt = count_stmt.where(Device.status == status)
    if quarantine is not None:
        stmt = stmt.where(Device.quarantine == quarantine)
        count_stmt = count_stmt.where(Device.quarantine == quarantine)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            (Device.device_id.ilike(pattern))
            | (Device.hostname.ilike(pattern))
            | (Device.username.ilike(pattern))
        )
        count_stmt = count_stmt.where(
            (Device.device_id.ilike(pattern))
            | (Device.hostname.ilike(pattern))
            | (Device.username.ilike(pattern))
        )

    # Total count
    total = (await db.execute(count_stmt)).scalar() or 0

    # Pagination
    stmt = stmt.order_by(Device.last_seen_at.desc().nulls_last()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    devices = list(result.scalars().all())

    return devices, total


async def mark_offline_stale_devices(db: AsyncSession) -> int:
    """Mark devices as offline if they haven't sent heartbeat within threshold. Returns count."""
    threshold = datetime.now(timezone.utc).timestamp() - settings.device_offline_threshold_seconds
    threshold_dt = datetime.fromtimestamp(threshold, tz=timezone.utc)

    stmt = (
        update(Device)
        .where(
            Device.last_seen_at < threshold_dt,
            Device.status == "online",
        )
        .values(status="offline")
    )
    result = await db.execute(stmt)
    await db.flush()
    return result.rowcount
