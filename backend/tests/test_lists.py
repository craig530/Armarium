"""Tests for app.api.v1.item_lists — CRUD, uniqueness, and permissions."""
from .conftest import _create_user_and_login, _subtype_id


async def test_list_crud_across_categories(client, auth_headers):
    resp = await client.post("/api/v1/lists", json={"name": "Want to read", "category": "books"}, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    book_list = resp.json()
    assert book_list["name"] == "Want to read"
    assert book_list["category"] == "books"
    assert book_list["item_count"] == 0

    resp = await client.post("/api/v1/lists", json={"name": "Favourites", "category": "music"}, headers=auth_headers)
    assert resp.status_code == 201
    music_list = resp.json()

    resp = await client.post("/api/v1/lists", json={"name": "To watch", "category": "films_tv"}, headers=auth_headers)
    assert resp.status_code == 201
    films_list = resp.json()

    # List all
    resp = await client.get("/api/v1/lists", headers=auth_headers)
    assert resp.status_code == 200
    names = {(l["name"], l["category"]) for l in resp.json()}
    assert ("Want to read", "books") in names
    assert ("Favourites", "music") in names
    assert ("To watch", "films_tv") in names

    # Filter by category
    resp = await client.get("/api/v1/lists", params={"category": "books"}, headers=auth_headers)
    assert resp.status_code == 200
    assert all(l["category"] == "books" for l in resp.json())

    # Rename
    resp = await client.put(f"/api/v1/lists/{book_list['id']}", json={"name": "Want to Read"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Want to Read"

    # Delete
    for created in (book_list, music_list, films_list):
        resp = await client.delete(f"/api/v1/lists/{created['id']}", headers=auth_headers)
        assert resp.status_code == 204


async def test_list_name_uniqueness_per_category(client, auth_headers):
    resp = await client.post("/api/v1/lists", json={"name": "Favourites", "category": "books"}, headers=auth_headers)
    assert resp.status_code == 201
    first = resp.json()

    # Duplicate name within the same category -> 409
    resp = await client.post("/api/v1/lists", json={"name": "Favourites", "category": "books"}, headers=auth_headers)
    assert resp.status_code == 409

    # Same name in a different category is allowed
    resp = await client.post("/api/v1/lists", json={"name": "Favourites", "category": "music"}, headers=auth_headers)
    assert resp.status_code == 201
    second = resp.json()

    # Rename to a duplicate name within the same category -> 409
    resp = await client.post("/api/v1/lists", json={"name": "Other", "category": "books"}, headers=auth_headers)
    assert resp.status_code == 201
    other = resp.json()

    resp = await client.put(f"/api/v1/lists/{other['id']}", json={"name": "Favourites"}, headers=auth_headers)
    assert resp.status_code == 409

    for created in (first, second, other):
        resp = await client.delete(f"/api/v1/lists/{created['id']}", headers=auth_headers)
        assert resp.status_code == 204


async def test_list_update_and_delete_missing_returns_404(client, auth_headers):
    resp = await client.put("/api/v1/lists/999999", json={"name": "Nope"}, headers=auth_headers)
    assert resp.status_code == 404

    resp = await client.delete("/api/v1/lists/999999", headers=auth_headers)
    assert resp.status_code == 404


async def test_can_manage_lists_permission_enforced(client, auth_headers):
    _, headers = await _create_user_and_login(client, auth_headers, "listsuser", can_manage_lists=False)

    # Reading lists is allowed regardless of the permission.
    resp = await client.get("/api/v1/lists", headers=headers)
    assert resp.status_code == 200

    resp = await client.post("/api/v1/lists", json={"name": "Forbidden", "category": "books"}, headers=headers)
    assert resp.status_code == 403

    existing = await client.post("/api/v1/lists", json={"name": "Existing", "category": "books"}, headers=auth_headers)
    list_id = existing.json()["id"]

    resp = await client.put(f"/api/v1/lists/{list_id}", json={"name": "Renamed"}, headers=headers)
    assert resp.status_code == 403

    resp = await client.delete(f"/api/v1/lists/{list_id}", headers=headers)
    assert resp.status_code == 403

    resp = await client.delete(f"/api/v1/lists/{list_id}", headers=auth_headers)
    assert resp.status_code == 204


async def test_create_and_update_item_list_ids_round_trip(client, auth_headers):
    book_id = await _subtype_id(client, auth_headers, "Book")

    resp = await client.post("/api/v1/lists", json={"name": "Want to read", "category": "books"}, headers=auth_headers)
    assert resp.status_code == 201
    want_to_read = resp.json()

    resp = await client.post("/api/v1/lists", json={"name": "Favourites", "category": "books"}, headers=auth_headers)
    assert resp.status_code == 201
    favourites = resp.json()

    # Create with a list membership.
    resp = await client.post(
        "/api/v1/media",
        json={"title": "Dune", "media_subtype_id": book_id, "list_ids": [want_to_read["id"]]},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    item = resp.json()
    assert item["list_ids"] == [want_to_read["id"]]
    item_id = item["id"]

    resp = await client.get(f"/api/v1/media/{item_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["list_ids"] == [want_to_read["id"]]

    # Update to add another list.
    resp = await client.put(
        f"/api/v1/media/{item_id}",
        json={"list_ids": [want_to_read["id"], favourites["id"]]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert sorted(resp.json()["list_ids"]) == sorted([want_to_read["id"], favourites["id"]])

    # Update to remove one.
    resp = await client.put(f"/api/v1/media/{item_id}", json={"list_ids": [favourites["id"]]}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["list_ids"] == [favourites["id"]]

    # Update to clear all lists.
    resp = await client.put(f"/api/v1/media/{item_id}", json={"list_ids": []}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["list_ids"] == []

    # Cleanup
    resp = await client.delete(f"/api/v1/media/{item_id}", headers=auth_headers)
    assert resp.status_code == 204
    for created in (want_to_read, favourites):
        resp = await client.delete(f"/api/v1/lists/{created['id']}", headers=auth_headers)
        assert resp.status_code == 204


async def test_item_list_category_and_existence_validation(client, auth_headers):
    book_id = await _subtype_id(client, auth_headers, "Book")

    resp = await client.post("/api/v1/lists", json={"name": "Favourites", "category": "music"}, headers=auth_headers)
    assert resp.status_code == 201
    music_list = resp.json()

    # Creating a book item with a music list -> 400.
    resp = await client.post(
        "/api/v1/media",
        json={"title": "Mismatched", "media_subtype_id": book_id, "list_ids": [music_list["id"]]},
        headers=auth_headers,
    )
    assert resp.status_code == 400

    # Creating a book item with a non-existent list -> 400.
    resp = await client.post(
        "/api/v1/media",
        json={"title": "Missing List", "media_subtype_id": book_id, "list_ids": [999999]},
        headers=auth_headers,
    )
    assert resp.status_code == 400

    # Create a valid item, then try to update it with a mismatched-category list.
    resp = await client.post(
        "/api/v1/media", json={"title": "Valid Book", "media_subtype_id": book_id}, headers=auth_headers
    )
    assert resp.status_code == 201
    item_id = resp.json()["id"]

    resp = await client.put(
        f"/api/v1/media/{item_id}", json={"list_ids": [music_list["id"]]}, headers=auth_headers
    )
    assert resp.status_code == 400

    resp = await client.put(f"/api/v1/media/{item_id}", json={"list_ids": [999999]}, headers=auth_headers)
    assert resp.status_code == 400

    # Cleanup
    resp = await client.delete(f"/api/v1/media/{item_id}", headers=auth_headers)
    assert resp.status_code == 204
    resp = await client.delete(f"/api/v1/lists/{music_list['id']}", headers=auth_headers)
    assert resp.status_code == 204


async def test_media_list_id_filter_and_list_deletion(client, auth_headers):
    book_id = await _subtype_id(client, auth_headers, "Book")

    resp = await client.post("/api/v1/lists", json={"name": "Want to read", "category": "books"}, headers=auth_headers)
    assert resp.status_code == 201
    want_to_read = resp.json()

    resp = await client.post(
        "/api/v1/media",
        json={"title": "In List", "media_subtype_id": book_id, "list_ids": [want_to_read["id"]]},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    in_list_id = resp.json()["id"]

    resp = await client.post(
        "/api/v1/media", json={"title": "Not In List", "media_subtype_id": book_id}, headers=auth_headers
    )
    assert resp.status_code == 201
    not_in_list_id = resp.json()["id"]

    # item_count reflects current membership.
    resp = await client.get("/api/v1/lists", params={"category": "books"}, headers=auth_headers)
    assert resp.status_code == 200
    counts = {l["id"]: l["item_count"] for l in resp.json()}
    assert counts[want_to_read["id"]] == 1

    # GET /media?list_id=X returns only items in that list.
    resp = await client.get(f"/api/v1/media?list_id={want_to_read['id']}", headers=auth_headers)
    assert resp.status_code == 200
    titles = {i["title"] for i in resp.json()["items"]}
    assert titles == {"In List"}

    # Deleting the list leaves the item intact, with no remaining membership.
    resp = await client.delete(f"/api/v1/lists/{want_to_read['id']}", headers=auth_headers)
    assert resp.status_code == 204

    resp = await client.get("/api/v1/lists", params={"category": "books"}, headers=auth_headers)
    assert resp.status_code == 200
    assert want_to_read["id"] not in {l["id"] for l in resp.json()}

    resp = await client.get(f"/api/v1/media/{in_list_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["list_ids"] == []

    # Cleanup
    for item_id in (in_list_id, not_in_list_id):
        resp = await client.delete(f"/api/v1/media/{item_id}", headers=auth_headers)
        assert resp.status_code == 204
