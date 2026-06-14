"""Tests for app.api.v1.auth — login, current-user, and auth enforcement."""


async def test_login_success(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "testpass123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


async def test_login_wrong_password(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


async def test_me(client, auth_headers):
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin"
    assert resp.json()["is_admin"] is True


# ── Auth enforcement ────────────────────────────────────────────────────────

async def test_media_requires_auth(client):
    resp = await client.get("/api/v1/media")
    assert resp.status_code == 401


async def test_locations_requires_auth(client):
    resp = await client.get("/api/v1/locations")
    assert resp.status_code == 401
