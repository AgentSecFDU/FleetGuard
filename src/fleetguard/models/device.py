"""Device ORM model."""

from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from fleetguard.models.base import Base, UpdatedAtMixin


class Device(Base, UpdatedAtMixin):
    __tablename__ = "devices"

    device_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    os: Mapped[str] = mapped_column(String(100), nullable=False)
    os_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    openclaw_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    plugin_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sidecar_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="offline", index=True)
    quarantine: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    quarantine_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    quarantined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    policy_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    policy_version: Mapped[int] = mapped_column(Integer, default=1)
    device_token_hash: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    current_sessions: Mapped[int] = mapped_column(Integer, default=0)
    active_agent_runs: Mapped[int] = mapped_column(Integer, default=0)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
