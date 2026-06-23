"""Sidecar configuration — reads from ~/.fleetguard/config.json and env vars."""

import json
import os
from pathlib import Path
from dataclasses import dataclass, field, asdict

FLEETGUARD_DIR = Path.home() / ".fleetguard"
CONFIG_PATH = FLEETGUARD_DIR / "config.json"
POLICY_CACHE_PATH = FLEETGUARD_DIR / "policy-cache.json"
EVENT_QUEUE_PATH = FLEETGUARD_DIR / "events.queue.jsonl"


@dataclass
class SidecarConfig:
    # Identity
    device_id: str = ""
    hostname: str = ""
    username: str = ""
    os_name: str = ""
    os_version: str = ""

    # Control Center
    control_center_url: str = "http://localhost:8000"
    device_token: str = ""

    # Local server
    local_api_host: str = "127.0.0.1"
    local_api_port: int = 18900

    # Intervals
    heartbeat_interval: int = 10
    policy_sync_interval: int = 30
    event_upload_interval: int = 5

    # Plugin info
    openclaw_version: str = ""
    plugin_version: str = "0.1.0"
    sidecar_version: str = "0.1.0"

    # Enrollment
    enrollment_token: str = ""

    # Runtime state
    quarantine: bool = False
    current_sessions: int = 0
    active_agent_runs: int = 0
    last_event_id: str = ""
    policy_version: int = 0

    def save(self):
        FLEETGUARD_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load(cls) -> "SidecarConfig":
        if CONFIG_PATH.exists():
            data = json.loads(CONFIG_PATH.read_text())
            return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        return cls()

    @classmethod
    def load_or_create(cls) -> "SidecarConfig":
        cfg = cls.load()
        # Auto-detect host info
        if not cfg.hostname:
            cfg.hostname = os.environ.get("FG_HOSTNAME", "")
            if not cfg.hostname:
                import socket
                cfg.hostname = socket.gethostname()
        if not cfg.username:
            cfg.username = os.environ.get("FG_USERNAME", os.environ.get("USER", os.environ.get("USERNAME", "unknown")))
        if not cfg.os_name:
            import platform
            cfg.os_name = os.environ.get("FG_OS", platform.system())
            cfg.os_version = platform.release()
        # Env overrides
        if os.environ.get("FG_CONTROL_CENTER_URL"):
            cfg.control_center_url = os.environ["FG_CONTROL_CENTER_URL"]
        if os.environ.get("FG_ENROLLMENT_TOKEN"):
            cfg.enrollment_token = os.environ["FG_ENROLLMENT_TOKEN"]
        if os.environ.get("FG_DEVICE_ID"):
            cfg.device_id = os.environ["FG_DEVICE_ID"]
        return cfg
