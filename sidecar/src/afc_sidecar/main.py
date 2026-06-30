#!/usr/bin/env python3
"""
AgentFleetControl Sidecar — Local device agent.

Usage:
  python -m afc_sidecar.main
  python -m afc_sidecar.main --enroll  # Force re-enrollment
  python -m afc_sidecar.main --control-center http://192.168.1.100:8000
"""

import argparse
import asyncio
import signal
import sys
import uuid

from afc_sidecar.config import SidecarConfig
from afc_sidecar.enrollment import enroll, is_enrolled
from afc_sidecar.heartbeat import HeartbeatLoop
from afc_sidecar.policy_sync import PolicySyncer
from afc_sidecar.event_queue import EventQueue
from afc_sidecar.quarantine import QuarantineController
from afc_sidecar.integrity import run_integrity_checks
from afc_sidecar.local_api import create_local_api


async def main():
    parser = argparse.ArgumentParser(description="AgentFleetControl Sidecar")
    parser.add_argument("--enroll", action="store_true", help="Force re-enrollment")
    parser.add_argument("--control-center", default=None, help="Control Center URL")
    parser.add_argument("--device-id", default=None, help="Device ID override")
    parser.add_argument("--api-port", type=int, default=18900, help="Local API port (default: 18900)")
    args = parser.parse_args()

    # ── Load config ─────────────────────────────────────────────────
    cfg = SidecarConfig.load_or_create()

    if args.control_center:
        cfg.control_center_url = args.control_center
    if args.device_id:
        cfg.device_id = args.device_id
    if args.api_port:
        cfg.local_api_port = args.api_port

    cfg.sidecar_version = "0.1.0"

    print("╔════════════════════════════════════════════╗")
    print("║   AgentFleetControl Sidecar v0.1.0                ║")
    print("╚════════════════════════════════════════════╝")
    print(f"   Hostname:  {cfg.hostname}")
    print(f"   OS:        {cfg.os_name} {cfg.os_version}")
    print(f"   User:      {cfg.username}")
    print(f"   Device ID: {cfg.device_id or '(not enrolled)'}")
    print(f"   Control Center: {cfg.control_center_url}")
    print(f"   Local API: http://{cfg.local_api_host}:{cfg.local_api_port}")
    print()

    # ── Enrollment ──────────────────────────────────────────────────
    if args.enroll or not is_enrolled(cfg):
        success = await enroll(cfg)
        if not success:
            print("❌ Enrollment failed. Sidecar cannot start without registration.")
            print("   Run again with --enroll to retry, or check your enrollment token.")
            sys.exit(1)

    print(f"✅ Device {cfg.device_id} is enrolled")
    print()

    # ── Initialize components ───────────────────────────────────────
    event_queue = EventQueue(cfg)
    policy_syncer = PolicySyncer(cfg)
    quarantine_ctrl = QuarantineController(cfg)

    # Initial policy sync
    print("📋 Syncing policy...")
    await policy_syncer.sync()
    print(f"   Policy v{cfg.policy_version} loaded")
    print()

    # ── Start background tasks ──────────────────────────────────────
    heartbeat_loop = HeartbeatLoop(cfg)
    bg_tasks = [
        asyncio.create_task(heartbeat_loop.run(), name="heartbeat"),
        asyncio.create_task(policy_syncer.run(), name="policy_sync"),
        asyncio.create_task(event_queue.upload_worker(), name="event_upload"),
        asyncio.create_task(run_integrity_checks(cfg, event_queue), name="integrity"),
    ]

    # ── Start local HTTP API ────────────────────────────────────────
    local_app = create_local_api(cfg, event_queue, policy_syncer, quarantine_ctrl)

    import uvicorn
    config = uvicorn.Config(
        local_app,
        host=cfg.local_api_host,
        port=cfg.local_api_port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)

    # ── Signal handling ─────────────────────────────────────────────
    shutdown_event = asyncio.Event()

    def handle_signal(sig, frame):
        print("\n🛑 Shutting down...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # ── Run ─────────────────────────────────────────────────────────
    print("🚀 Sidecar is running. Press Ctrl+C to stop.")
    print(f"   Heartbeat: every {cfg.heartbeat_interval}s")
    print(f"   Policy sync: every {cfg.policy_sync_interval}s")
    print(f"   Event upload: every {cfg.event_upload_interval}s")
    print()

    # Run API server in background
    api_task = asyncio.create_task(server.serve(), name="local_api")

    # Wait for shutdown signal
    await shutdown_event.wait()

    # Cleanup
    server.should_exit = True
    api_task.cancel()
    for task in bg_tasks:
        task.cancel()

    # Flush remaining events
    print(f"📤 Flushing {event_queue.queue_size} remaining events...")
    await event_queue.flush()

    await asyncio.gather(api_task, *bg_tasks, return_exceptions=True)
    print("👋 Sidecar stopped.")


if __name__ == "__main__":
    asyncio.run(main())
