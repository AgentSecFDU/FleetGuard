"""Device management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from fleetguard.database import get_db
from fleetguard.deps import get_current_admin, get_current_device
from fleetguard.models.admin_user import AdminUser
from fleetguard.models.device import Device
from fleetguard.schemas.auth import DeviceEnrollRequest, DeviceEnrollResponse
from fleetguard.schemas.device import (
    HeartbeatRequest, DeviceRead, DeviceListResponse,
    QuarantineRequest, DevicePolicyResponse,
)
from fleetguard.schemas.event import EventRead, EventListResponse
from fleetguard.services.device_service import (
    enroll_device, process_heartbeat, quarantine_device,
    unquarantine_device, get_device, list_devices,
)
from fleetguard.services.event_service import query_events
from fleetguard.api.v1.events import _event_to_read
from fleetguard.services.audit_service import log_audit

router = APIRouter()


def _device_to_read(d: Device) -> DeviceRead:
    return DeviceRead(
        id=str(d.id),
        device_id=d.device_id,
        hostname=d.hostname,
        os=d.os,
        os_version=d.os_version,
        username=d.username,
        openclaw_version=d.openclaw_version,
        plugin_version=d.plugin_version,
        sidecar_version=d.sidecar_version,
        status=d.status,
        quarantine=d.quarantine,
        quarantine_reason=d.quarantine_reason,
        quarantined_at=d.quarantined_at.isoformat() if d.quarantined_at else None,
        policy_id=d.policy_id,
        policy_version=d.policy_version,
        current_sessions=d.current_sessions,
        active_agent_runs=d.active_agent_runs,
        last_seen_at=d.last_seen_at.isoformat() if d.last_seen_at else None,
        created_at=d.created_at.isoformat() if d.created_at else "",
        updated_at=d.updated_at.isoformat() if d.updated_at else "",
    )


@router.post("/enroll", response_model=DeviceEnrollResponse)
async def enroll(req: DeviceEnrollRequest, db: AsyncSession = Depends(get_db)):
    """Device enrollment - exchanges enrollment token for device token."""
    try:
        device, raw_token = await enroll_device(
            db,
            enrollment_token_raw=req.enrollment_token,
            device_id=req.device_id,
            hostname=req.hostname,
            os=req.os,
            username=req.username,
            os_version=req.os_version,
            openclaw_version=req.openclaw_version,
            plugin_version=req.plugin_version,
            sidecar_version=req.sidecar_version,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Audit
    await log_audit(db, actor="system", action="device.enroll", target_type="device", target_id=device.device_id,
                    detail={"hostname": device.hostname, "username": device.username})

    return DeviceEnrollResponse(device_id=device.device_id, device_token=raw_token)


@router.post("/heartbeat")
async def heartbeat(req: HeartbeatRequest, db: AsyncSession = Depends(get_db),
                    device: Device = Depends(get_current_device)):
    """Device heartbeat - updates last_seen_at and device status."""
    if device.device_id != req.device_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Device ID mismatch")

    await process_heartbeat(
        db,
        device_id=req.device_id,
        status=req.status,
        current_sessions=req.current_sessions,
        active_agent_runs=req.active_agent_runs,
        policy_version=req.policy_version,
        quarantine=req.quarantine,
        last_event_id=req.last_event_id,
    )
    return {"status": "ok"}


@router.get("/", response_model=DeviceListResponse)
async def list_devices_route(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    quarantine: bool | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Admin: list all devices with optional filters."""
    devices, total = await list_devices(
        db, page=page, page_size=page_size,
        status=status_filter, quarantine=quarantine, search=search,
    )
    return DeviceListResponse(
        data=[_device_to_read(d) for d in devices],
        pagination={"page": page, "page_size": page_size, "total": total},
    )


@router.get("/{device_id}", response_model=DeviceRead)
async def get_device_route(device_id: str, db: AsyncSession = Depends(get_db),
                           admin: AdminUser = Depends(get_current_admin)):
    """Admin: get device detail."""
    device = await get_device(db, device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Device {device_id} not found")
    return _device_to_read(device)


@router.post("/{device_id}/quarantine", response_model=DeviceRead)
async def quarantine_device_route(
    device_id: str, req: QuarantineRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Admin: quarantine a device. Device enters lockdown mode."""
    try:
        device = await quarantine_device(db, device_id, req.reason, actor=admin.username)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    await log_audit(db, actor=admin.username, action="device.quarantine",
                    target_type="device", target_id=device_id,
                    detail={"reason": req.reason})

    return _device_to_read(device)


@router.post("/{device_id}/unquarantine", response_model=DeviceRead)
async def unquarantine_device_route(
    device_id: str, db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Admin: remove quarantine from a device."""
    try:
        device = await unquarantine_device(db, device_id, actor=admin.username)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    await log_audit(db, actor=admin.username, action="device.unquarantine",
                    target_type="device", target_id=device_id)

    return _device_to_read(device)


@router.get("/{device_id}/events", response_model=EventListResponse)
async def get_device_events(
    device_id: str,
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Admin: get events for a specific device."""
    device = await get_device(db, device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Device {device_id} not found")

    events, next_cursor = await query_events(
        db, cursor=cursor, limit=limit, device_id=device_id,
    )
    return EventListResponse(
        data=[_event_to_read(e) for e in events],
        pagination={"cursor": next_cursor, "limit": limit},
    )


@router.get("/{device_id}/policy", response_model=DevicePolicyResponse)
async def get_device_policy_route(device_id: str, db: AsyncSession = Depends(get_db)):
    """Device/Admin: get current effective policy for a device."""
    device = await get_device(db, device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Device {device_id} not found")

    # Try DB first, fall back to filesystem
    from fleetguard.services.policy_service import get_effective_policy_for_device as get_policy_yaml
    yaml_content = await get_policy_yaml(db, device)

    return DevicePolicyResponse(
        device_id=device.device_id,
        policy_id=device.policy_id or "default",
        policy_version=device.policy_version,
        yaml_content=yaml_content,
    )
