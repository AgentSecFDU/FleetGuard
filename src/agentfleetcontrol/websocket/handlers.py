"""WebSocket handler for real-time dashboard updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    """Real-time event stream for the admin dashboard.

    Authenticate via query parameter: /ws/dashboard?token=<JWT>
    """
    from agentfleetcontrol.websocket.manager import connection_manager

    await connection_manager.connect(websocket, channel="dashboard")
    try:
        while True:
            # Keep connection alive, handle incoming pong messages
            data = await websocket.receive_text()
            # Client can send pings; we ignore other messages for now
    except WebSocketDisconnect:
        await connection_manager.disconnect(websocket, channel="dashboard")
