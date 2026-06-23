"""initial

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-23
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # admin_users
    op.create_table(
        "admin_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("username", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # devices
    op.create_table(
        "devices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("device_id", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("hostname", sa.String(255), nullable=False),
        sa.Column("os", sa.String(100), nullable=False),
        sa.Column("os_version", sa.String(100), nullable=True),
        sa.Column("username", sa.String(255), nullable=False, index=True),
        sa.Column("openclaw_version", sa.String(50), nullable=True),
        sa.Column("plugin_version", sa.String(50), nullable=True),
        sa.Column("sidecar_version", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="offline", index=True),
        sa.Column("quarantine", sa.Boolean, nullable=False, server_default=sa.text("false"), index=True),
        sa.Column("quarantine_reason", sa.Text, nullable=True),
        sa.Column("quarantined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("policy_id", sa.String(255), nullable=True),
        sa.Column("policy_version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("device_token_hash", sa.String(255), unique=True, nullable=True),
        sa.Column("current_sessions", sa.Integer, nullable=False, server_default="0"),
        sa.Column("active_agent_runs", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # events
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_id", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("event_type", sa.String(100), nullable=False, index=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("device_id", sa.String(255), nullable=False, index=True),
        sa.Column("user_id", sa.String(255), nullable=True),
        sa.Column("hostname", sa.String(255), nullable=True),
        sa.Column("session_id", sa.String(255), nullable=True, index=True),
        sa.Column("agent_id", sa.String(255), nullable=True),
        sa.Column("run_id", sa.String(255), nullable=True),
        sa.Column("tool_name", sa.String(255), nullable=True),
        sa.Column("tool_category", sa.String(100), nullable=True, index=True),
        sa.Column("input_provenance", sa.String(100), nullable=True),
        sa.Column("params_summary", sa.Text, nullable=True),
        sa.Column("params_redacted_json", postgresql.JSON, nullable=True),
        sa.Column("risk_score", sa.Integer, nullable=False, server_default="0", index=True),
        sa.Column("risk_labels_json", postgresql.JSON, nullable=True),
        sa.Column("policy_decision", sa.String(50), nullable=True, index=True),
        sa.Column("policy_id", sa.String(255), nullable=True),
        sa.Column("policy_version", sa.Integer, nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("severity", sa.String(20), nullable=True, index=True),
        sa.Column("content_uploaded", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_events_cursor", "events", ["created_at", "id"], postgresql_using="btree")
    op.create_index("ix_events_device_created", "events", ["device_id", "created_at"])

    # policies
    op.create_table(
        "policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("policy_id", sa.String(255), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("yaml_content", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft", index=True),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_policies_policy_version", "policies", ["policy_id", "version"], unique=True)

    # approvals
    op.create_table(
        "approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("approval_id", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("device_id", sa.String(255), nullable=False, index=True),
        sa.Column("event_id", sa.String(255), nullable=True),
        sa.Column("session_id", sa.String(255), nullable=True),
        sa.Column("run_id", sa.String(255), nullable=True),
        sa.Column("tool_name", sa.String(255), nullable=True),
        sa.Column("params_summary", sa.Text, nullable=True),
        sa.Column("risk_score", sa.Integer, nullable=True),
        sa.Column("risk_labels_json", postgresql.JSON, nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending", index=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("decided_by", sa.String(255), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_approvals_status_expires", "approvals", ["status", "expires_at"])

    # audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("actor", sa.String(255), nullable=False, index=True),
        sa.Column("action", sa.String(100), nullable=False, index=True),
        sa.Column("target_type", sa.String(100), nullable=True, index=True),
        sa.Column("target_id", sa.String(255), nullable=True),
        sa.Column("detail_json", postgresql.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_created", "audit_logs", ["created_at"])

    # enrollment_tokens
    op.create_table(
        "enrollment_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("token_hash", sa.String(255), nullable=False, index=True),
        sa.Column("token_prefix", sa.String(20), nullable=False),
        sa.Column("used_by_device", sa.String(255), nullable=True),
        sa.Column("used", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_enrollment_tokens_used_expires", "enrollment_tokens", ["used", "expires_at"])


def downgrade() -> None:
    op.drop_table("enrollment_tokens")
    op.drop_table("audit_logs")
    op.drop_table("approvals")
    op.drop_table("policies")
    op.drop_table("events")
    op.drop_table("devices")
    op.drop_table("admin_users")
