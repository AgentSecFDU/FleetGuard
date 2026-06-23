"""Policy sync — periodically fetches latest policy from Control Center."""

import asyncio
import json

import httpx

from fleetguard_sidecar.config import SidecarConfig, POLICY_CACHE_PATH


class PolicySyncer:
    """Fetches and caches the effective policy for this device."""

    def __init__(self, cfg: SidecarConfig):
        self.cfg = cfg
        self._current_policy: dict | None = None
        self._load_cache()

    def _load_cache(self):
        """Load cached policy from disk."""
        if POLICY_CACHE_PATH.exists():
            try:
                self._current_policy = json.loads(POLICY_CACHE_PATH.read_text())
                if self._current_policy:
                    self.cfg.policy_version = self._current_policy.get("version", 0)
            except Exception:
                self._current_policy = None

    def _save_cache(self, policy_data: dict):
        """Save policy to local cache."""
        POLICY_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        POLICY_CACHE_PATH.write_text(json.dumps(policy_data, indent=2))
        self._current_policy = policy_data
        if policy_data:
            self.cfg.policy_version = policy_data.get("version", 0)
            self.cfg.save()

    async def sync(self) -> bool:
        """Fetch latest policy from Control Center. Returns True if updated."""
        try:
            async with httpx.AsyncClient(base_url=self.cfg.control_center_url, timeout=10.0) as client:
                headers = {"Authorization": f"Bearer {self.cfg.device_token}"}
                resp = await client.get(f"/api/v1/devices/{self.cfg.device_id}/policy", headers=headers)
                resp.raise_for_status()
                data = resp.json()

            new_version = data.get("policy_version", 0)
            if new_version > self.cfg.policy_version or self._current_policy is None:
                self._save_cache(data)
                print(f"  📋 Policy updated to v{new_version}")
                return True
            return False
        except Exception:
            # Offline mode: use cached policy
            return False

    async def run(self):
        """Main policy sync loop."""
        while True:
            await asyncio.sleep(self.cfg.policy_sync_interval)
            await self.sync()

    def get_policy(self) -> dict | None:
        """Get the current cached policy."""
        return self._current_policy

    def get_default_action(self) -> str:
        """Get the default action from current policy."""
        if self._current_policy:
            return self._current_policy.get("default_action", "allow")
        return "deny"  # Offline mode: deny by default

    def is_offline_policy(self) -> bool:
        """Check if we're running in offline/fallback mode."""
        return self._current_policy is None
