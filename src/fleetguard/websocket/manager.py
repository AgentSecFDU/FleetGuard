"""WebSocket connection manager with Redis pub/sub support."""

import asyncio
from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections and broadcasts via Redis pub/sub."""

    def __init__(self):
        self._connections: dict[str, set[WebSocket]] = {}
        self._redis = None
        self._pubsub_task: asyncio.Task | None = None

    async def initialize(self, redis_client):
        """Initialize with a Redis client and start pubsub listener."""
        self._redis = redis_client
        self._pubsub_task = asyncio.create_task(self._listen_redis())

    async def connect(self, websocket: WebSocket, channel: str = "dashboard"):
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        self._connections.setdefault(channel, set()).add(websocket)
        await websocket.send_json({
            "type": "connected",
            "data": {"channel": channel}
        })

    async def disconnect(self, websocket: WebSocket, channel: str = "dashboard"):
        """Unregister a WebSocket connection."""
        if channel in self._connections:
            self._connections[channel].discard(websocket)
            if not self._connections[channel]:
                del self._connections[channel]

    async def broadcast_to_channel(self, channel: str, message: dict):
        """Send a message to all connections in a channel."""
        if channel in self._connections:
            dead: list[WebSocket] = []
            for ws in self._connections[channel]:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self._connections[channel].discard(ws)

    async def broadcast_event(self, event_data: dict):
        """High-level: publish an event notification to Redis for fan-out."""
        if self._redis:
            import json
            await self._redis.publish("events:publish", json.dumps(event_data, default=str))
        # Also broadcast to local connections immediately
        await self.broadcast_to_channel("dashboard", {
            "type": "event",
            "data": event_data,
        })

    async def _listen_redis(self):
        """Background task: listen for Redis pub/sub messages and fan out locally."""
        if not self._redis:
            return
        import json
        pubsub = self._redis.pubsub()
        await pubsub.subscribe("events:publish")
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        await self.broadcast_to_channel("dashboard", {
                            "type": "event",
                            "data": data,
                        })
                    except Exception:
                        pass
        except asyncio.CancelledError:
            await pubsub.unsubscribe("events:publish")


# Singleton
connection_manager = ConnectionManager()
