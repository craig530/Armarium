"""
Basic smoke tests for the Armarium API.
Run: cd backend && pip install -r requirements.txt && pytest
"""
import pytest
import os
from httpx import AsyncClient, ASGITransport

# Use an in-memory SQLite database for tests
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "testpass123")
os.environ.setdefault("JWT_SECRET", "test-secret-key-not-for-production")
os.environ.setdefault("COVERS_DIR", "/tmp/armarium_test_covers")
os.environ.setdefault("BACKUP_DIR", "/tmp/armarium_test_backups")


@pytest.fixture
async def client():
    from app.main import app, lifespan

    async with lifespan(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c


@pytest.fixture
async def auth_headers(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "testpass123"},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ── System ──────────────────────────────────────────────────────────────────

async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ── Auth ────────────────────────────────────────────────────────────────────

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


# ── Media CRUD ──────────────────────────────────────────────────────────────

async def test_media_crud(client, auth_headers):
    # Create
    resp = await client.post(
        "/api/v1/media",
        json={"title": "Test Album", "media_type": "cd", "artist": "Test Artist", "year": 2024},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    item = resp.json()
    item_id = item["id"]
    assert item["title"] == "Test Album"
    assert item["media_type"] == "cd"

    # Read
    resp = await client.get(f"/api/v1/media/{item_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["artist"] == "Test Artist"

    # List
    resp = await client.get("/api/v1/media", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1

    # Search
    resp = await client.get("/api/v1/media?q=Test+Album", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1

    # Update
    resp = await client.put(
        f"/api/v1/media/{item_id}",
        json={"title": "Updated Album"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Album"

    # Delete
    resp = await client.delete(f"/api/v1/media/{item_id}", headers=auth_headers)
    assert resp.status_code == 204

    # Confirm gone
    resp = await client.get(f"/api/v1/media/{item_id}", headers=auth_headers)
    assert resp.status_code == 404


# ── Locations ───────────────────────────────────────────────────────────────

async def test_location_crud(client, auth_headers):
    # Create root
    resp = await client.post(
        "/api/v1/locations",
        json={"name": "Living Room"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    root_id = resp.json()["id"]

    # Create child
    resp = await client.post(
        "/api/v1/locations",
        json={"name": "Bookshelf", "parent_id": root_id},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    child_id = resp.json()["id"]

    # List — tree structure
    resp = await client.get("/api/v1/locations", headers=auth_headers)
    assert resp.status_code == 200

    # Delete child first, then root
    resp = await client.delete(f"/api/v1/locations/{child_id}", headers=auth_headers)
    assert resp.status_code == 204
    resp = await client.delete(f"/api/v1/locations/{root_id}", headers=auth_headers)
    assert resp.status_code == 204


async def test_location_reparent_rejects_cycle(client, auth_headers):
    root_resp = await client.post("/api/v1/locations", json={"name": "Root"}, headers=auth_headers)
    root_id = root_resp.json()["id"]

    child_resp = await client.post(
        "/api/v1/locations",
        json={"name": "Child", "parent_id": root_id},
        headers=auth_headers,
    )
    child_id = child_resp.json()["id"]

    # Reparenting root under its own child would create a 2-node cycle.
    resp = await client.put(
        f"/api/v1/locations/{root_id}",
        json={"parent_id": child_id},
        headers=auth_headers,
    )
    assert resp.status_code == 400

    # Tree should still be intact and listable without recursing forever.
    resp = await client.get("/api/v1/locations", headers=auth_headers)
    assert resp.status_code == 200


# ── Stats ────────────────────────────────────────────────────────────────────

async def test_stats(client, auth_headers):
    resp = await client.get("/api/v1/media/stats", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "total" in body
    assert "by_type" in body


# ── Export ───────────────────────────────────────────────────────────────────

async def test_export_json(client, auth_headers):
    resp = await client.get("/api/v1/library/export?format=json", headers=auth_headers)
    assert resp.status_code == 200
    assert "items" in resp.json()


async def test_export_csv(client, auth_headers):
    resp = await client.get("/api/v1/library/export?format=csv", headers=auth_headers)
    assert resp.status_code == 200
    assert b"title" in resp.content
