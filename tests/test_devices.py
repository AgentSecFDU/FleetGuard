"""Device endpoint tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_login(client: AsyncClient, admin_user, db_session):
    """Test admin login returns JWT tokens."""
    resp = await client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "admin123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


@pytest.mark.asyncio
async def test_admin_login_invalid(client: AsyncClient, admin_user):
    """Test login with wrong password."""
    resp = await client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "wrong",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_enrollment_token(client: AsyncClient, admin_token):
    """Test admin can create an enrollment token."""
    resp = await client.post(
        "/api/v1/auth/enrollment-token",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert data["token"].startswith("fget_")
    assert "token_prefix" in data
    assert "expires_at" in data


@pytest.mark.asyncio
async def test_device_enroll(client: AsyncClient, enrollment_token):
    """Test device enrollment with valid token."""
    resp = await client.post("/api/v1/devices/enroll", json={
        "enrollment_token": enrollment_token,
        "device_id": "fg-dev-unique-001",
        "hostname": "alice-macbook",
        "os": "macOS",
        "os_version": "15.0",
        "username": "alice",
        "openclaw_version": "1.0.0",
        "plugin_version": "0.1.0",
        "sidecar_version": "0.1.0",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["device_id"] == "fg-dev-unique-001"
    assert "device_token" in data
    assert data["device_token"].startswith("fgdt_")


@pytest.mark.asyncio
async def test_device_enroll_duplicate(client: AsyncClient, enrollment_token):
    """Test enrolling the same device_id twice fails."""
    # First enrollment
    resp = await client.post("/api/v1/devices/enroll", json={
        "enrollment_token": enrollment_token,
        "device_id": "fg-dev-dup-001",
        "hostname": "dup-macbook",
        "os": "macOS",
        "username": "dupuser",
    })
    assert resp.status_code == 200

    # Duplicate - should fail (enrollment token is already used)
    resp = await client.post("/api/v1/devices/enroll", json={
        "enrollment_token": enrollment_token,
        "device_id": "fg-dev-dup-002",
        "hostname": "dup2-macbook",
        "os": "macOS",
        "username": "dupuser2",
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_device_heartbeat(client: AsyncClient, device_token):
    """Test device heartbeat."""
    resp = await client.post(
        "/api/v1/devices/heartbeat",
        json={
            "device_id": "fg-dev-test-001",
            "status": "online",
            "current_sessions": 2,
            "active_agent_runs": 1,
            "policy_version": 1,
            "quarantine": False,
            "timestamp": "2026-06-23T10:00:10Z",
        },
        headers={"Authorization": f"Bearer {device_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_list_devices(client: AsyncClient, admin_token, device_token):
    """Test admin can list devices."""
    resp = await client.get(
        "/api/v1/devices/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert "pagination" in data
    assert len(data["data"]) >= 1


@pytest.mark.asyncio
async def test_get_device_detail(client: AsyncClient, admin_token, device_token):
    """Test admin can get device detail."""
    resp = await client.get(
        "/api/v1/devices/fg-dev-test-001",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["device_id"] == "fg-dev-test-001"
    assert data["hostname"] == "test-macbook"


@pytest.mark.asyncio
async def test_quarantine_device(client: AsyncClient, admin_token, device_token):
    """Test admin can quarantine a device."""
    resp = await client.post(
        "/api/v1/devices/fg-dev-test-001/quarantine",
        json={"reason": "Suspicious activity detected"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["quarantine"] is True
    assert data["status"] == "quarantined"


@pytest.mark.asyncio
async def test_unquarantine_device(client: AsyncClient, admin_token, device_token):
    """Test admin can unquarantine a device."""
    # First quarantine
    await client.post(
        "/api/v1/devices/fg-dev-test-001/quarantine",
        json={"reason": "Test quarantine"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    # Then unquarantine
    resp = await client.post(
        "/api/v1/devices/fg-dev-test-001/unquarantine",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["quarantine"] is False
    assert data["status"] == "online"


@pytest.mark.asyncio
async def test_get_user_info(client: AsyncClient, admin_token):
    """Test getting current user info."""
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "admin"
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_token_refresh(client: AsyncClient, admin_user):
    """Test token refresh."""
    # First login
    login_resp = await client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "admin123",
    })
    refresh_token = login_resp.json()["refresh_token"]

    # Refresh
    resp = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient):
    """Test accessing admin endpoints without auth."""
    resp = await client.get("/api/v1/devices/")
    assert resp.status_code == 401
