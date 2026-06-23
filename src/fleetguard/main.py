from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as aioredis

from fleetguard.config import settings
from fleetguard.database import engine, async_session_factory
from fleetguard.api.router import api_router
from fleetguard.websocket.handlers import router as ws_router
from fleetguard.websocket.manager import connection_manager


async def background_mark_offline_devices():
    """Periodically mark stale devices as offline."""
    while True:
        try:
            async with async_session_factory() as db:
                from fleetguard.services.device_service import mark_offline_stale_devices
                await mark_offline_stale_devices(db)
                await db.commit()
        except Exception:
            pass
        await asyncio.sleep(30)


async def background_expire_approvals():
    """Periodically expire stale approvals."""
    while True:
        try:
            async with async_session_factory() as db:
                from datetime import datetime, timezone
                from sqlalchemy import update
                from fleetguard.models.approval import Approval
                stmt = (
                    update(Approval)
                    .where(
                        Approval.status == "pending",
                        Approval.expires_at < datetime.now(timezone.utc),
                    )
                    .values(status="expired")
                )
                await db.execute(stmt)
                await db.commit()
        except Exception:
            pass
        await asyncio.sleep(30)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        app.state.redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        await connection_manager.initialize(app.state.redis)
        print(f"  Redis connected: {settings.redis_url}")
    except Exception:
        app.state.redis = None
        print(f"  ⚠️  Redis unavailable — WebSocket push disabled")

    # Background tasks
    offline_task = asyncio.create_task(background_mark_offline_devices())
    approval_task = asyncio.create_task(background_expire_approvals())

    print(f"🚀 {settings.app_name} started on http://0.0.0.0:8000")
    print(f"   API docs: http://localhost:8000/docs")

    yield

    # Shutdown
    offline_task.cancel()
    approval_task.cancel()
    try:
        await offline_task
        await approval_task
    except asyncio.CancelledError:
        pass

    await app.state.redis.close()
    await engine.dispose()
    print(f"🛑 {settings.app_name} stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount routers
    app.include_router(api_router)
    app.include_router(ws_router)

    @app.get("/health")
    async def health_check():
        return {"status": "ok", "service": settings.app_name}

    return app


app = create_app()
