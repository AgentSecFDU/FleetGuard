"""Authentication schemas."""

from pydantic import BaseModel, Field
from typing import Optional


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseModel):
    refresh_token: str


class EnrollmentTokenRequest(BaseModel):
    pass  # Admin auth suffices


class EnrollmentTokenResponse(BaseModel):
    token: str
    token_prefix: str
    expires_at: str
    message: str = "Save this token - it will not be shown again."


class DeviceEnrollRequest(BaseModel):
    enrollment_token: str
    device_id: str
    hostname: str
    os: str
    os_version: Optional[str] = None
    username: str
    openclaw_version: Optional[str] = None
    plugin_version: Optional[str] = None
    sidecar_version: Optional[str] = None


class DeviceEnrollResponse(BaseModel):
    device_id: str
    device_token: str
    message: str = "Device enrolled successfully. Store this token securely."


class UserInfo(BaseModel):
    username: str
    role: str
    is_active: bool
