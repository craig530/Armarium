"""Shared pytest fixtures, test environment setup, and helpers for the
Armarium API test suite."""
import base64
import os

import pytest
from httpx import AsyncClient, ASGITransport

# Use an in-memory SQLite database for tests
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "testpass123")
os.environ.setdefault("JWT_SECRET", "test-secret-key-not-for-production")
# The test client talks to the app over plain "http://test", but the access-
# token cookie defaults to Secure (HTTPS-only) — without this, httpx's
# cookie jar would accept the cookie from Set-Cookie but never send it back,
# breaking cookie-based auth tests.
os.environ.setdefault("COOKIE_SECURE", "false")
os.environ.setdefault("COVERS_DIR", "/tmp/armarium_test_covers")
os.environ.setdefault("BACKUP_DIR", "/tmp/armarium_test_backups")
os.environ.setdefault("LOCATION_ICONS_DIR", "/tmp/armarium_test_location_icons")
os.environ.setdefault("PLATFORM_LOGOS_DIR", "/tmp/armarium_test_platform_logos")

# A minimal valid 1x1 PNG, used for icon/logo/cover upload tests.
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)

# SVG can carry an embedded <script>, so all icon/logo/cover uploads must
# reject it regardless of the declared content-type.
SVG_PAYLOAD = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'


@pytest.fixture
async def client():
    from app.main import app, lifespan

    async with lifespan(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """The login/lookup rate limiters are in-process globals, so they persist
    across tests within the same pytest run. Reset them before each test so
    the number of tests doesn't accidentally trip the production limits."""
    from app.api.v1.auth import login_limiter
    from app.api.v1.lookup import lookup_limiter, scan_limiter

    login_limiter.reset()
    lookup_limiter.reset()
    scan_limiter.reset()
    yield


@pytest.fixture(autouse=True)
def _reset_plex_sync_jobs():
    """plex_sync_jobs._jobs is a process-global dict keyed by mapping_id, but
    the `client` fixture gives every test a fresh in-memory database whose
    autoincrement ids restart at 1 — so a sync job left at status="running"
    by a prior test (e.g. its background asyncio.create_task hadn't reached
    a terminal state before that test's event loop was torn down) would
    otherwise be mistaken for an in-progress sync on an unrelated later
    test's mapping with the same id, causing spurious 409s or polls that
    never see a terminal status. Clear it before every test."""
    from app.services import plex_sync_jobs

    plex_sync_jobs._jobs.clear()
    yield


@pytest.fixture
async def auth_headers(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "testpass123"},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _subtype_id(client, auth_headers, name: str) -> int:
    """Resolve a seeded media subtype's id by name (e.g. "CD", "Blu-ray", "Book")."""
    resp = await client.get("/api/v1/media-subtypes", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    for subtype in resp.json():
        if subtype["name"] == name:
            return subtype["id"]
    raise AssertionError(f"Media subtype {name!r} not found in {resp.json()!r}")


async def _create_user_and_login(client, auth_headers, username, **permission_overrides):
    """Create a non-admin user with optional permission overrides and log in as them."""
    payload = {"username": username, "password": "userpass123", **permission_overrides}
    resp = await client.post("/api/v1/users", json=payload, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    user = resp.json()

    resp = await client.post("/api/v1/auth/login", json={"username": username, "password": "userpass123"})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return user, {"Authorization": f"Bearer {token}"}
