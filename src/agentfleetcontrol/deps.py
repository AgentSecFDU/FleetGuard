"""FastAPI shared dependencies for authentication."""

from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError

from agentfleetcontrol.database import get_db
from agentfleetcontrol.utils.crypto import decode_token, verify_token
from agentfleetcontrol.models.admin_user import AdminUser
from agentfleetcontrol.models.device import Device

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> AdminUser:
    """Validate JWT and return the current admin user."""
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization header")

    token = credentials.credentials
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    result = await db.execute(select(AdminUser).where(AdminUser.username == username))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return user


async def get_current_device(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Device:
    """Validate device API token and return the device."""
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization header")

    token = credentials.credentials
    # The token is an opaque bearer; look up all devices with non-null hashes
    result = await db.execute(select(Device).where(Device.device_token_hash.is_not(None)))
    devices = result.scalars().all()

    for device in devices:
        if device.device_token_hash and verify_token(token, device.device_token_hash):
            return device

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device token")


async def get_valid_enrollment_token(
    enrollment_token: str = Header(alias="X-Enrollment-Token", default=None),
    db: AsyncSession = Depends(get_db),
) -> str:
    """Validate enrollment token from header. Returns the raw token if valid."""
    if not enrollment_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing enrollment token")

    from agentfleetcontrol.models.enrollment_token import EnrollmentToken
    from datetime import datetime, timezone

    result = await db.execute(
        select(EnrollmentToken).where(
            EnrollmentToken.used == False,
            EnrollmentToken.expires_at > datetime.now(timezone.utc),
        )
    )
    tokens = result.scalars().all()

    for t in tokens:
        if verify_token(enrollment_token, t.token_hash):
            return enrollment_token

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired enrollment token")


# Optional admin auth (for endpoints that work both authenticated and not)
async def get_optional_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> AdminUser | None:
    """Like get_current_admin but returns None if no auth provided."""
    if not credentials:
        return None
    try:
        return await get_current_admin(credentials, db)
    except HTTPException:
        return None
