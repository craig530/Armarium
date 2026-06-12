"""
Basic smoke tests for the Armarium API.
Run: cd backend && pip install -r requirements.txt && pytest
"""
import pytest
import os
import base64
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport

# Use an in-memory SQLite database for tests
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "testpass123")
os.environ.setdefault("JWT_SECRET", "test-secret-key-not-for-production")
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
    from app.api.v1.lookup import lookup_limiter

    login_limiter.reset()
    lookup_limiter.reset()
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
    cd_id = await _subtype_id(client, auth_headers, "CD")

    # Create
    resp = await client.post(
        "/api/v1/media",
        json={"title": "Test Album", "media_subtype_id": cd_id, "artist": "Test Artist", "year": 2024},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    item = resp.json()
    item_id = item["id"]
    assert item["title"] == "Test Album"
    assert item["media_subtype"]["name"] == "CD"
    assert item["category"] == "music"
    assert item["supertype"] == "physical"
    assert item["ownership"] == "physical"

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


async def test_create_media_rejects_unknown_location(client, auth_headers):
    cd_id = await _subtype_id(client, auth_headers, "CD")
    resp = await client.post(
        "/api/v1/media",
        json={"title": "Orphaned Item", "media_subtype_id": cd_id, "location_id": 999999},
        headers=auth_headers,
    )
    assert resp.status_code == 404


async def test_update_media_rejects_unknown_location(client, auth_headers):
    cd_id = await _subtype_id(client, auth_headers, "CD")
    resp = await client.post(
        "/api/v1/media",
        json={"title": "Movable Item", "media_subtype_id": cd_id},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    item_id = resp.json()["id"]

    resp = await client.put(
        f"/api/v1/media/{item_id}",
        json={"location_id": 999999},
        headers=auth_headers,
    )
    assert resp.status_code == 404

    resp = await client.delete(f"/api/v1/media/{item_id}", headers=auth_headers)
    assert resp.status_code == 204


async def test_create_media_rejects_unknown_subtype(client, auth_headers):
    resp = await client.post(
        "/api/v1/media",
        json={"title": "No Subtype", "media_subtype_id": 999999},
        headers=auth_headers,
    )
    assert resp.status_code == 404


# ── Ownership validation (physical vs digital) ───────────────────────────────

async def test_ownership_field_validation(client, auth_headers):
    cd_id = await _subtype_id(client, auth_headers, "CD")
    digital_music_id = await _subtype_id(client, auth_headers, "Music")

    resp = await client.post("/api/v1/platforms", json={"name": "Validation Platform"}, headers=auth_headers)
    assert resp.status_code == 201
    platform_id = resp.json()["id"]

    resp = await client.post("/api/v1/locations", json={"name": "Validation Shelf"}, headers=auth_headers)
    assert resp.status_code == 201
    location_id = resp.json()["id"]

    # Physical item with a platform set -> rejected
    resp = await client.post(
        "/api/v1/media",
        json={"title": "Bad Physical", "media_subtype_id": cd_id, "platform_id": platform_id},
        headers=auth_headers,
    )
    assert resp.status_code == 400

    # Digital item with a location set -> rejected
    resp = await client.post(
        "/api/v1/media",
        json={"title": "Bad Digital", "media_subtype_id": digital_music_id, "location_id": location_id},
        headers=auth_headers,
    )
    assert resp.status_code == 400

    # Cleanup
    resp = await client.delete(f"/api/v1/platforms/{platform_id}", headers=auth_headers)
    assert resp.status_code == 204
    resp = await client.delete(f"/api/v1/locations/{location_id}", headers=auth_headers)
    assert resp.status_code == 204


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


async def test_media_with_nested_location_returns_breadcrumb_path(client, auth_headers):
    # Build a 3-level location tree: Living Room -> Bookshelf -> Top Shelf.
    # Past bug: location_path / list / get / stats all 500'd once a media
    # item's location had a parent (MissingGreenlet on Location.parent).
    cd_id = await _subtype_id(client, auth_headers, "CD")

    root_resp = await client.post("/api/v1/locations", json={"name": "Living Room"}, headers=auth_headers)
    root_id = root_resp.json()["id"]

    mid_resp = await client.post(
        "/api/v1/locations", json={"name": "Bookshelf", "parent_id": root_id}, headers=auth_headers
    )
    mid_id = mid_resp.json()["id"]

    leaf_resp = await client.post(
        "/api/v1/locations", json={"name": "Top Shelf", "parent_id": mid_id}, headers=auth_headers
    )
    leaf_id = leaf_resp.json()["id"]

    create_resp = await client.post(
        "/api/v1/media",
        json={"title": "Located CD", "media_subtype_id": cd_id},
        headers=auth_headers,
    )
    item_id = create_resp.json()["id"]

    # Update (set location) — this is the request that previously 500'd.
    update_resp = await client.put(
        f"/api/v1/media/{item_id}",
        json={"location_id": leaf_id},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["location_path"] == "Living Room → Bookshelf → Top Shelf"
    assert update_resp.json()["location_name"] == "Top Shelf"

    # Get, list and stats all previously 500'd once an item had a located parent chain.
    get_resp = await client.get(f"/api/v1/media/{item_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["location_path"] == "Living Room → Bookshelf → Top Shelf"

    list_resp = await client.get("/api/v1/media", headers=auth_headers)
    assert list_resp.status_code == 200

    stats_resp = await client.get("/api/v1/media/stats", headers=auth_headers)
    assert stats_resp.status_code == 200

    # 3-level nesting also previously crashed location list/get endpoints.
    locations_resp = await client.get("/api/v1/locations", headers=auth_headers)
    assert locations_resp.status_code == 200

    leaf_loc_resp = await client.get(f"/api/v1/locations/{leaf_id}", headers=auth_headers)
    assert leaf_loc_resp.status_code == 200
    assert leaf_loc_resp.json()["item_count"] == 1

    root_loc_resp = await client.get(f"/api/v1/locations/{root_id}", headers=auth_headers)
    assert root_loc_resp.status_code == 200
    assert root_loc_resp.json()["children"][0]["children"][0]["name"] == "Top Shelf"

    # Cleanup
    resp = await client.delete(f"/api/v1/media/{item_id}", headers=auth_headers)
    assert resp.status_code == 204
    resp = await client.delete(f"/api/v1/locations/{leaf_id}", headers=auth_headers)
    assert resp.status_code == 204
    resp = await client.delete(f"/api/v1/locations/{mid_id}", headers=auth_headers)
    assert resp.status_code == 204
    resp = await client.delete(f"/api/v1/locations/{root_id}", headers=auth_headers)
    assert resp.status_code == 204


async def test_delete_location_with_children_rejected(client, auth_headers):
    root_resp = await client.post("/api/v1/locations", json={"name": "Shelf"}, headers=auth_headers)
    root_id = root_resp.json()["id"]

    child_resp = await client.post(
        "/api/v1/locations", json={"name": "Bin", "parent_id": root_id}, headers=auth_headers
    )
    child_id = child_resp.json()["id"]

    resp = await client.delete(f"/api/v1/locations/{root_id}", headers=auth_headers)
    assert resp.status_code == 400

    # Removing the child first allows the (now childless) root to be deleted.
    resp = await client.delete(f"/api/v1/locations/{child_id}", headers=auth_headers)
    assert resp.status_code == 204
    resp = await client.delete(f"/api/v1/locations/{root_id}", headers=auth_headers)
    assert resp.status_code == 204


async def test_location_icon_key_and_upload(client, auth_headers):
    resp = await client.post(
        "/api/v1/locations",
        json={"name": "Iconic Shelf", "icon_key": "bookshelf"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    loc = resp.json()
    loc_id = loc["id"]
    assert loc["icon_key"] == "bookshelf"
    assert loc["icon_url"] is None

    files = {"file": ("icon.png", PNG_1X1, "image/png")}
    resp = await client.post(f"/api/v1/locations/{loc_id}/icon", files=files, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["icon_url"] == f"/location-icons/location_{loc_id}.png"

    # Icon should appear on media items located here too.
    cd_id = await _subtype_id(client, auth_headers, "CD")
    resp = await client.post(
        "/api/v1/media",
        json={"title": "Iconic Item", "media_subtype_id": cd_id, "location_id": loc_id},
        headers=auth_headers,
    )
    item_id = resp.json()["id"]
    assert resp.json()["location_icon_url"] == f"/location-icons/location_{loc_id}.png"
    assert resp.json()["location_icon_key"] == "bookshelf"

    # Cleanup
    resp = await client.delete(f"/api/v1/media/{item_id}", headers=auth_headers)
    assert resp.status_code == 204
    resp = await client.delete(f"/api/v1/locations/{loc_id}", headers=auth_headers)
    assert resp.status_code == 204


# ── Media Subtypes ───────────────────────────────────────────────────────────

async def test_media_subtype_seed_and_crud(client, auth_headers):
    resp = await client.get("/api/v1/media-subtypes", headers=auth_headers)
    assert resp.status_code == 200
    subtypes = resp.json()
    names = {s["name"] for s in subtypes}
    assert {"CD", "Blu-ray", "Book", "Music", "TV Series", "eBook"}.issubset(names)

    # Create
    resp = await client.post(
        "/api/v1/media-subtypes",
        json={"name": "Cassette", "category": "music", "supertype": "physical", "sort_order": 99},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    subtype = resp.json()
    subtype_id = subtype["id"]
    assert subtype["item_count"] == 0

    # Duplicate name within the same category/supertype -> 409
    resp = await client.post(
        "/api/v1/media-subtypes",
        json={"name": "Cassette", "category": "music", "supertype": "physical"},
        headers=auth_headers,
    )
    assert resp.status_code == 409

    # Rename
    resp = await client.put(
        f"/api/v1/media-subtypes/{subtype_id}",
        json={"name": "Cassette Tape", "sort_order": 5},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Cassette Tape"
    assert resp.json()["sort_order"] == 5

    # Delete
    resp = await client.delete(f"/api/v1/media-subtypes/{subtype_id}", headers=auth_headers)
    assert resp.status_code == 204


async def test_delete_media_subtype_in_use_rejected(client, auth_headers):
    cd_id = await _subtype_id(client, auth_headers, "CD")

    resp = await client.post(
        "/api/v1/media",
        json={"title": "In-use CD", "media_subtype_id": cd_id},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    item_id = resp.json()["id"]

    resp = await client.delete(f"/api/v1/media-subtypes/{cd_id}", headers=auth_headers)
    assert resp.status_code == 400

    resp = await client.delete(f"/api/v1/media/{item_id}", headers=auth_headers)
    assert resp.status_code == 204


# ── Platforms ────────────────────────────────────────────────────────────────

async def test_platform_crud_and_logo_upload(client, auth_headers):
    resp = await client.post(
        "/api/v1/platforms",
        json={"name": "Netflix", "logo_key": "netflix"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    platform = resp.json()
    platform_id = platform["id"]
    assert platform["logo_key"] == "netflix"
    assert platform["logo_url"] is None
    assert platform["item_count"] == 0

    # Duplicate name -> 409
    resp = await client.post("/api/v1/platforms", json={"name": "Netflix"}, headers=auth_headers)
    assert resp.status_code == 409

    # List
    resp = await client.get("/api/v1/platforms", headers=auth_headers)
    assert resp.status_code == 200
    assert any(p["name"] == "Netflix" for p in resp.json())

    # Update
    resp = await client.put(
        f"/api/v1/platforms/{platform_id}",
        json={"name": "Netflix UK"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Netflix UK"

    # Logo upload
    files = {"file": ("logo.png", PNG_1X1, "image/png")}
    resp = await client.post(f"/api/v1/platforms/{platform_id}/logo", files=files, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["logo_url"] == f"/platform-logos/platform_{platform_id}.png"

    # Delete
    resp = await client.delete(f"/api/v1/platforms/{platform_id}", headers=auth_headers)
    assert resp.status_code == 204


async def test_delete_platform_in_use_rejected(client, auth_headers):
    resp = await client.post("/api/v1/platforms", json={"name": "Spotify"}, headers=auth_headers)
    assert resp.status_code == 201
    platform_id = resp.json()["id"]

    digital_music_id = await _subtype_id(client, auth_headers, "Music")

    resp = await client.post(
        "/api/v1/media",
        json={"title": "Streamed Album", "media_subtype_id": digital_music_id, "platform_id": platform_id},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    item = resp.json()
    item_id = item["id"]
    assert item["platform"]["name"] == "Spotify"
    assert item["ownership"] == "digital"

    resp = await client.delete(f"/api/v1/platforms/{platform_id}", headers=auth_headers)
    assert resp.status_code == 400

    resp = await client.delete(f"/api/v1/media/{item_id}", headers=auth_headers)
    assert resp.status_code == 204
    resp = await client.delete(f"/api/v1/platforms/{platform_id}", headers=auth_headers)
    assert resp.status_code == 204


# ── Upload validation ────────────────────────────────────────────────────────

async def test_cover_upload_rejects_svg(client, auth_headers):
    cd_id = await _subtype_id(client, auth_headers, "CD")
    resp = await client.post(
        "/api/v1/media", json={"title": "Cover Upload Test", "media_subtype_id": cd_id}, headers=auth_headers
    )
    item_id = resp.json()["id"]

    files = {"file": ("evil.svg", SVG_PAYLOAD, "image/svg+xml")}
    resp = await client.post(f"/api/v1/media/{item_id}/cover", files=files, headers=auth_headers)
    assert resp.status_code == 400

    resp = await client.delete(f"/api/v1/media/{item_id}", headers=auth_headers)
    assert resp.status_code == 204


async def test_location_icon_upload_rejects_svg(client, auth_headers):
    resp = await client.post("/api/v1/locations", json={"name": "Icon Upload Test Shelf"}, headers=auth_headers)
    loc_id = resp.json()["id"]

    files = {"file": ("evil.svg", SVG_PAYLOAD, "image/svg+xml")}
    resp = await client.post(f"/api/v1/locations/{loc_id}/icon", files=files, headers=auth_headers)
    assert resp.status_code == 400

    resp = await client.delete(f"/api/v1/locations/{loc_id}", headers=auth_headers)
    assert resp.status_code == 204


async def test_platform_logo_upload_rejects_svg(client, auth_headers):
    resp = await client.post("/api/v1/platforms", json={"name": "Logo Upload Test Platform"}, headers=auth_headers)
    platform_id = resp.json()["id"]

    files = {"file": ("evil.svg", SVG_PAYLOAD, "image/svg+xml")}
    resp = await client.post(f"/api/v1/platforms/{platform_id}/logo", files=files, headers=auth_headers)
    assert resp.status_code == 400

    resp = await client.delete(f"/api/v1/platforms/{platform_id}", headers=auth_headers)
    assert resp.status_code == 204


# ── Media filters ─────────────────────────────────────────────────────────────

async def test_media_filters_by_category_supertype_subtype_platform(client, auth_headers):
    cd_id = await _subtype_id(client, auth_headers, "CD")
    book_id = await _subtype_id(client, auth_headers, "Book")
    digital_music_id = await _subtype_id(client, auth_headers, "Music")

    resp = await client.post("/api/v1/platforms", json={"name": "Filter Platform"}, headers=auth_headers)
    platform_id = resp.json()["id"]

    cd_resp = await client.post(
        "/api/v1/media", json={"title": "Filter CD", "media_subtype_id": cd_id}, headers=auth_headers
    )
    cd_item_id = cd_resp.json()["id"]

    book_resp = await client.post(
        "/api/v1/media", json={"title": "Filter Book", "media_subtype_id": book_id}, headers=auth_headers
    )
    book_item_id = book_resp.json()["id"]

    digital_resp = await client.post(
        "/api/v1/media",
        json={"title": "Filter Digital Music", "media_subtype_id": digital_music_id, "platform_id": platform_id},
        headers=auth_headers,
    )
    digital_item_id = digital_resp.json()["id"]

    # category filter
    resp = await client.get("/api/v1/media?category=music", headers=auth_headers)
    assert resp.status_code == 200
    titles = {i["title"] for i in resp.json()["items"]}
    assert "Filter CD" in titles and "Filter Digital Music" in titles
    assert "Filter Book" not in titles

    # supertype filter
    resp = await client.get("/api/v1/media?supertype=digital", headers=auth_headers)
    assert resp.status_code == 200
    titles = {i["title"] for i in resp.json()["items"]}
    assert "Filter Digital Music" in titles
    assert "Filter CD" not in titles

    # media_subtype_id filter
    resp = await client.get(f"/api/v1/media?media_subtype_id={cd_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert all(i["media_subtype_id"] == cd_id for i in resp.json()["items"])

    # platform_id filter
    resp = await client.get(f"/api/v1/media?platform_id={platform_id}", headers=auth_headers)
    assert resp.status_code == 200
    titles = {i["title"] for i in resp.json()["items"]}
    assert titles == {"Filter Digital Music"}

    # Cleanup
    for item_id in (cd_item_id, book_item_id, digital_item_id):
        resp = await client.delete(f"/api/v1/media/{item_id}", headers=auth_headers)
        assert resp.status_code == 204
    resp = await client.delete(f"/api/v1/platforms/{platform_id}", headers=auth_headers)
    assert resp.status_code == 204


# ── Physical/Digital linking ─────────────────────────────────────────────────

async def test_manual_link_and_unlink(client, auth_headers):
    bluray_id = await _subtype_id(client, auth_headers, "Blu-ray")
    digital_film_id = await _subtype_id(client, auth_headers, "Film")

    physical_resp = await client.post(
        "/api/v1/media", json={"title": "Physical Film", "media_subtype_id": bluray_id}, headers=auth_headers
    )
    physical_id = physical_resp.json()["id"]

    digital_resp = await client.post(
        "/api/v1/media", json={"title": "Digital Film", "media_subtype_id": digital_film_id}, headers=auth_headers
    )
    digital_id = digital_resp.json()["id"]

    # Same supertype -> rejected
    resp = await client.post(
        "/api/v1/media/link",
        json={"item_a_id": physical_id, "item_b_id": physical_id},
        headers=auth_headers,
    )
    assert resp.status_code == 400

    resp = await client.post(
        "/api/v1/media/link",
        json={"item_a_id": physical_id, "item_b_id": digital_id},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["ownership"] == "both"
    assert body["linked_item"]["id"] == digital_id
    assert body["linked_item"]["title"] == "Digital Film"

    # Already linked -> rejected
    resp = await client.post(
        "/api/v1/media/link",
        json={"item_a_id": physical_id, "item_b_id": digital_id},
        headers=auth_headers,
    )
    assert resp.status_code == 400

    # Partner reflects the link too
    resp = await client.get(f"/api/v1/media/{digital_id}", headers=auth_headers)
    assert resp.json()["ownership"] == "both"
    assert resp.json()["linked_item"]["id"] == physical_id

    # Unlink
    resp = await client.delete(f"/api/v1/media/{physical_id}/link", headers=auth_headers)
    assert resp.status_code == 204

    # Unlinking again -> 404
    resp = await client.delete(f"/api/v1/media/{physical_id}/link", headers=auth_headers)
    assert resp.status_code == 404

    resp = await client.get(f"/api/v1/media/{physical_id}", headers=auth_headers)
    assert resp.json()["ownership"] == "physical"
    assert resp.json()["linked_item"] is None

    # Cleanup
    resp = await client.delete(f"/api/v1/media/{physical_id}", headers=auth_headers)
    assert resp.status_code == 204
    resp = await client.delete(f"/api/v1/media/{digital_id}", headers=auth_headers)
    assert resp.status_code == 204


async def test_delete_linked_item_clears_partner_link(client, auth_headers):
    bluray_id = await _subtype_id(client, auth_headers, "Blu-ray")
    digital_film_id = await _subtype_id(client, auth_headers, "Film")

    physical_resp = await client.post(
        "/api/v1/media", json={"title": "Surviving Physical", "media_subtype_id": bluray_id}, headers=auth_headers
    )
    physical_id = physical_resp.json()["id"]

    digital_resp = await client.post(
        "/api/v1/media", json={"title": "Doomed Digital", "media_subtype_id": digital_film_id}, headers=auth_headers
    )
    digital_id = digital_resp.json()["id"]

    resp = await client.post(
        "/api/v1/media/link",
        json={"item_a_id": physical_id, "item_b_id": digital_id},
        headers=auth_headers,
    )
    assert resp.status_code == 201

    # Delete one half of the linked pair...
    resp = await client.delete(f"/api/v1/media/{digital_id}", headers=auth_headers)
    assert resp.status_code == 204

    # ...the survivor should revert to a single-ownership item, not point at
    # a now-deleted item.
    resp = await client.get(f"/api/v1/media/{physical_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["ownership"] == "physical"
    assert resp.json()["linked_item"] is None

    # And the link itself is gone, so unlinking again is a 404.
    resp = await client.delete(f"/api/v1/media/{physical_id}/link", headers=auth_headers)
    assert resp.status_code == 404

    resp = await client.delete(f"/api/v1/media/{physical_id}", headers=auth_headers)
    assert resp.status_code == 204


async def test_auto_link_on_matching_tmdb_id(client, auth_headers):
    bluray_id = await _subtype_id(client, auth_headers, "Blu-ray")
    digital_film_id = await _subtype_id(client, auth_headers, "Film")

    physical_resp = await client.post(
        "/api/v1/media",
        json={"title": "Inception", "media_subtype_id": bluray_id, "tmdb_id": 27205},
        headers=auth_headers,
    )
    assert physical_resp.status_code == 201
    physical_id = physical_resp.json()["id"]
    assert physical_resp.json()["ownership"] == "physical"
    assert physical_resp.json()["linked_item"] is None

    digital_resp = await client.post(
        "/api/v1/media",
        json={"title": "Inception (Digital)", "media_subtype_id": digital_film_id, "tmdb_id": 27205},
        headers=auth_headers,
    )
    assert digital_resp.status_code == 201
    digital_id = digital_resp.json()["id"]
    assert digital_resp.json()["ownership"] == "both"
    assert digital_resp.json()["linked_item"]["id"] == physical_id

    resp = await client.get(f"/api/v1/media/{physical_id}", headers=auth_headers)
    assert resp.json()["ownership"] == "both"
    assert resp.json()["linked_item"]["id"] == digital_id

    # Cleanup
    resp = await client.delete(f"/api/v1/media/{physical_id}", headers=auth_headers)
    assert resp.status_code == 204
    resp = await client.delete(f"/api/v1/media/{digital_id}", headers=auth_headers)
    assert resp.status_code == 204


# ── Lookup ───────────────────────────────────────────────────────────────────

async def test_lookup_barcode_flags_existing_library_item(client, auth_headers):
    from app.models.enums import MediaCategory
    from app.schemas.media import LookupCandidate

    isbn = "9780134685991"
    book_id = await _subtype_id(client, auth_headers, "Book")

    resp = await client.post(
        "/api/v1/media",
        json={"title": "Effective Java", "media_subtype_id": book_id, "isbn": isbn},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    item_id = resp.json()["id"]

    fake_candidate = LookupCandidate(
        external_id=isbn,
        source="openlibrary",
        title="Effective Java",
        category=MediaCategory.BOOKS,
    )

    with patch("app.services.openlibrary.lookup_by_isbn", new=AsyncMock(return_value=[fake_candidate])):
        resp = await client.get(f"/api/v1/lookup/barcode/{isbn}", headers=auth_headers)

    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["metadata"]["library_count"] == 1

    resp = await client.delete(f"/api/v1/media/{item_id}", headers=auth_headers)
    assert resp.status_code == 204


# ── Stats ────────────────────────────────────────────────────────────────────

async def test_stats(client, auth_headers):
    resp = await client.get("/api/v1/media/stats", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "total" in body
    assert "by_category" in body
    assert "by_supertype" in body
    assert "by_subtype" in body


# ── Users & Permissions ──────────────────────────────────────────────────────

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


async def test_create_user_default_permissions(client, auth_headers):
    resp = await client.post(
        "/api/v1/users",
        json={"username": "defaultuser", "password": "userpass123"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    user = resp.json()
    assert user["is_admin"] is False
    assert user["is_read_only"] is False
    assert user["can_add_items"] is True
    assert user["can_manage_locations"] is True
    assert user["can_manage_platforms"] is True
    assert user["can_manage_media_types"] is False

    resp = await client.delete(f"/api/v1/users/{user['id']}", headers=auth_headers)
    assert resp.status_code == 204


async def test_create_user_custom_permissions(client, auth_headers):
    resp = await client.post(
        "/api/v1/users",
        json={
            "username": "customuser",
            "password": "userpass123",
            "is_read_only": True,
            "can_add_items": False,
            "can_manage_locations": False,
            "can_manage_platforms": False,
            "can_manage_media_types": True,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    user = resp.json()
    assert user["is_read_only"] is True
    assert user["can_add_items"] is False
    assert user["can_manage_locations"] is False
    assert user["can_manage_platforms"] is False
    assert user["can_manage_media_types"] is True

    resp = await client.delete(f"/api/v1/users/{user['id']}", headers=auth_headers)
    assert resp.status_code == 204


async def test_non_admin_cannot_manage_users(client, auth_headers):
    user, headers = await _create_user_and_login(client, auth_headers, "plainuser")

    resp = await client.get("/api/v1/users", headers=headers)
    assert resp.status_code == 403

    resp = await client.post(
        "/api/v1/users", json={"username": "another", "password": "userpass123"}, headers=headers
    )
    assert resp.status_code == 403

    resp = await client.delete(f"/api/v1/users/{user['id']}", headers=auth_headers)
    assert resp.status_code == 204


async def test_can_add_items_permission_enforced(client, auth_headers):
    cd_id = await _subtype_id(client, auth_headers, "CD")
    user, headers = await _create_user_and_login(client, auth_headers, "noadditemsuser", can_add_items=False)

    resp = await client.post(
        "/api/v1/media",
        json={"title": "Forbidden Item", "media_subtype_id": cd_id},
        headers=headers,
    )
    assert resp.status_code == 403

    # Read access is unaffected.
    resp = await client.get("/api/v1/media", headers=headers)
    assert resp.status_code == 200

    resp = await client.delete(f"/api/v1/users/{user['id']}", headers=auth_headers)
    assert resp.status_code == 204


async def test_is_read_only_overrides_all_permissions(client, auth_headers):
    cd_id = await _subtype_id(client, auth_headers, "CD")
    user, headers = await _create_user_and_login(client, auth_headers, "readonlyuser", is_read_only=True)

    resp = await client.post("/api/v1/locations", json={"name": "Read Only Shelf"}, headers=headers)
    assert resp.status_code == 403

    resp = await client.post(
        "/api/v1/media",
        json={"title": "Read Only Item", "media_subtype_id": cd_id},
        headers=headers,
    )
    assert resp.status_code == 403

    resp = await client.delete(f"/api/v1/users/{user['id']}", headers=auth_headers)
    assert resp.status_code == 204


async def test_can_manage_media_types_permission_enforced(client, auth_headers):
    # Default for new users is can_manage_media_types=False.
    user, headers = await _create_user_and_login(client, auth_headers, "subtypeuser")

    subtype_payload = {"name": "Vinyl", "category": "music", "supertype": "physical", "sort_order": 50}
    resp = await client.post("/api/v1/media-subtypes", json=subtype_payload, headers=headers)
    assert resp.status_code == 403

    resp = await client.put(
        f"/api/v1/users/{user['id']}", json={"can_manage_media_types": True}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["can_manage_media_types"] is True

    resp = await client.post("/api/v1/media-subtypes", json=subtype_payload, headers=headers)
    assert resp.status_code == 201, resp.text
    subtype_id = resp.json()["id"]

    resp = await client.delete(f"/api/v1/media-subtypes/{subtype_id}", headers=auth_headers)
    assert resp.status_code == 204
    resp = await client.delete(f"/api/v1/users/{user['id']}", headers=auth_headers)
    assert resp.status_code == 204


async def test_admin_bypasses_permission_checks(client, auth_headers):
    """An admin retains full access even with restrictive permission flags set."""
    resp = await client.post(
        "/api/v1/users",
        json={
            "username": "superadmin",
            "password": "userpass123",
            "is_admin": True,
            "is_read_only": True,
            "can_add_items": False,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    user = resp.json()

    resp = await client.post("/api/v1/auth/login", json={"username": "superadmin", "password": "userpass123"})
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    cd_id = await _subtype_id(client, auth_headers, "CD")
    resp = await client.post(
        "/api/v1/media",
        json={"title": "Admin Override Item", "media_subtype_id": cd_id},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    item_id = resp.json()["id"]

    resp = await client.delete(f"/api/v1/media/{item_id}", headers=auth_headers)
    assert resp.status_code == 204
    resp = await client.delete(f"/api/v1/users/{user['id']}", headers=auth_headers)
    assert resp.status_code == 204


async def test_cannot_demote_deactivate_or_delete_self(client, auth_headers):
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    me = resp.json()

    resp = await client.put(f"/api/v1/users/{me['id']}", json={"is_admin": False}, headers=auth_headers)
    assert resp.status_code == 400

    resp = await client.put(f"/api/v1/users/{me['id']}", json={"is_active": False}, headers=auth_headers)
    assert resp.status_code == 400

    resp = await client.delete(f"/api/v1/users/{me['id']}", headers=auth_headers)
    assert resp.status_code == 400


async def test_last_admin_cannot_be_demoted_by_others(client, auth_headers):
    """With two admins, one can be demoted; the resulting sole admin is protected."""
    resp = await client.post(
        "/api/v1/users",
        json={"username": "coadmin", "password": "userpass123", "is_admin": True},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    coadmin = resp.json()

    resp = await client.post("/api/v1/auth/login", json={"username": "coadmin", "password": "userpass123"})
    coadmin_headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    # Two admins exist — coadmin may demote the original admin... except that's
    # "admin"'s own account from coadmin's perspective it's not self, but
    # demoting the *only remaining* admin afterwards is blocked.
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    admin_id = resp.json()["id"]

    resp = await client.put(f"/api/v1/users/{admin_id}", json={"is_admin": False}, headers=coadmin_headers)
    assert resp.status_code == 200
    assert resp.json()["is_admin"] is False

    # Now "coadmin" is the sole admin — coadmin cannot demote themselves either.
    resp = await client.put(f"/api/v1/users/{coadmin['id']}", json={"is_admin": False}, headers=coadmin_headers)
    assert resp.status_code == 400

    # Restore "admin" to admin (using coadmin's credentials) for other tests, then clean up coadmin.
    resp = await client.put(f"/api/v1/users/{admin_id}", json={"is_admin": True}, headers=coadmin_headers)
    assert resp.status_code == 200

    resp = await client.delete(f"/api/v1/users/{coadmin['id']}", headers=auth_headers)
    assert resp.status_code == 204


# ── Export / Import ──────────────────────────────────────────────────────────

async def test_export_json(client, auth_headers):
    resp = await client.get("/api/v1/library/export?format=json", headers=auth_headers)
    assert resp.status_code == 200
    assert "items" in resp.json()


async def test_export_csv(client, auth_headers):
    resp = await client.get("/api/v1/library/export?format=csv", headers=auth_headers)
    assert resp.status_code == 200
    assert b"title" in resp.content


async def test_import_csv_validates_foreign_keys(client, auth_headers):
    """Imported rows referencing locations/platforms/subtypes that don't
    exist must not create dangling foreign keys — invalid location/platform
    references are nulled, and rows with an unresolvable subtype are
    skipped."""
    import csv
    import io
    from app.api.v1.export_import import CSV_FIELDS

    cd_id = await _subtype_id(client, auth_headers, "CD")

    rows = [
        # Valid subtype, but location_id/platform_id point at rows that don't exist.
        {"title": "Imported Orphaned CD", "media_subtype_id": cd_id, "location_id": 999999, "platform_id": 999999},
        # media_subtype_id doesn't exist -> row is skipped entirely.
        {"title": "Imported Unknown Subtype", "media_subtype_id": 999999},
    ]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

    files = {"file": ("import.csv", output.getvalue().encode(), "text/csv")}
    resp = await client.post("/api/v1/library/import?format=csv", files=files, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == {"imported": 1, "skipped": 1}

    resp = await client.get("/api/v1/media?q=Imported+Orphaned+CD", headers=auth_headers)
    items = resp.json()["items"]
    assert len(items) == 1
    item = items[0]
    assert item["location_id"] is None
    assert item["platform_id"] is None

    resp = await client.delete(f"/api/v1/media/{item['id']}", headers=auth_headers)
    assert resp.status_code == 204


# ── Performance ──────────────────────────────────────────────────────────────

async def test_list_endpoint_stays_fast_with_large_catalogue(client, auth_headers):
    """Seed 10,000 items directly (bypassing the API) and confirm the list
    endpoint — including a filter on the media_subtype_id column added to
    `_MISSING_INDEXES` — stays fast."""
    import time
    from sqlalchemy import insert, delete
    from app.database import AsyncSessionLocal
    from app.models.media import MediaItem

    cd_id = await _subtype_id(client, auth_headers, "CD")
    item_count = 10_000

    async with AsyncSessionLocal() as db:
        await db.execute(
            insert(MediaItem),
            [
                {"title": f"Perf Item {i}", "media_subtype_id": cd_id, "year": 2000 + (i % 25)}
                for i in range(item_count)
            ],
        )
        await db.commit()

    try:
        start = time.perf_counter()
        resp = await client.get("/api/v1/media?per_page=24", headers=auth_headers)
        elapsed = time.perf_counter() - start
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= item_count
        assert len(body["items"]) == 24
        assert elapsed < 2.0, f"List endpoint took {elapsed:.2f}s with {item_count}+ items"

        start = time.perf_counter()
        resp = await client.get(f"/api/v1/media?media_subtype_id={cd_id}&per_page=24", headers=auth_headers)
        elapsed = time.perf_counter() - start
        assert resp.status_code == 200
        assert resp.json()["total"] >= item_count
        assert elapsed < 2.0, f"Filtered list took {elapsed:.2f}s with {item_count}+ items"
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(delete(MediaItem).where(MediaItem.title.like("Perf Item %")))
            await db.commit()
