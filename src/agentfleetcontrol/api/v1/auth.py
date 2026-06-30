"""Authentication endpoints."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentfleetcontrol.database import get_db
from agentfleetcontrol.deps import get_current_admin
from agentfleetcontrol.models.admin_user import AdminUser
from agentfleetcontrol.models.enrollment_token import EnrollmentToken
from agentfleetcontrol.utils.crypto import hash_password, verify_password, create_access_token, create_refresh_token, decode_token, hash_token
from agentfleetcontrol.utils.id_generator import generate_enrollment_token
from agentfleetcontrol.schemas.auth import (
    LoginRequest, TokenResponse, RefreshRequest,
    EnrollmentTokenResponse, UserInfo,
)
from agentfleetcontrol.config import settings

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Admin login - returns JWT access and refresh tokens."""
    result = await db.execute(select(AdminUser).where(AdminUser.username == req.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)

    # Generate tokens
    token_data = {"sub": user.username, "role": user.role}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(req: RefreshRequest):
    """Refresh an expired access token using a refresh token."""
    try:
        payload = decode_token(req.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    username = payload.get("sub")
    role = payload.get("role", "user")
    token_data = {"sub": username, "role": role}
    access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/enrollment-token", response_model=EnrollmentTokenResponse)
async def create_enrollment_token(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Admin: generate a one-time device enrollment token."""
    raw_token, prefix, _ = generate_enrollment_token()
    token_hash = hash_token(raw_token)

    from datetime import timedelta
    expires = datetime.now(timezone.utc) + timedelta(hours=1)

    entry = EnrollmentToken(
        token_hash=token_hash,
        token_prefix=prefix,
        expires_at=expires,
        created_by=admin.username,
    )
    db.add(entry)

    return EnrollmentTokenResponse(
        token=raw_token,
        token_prefix=prefix,
        expires_at=expires.isoformat(),
    )


@router.get("/me", response_model=UserInfo)
async def get_current_user(admin: AdminUser = Depends(get_current_admin)):
    """Return current admin user info."""
    return UserInfo(
        username=admin.username,
        role=admin.role,
        is_active=admin.is_active,
    )
