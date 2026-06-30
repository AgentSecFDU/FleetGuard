"""EnrollmentToken ORM model."""

from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from agentfleetcontrol.models.base import Base, TimestampMixin


class EnrollmentToken(Base, TimestampMixin):
    __tablename__ = "enrollment_tokens"

    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    token_prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    used_by_device: Mapped[str | None] = mapped_column(String(255), nullable=True)
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
