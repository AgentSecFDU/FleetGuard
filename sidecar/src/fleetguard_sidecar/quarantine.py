"""Quarantine controller — applies and manages device/session isolation."""

import json
from pathlib import Path
from datetime import datetime, timezone

from fleetguard_sidecar.config import SidecarConfig

LOCKDOWN_POLICY_PATH = Path(__file__).parent.parent.parent.parent.parent / "policies" / "lockdown.yaml"


class QuarantineController:
    """Manages quarantine state for the device."""

    def __init__(self, cfg: SidecarConfig):
        self.cfg = cfg
        self._session_quarantines: set[str] = set()

    def quarantine_device(self, reason: str = "Manual quarantine") -> str:
        """Quarantine the entire device — apply lockdown policy. Returns status."""
        self.cfg.quarantine = True
        self.cfg.save()
        print(f"🔒 DEVICE QUARANTINED: {reason}")
        return "quarantined"

    def unquarantine_device(self) -> str:
        """Remove device quarantine."""
        self.cfg.quarantine = False
        self.cfg.save()
        print(f"🔓 Device quarantine lifted")
        return "online"

    def quarantine_session(self, session_id: str, reason: str = "Suspicious activity") -> str:
        """Quarantine a specific session."""
        self._session_quarantines.add(session_id)
        print(f"🔒 Session {session_id} quarantined: {reason}")
        return "quarantined"

    def unquarantine_session(self, session_id: str) -> str:
        """Remove session quarantine."""
        self._session_quarantines.discard(session_id)
        return "online"

    def is_quarantined(self, session_id: str | None = None) -> bool:
        """Check if device or specific session is quarantined."""
        if self.cfg.quarantine:
            return True
        if session_id and session_id in self._session_quarantines:
            return True
        return False

    def get_lockdown_policy(self) -> dict | None:
        """Load the lockdown policy from disk."""
        if LOCKDOWN_POLICY_PATH.exists():
            import yaml
            return yaml.safe_load(LOCKDOWN_POLICY_PATH.read_text())
        return None

    def is_tool_allowed(self, tool_category: str, session_id: str | None = None) -> bool:
        """Check if a tool category is allowed under current quarantine state."""
        if not self.is_quarantined(session_id):
            return True

        # Under quarantine, only allow safe operations
        ALLOWED_UNDER_QUARANTINE = {"event_upload", "heartbeat", "policy_sync", "read_only_chat", "local_status"}
        # Map tool categories to lockdown permissions
        SAFE_CATEGORIES = {None}  # None category = not a tool call (chat, etc.)

        if tool_category in SAFE_CATEGORIES:
            return True

        # Block everything else under quarantine
        return False
