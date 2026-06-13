"""
Basic smoke tests for the Armarium API.
Run: cd backend && pip install -r requirements.txt && pytest
"""
import pytest
import os
import io
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
    from app.api.v1.lookup import lookup_limiter, scan_limiter

    login_limiter.reset()
    lookup_limiter.reset()
    scan_limiter.reset()
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

    # Rename — must actually persist, not just echo back the request
    resp = await client.put(
        f"/api/v1/locations/{child_id}",
        json={"name": "Shelf"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Shelf"

    resp = await client.get("/api/v1/locations", headers=auth_headers)
    root = next(loc for loc in resp.json() if loc["id"] == root_id)
    assert root["children"][0]["name"] == "Shelf"

    # Delete child first, then root
    resp = await client.delete(f"/api/v1/locations/{child_id}", headers=auth_headers)
    assert resp.status_code == 204
    resp = await client.delete(f"/api/v1/locations/{root_id}", headers=auth_headers)
    assert resp.status_code == 204


async def test_location_sort_order_reordering(client, auth_headers):
    parent_resp = await client.post("/api/v1/locations", json={"name": "Cabinet"}, headers=auth_headers)
    parent_id = parent_resp.json()["id"]

    a_resp = await client.post(
        "/api/v1/locations",
        json={"name": "Shelf A", "parent_id": parent_id, "sort_order": 0},
        headers=auth_headers,
    )
    b_resp = await client.post(
        "/api/v1/locations",
        json={"name": "Shelf B", "parent_id": parent_id, "sort_order": 1},
        headers=auth_headers,
    )
    a_id, b_id = a_resp.json()["id"], b_resp.json()["id"]
    assert a_resp.json()["sort_order"] == 0
    assert b_resp.json()["sort_order"] == 1

    # Initial order follows sort_order: A, B
    resp = await client.get("/api/v1/locations", headers=auth_headers)
    parent = next(loc for loc in resp.json() if loc["id"] == parent_id)
    assert [c["name"] for c in parent["children"]] == ["Shelf A", "Shelf B"]

    # Swap sort_order — B should now sort before A
    resp = await client.put(f"/api/v1/locations/{a_id}", json={"sort_order": 1}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["sort_order"] == 1
    resp = await client.put(f"/api/v1/locations/{b_id}", json={"sort_order": 0}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["sort_order"] == 0

    resp = await client.get("/api/v1/locations", headers=auth_headers)
    parent = next(loc for loc in resp.json() if loc["id"] == parent_id)
    assert [c["name"] for c in parent["children"]] == ["Shelf B", "Shelf A"]

    for loc_id in (a_id, b_id, parent_id):
        resp = await client.delete(f"/api/v1/locations/{loc_id}", headers=auth_headers)
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


async def test_reference_data_lists_have_no_cache_control_header(client, auth_headers):
    # A `Cache-Control` header on these list endpoints previously caused the
    # browser to serve stale data after a rename/delete/reorder, making those
    # actions appear to silently fail.
    for path in ("/api/v1/locations", "/api/v1/platforms", "/api/v1/media-subtypes"):
        resp = await client.get(path, headers=auth_headers)
        assert resp.status_code == 200
        assert "cache-control" not in {h.lower() for h in resp.headers}


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


async def test_delete_cover_clears_path_and_falls_back_to_url(client, auth_headers):
    from sqlalchemy import update
    from app.database import AsyncSessionLocal
    from app.models.media import MediaItem

    cd_id = await _subtype_id(client, auth_headers, "CD")
    resp = await client.post(
        "/api/v1/media",
        json={"title": "Delete Cover Test", "media_subtype_id": cd_id, "cover_image_url": "https://example.com/cover.jpg"},
        headers=auth_headers,
    )
    item_id = resp.json()["id"]

    files = {"file": ("cover.png", PNG_1X1, "image/png")}
    resp = await client.post(f"/api/v1/media/{item_id}/cover", files=files, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["cover_image_path"]
    assert body["cover_image_url"] is None
    assert body["cover_url"] == body["cover_image_path"]

    # Simulate an item whose local cover came from a `cover/refresh` download
    # rather than an upload — refresh leaves cover_image_url intact.
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(MediaItem).where(MediaItem.id == item_id).values(cover_image_url="https://example.com/cover.jpg")
        )
        await db.commit()

    resp = await client.delete(f"/api/v1/media/{item_id}/cover", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["cover_image_path"] is None
    assert body["cover_url"] == "https://example.com/cover.jpg"

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

    # category + supertype combined — the "Recently added" panel in the add
    # flow filters by both at once, so they must compose with AND, not
    # override each other.
    resp = await client.get("/api/v1/media?category=music&supertype=digital", headers=auth_headers)
    assert resp.status_code == 200
    titles = {i["title"] for i in resp.json()["items"]}
    assert titles == {"Filter Digital Music"}

    resp = await client.get("/api/v1/media?category=music&supertype=physical", headers=auth_headers)
    assert resp.status_code == 200
    titles = {i["title"] for i in resp.json()["items"]}
    assert titles == {"Filter CD"}

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


async def test_search_matches_extended_metadata_fields(client, auth_headers):
    # `q` search was extended beyond title/artist/author/director/genres/
    # description to cover studio/label/publisher/cast_list/isbn/barcode/
    # edition/notes/rating — confirm a couple of the newly-added fields match,
    # under both the FTS5 and ILIKE-fallback code paths.
    cd_id = await _subtype_id(client, auth_headers, "CD")

    resp = await client.post(
        "/api/v1/media",
        json={
            "title": "Extended Search Test Album",
            "media_subtype_id": cd_id,
            "studio": "Zzyzx Recording Co",
            "notes": "Signed by the band at a record store gig",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    item_id = resp.json()["id"]

    resp = await client.get("/api/v1/media?q=Zzyzx", headers=auth_headers)
    assert resp.status_code == 200
    assert "Extended Search Test Album" in {i["title"] for i in resp.json()["items"]}

    resp = await client.get("/api/v1/media?q=record+store+gig", headers=auth_headers)
    assert resp.status_code == 200
    assert "Extended Search Test Album" in {i["title"] for i in resp.json()["items"]}

    resp = await client.delete(f"/api/v1/media/{item_id}", headers=auth_headers)
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

    # Self-link -> rejected
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
    assert [li["id"] for li in body["linked_items"]] == [digital_id]
    assert body["linked_items"][0]["title"] == "Digital Film"

    # Same pair again -> rejected (duplicate edge)
    resp = await client.post(
        "/api/v1/media/link",
        json={"item_a_id": physical_id, "item_b_id": digital_id},
        headers=auth_headers,
    )
    assert resp.status_code == 400

    # Partner reflects the link too
    resp = await client.get(f"/api/v1/media/{digital_id}", headers=auth_headers)
    assert resp.json()["ownership"] == "both"
    assert [li["id"] for li in resp.json()["linked_items"]] == [physical_id]

    # Unlink
    resp = await client.delete(f"/api/v1/media/{physical_id}/link/{digital_id}", headers=auth_headers)
    assert resp.status_code == 204

    # Unlinking again -> 404
    resp = await client.delete(f"/api/v1/media/{physical_id}/link/{digital_id}", headers=auth_headers)
    assert resp.status_code == 404

    resp = await client.get(f"/api/v1/media/{physical_id}", headers=auth_headers)
    assert resp.json()["ownership"] == "physical"
    assert resp.json()["linked_items"] == []

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
    assert resp.json()["linked_items"] == []

    # And the link itself is gone, so unlinking again is a 404.
    resp = await client.delete(f"/api/v1/media/{physical_id}/link/{digital_id}", headers=auth_headers)
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
    assert physical_resp.json()["linked_items"] == []

    digital_resp = await client.post(
        "/api/v1/media",
        json={"title": "Inception (Digital)", "media_subtype_id": digital_film_id, "tmdb_id": 27205},
        headers=auth_headers,
    )
    assert digital_resp.status_code == 201
    digital_id = digital_resp.json()["id"]
    assert digital_resp.json()["ownership"] == "both"
    assert [li["id"] for li in digital_resp.json()["linked_items"]] == [physical_id]

    resp = await client.get(f"/api/v1/media/{physical_id}", headers=auth_headers)
    assert resp.json()["ownership"] == "both"
    assert [li["id"] for li in resp.json()["linked_items"]] == [digital_id]

    # Cleanup
    resp = await client.delete(f"/api/v1/media/{physical_id}", headers=auth_headers)
    assert resp.status_code == 204
    resp = await client.delete(f"/api/v1/media/{digital_id}", headers=auth_headers)
    assert resp.status_code == 204


async def test_multi_link_connected_component(client, auth_headers):
    bluray_id = await _subtype_id(client, auth_headers, "Blu-ray")
    digital_film_id = await _subtype_id(client, auth_headers, "Film")
    digital_tv_id = await _subtype_id(client, auth_headers, "TV Series")

    a_resp = await client.post(
        "/api/v1/media", json={"title": "Multi A (physical)", "media_subtype_id": bluray_id}, headers=auth_headers
    )
    a_id = a_resp.json()["id"]

    b_resp = await client.post(
        "/api/v1/media", json={"title": "Multi B (digital film)", "media_subtype_id": digital_film_id}, headers=auth_headers
    )
    b_id = b_resp.json()["id"]

    c_resp = await client.post(
        "/api/v1/media", json={"title": "Multi C (digital tv)", "media_subtype_id": digital_tv_id}, headers=auth_headers
    )
    c_id = c_resp.json()["id"]

    # Link A <-> B
    resp = await client.post(
        "/api/v1/media/link", json={"item_a_id": a_id, "item_b_id": b_id}, headers=auth_headers
    )
    assert resp.status_code == 201

    # A third link on an already-linked item is allowed: A <-> C
    resp = await client.post(
        "/api/v1/media/link", json={"item_a_id": a_id, "item_b_id": c_id}, headers=auth_headers
    )
    assert resp.status_code == 201

    # All three are in the same connected component
    resp = await client.get(f"/api/v1/media/{a_id}", headers=auth_headers)
    body = resp.json()
    assert body["ownership"] == "both"
    assert {li["id"] for li in body["linked_items"]} == {b_id, c_id}

    resp = await client.get(f"/api/v1/media/{b_id}", headers=auth_headers)
    body = resp.json()
    assert body["ownership"] == "both"
    assert {li["id"] for li in body["linked_items"]} == {a_id, c_id}

    resp = await client.get(f"/api/v1/media/{c_id}", headers=auth_headers)
    body = resp.json()
    assert body["ownership"] == "both"
    assert {li["id"] for li in body["linked_items"]} == {a_id, b_id}

    # Unlinking A <-> C only removes that pair, leaving A <-> B intact
    resp = await client.delete(f"/api/v1/media/{a_id}/link/{c_id}", headers=auth_headers)
    assert resp.status_code == 204

    resp = await client.get(f"/api/v1/media/{a_id}", headers=auth_headers)
    assert {li["id"] for li in resp.json()["linked_items"]} == {b_id}

    # C is now isolated again
    resp = await client.get(f"/api/v1/media/{c_id}", headers=auth_headers)
    body = resp.json()
    assert body["linked_items"] == []
    assert body["ownership"] == "digital"

    # Same-supertype (digital <-> digital) links are allowed
    resp = await client.post(
        "/api/v1/media/link", json={"item_a_id": b_id, "item_b_id": c_id}, headers=auth_headers
    )
    assert resp.status_code == 201

    resp = await client.get(f"/api/v1/media/{b_id}", headers=auth_headers)
    assert {li["id"] for li in resp.json()["linked_items"]} == {a_id, c_id}

    # Cleanup
    for item_id in (a_id, b_id, c_id):
        resp = await client.delete(f"/api/v1/media/{item_id}", headers=auth_headers)
        assert resp.status_code == 204


async def test_admin_auto_link_scans_and_links_unlinked_duplicates(client, auth_headers):
    """POST /admin/auto-link finds items sharing a tmdb_id/musicbrainz_id/isbn
    that aren't linked yet (e.g. duplicates added before linking existed) and
    links them. Idempotent on rerun, admin-only."""
    bluray_id = await _subtype_id(client, auth_headers, "Blu-ray")
    digital_film_id = await _subtype_id(client, auth_headers, "Film")

    physical_resp = await client.post(
        "/api/v1/media",
        json={"title": "The Matrix", "media_subtype_id": bluray_id, "tmdb_id": 603},
        headers=auth_headers,
    )
    assert physical_resp.status_code == 201, physical_resp.text
    physical_id = physical_resp.json()["id"]

    digital_resp = await client.post(
        "/api/v1/media",
        json={"title": "The Matrix (Digital)", "media_subtype_id": digital_film_id, "tmdb_id": 603},
        headers=auth_headers,
    )
    assert digital_resp.status_code == 201, digital_resp.text
    digital_id = digital_resp.json()["id"]

    # Created with matching tmdb_id, so they're auto-linked already — undo
    # that to simulate duplicates that predate linking.
    resp = await client.delete(f"/api/v1/media/{physical_id}/link/{digital_id}", headers=auth_headers)
    assert resp.status_code == 204, resp.text
    resp = await client.get(f"/api/v1/media/{physical_id}", headers=auth_headers)
    assert resp.json()["linked_items"] == []

    # Non-admin cannot run the scan
    _, headers = await _create_user_and_login(client, auth_headers, "autolinkuser")
    resp = await client.post("/api/v1/admin/auto-link", headers=headers)
    assert resp.status_code == 403

    resp = await client.post("/api/v1/admin/auto-link", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["linked"] == 1

    resp = await client.get(f"/api/v1/media/{physical_id}", headers=auth_headers)
    assert [li["id"] for li in resp.json()["linked_items"]] == [digital_id]

    # Idempotent: nothing left to link on rerun
    resp = await client.post("/api/v1/admin/auto-link", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["linked"] == 0

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


async def test_lookup_barcode_rejects_invalid_barcode(client, auth_headers):
    # A 5-digit EAN-5 price extension is not a valid product barcode.
    resp = await client.get("/api/v1/lookup/barcode/51995", headers=auth_headers)

    assert resp.status_code == 400
    assert "barcode" in resp.json()["detail"].lower()


async def test_lookup_barcode_rejects_non_isbn_for_books_category(client, auth_headers):
    # 13-digit EAN-13 that doesn't start with 978/979 — not a valid ISBN, so
    # a category=books lookup must reject it before calling Open Library.
    with patch("app.services.openlibrary.lookup_by_isbn", new=AsyncMock(return_value=[])) as mock_lookup:
        resp = await client.get(
            "/api/v1/lookup/barcode/3916681812733?category=books", headers=auth_headers
        )

    assert resp.status_code == 400
    assert "isbn" in resp.json()["detail"].lower()
    mock_lookup.assert_not_awaited()


async def test_lookup_barcode_cd_queries_musicbrainz_with_ean13_from_upc(client, auth_headers):
    with patch("app.services.musicbrainz.lookup_by_barcode", new=AsyncMock(return_value=[])) as mock_lookup:
        resp = await client.get("/api/v1/lookup/barcode/075678563598", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json() == []
    # The 12-digit UPC-A is converted to its 13-digit EAN-13 form before
    # being passed to MusicBrainz.
    mock_lookup.assert_awaited_once_with("0075678563598")


async def test_lookup_barcode_music_category_queries_musicbrainz(client, auth_headers):
    with patch("app.services.musicbrainz.lookup_by_barcode", new=AsyncMock(return_value=[])) as mock_lookup:
        resp = await client.get("/api/v1/lookup/barcode/075678563598?category=music", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json() == []
    mock_lookup.assert_awaited_once_with("0075678563598")


async def test_lookup_barcode_films_tv_category_does_not_query_musicbrainz(client, auth_headers):
    # MusicBrainz only knows about music releases — a UPC/EAN-13 scanned while
    # adding a film/TV item must not return mismatched (category=music)
    # candidates, and must not even call MusicBrainz.
    with patch("app.services.musicbrainz.lookup_by_barcode", new=AsyncMock(return_value=[])) as mock_lookup:
        resp = await client.get("/api/v1/lookup/barcode/075678563598?category=films_tv", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json() == []
    mock_lookup.assert_not_awaited()


async def test_lookup_barcode_isbn_queries_open_library(client, auth_headers):
    from app.models.enums import MediaCategory
    from app.schemas.media import LookupCandidate
    from app.services.cache import lookup_cache

    # Avoid a cache hit from another test's lookup of the same ISBN.
    lookup_cache.clear()

    fake_candidate = LookupCandidate(
        external_id="9780134685991",
        source="openlibrary",
        title="Effective Java",
        category=MediaCategory.BOOKS,
    )

    with patch("app.services.openlibrary.lookup_by_isbn", new=AsyncMock(return_value=[fake_candidate])) as mock_lookup:
        resp = await client.get("/api/v1/lookup/barcode/978-0-13-468599-1", headers=auth_headers)

    assert resp.status_code == 200
    assert len(resp.json()) == 1
    # Hyphens stripped server-side before querying Open Library.
    mock_lookup.assert_awaited_once_with("9780134685991")


# ── Cover proxy ──────────────────────────────────────────────────────────────

async def test_cover_proxy_streams_remote_image(client):
    fake_bytes = b"\xff\xd8\xfake-jpeg-data"
    with patch("app.api.v1.lookup.fetch_remote_image", new=AsyncMock(return_value=(fake_bytes, "image/jpeg"))) as mock_fetch:
        resp = await client.get(
            "/api/v1/lookup/cover-proxy",
            params={"url": "https://image.tmdb.org/t/p/w500/poster.jpg"},
        )

    assert resp.status_code == 200
    assert resp.content == fake_bytes
    assert resp.headers["content-type"] == "image/jpeg"
    mock_fetch.assert_awaited_once_with("https://image.tmdb.org/t/p/w500/poster.jpg")


async def test_cover_proxy_404_when_unavailable(client):
    with patch("app.api.v1.lookup.fetch_remote_image", new=AsyncMock(return_value=None)):
        resp = await client.get(
            "/api/v1/lookup/cover-proxy",
            params={"url": "https://image.tmdb.org/t/p/w500/missing.jpg"},
        )

    assert resp.status_code == 404


async def test_cover_proxy_does_not_require_auth(client):
    # <img> tags can't send the Authorization header, so this endpoint must
    # be reachable without auth_headers.
    with patch("app.api.v1.lookup.fetch_remote_image", new=AsyncMock(return_value=(b"data", "image/png"))):
        resp = await client.get(
            "/api/v1/lookup/cover-proxy",
            params={"url": "https://covers.openlibrary.org/b/id/12345-L.jpg"},
        )

    assert resp.status_code == 200


async def test_cover_proxy_rejects_private_addresses(client):
    # The same SSRF guard used by download_cover applies here — a
    # loopback/link-local target must be rejected before any request is made,
    # without needing to mock httpx (resolves instantly, no network access).
    resp = await client.get("/api/v1/lookup/cover-proxy", params={"url": "http://127.0.0.1/secret.jpg"})
    assert resp.status_code == 404

    resp = await client.get("/api/v1/lookup/cover-proxy", params={"url": "http://169.254.169.254/latest/meta-data/"})
    assert resp.status_code == 404


# ── Barcode image scan ───────────────────────────────────────────────────────

# EAN-13 module width tables, used to render a real decodable barcode image
# for /lookup/scan tests (mirrors the encoding the camera scanner is reading).
_EAN13_L_CODES = ['0001101', '0011001', '0010011', '0111101', '0100011', '0110001', '0101111', '0111011', '0110111', '0001011']
_EAN13_G_CODES = ['0100111', '0110011', '0011011', '0100001', '0011101', '0111001', '0000101', '0010001', '0001001', '0010111']
_EAN13_R_CODES = ['1110010', '1100110', '1101100', '1000010', '1011100', '1001110', '1010000', '1000100', '1001000', '1110100']
_EAN13_PARITY = {
    0: 'LLLLLL', 1: 'LLGLGG', 2: 'LLGGLG', 3: 'LLGGGL', 4: 'LGLLGG',
    5: 'LGGLLG', 6: 'LGGGLL', 7: 'LGLGLG', 8: 'LGLGGL', 9: 'LGGLGL',
}


def _ean13_png(digits: str) -> bytes:
    from PIL import Image as PILImage

    parity = _EAN13_PARITY[int(digits[0])]
    left_bits = ''.join(
        _EAN13_L_CODES[int(d)] if p == 'L' else _EAN13_G_CODES[int(d)]
        for d, p in zip(digits[1:7], parity)
    )
    right_bits = ''.join(_EAN13_R_CODES[int(d)] for d in digits[7:13])
    bits = '101' + left_bits + '01010' + right_bits + '101'

    module_width, quiet, height = 4, 10, 100
    width = (len(bits) + 2 * quiet) * module_width
    img = PILImage.new('L', (width, height), 255)
    px = img.load()
    for m, b in enumerate(bits):
        if b == '1':
            for w in range(module_width):
                x = (quiet + m) * module_width + w
                for y in range(height):
                    px[x, y] = 0

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


async def test_scan_decodes_barcode_image(client, auth_headers):
    pytest.importorskip("zxingcpp")

    files = {"file": ("frame.png", _ean13_png("9781529052008"), "image/png")}
    resp = await client.post("/api/v1/lookup/scan", files=files, headers=auth_headers)

    assert resp.status_code == 200, resp.text
    results = resp.json()["results"]
    assert any(r["text"] == "9781529052008" for r in results)


async def test_scan_returns_no_results_for_blank_image(client, auth_headers):
    pytest.importorskip("zxingcpp")
    from PIL import Image as PILImage

    buf = io.BytesIO()
    PILImage.new('L', (200, 100), 255).save(buf, format='PNG')

    files = {"file": ("frame.png", buf.getvalue(), "image/png")}
    resp = await client.post("/api/v1/lookup/scan", files=files, headers=auth_headers)

    assert resp.status_code == 200, resp.text
    assert resp.json()["results"] == []


async def test_scan_rejects_unsupported_content_type(client, auth_headers):
    files = {"file": ("frame.txt", b"not an image", "text/plain")}
    resp = await client.post("/api/v1/lookup/scan", files=files, headers=auth_headers)
    assert resp.status_code == 400


async def test_scan_requires_auth(client):
    files = {"file": ("frame.png", PNG_1X1, "image/png")}
    resp = await client.post("/api/v1/lookup/scan", files=files)
    assert resp.status_code == 401


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


async def test_backup_list_download_delete(client, auth_headers):
    from pathlib import Path
    from app.config import settings

    backup_dir = Path(settings.backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    name = "armarium_20260101_120000.db"
    (backup_dir / name).write_bytes(b"fake-db-contents")

    resp = await client.get("/api/v1/library/backup/list", headers=auth_headers)
    assert resp.status_code == 200
    assert any(b["name"] == name for b in resp.json()["backups"])

    resp = await client.get(f"/api/v1/library/backup/{name}/download", headers=auth_headers)
    assert resp.status_code == 200

    resp = await client.delete(f"/api/v1/library/backup/{name}", headers=auth_headers)
    assert resp.status_code == 204

    resp = await client.get("/api/v1/library/backup/list", headers=auth_headers)
    assert resp.status_code == 200
    assert not any(b["name"] == name for b in resp.json()["backups"])


async def test_backup_delete_unknown_or_invalid_name(client, auth_headers):
    resp = await client.delete("/api/v1/library/backup/does_not_exist.db", headers=auth_headers)
    assert resp.status_code == 400

    resp = await client.delete("/api/v1/library/backup/armarium_20260101_000000.db", headers=auth_headers)
    assert resp.status_code == 404


async def test_backup_delete_requires_admin(client, auth_headers):
    _, headers = await _create_user_and_login(client, auth_headers, "backupuser")

    resp = await client.delete("/api/v1/library/backup/armarium_20260101_000000.db", headers=headers)
    assert resp.status_code == 403


async def test_media_item_source_fields(client, auth_headers):
    """`source`/`source_id` are nullable provenance columns set by external
    syncs (e.g. Plex) — not part of MediaItemCreate/Update, but round-trip
    through MediaItemResponse once set directly on the row."""
    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.models.media import MediaItem

    cd_id = await _subtype_id(client, auth_headers, "CD")
    resp = await client.post(
        "/api/v1/media",
        json={"title": "Synced Album", "media_subtype_id": cd_id},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    item_id = resp.json()["id"]
    assert resp.json()["source"] is None
    assert resp.json()["source_id"] is None

    async with AsyncSessionLocal() as db:
        item = (await db.execute(select(MediaItem).where(MediaItem.id == item_id))).scalar_one()
        item.source = "plex"
        item.source_id = "1:plex://abc123"
        await db.commit()

    resp = await client.get(f"/api/v1/media/{item_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["source"] == "plex"
    assert resp.json()["source_id"] == "1:plex://abc123"


# Plex integration config ──────────────────────────────────────────────────

async def test_plex_config_not_configured_by_default(client, auth_headers):
    resp = await client.get("/api/v1/admin/plex/config", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["configured"] is False
    assert body["enabled"] is False
    assert body["base_url"] is None
    assert body["platform"] is None


async def test_plex_config_create_update_delete(client, auth_headers):
    from app.database import AsyncSessionLocal

    resp = await client.post("/api/v1/platforms", json={"name": "Plex Config Platform"}, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    platform_id = resp.json()["id"]

    # platform_id is required.
    resp = await client.put(
        "/api/v1/admin/plex/config",
        json={"base_url": "http://192.168.1.10:32400", "token": "secret-token", "enabled": True},
        headers=auth_headers,
    )
    assert resp.status_code == 422

    # Initial setup requires a token.
    resp = await client.put(
        "/api/v1/admin/plex/config",
        json={"base_url": "http://192.168.1.10:32400", "enabled": True, "platform_id": platform_id},
        headers=auth_headers,
    )
    assert resp.status_code == 400

    # Unknown platform_id -> 404.
    resp = await client.put(
        "/api/v1/admin/plex/config",
        json={"base_url": "http://192.168.1.10:32400", "token": "secret-token", "enabled": True, "platform_id": 999999},
        headers=auth_headers,
    )
    assert resp.status_code == 404

    resp = await client.put(
        "/api/v1/admin/plex/config",
        json={"base_url": "http://192.168.1.10:32400", "token": "secret-token", "enabled": True, "platform_id": platform_id},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["configured"] is True
    assert body["enabled"] is True
    assert body["base_url"] == "http://192.168.1.10:32400"
    assert body["platform"]["id"] == platform_id
    assert "token" not in body

    # GET never returns the token either.
    resp = await client.get("/api/v1/admin/plex/config", headers=auth_headers)
    assert resp.status_code == 200
    assert "token" not in resp.json()
    assert resp.json()["platform"]["id"] == platform_id

    # Omitting the token on update preserves the existing one — just toggling `enabled`.
    resp = await client.put(
        "/api/v1/admin/plex/config",
        json={"base_url": "http://192.168.1.10:32400", "enabled": False, "platform_id": platform_id},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["enabled"] is False
    assert resp.json()["base_url"] == "http://192.168.1.10:32400"

    async with AsyncSessionLocal() as db:
        from app.models.plex_config import PlexConfig
        from sqlalchemy import select
        config = (await db.execute(select(PlexConfig))).scalar_one()
        assert config.token == "secret-token"

    resp = await client.delete("/api/v1/admin/plex/config", headers=auth_headers)
    assert resp.status_code == 204

    resp = await client.get("/api/v1/admin/plex/config", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["configured"] is False


async def test_plex_test_connection(client, auth_headers):
    with patch("app.services.plex.test_connection", new=AsyncMock(return_value={"ok": True, "name": "My Plex", "version": "1.2.3"})):
        resp = await client.post(
            "/api/v1/admin/plex/test",
            json={"base_url": "http://192.168.1.10:32400", "token": "secret-token"},
            headers=auth_headers,
        )
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "My Plex"

    with patch("app.services.plex.test_connection", new=AsyncMock(side_effect=Exception("connection refused"))):
        resp = await client.post(
            "/api/v1/admin/plex/test",
            json={"base_url": "http://192.168.1.10:32400", "token": "bad-token"},
            headers=auth_headers,
        )
    assert resp.status_code == 400


async def test_plex_config_requires_admin(client, auth_headers):
    _, headers = await _create_user_and_login(client, auth_headers, "plexuser")

    resp = await client.get("/api/v1/admin/plex/config", headers=headers)
    assert resp.status_code == 403

    resp = await client.put(
        "/api/v1/admin/plex/config",
        json={"base_url": "http://example.com", "token": "x", "platform_id": 1},
        headers=headers,
    )
    assert resp.status_code == 403


# Plex library mappings ──────────────────────────────────────────────────────

_PLEX_SECTIONS = [
    {"key": "1", "title": "Movies", "type": "movie"},
    {"key": "2", "title": "TV Shows", "type": "show"},
    {"key": "3", "title": "Music", "type": "artist"},
]


async def _ensure_plex_platform(client, auth_headers) -> dict:
    """Get or create the platform named "Plex", used as the admin-configured
    Plex sync platform across the Plex test suite."""
    resp = await client.get("/api/v1/platforms", headers=auth_headers)
    for platform in resp.json():
        if platform["name"] == "Plex":
            return platform
    resp = await client.post("/api/v1/platforms", json={"name": "Plex", "logo_key": "plex"}, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _configure_plex(client, auth_headers):
    platform = await _ensure_plex_platform(client, auth_headers)
    resp = await client.put(
        "/api/v1/admin/plex/config",
        json={"base_url": "http://192.168.1.10:32400", "token": "secret-token", "enabled": True, "platform_id": platform["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    return platform


async def test_delete_platform_used_by_plex_config_rejected(client, auth_headers):
    """A platform configured as the Plex sync platform can't be deleted, even
    if no media items use it yet — otherwise PlexConfig.platform_id would
    dangle (and the FK's ON DELETE RESTRICT would surface as a 500)."""
    plex_platform = await _configure_plex(client, auth_headers)

    resp = await client.delete(f"/api/v1/platforms/{plex_platform['id']}", headers=auth_headers)
    assert resp.status_code == 400

    # Restore the unconfigured state for tests that follow.
    resp = await client.delete("/api/v1/admin/plex/config", headers=auth_headers)
    assert resp.status_code == 204


async def test_plex_mappings_require_config(client, auth_headers):
    resp = await client.get("/api/v1/admin/plex/sections", headers=auth_headers)
    assert resp.status_code == 400

    resp = await client.post(
        "/api/v1/admin/plex/mappings", json={"section_key": "1"}, headers=auth_headers
    )
    assert resp.status_code == 400


async def test_plex_sections_list_and_mapped_flag(client, auth_headers):
    await _configure_plex(client, auth_headers)

    with patch("app.services.plex.list_sections", new=AsyncMock(return_value=_PLEX_SECTIONS)):
        resp = await client.get("/api/v1/admin/plex/sections", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    sections = resp.json()
    assert {s["key"]: s["mapped"] for s in sections} == {"1": False, "2": False, "3": False}


async def test_plex_mapping_create_list_delete(client, auth_headers):
    await _configure_plex(client, auth_headers)

    with patch("app.services.plex.list_sections", new=AsyncMock(return_value=_PLEX_SECTIONS)):
        resp = await client.post(
            "/api/v1/admin/plex/mappings", json={"section_key": "1"}, headers=auth_headers
        )
    assert resp.status_code == 201, resp.text
    mapping = resp.json()
    assert mapping["section_key"] == "1"
    assert mapping["section_title"] == "Movies"
    assert mapping["section_type"] == "movie"
    assert mapping["category"] == "films_tv"
    assert mapping["last_synced_at"] is None

    # The section now shows as mapped.
    with patch("app.services.plex.list_sections", new=AsyncMock(return_value=_PLEX_SECTIONS)):
        resp = await client.get("/api/v1/admin/plex/sections", headers=auth_headers)
    assert {s["key"]: s["mapped"] for s in resp.json()} == {"1": True, "2": False, "3": False}

    resp = await client.get("/api/v1/admin/plex/mappings", headers=auth_headers)
    assert resp.status_code == 200
    mappings = resp.json()
    assert len(mappings) == 1
    assert mappings[0]["id"] == mapping["id"]

    with patch("app.services.plex.list_sections", new=AsyncMock(return_value=_PLEX_SECTIONS)):
        resp = await client.post(
            "/api/v1/admin/plex/mappings", json={"section_key": "3"}, headers=auth_headers
        )
    assert resp.status_code == 201, resp.text
    second = resp.json()
    assert second["category"] == "music"

    resp = await client.delete(f"/api/v1/admin/plex/mappings/{mapping['id']}", headers=auth_headers)
    assert resp.status_code == 204

    resp = await client.get("/api/v1/admin/plex/mappings", headers=auth_headers)
    assert [m["id"] for m in resp.json()] == [second["id"]]


async def test_plex_mapping_duplicate_and_unknown_section(client, auth_headers):
    await _configure_plex(client, auth_headers)

    with patch("app.services.plex.list_sections", new=AsyncMock(return_value=_PLEX_SECTIONS)):
        resp = await client.post(
            "/api/v1/admin/plex/mappings", json={"section_key": "1"}, headers=auth_headers
        )
        assert resp.status_code == 201

        # Re-mapping the same section -> 409.
        resp = await client.post(
            "/api/v1/admin/plex/mappings", json={"section_key": "1"}, headers=auth_headers
        )
        assert resp.status_code == 409

        # Unknown section key -> 404.
        resp = await client.post(
            "/api/v1/admin/plex/mappings", json={"section_key": "does-not-exist"}, headers=auth_headers
        )
        assert resp.status_code == 404


async def test_plex_mapping_delete_unknown_404(client, auth_headers):
    await _configure_plex(client, auth_headers)

    resp = await client.delete("/api/v1/admin/plex/mappings/999999", headers=auth_headers)
    assert resp.status_code == 404


async def test_plex_mappings_permission_enforced(client, auth_headers):
    await _configure_plex(client, auth_headers)
    _, headers = await _create_user_and_login(client, auth_headers, "plexmappinguser", can_add_items=False)

    resp = await client.get("/api/v1/admin/plex/sections", headers=headers)
    assert resp.status_code == 403

    resp = await client.get("/api/v1/admin/plex/mappings", headers=headers)
    assert resp.status_code == 403

    resp = await client.post(
        "/api/v1/admin/plex/mappings", json={"section_key": "1"}, headers=headers
    )
    assert resp.status_code == 403


# Plex sync engine ────────────────────────────────────────────────────────

_PLEX_MOVIE_ITEM = {
    "guid": "plex://movie/abc123",
    "title": "The Matrix",
    "year": 1999,
    "summary": "A computer hacker learns about the true nature of reality.",
    "genres": ["Action", "Sci-Fi"],
    "studio": "Warner Bros.",
    "thumb": "/library/metadata/1/thumb/1",
    "tmdb_id": 603,
    "musicbrainz_id": None,
    "directors": ["Lana Wachowski", "Lilly Wachowski"],
    "cast": ["Keanu Reeves", "Laurence Fishburne"],
    "duration_ms": 8160000,
    "content_rating": "R",
}

_PLEX_MOVIE_ITEM_2 = {
    "guid": "plex://movie/def456",
    "title": "Inception",
    "year": 2010,
    "summary": "A thief who steals corporate secrets through dream-sharing.",
    "genres": ["Action", "Sci-Fi"],
    "studio": "Warner Bros.",
    "thumb": "/library/metadata/2/thumb/1",
    "tmdb_id": 27205,
    "musicbrainz_id": None,
    "directors": ["Christopher Nolan"],
    "cast": ["Leonardo DiCaprio"],
    "duration_ms": 8880000,
    "content_rating": "PG-13",
}

_PLEX_MOVIE_ITEM_RELOADED = {
    "guid": "plex://movie/reloaded",
    "title": "The Matrix Reloaded",
    "year": 2003,
    "summary": "Neo and his allies race against time before the machines discover the keys to Zion's hidden location.",
    "genres": ["Action", "Sci-Fi"],
    "studio": "Warner Bros.",
    "thumb": "/library/metadata/4/thumb/1",
    "tmdb_id": 604,
    "musicbrainz_id": None,
    "directors": ["Lana Wachowski", "Lilly Wachowski"],
    "cast": ["Keanu Reeves", "Laurence Fishburne"],
    "duration_ms": 8160000,
    "content_rating": "R",
}

_PLEX_MOVIE_ITEM_REVOLUTIONS = {
    "guid": "plex://movie/revolutions",
    "title": "The Matrix Revolutions",
    "year": 2003,
    "summary": "The human city of Zion defends itself against the massive invasion of the machines.",
    "genres": ["Action", "Sci-Fi"],
    "studio": "Warner Bros.",
    "thumb": "/library/metadata/6/thumb/1",
    "tmdb_id": 605,
    "musicbrainz_id": None,
    "directors": ["Lana Wachowski", "Lilly Wachowski"],
    "cast": ["Keanu Reeves", "Laurence Fishburne"],
    "duration_ms": 7800000,
    "content_rating": "R",
}

_PLEX_MOVIE_ITEM_JOHN_WICK = {
    "guid": "plex://movie/johnwick",
    "title": "John Wick",
    "year": 2014,
    "summary": "An ex-hitman comes out of retirement to track down the gangsters that took everything from him.",
    "genres": ["Action", "Thriller"],
    "studio": "Summit Entertainment",
    "thumb": "/library/metadata/7/thumb/1",
    "tmdb_id": 606,
    "musicbrainz_id": None,
    "directors": ["Chad Stahelski", "David Leitch"],
    "cast": ["Keanu Reeves"],
    "duration_ms": 6120000,
    "content_rating": "R",
}

_PLEX_MOVIE_ITEM_RESURRECTIONS = {
    "guid": "plex://movie/resurrections",
    "title": "The Matrix Resurrections",
    "year": 2021,
    "summary": "Plex synopsis: Neo must choose to follow the white rabbit once more.",
    "genres": ["Action", "Sci-Fi"],
    "studio": "Warner Bros.",
    "thumb": "/library/metadata/8/thumb/1",
    "tmdb_id": 607,
    "musicbrainz_id": None,
    "directors": ["Lana Wachowski"],
    "cast": ["Keanu Reeves", "Carrie-Anne Moss"],
    "duration_ms": 8520000,
    "content_rating": "R",
}

_PLEX_MOVIE_ITEM_3 = {
    "guid": "plex://movie/speed",
    "title": "Speed",
    "year": 1994,
    "summary": "A young police officer must prevent a bomb exploding aboard a city bus.",
    "genres": ["Action", "Thriller"],
    "studio": "20th Century Fox",
    "thumb": "/library/metadata/5/thumb/1",
    "tmdb_id": 1234,
    "musicbrainz_id": None,
    "directors": ["Jan de Bont"],
    "cast": ["Keanu Reeves", "Sandra Bullock"],
    "duration_ms": 6960000,
    "content_rating": "R",
}

_PLEX_MOVIE_ITEM_EDGE = {
    "guid": "plex://movie/edgeoftomorrow",
    "title": "Edge of Tomorrow",
    "year": 2014,
    "summary": "A soldier fighting aliens gets to relive the same day over and over again.",
    "genres": ["Action", "Sci-Fi"],
    "studio": "Warner Bros.",
    "thumb": "/library/metadata/10/thumb/1",
    "tmdb_id": 137113,
    "musicbrainz_id": None,
    "directors": ["Doug Liman"],
    "cast": ["Tom Cruise", "Emily Blunt"],
    "duration_ms": 6960000,
    "content_rating": "PG-13",
}

_PLEX_MOVIE_ITEM_NO_TMDB = {
    "guid": "plex://movie/indiedarling",
    "title": "Indie Darling",
    "year": 2010,
    "summary": "A tiny indie film with no TMDB listing.",
    "genres": ["Drama"],
    "studio": "Indie Studio",
    "thumb": "/library/metadata/11/thumb/1",
    "tmdb_id": None,
    "musicbrainz_id": None,
    "directors": ["Some Director"],
    "cast": ["Some Actor"],
    "duration_ms": 5400000,
    "content_rating": "R",
}

_PLEX_MOVIE_ITEM_QUANTUM = {
    "guid": "plex://movie/quantumheist",
    "title": "The Quantum Heist",
    "year": 2012,
    "summary": "A crew of thieves attempt to steal a prototype quantum computer.",
    "genres": ["Action", "Sci-Fi"],
    "studio": "Fictional Studios",
    "thumb": "/library/metadata/12/thumb/1",
    "tmdb_id": 555444,
    "musicbrainz_id": None,
    "directors": ["A. Director"],
    "cast": ["An Actor"],
    "duration_ms": 6300000,
    "content_rating": "PG-13",
}

_PLEX_MOVIE_ITEM_OUTPOST = {
    "guid": "plex://movie/lastoutpost",
    "title": "The Last Outpost",
    "year": 2016,
    "summary": "Survivors hold out at a remote research station.",
    "genres": ["Sci-Fi", "Thriller"],
    "studio": "Fictional Studios",
    "thumb": "/library/metadata/13/thumb/1",
    "tmdb_id": 778899,
    "musicbrainz_id": None,
    "directors": ["B. Director"],
    "cast": ["Another Actor"],
    "duration_ms": 6000000,
    "content_rating": "PG-13",
}

_PLEX_ALBUM_ITEM = {
    "guid": "plex://album/xyz789",
    "title": "OK Computer",
    "year": 1997,
    "summary": "Third studio album by Radiohead.",
    "genres": ["Alternative Rock"],
    "studio": "Parlophone",
    "thumb": "/library/metadata/3/thumb/1",
    "tmdb_id": None,
    "musicbrainz_id": "b9f3a0b9-4c0c-4d3a-9c2a-0123456789ab",
    "artist_name": "Radiohead",
    "leaf_count": 12,
}

_PLEX_TVSHOW_ITEM_REMOVE = {
    "guid": "plex://show/removeme",
    "title": "Quietly Cancelled Show",
    "year": 2015,
    "summary": "A show that got cancelled after one season.",
    "genres": ["Drama"],
    "studio": "Indie Studio",
    "thumb": "/library/metadata/9/thumb/1",
    "tmdb_id": 9001,
    "musicbrainz_id": None,
    "directors": ["Jane Doe"],
    "cast": ["Someone Else"],
    "duration_ms": 2700000,
    "content_rating": "TV-14",
}


async def _get_or_create_mapping_for_section(client, auth_headers, section_key):
    """Reuse a mapping left over from earlier tests for `section_key`, or
    create one. Reusing keeps mapping ids stable across tests, which matters
    because stale-item detection scopes by `source_id` prefix `"{mapping.id}:"`."""
    await _configure_plex(client, auth_headers)
    resp = await client.get("/api/v1/admin/plex/mappings", headers=auth_headers)
    for existing in resp.json():
        if existing["section_key"] == section_key:
            return existing

    with patch("app.services.plex.list_sections", new=AsyncMock(return_value=_PLEX_SECTIONS)):
        resp = await client.post(
            "/api/v1/admin/plex/mappings", json={"section_key": section_key}, headers=auth_headers
        )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_movie_mapping(client, auth_headers):
    return await _get_or_create_mapping_for_section(client, auth_headers, "1")


async def _create_tvshow_mapping(client, auth_headers):
    return await _get_or_create_mapping_for_section(client, auth_headers, "2")


async def _create_music_mapping(client, auth_headers):
    return await _get_or_create_mapping_for_section(client, auth_headers, "3")


async def _find_item_by_title(client, auth_headers, title: str) -> dict:
    resp = await client.get("/api/v1/media", params={"per_page": 100}, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    for item in resp.json()["items"]:
        if item["title"] == title:
            return item
    raise AssertionError(f"No item titled {title!r} found")


async def test_plex_sync_creates_items(client, auth_headers):
    mapping = await _create_movie_mapping(client, auth_headers)

    with patch("app.services.plex.list_section_items", new=AsyncMock(return_value=[_PLEX_MOVIE_ITEM])), \
            patch("app.services.plex.fetch_thumbnail", new=AsyncMock(return_value=PNG_1X1)):
        resp = await client.post(f"/api/v1/admin/plex/mappings/{mapping['id']}/sync", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["created"] == 1
    assert result["updated"] == 0
    assert result["conflicts"] == []
    assert result["stale_items"] == []

    item = await _find_item_by_title(client, auth_headers, "The Matrix")
    assert item["source"] == "plex"
    assert item["source_id"] == f"{mapping['id']}:plex://movie/abc123"
    assert item["platform"]["name"] == "Plex"
    assert item["media_subtype"]["name"] == "Film"
    assert item["category"] == "films_tv"
    assert item["tmdb_id"] == 603
    assert item["genres"] == "Action, Sci-Fi"
    assert item["director"] == "Lana Wachowski, Lilly Wachowski"
    assert item["cast_list"] == "Keanu Reeves, Laurence Fishburne"
    assert item["runtime_minutes"] == 136
    assert item["rating"] == "R"
    assert item["cover_image_path"] is not None

    # last_synced_at is stamped.
    resp = await client.get("/api/v1/admin/plex/mappings", headers=auth_headers)
    synced = next(m for m in resp.json() if m["id"] == mapping["id"])
    assert synced["last_synced_at"] is not None


async def test_plex_sync_rerun_updates_not_duplicates(client, auth_headers):
    mapping = await _create_movie_mapping(client, auth_headers)

    with patch("app.services.plex.list_section_items", new=AsyncMock(return_value=[_PLEX_MOVIE_ITEM_RELOADED])), \
            patch("app.services.plex.fetch_thumbnail", new=AsyncMock(return_value=None)):
        resp = await client.post(f"/api/v1/admin/plex/mappings/{mapping['id']}/sync", headers=auth_headers)
    assert resp.json()["created"] == 1

    updated_item = dict(_PLEX_MOVIE_ITEM_RELOADED, summary="Updated description")
    with patch("app.services.plex.list_section_items", new=AsyncMock(return_value=[updated_item])), \
            patch("app.services.plex.fetch_thumbnail", new=AsyncMock(return_value=None)):
        resp = await client.post(f"/api/v1/admin/plex/mappings/{mapping['id']}/sync", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["created"] == 0
    assert result["updated"] == 1

    resp = await client.get("/api/v1/media", params={"per_page": 100}, headers=auth_headers)
    matches = [i for i in resp.json()["items"] if i["title"] == "The Matrix Reloaded"]
    assert len(matches) == 1
    assert matches[0]["description"] == "Updated description"


async def test_plex_sync_detects_conflict_with_same_platform_item(client, auth_headers):
    """A duplicate is when platform and item match: an existing item on the
    admin-configured Plex platform with the same identity is a conflict, just
    like before this item ever appeared on a different platform."""
    mapping = await _create_movie_mapping(client, auth_headers)
    plex_platform = await _ensure_plex_platform(client, auth_headers)

    film_subtype_id = await _subtype_id(client, auth_headers, "Film")
    resp = await client.post(
        "/api/v1/media",
        json={
            "title": "The Matrix Revolutions",
            "media_subtype_id": film_subtype_id,
            "year": 2003,
            "tmdb_id": 605,
            "platform_id": plex_platform["id"],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    manual_item_id = resp.json()["id"]

    with patch("app.services.plex.list_section_items", new=AsyncMock(return_value=[_PLEX_MOVIE_ITEM_REVOLUTIONS])), \
            patch("app.services.plex.fetch_thumbnail", new=AsyncMock(return_value=None)):
        resp = await client.post(f"/api/v1/admin/plex/mappings/{mapping['id']}/sync", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["created"] == 0
    assert result["updated"] == 0
    assert len(result["conflicts"]) == 1

    conflict = result["conflicts"][0]
    assert conflict["existing_item"]["id"] == manual_item_id
    assert conflict["plex_item"]["guid"] == _PLEX_MOVIE_ITEM_REVOLUTIONS["guid"]
    assert conflict["plex_item"]["title"] == "The Matrix Revolutions"

    # The manual item is untouched and not adopted.
    resp = await client.get(f"/api/v1/media/{manual_item_id}", headers=auth_headers)
    assert resp.json()["source"] is None


async def test_plex_sync_links_other_platform_and_physical_matches(client, auth_headers):
    """If we already have a physical copy or a copy on a different digital
    platform, the new Plex item is created on the configured platform and
    linked to those copies instead of being flagged as a conflict."""
    mapping = await _create_movie_mapping(client, auth_headers)

    bluray_id = await _subtype_id(client, auth_headers, "Blu-ray")
    film_subtype_id = await _subtype_id(client, auth_headers, "Film")

    resp = await client.post(
        "/api/v1/media",
        json={"title": "Edge of Tomorrow", "media_subtype_id": bluray_id, "year": 2014, "tmdb_id": 137113},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    physical_id = resp.json()["id"]

    resp = await client.post("/api/v1/platforms", json={"name": "Amazon Video"}, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    amazon_platform_id = resp.json()["id"]

    resp = await client.post(
        "/api/v1/media",
        json={
            "title": "Edge of Tomorrow",
            "media_subtype_id": film_subtype_id,
            "year": 2014,
            "tmdb_id": 137113,
            "platform_id": amazon_platform_id,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    amazon_id = resp.json()["id"]

    with patch("app.services.plex.list_section_items", new=AsyncMock(return_value=[_PLEX_MOVIE_ITEM_EDGE])), \
            patch("app.services.plex.fetch_thumbnail", new=AsyncMock(return_value=None)):
        resp = await client.post(f"/api/v1/admin/plex/mappings/{mapping['id']}/sync", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["created"] == 1
    assert result["conflicts"] == []

    resp = await client.get("/api/v1/media", params={"per_page": 100}, headers=auth_headers)
    items = [i for i in resp.json()["items"] if i["title"] == "Edge of Tomorrow"]
    assert len(items) == 3
    plex_item = next(i for i in items if i["source"] == "plex")
    assert plex_item["platform"]["name"] == "Plex"
    assert {li["id"] for li in plex_item["linked_items"]} == {physical_id, amazon_id}
    assert plex_item["ownership"] == "both"

    resp = await client.get(f"/api/v1/media/{physical_id}", headers=auth_headers)
    assert plex_item["id"] in {li["id"] for li in resp.json()["linked_items"]}

    resp = await client.get(f"/api/v1/media/{amazon_id}", headers=auth_headers)
    assert plex_item["id"] in {li["id"] for li in resp.json()["linked_items"]}


async def test_plex_sync_matches_by_title_and_year_without_tmdb_id(client, auth_headers):
    """A Plex item with no tmdb_id falls back to a case-insensitive title +
    year match against existing items — so a physical copy that predates any
    TMDB metadata is linked rather than left as an unrelated duplicate."""
    mapping = await _create_movie_mapping(client, auth_headers)

    bluray_id = await _subtype_id(client, auth_headers, "Blu-ray")
    resp = await client.post(
        "/api/v1/media",
        json={"title": "indie darling", "media_subtype_id": bluray_id, "year": 2010},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    physical_id = resp.json()["id"]
    assert resp.json()["linked_items"] == []

    with patch("app.services.plex.list_section_items", new=AsyncMock(return_value=[_PLEX_MOVIE_ITEM_NO_TMDB])), \
            patch("app.services.plex.fetch_thumbnail", new=AsyncMock(return_value=None)):
        resp = await client.post(f"/api/v1/admin/plex/mappings/{mapping['id']}/sync", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["created"] == 1
    assert result["conflicts"] == []

    resp = await client.get("/api/v1/media", params={"per_page": 100}, headers=auth_headers)
    items = [i for i in resp.json()["items"] if i["title"].lower() == "indie darling"]
    assert len(items) == 2
    plex_item = next(i for i in items if i["source"] == "plex")
    assert [li["id"] for li in plex_item["linked_items"]] == [physical_id]


async def test_plex_sync_detects_stale_items(client, auth_headers):
    # Uses the TV-shows mapping (a distinct mapping id from the movie tests
    # above) so stale-detection's "{mapping.id}:" prefix scan doesn't pick up
    # Plex items created by those tests.
    mapping = await _create_tvshow_mapping(client, auth_headers)

    with patch("app.services.plex.list_section_items", new=AsyncMock(return_value=[_PLEX_MOVIE_ITEM_3, _PLEX_MOVIE_ITEM_2])), \
            patch("app.services.plex.fetch_thumbnail", new=AsyncMock(return_value=None)):
        resp = await client.post(f"/api/v1/admin/plex/mappings/{mapping['id']}/sync", headers=auth_headers)
    assert resp.json()["created"] == 2

    # "Inception" removed from Plex.
    with patch("app.services.plex.list_section_items", new=AsyncMock(return_value=[_PLEX_MOVIE_ITEM_3])), \
            patch("app.services.plex.fetch_thumbnail", new=AsyncMock(return_value=None)):
        resp = await client.post(f"/api/v1/admin/plex/mappings/{mapping['id']}/sync", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["created"] == 0
    assert result["updated"] == 1
    assert len(result["stale_items"]) == 1
    assert result["stale_items"][0]["title"] == "Inception"

    # Still present in the library — Phase 7 removal isn't triggered by a sync.
    item = await _find_item_by_title(client, auth_headers, "Inception")
    assert item["source"] == "plex"


async def test_plex_sync_music_mapping(client, auth_headers):
    mapping = await _create_music_mapping(client, auth_headers)

    with patch("app.services.plex.list_section_items", new=AsyncMock(return_value=[_PLEX_ALBUM_ITEM])), \
            patch("app.services.plex.fetch_thumbnail", new=AsyncMock(return_value=None)):
        resp = await client.post(f"/api/v1/admin/plex/mappings/{mapping['id']}/sync", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["created"] == 1

    item = await _find_item_by_title(client, auth_headers, "OK Computer")
    assert item["category"] == "music"
    assert item["media_subtype"]["name"] == "Music"
    assert item["artist"] == "Radiohead"
    assert item["label"] == "Parlophone"
    assert item["track_count"] == 12
    assert item["musicbrainz_id"] == "b9f3a0b9-4c0c-4d3a-9c2a-0123456789ab"


async def test_plex_sync_unknown_mapping_404(client, auth_headers):
    await _configure_plex(client, auth_headers)
    resp = await client.post("/api/v1/admin/plex/mappings/999999/sync", headers=auth_headers)
    assert resp.status_code == 404


async def test_plex_sync_permission_enforced(client, auth_headers):
    mapping = await _create_movie_mapping(client, auth_headers)
    _, headers = await _create_user_and_login(client, auth_headers, "plexsyncuser", can_add_items=False)

    resp = await client.post(f"/api/v1/admin/plex/mappings/{mapping['id']}/sync", headers=headers)
    assert resp.status_code == 403

    resp = await client.delete("/api/v1/admin/plex/mappings/1", headers=headers)
    assert resp.status_code == 403


# Plex conflict resolution ──────────────────────────────────────────────────


async def test_plex_resolve_conflict_keep_mine(client, auth_headers):
    mapping = await _create_movie_mapping(client, auth_headers)
    plex_platform = await _ensure_plex_platform(client, auth_headers)

    film_subtype_id = await _subtype_id(client, auth_headers, "Film")
    resp = await client.post(
        "/api/v1/media",
        json={
            "title": "John Wick",
            "media_subtype_id": film_subtype_id,
            "year": 2014,
            "tmdb_id": 606,
            "description": "My manual notes",
            "platform_id": plex_platform["id"],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    manual_item_id = resp.json()["id"]

    with patch("app.services.plex.list_section_items", new=AsyncMock(return_value=[_PLEX_MOVIE_ITEM_JOHN_WICK])), \
            patch("app.services.plex.fetch_thumbnail", new=AsyncMock(return_value=None)):
        resp = await client.post(f"/api/v1/admin/plex/mappings/{mapping['id']}/sync", headers=auth_headers)
    conflicts = resp.json()["conflicts"]
    assert len(conflicts) == 1
    plex_item = conflicts[0]["plex_item"]

    resp = await client.post(
        f"/api/v1/admin/plex/mappings/{mapping['id']}/resolve-conflicts",
        json={"resolutions": [{"existing_item_id": manual_item_id, "plex_item": plex_item, "resolution": "keep_mine"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"resolved": 1}

    resp = await client.get(f"/api/v1/media/{manual_item_id}", headers=auth_headers)
    item = resp.json()
    assert item["source"] == "plex"
    assert item["source_id"] == f"{mapping['id']}:plex://movie/johnwick"
    assert item["platform"]["name"] == "Plex"
    assert item["media_subtype"]["name"] == "Film"
    # "keep_mine" leaves content untouched.
    assert item["description"] == "My manual notes"

    # Re-syncing now updates the adopted item in place instead of flagging it
    # as a conflict again, and doesn't create a duplicate.
    with patch("app.services.plex.list_section_items", new=AsyncMock(return_value=[_PLEX_MOVIE_ITEM_JOHN_WICK])), \
            patch("app.services.plex.fetch_thumbnail", new=AsyncMock(return_value=None)):
        resp = await client.post(f"/api/v1/admin/plex/mappings/{mapping['id']}/sync", headers=auth_headers)
    result = resp.json()
    assert result["conflicts"] == []
    assert result["created"] == 0
    assert result["updated"] == 1

    resp = await client.get("/api/v1/media", params={"per_page": 100}, headers=auth_headers)
    matches = [i for i in resp.json()["items"] if i["title"] == "John Wick"]
    assert len(matches) == 1


async def test_plex_resolve_conflict_use_plex(client, auth_headers):
    mapping = await _create_movie_mapping(client, auth_headers)
    plex_platform = await _ensure_plex_platform(client, auth_headers)

    film_subtype_id = await _subtype_id(client, auth_headers, "Film")
    resp = await client.post(
        "/api/v1/media",
        json={
            "title": "The Matrix Resurrections",
            "media_subtype_id": film_subtype_id,
            "year": 2021,
            "tmdb_id": 607,
            "description": "My manual notes",
            "genres": "Comedy",
            "platform_id": plex_platform["id"],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    manual_item_id = resp.json()["id"]

    with patch("app.services.plex.list_section_items", new=AsyncMock(return_value=[_PLEX_MOVIE_ITEM_RESURRECTIONS])), \
            patch("app.services.plex.fetch_thumbnail", new=AsyncMock(return_value=None)):
        resp = await client.post(f"/api/v1/admin/plex/mappings/{mapping['id']}/sync", headers=auth_headers)
    conflicts = resp.json()["conflicts"]
    assert len(conflicts) == 1
    plex_item = conflicts[0]["plex_item"]

    with patch("app.services.plex.fetch_thumbnail", new=AsyncMock(return_value=PNG_1X1)):
        resp = await client.post(
            f"/api/v1/admin/plex/mappings/{mapping['id']}/resolve-conflicts",
            json={"resolutions": [{"existing_item_id": manual_item_id, "plex_item": plex_item, "resolution": "use_plex"}]},
            headers=auth_headers,
        )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"resolved": 1}

    resp = await client.get(f"/api/v1/media/{manual_item_id}", headers=auth_headers)
    item = resp.json()
    assert item["source"] == "plex"
    assert item["source_id"] == f"{mapping['id']}:plex://movie/resurrections"
    assert item["platform"]["name"] == "Plex"
    # "use_plex" overwrites content fields and the cover with Plex's data.
    assert item["description"].startswith("Plex synopsis")
    assert item["genres"] == "Action, Sci-Fi"
    assert item["cover_image_path"] is not None


async def test_plex_resolve_conflict_links_other_platform_match(client, auth_headers):
    """Resolving a conflict also links any physical/other-platform copies of
    the same item that exist at sync time — not just the adopted item."""
    mapping = await _create_movie_mapping(client, auth_headers)
    plex_platform = await _ensure_plex_platform(client, auth_headers)

    film_subtype_id = await _subtype_id(client, auth_headers, "Film")
    bluray_id = await _subtype_id(client, auth_headers, "Blu-ray")

    resp = await client.post(
        "/api/v1/media",
        json={
            "title": "The Quantum Heist",
            "media_subtype_id": film_subtype_id,
            "year": 2012,
            "tmdb_id": 555444,
            "platform_id": plex_platform["id"],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    manual_item_id = resp.json()["id"]

    resp = await client.post(
        "/api/v1/media",
        json={"title": "The Quantum Heist", "media_subtype_id": bluray_id, "year": 2012, "tmdb_id": 555444},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    physical_id = resp.json()["id"]

    # The two were auto-linked on creation (same tmdb_id) — unlink them to
    # simulate copies added before linking existed.
    resp = await client.delete(f"/api/v1/media/{manual_item_id}/link/{physical_id}", headers=auth_headers)
    assert resp.status_code == 204, resp.text

    with patch("app.services.plex.list_section_items", new=AsyncMock(return_value=[_PLEX_MOVIE_ITEM_QUANTUM])), \
            patch("app.services.plex.fetch_thumbnail", new=AsyncMock(return_value=None)):
        resp = await client.post(f"/api/v1/admin/plex/mappings/{mapping['id']}/sync", headers=auth_headers)
    conflicts = resp.json()["conflicts"]
    assert len(conflicts) == 1
    plex_item = conflicts[0]["plex_item"]

    resp = await client.post(
        f"/api/v1/admin/plex/mappings/{mapping['id']}/resolve-conflicts",
        json={"resolutions": [{"existing_item_id": manual_item_id, "plex_item": plex_item, "resolution": "keep_mine"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"resolved": 1}

    resp = await client.get(f"/api/v1/media/{manual_item_id}", headers=auth_headers)
    assert [li["id"] for li in resp.json()["linked_items"]] == [physical_id]


async def test_plex_resolve_conflict_unknown_item_404(client, auth_headers):
    mapping = await _create_movie_mapping(client, auth_headers)

    resp = await client.post(
        f"/api/v1/admin/plex/mappings/{mapping['id']}/resolve-conflicts",
        json={
            "resolutions": [
                {"existing_item_id": 999999, "plex_item": {"guid": "plex://movie/missing", "title": "Missing"}, "resolution": "keep_mine"}
            ]
        },
        headers=auth_headers,
    )
    assert resp.status_code == 404


async def test_plex_resolve_conflicts_permission_enforced(client, auth_headers):
    mapping = await _create_movie_mapping(client, auth_headers)
    _, headers = await _create_user_and_login(client, auth_headers, "plexresolveuser", can_add_items=False)

    resp = await client.post(
        f"/api/v1/admin/plex/mappings/{mapping['id']}/resolve-conflicts",
        json={"resolutions": []},
        headers=headers,
    )
    assert resp.status_code == 403


# Plex stale-item removal ────────────────────────────────────────────────────


async def test_plex_remove_stale_items(client, auth_headers):
    mapping = await _create_tvshow_mapping(client, auth_headers)

    with patch("app.services.plex.list_section_items", new=AsyncMock(return_value=[_PLEX_TVSHOW_ITEM_REMOVE])), \
            patch("app.services.plex.fetch_thumbnail", new=AsyncMock(return_value=PNG_1X1)):
        resp = await client.post(f"/api/v1/admin/plex/mappings/{mapping['id']}/sync", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["created"] == 1

    item = await _find_item_by_title(client, auth_headers, "Quietly Cancelled Show")
    assert item["source"] == "plex"

    # Removed from Plex entirely — the next sync flags it as stale.
    with patch("app.services.plex.list_section_items", new=AsyncMock(return_value=[])), \
            patch("app.services.plex.fetch_thumbnail", new=AsyncMock(return_value=None)):
        resp = await client.post(f"/api/v1/admin/plex/mappings/{mapping['id']}/sync", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    stale_item = next(i for i in resp.json()["stale_items"] if i["title"] == "Quietly Cancelled Show")

    resp = await client.post(
        f"/api/v1/admin/plex/mappings/{mapping['id']}/remove-stale",
        json={"item_ids": [stale_item["id"]]},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"removed": 1}

    resp = await client.get(f"/api/v1/media/{stale_item['id']}", headers=auth_headers)
    assert resp.status_code == 404


async def test_plex_remove_stale_item_delinks_without_damaging_partner(client, auth_headers):
    """Removing a stale Plex item that's linked to a physical copy deletes
    only the Plex item and its link — the physical record is left intact
    (link or delink, but don't damage the physical record)."""
    mapping = await _create_movie_mapping(client, auth_headers)

    bluray_id = await _subtype_id(client, auth_headers, "Blu-ray")
    resp = await client.post(
        "/api/v1/media",
        json={"title": "The Last Outpost", "media_subtype_id": bluray_id, "year": 2016, "tmdb_id": 778899},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    physical_id = resp.json()["id"]

    with patch("app.services.plex.list_section_items", new=AsyncMock(return_value=[_PLEX_MOVIE_ITEM_OUTPOST])), \
            patch("app.services.plex.fetch_thumbnail", new=AsyncMock(return_value=None)):
        resp = await client.post(f"/api/v1/admin/plex/mappings/{mapping['id']}/sync", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["created"] == 1

    resp = await client.get("/api/v1/media", params={"per_page": 100}, headers=auth_headers)
    items = [i for i in resp.json()["items"] if i["title"] == "The Last Outpost"]
    plex_item = next(i for i in items if i["source"] == "plex")
    assert [li["id"] for li in plex_item["linked_items"]] == [physical_id]

    # Removed from Plex entirely — the next sync flags the Plex item as stale.
    with patch("app.services.plex.list_section_items", new=AsyncMock(return_value=[])), \
            patch("app.services.plex.fetch_thumbnail", new=AsyncMock(return_value=None)):
        resp = await client.post(f"/api/v1/admin/plex/mappings/{mapping['id']}/sync", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    stale_item = next(i for i in resp.json()["stale_items"] if i["title"] == "The Last Outpost")
    assert stale_item["id"] == plex_item["id"]

    resp = await client.post(
        f"/api/v1/admin/plex/mappings/{mapping['id']}/remove-stale",
        json={"item_ids": [stale_item["id"]]},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"removed": 1}

    # The Plex item is gone...
    resp = await client.get(f"/api/v1/media/{plex_item['id']}", headers=auth_headers)
    assert resp.status_code == 404

    # ...but the physical copy survives, delinked.
    resp = await client.get(f"/api/v1/media/{physical_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["linked_items"] == []


async def test_plex_remove_stale_defensive_checks(client, auth_headers):
    movie_mapping = await _create_movie_mapping(client, auth_headers)
    tvshow_mapping = await _create_tvshow_mapping(client, auth_headers)

    # A manually-added item (source=None) is never removed, even if selected.
    resp = await client.post("/api/v1/platforms", json={"name": "Manual Removal Platform"}, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    platform_id = resp.json()["id"]

    film_subtype_id = await _subtype_id(client, auth_headers, "Film")
    resp = await client.post(
        "/api/v1/media",
        json={"title": "Manually Added Movie", "media_subtype_id": film_subtype_id, "platform_id": platform_id},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    manual_item_id = resp.json()["id"]

    # An item sourced from a different mapping isn't removable via this one.
    matrix_item = await _find_item_by_title(client, auth_headers, "The Matrix")
    assert matrix_item["source"] == "plex"
    assert matrix_item["source_id"].startswith(f"{movie_mapping['id']}:")

    resp = await client.post(
        f"/api/v1/admin/plex/mappings/{tvshow_mapping['id']}/remove-stale",
        json={"item_ids": [manual_item_id, matrix_item["id"], 999999]},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"removed": 0}

    resp = await client.get(f"/api/v1/media/{manual_item_id}", headers=auth_headers)
    assert resp.status_code == 200
    resp = await client.get(f"/api/v1/media/{matrix_item['id']}", headers=auth_headers)
    assert resp.status_code == 200


async def test_plex_remove_stale_unknown_mapping_404(client, auth_headers):
    await _configure_plex(client, auth_headers)
    resp = await client.post(
        "/api/v1/admin/plex/mappings/999999/remove-stale", json={"item_ids": []}, headers=auth_headers
    )
    assert resp.status_code == 404


async def test_plex_remove_stale_permission_enforced(client, auth_headers):
    mapping = await _create_tvshow_mapping(client, auth_headers)
    _, headers = await _create_user_and_login(client, auth_headers, "plexstaleuser", can_add_items=False)

    resp = await client.post(
        f"/api/v1/admin/plex/mappings/{mapping['id']}/remove-stale",
        json={"item_ids": []},
        headers=headers,
    )
    assert resp.status_code == 403
