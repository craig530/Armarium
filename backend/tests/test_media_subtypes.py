"""Tests for app.api.v1.media_subtypes — seeding, CRUD, and lock-on-use."""
from .conftest import _create_user_and_login, _subtype_id


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


# ── Permissions ──────────────────────────────────────────────────────────────

async def test_can_manage_media_types_permission_enforced_for_update_and_delete(client, auth_headers):
    # Default for new users is can_manage_media_types=False.
    _, headers = await _create_user_and_login(client, auth_headers, "subtypeupdateuser")
    cd_id = await _subtype_id(client, auth_headers, "CD")

    resp = await client.put(f"/api/v1/media-subtypes/{cd_id}", json={"name": "Compact Disc"}, headers=headers)
    assert resp.status_code == 403

    resp = await client.delete(f"/api/v1/media-subtypes/{cd_id}", headers=headers)
    assert resp.status_code == 403
