"""Event ORM model."""

from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from fleetguard.models.base import Base, TimestampMixin


class Event(Base, TimestampMixin):
    __tablename__ = "events"

    event_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    device_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    agent_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    run_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tool_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tool_category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    input_provenance: Mapped[str | None] = mapped_column(String(100), nullable=True)
    params_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    params_redacted_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    risk_score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    risk_labels_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    policy_decision: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    policy_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    policy_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    content_uploaded: Mapped[bool] = mapped_column(default=False)
