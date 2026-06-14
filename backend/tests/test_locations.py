"""Tests for app.api.v1.locations — CRUD, hierarchy, sort order, and icons."""
from .conftest import _subtype_id, SVG_PAYLOAD, PNG_1X1


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


# ── Upload validation ────────────────────────────────────────────────────────

async def test_location_icon_upload_rejects_svg(client, auth_headers):
    resp = await client.post("/api/v1/locations", json={"name": "Icon Upload Test Shelf"}, headers=auth_headers)
    loc_id = resp.json()["id"]

    files = {"file": ("evil.svg", SVG_PAYLOAD, "image/svg+xml")}
    resp = await client.post(f"/api/v1/locations/{loc_id}/icon", files=files, headers=auth_headers)
    assert resp.status_code == 400

    resp = await client.delete(f"/api/v1/locations/{loc_id}", headers=auth_headers)
    assert resp.status_code == 204
