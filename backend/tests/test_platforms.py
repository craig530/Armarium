"""Tests for app.api.v1.platforms — CRUD, logo upload, and lock-on-use."""
from .conftest import _subtype_id, SVG_PAYLOAD, PNG_1X1


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

async def test_platform_logo_upload_rejects_svg(client, auth_headers):
    resp = await client.post("/api/v1/platforms", json={"name": "Logo Upload Test Platform"}, headers=auth_headers)
    platform_id = resp.json()["id"]

    files = {"file": ("evil.svg", SVG_PAYLOAD, "image/svg+xml")}
    resp = await client.post(f"/api/v1/platforms/{platform_id}/logo", files=files, headers=auth_headers)
    assert resp.status_code == 400

    resp = await client.delete(f"/api/v1/platforms/{platform_id}", headers=auth_headers)
    assert resp.status_code == 204
