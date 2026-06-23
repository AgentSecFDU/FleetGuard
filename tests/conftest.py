"""Shared test fixtures."""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from fleetguard.main import create_app
from fleetguard.models import Base
from fleetguard.utils.crypto import hash_password
from fleetguard.models.admin_user import AdminUser
from fleetguard.models.enrollment_token import EnrollmentToken
from fleetguard.utils.crypto import hash_token

# Use an in-memory SQLite database for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///file::memory:?cache=shared"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create a test engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """Create a fresh database session per test, with rollback."""
    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest_asyncio.fixture
def app():
    """Create the FastAPI app (no lifespan for tests)."""
    return create_app()


@pytest_asyncio.fixture
async def client(app, db_session):
    """Create an async HTTP test client."""
    from fleetguard.database import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession):
    """Create a test admin user and return it."""
    user = AdminUser(
        username="admin",
        password_hash=hash_password("admin123"),
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def admin_token(client, admin_user):
    """Get a JWT admin token."""
    resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def enrollment_token(db_session: AsyncSession, admin_user, client, admin_token):
    """Create an enrollment token for testing."""
    raw_token = "fget_test_token_for_enrollment_1234567890abcdef"
    tok = EnrollmentToken(
        token_hash=hash_token(raw_token),
        token_prefix=raw_token[:12],
        used=False,
        created_by="admin",
    )
    from datetime import datetime, timezone, timedelta
    tok.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    db_session.add(tok)
    await db_session.flush()
    return raw_token


@pytest_asyncio.fixture
async def device_token(client, admin_token, enrollment_token):
    """Enroll a test device and return the device token."""
    resp = await client.post("/api/v1/devices/enroll", json={
        "enrollment_token": enrollment_token,
        "device_id": "fg-dev-test-001",
        "hostname": "test-macbook",
        "os": "macOS",
        "os_version": "15.0",
        "username": "testuser",
        "openclaw_version": "1.0.0",
        "plugin_version": "0.1.0",
        "sidecar_version": "0.1.0",
    })
    assert resp.status_code == 200
    return resp.json()["device_token"]
