"""Heartbeat loop — periodically reports device status to Control Center."""

import asyncio
from datetime import datetime, timezone

import httpx

from fleetguard_sidecar.config import SidecarConfig


class HeartbeatLoop:
    """Sends periodic heartbeat to Control Center."""

    def __init__(self, cfg: SidecarConfig):
        self.cfg = cfg
        self._online = True

    async def send(self) -> bool:
        """Send a single heartbeat. Returns True if successful."""
        try:
            async with httpx.AsyncClient(base_url=self.cfg.control_center_url, timeout=10.0) as client:
                headers = {"Authorization": f"Bearer {self.cfg.device_token}"}
                resp = await client.post("/api/v1/devices/heartbeat", json={
                    "device_id": self.cfg.device_id,
                    "status": "online" if self._online else "offline",
                    "current_sessions": self.cfg.current_sessions,
                    "active_agent_runs": self.cfg.active_agent_runs,
                    "policy_version": self.cfg.policy_version,
                    "quarantine": self.cfg.quarantine,
                    "last_event_id": self.cfg.last_event_id,
                    "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                }, headers=headers)
                resp.raise_for_status()
                return True
        except Exception:
            return False

    async def run(self):
        """Main heartbeat loop."""
        iteration = 0
        while True:
            await asyncio.sleep(self.cfg.heartbeat_interval)
            iteration += 1
            ok = await self.send()
            self._online = ok  # Track connectivity
            if iteration % 6 == 0:  # Print every ~60s
                status = "🟢" if ok else "🔴"
                print(f"  {status} Heartbeat #{iteration} sent")
