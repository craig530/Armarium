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


# ── Cookie-based auth (browser SPA) ─────────────────────────────────────────

async def test_login_sets_httponly_cookie(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "testpass123"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.cookies

    set_cookie = resp.headers["set-cookie"]
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie


async def test_me_via_cookie_only(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "testpass123"},
    )
    assert resp.status_code == 200

    # No Authorization header — the cookie set above authenticates this request.
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin"


async def test_logout_clears_cookie(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "testpass123"},
    )
    assert resp.status_code == 200

    resp = await client.post("/api/v1/auth/logout")
    assert resp.status_code == 200

    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


# ── Auth enforcement ────────────────────────────────────────────────────────

async def test_media_requires_auth(client):
    resp = await client.get("/api/v1/media")
    assert resp.status_code == 401


async def test_locations_requires_auth(client):
    resp = await client.get("/api/v1/locations")
    assert resp.status_code == 401
