"""Local event queue — buffers events before batch upload to Control Center."""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx

from afc_sidecar.config import SidecarConfig, EVENT_QUEUE_PATH


class EventQueue:
    """Thread-safe event buffer with file-based persistence."""

    def __init__(self, cfg: SidecarConfig):
        self.cfg = cfg
        self._queue: list[dict] = []
        self._lock = asyncio.Lock()
        self._load_from_disk()

    def _load_from_disk(self):
        """Load any persisted events from the queue file."""
        if EVENT_QUEUE_PATH.exists():
            try:
                lines = EVENT_QUEUE_PATH.read_text().strip().split("\n")
                self._queue = [json.loads(line) for line in lines if line.strip()]
            except Exception:
                self._queue = []

    def _save_to_disk(self):
        """Persist the queue to disk."""
        EVENT_QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
        content = "\n".join(json.dumps(e) for e in self._queue)
        EVENT_QUEUE_PATH.write_text(content)

    async def push(self, event: dict):
        """Add an event to the queue (called by Plugin via local API)."""
        async with self._lock:
            if "event_id" not in event:
                event["event_id"] = f"evt_{uuid.uuid4().hex[:12]}"
            if "timestamp" not in event:
                event["timestamp"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            event["device_id"] = self.cfg.device_id
            self._queue.append(event)
            self._save_to_disk()

    async def flush(self) -> int:
        """Upload all queued events to Control Center. Returns number uploaded."""
        async with self._lock:
            if not self._queue:
                return 0

            events_to_send = list(self._queue)

        try:
            async with httpx.AsyncClient(base_url=self.cfg.control_center_url, timeout=30.0) as client:
                headers = {"Authorization": f"Bearer {self.cfg.device_token}"}
                resp = await client.post("/api/v1/events/batch",
                    json={"events": events_to_send}, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            accepted = data.get("accepted", 0)
            async with self._lock:
                self._queue = self._queue[accepted:]  # Remove successfully uploaded
                self._save_to_disk()

            if accepted > 0:
                self.cfg.last_event_id = events_to_send[accepted - 1].get("event_id", "")
                self.cfg.save()
            return accepted

        except Exception:
            return 0

    async def upload_worker(self):
        """Background worker that periodically flushes the queue."""
        while True:
            await asyncio.sleep(self.cfg.event_upload_interval)
            try:
                sent = await self.flush()
                if sent > 0:
                    print(f"  📤 Uploaded {sent} events, {len(self._queue)} remaining")
            except Exception:
                pass

    @property
    def queue_size(self) -> int:
        return len(self._queue)
