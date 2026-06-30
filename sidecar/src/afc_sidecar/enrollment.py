"""Device enrollment flow."""

import uuid
import httpx
from afc_sidecar.config import SidecarConfig


async def enroll(cfg: SidecarConfig) -> bool:
    """Enroll this device with the AgentFleetControl Control Center.

    If no device_id is set, generates one.
    If no enrollment_token is set, prompts the user.
    Returns True if enrollment succeeded.
    """
    # Generate device ID if needed
    if not cfg.device_id:
        cfg.device_id = f"afc-dev-{uuid.uuid4().hex[:8]}"

    # Get enrollment token
    if not cfg.enrollment_token:
        print(f"\n🔑 AgentFleetControl Device Enrollment")
        print(f"   Device ID: {cfg.device_id}")
        print(f"   Hostname:  {cfg.hostname}")
        cfg.enrollment_token = input("   Enter enrollment token: ").strip()

    if not cfg.enrollment_token:
        print("❌ No enrollment token provided. Skipping enrollment.")
        return False

    print(f"\n📡 Enrolling device {cfg.device_id} with {cfg.control_center_url}...")

    try:
        async with httpx.AsyncClient(base_url=cfg.control_center_url, timeout=15.0) as client:
            resp = await client.post("/api/v1/devices/enroll", json={
                "enrollment_token": cfg.enrollment_token,
                "device_id": cfg.device_id,
                "hostname": cfg.hostname,
                "os": cfg.os_name,
                "os_version": cfg.os_version,
                "username": cfg.username,
                "openclaw_version": cfg.openclaw_version,
                "plugin_version": cfg.plugin_version,
                "sidecar_version": cfg.sidecar_version,
            })
            resp.raise_for_status()
            data = resp.json()

        cfg.device_token = data["device_token"]
        cfg.device_id = data["device_id"]
        cfg.save()
        print(f"✅ Device enrolled successfully!")
        print(f"   Token saved to {cfg.config_path if hasattr(cfg, 'config_path') else '~/.afc/config.json'}")
        return True

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 400 and "already registered" in str(e.response.text):
            print(f"⚠️  Device already registered. If you have the token, set it in ~/.afc/config.json")
            print(f"   Or delete ~/.afc/config.json and re-enroll.")
            return False
        print(f"❌ Enrollment failed: {e.response.status_code} - {e.response.text}")
        return False
    except Exception as e:
        print(f"❌ Cannot reach Control Center at {cfg.control_center_url}: {e}")
        return False


def is_enrolled(cfg: SidecarConfig) -> bool:
    """Check if the device has a valid enrollment."""
    return bool(cfg.device_id and cfg.device_token)
