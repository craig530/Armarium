"""Tests for the ownership feature: owner_id on items/lists, appConfig,
user summary endpoint, and owner filter."""
from .conftest import _create_user_and_login, _subtype_id


async def test_app_config_default_is_shared(client, auth_headers):
    resp = await client.get("/api/v1/admin/config", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["ownership_mode"] == "shared"


async def test_app_config_get_accessible_to_non_admin(client, auth_headers):
    _, headers = await _create_user_and_login(client, auth_headers, "configreader")
    resp = await client.get("/api/v1/admin/config", headers=headers)
    assert resp.status_code == 200
    assert "ownership_mode" in resp.json()


async def test_app_config_update_requires_admin(client, auth_headers):
    _, headers = await _create_user_and_login(client, auth_headers, "confignoadmin")
    resp = await client.put(
        "/api/v1/admin/config",
        json={"ownership_mode": "shared"},
        headers=headers,
    )
    assert resp.status_code == 403


async def test_app_config_switch_to_by_login_requires_migration(client, auth_headers):
    resp = await client.put(
        "/api/v1/admin/config",
        json={"ownership_mode": "by_login"},
        headers=auth_headers,
    )
    assert resp.status_code == 400, resp.text
    assert "migrate-ownership" in resp.json()["detail"]


async def test_migrate_ownership_and_switch_mode(client, auth_headers):
    user, _ = await _create_user_and_login(client, auth_headers, "migrationtarget")

    resp = await client.post(
        "/api/v1/admin/config/migrate-ownership",
        json={"target_user_id": user["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["ownership_mode"] == "by_login"

    # Reset back to shared for other tests
    await client.put("/api/v1/admin/config", json={"ownership_mode": "shared"}, headers=auth_headers)


async def test_migrate_ownership_invalid_user(client, auth_headers):
    resp = await client.post(
        "/api/v1/admin/config/migrate-ownership",
        json={"target_user_id": 999999},
        headers=auth_headers,
    )
    assert resp.status_code == 404


async def test_created_item_gets_shared_owner_by_default(client, auth_headers):
    subtype_id = await _subtype_id(client, auth_headers, "CD")
    resp = await client.post(
        "/api/v1/media",
        json={"title": "Ownership Test Album", "media_subtype_id": subtype_id},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    item = resp.json()
    # In "shared" mode the owner is the shared system user
    assert item["owner_username"] == "shared"

    await client.delete(f"/api/v1/media/{item['id']}", headers=auth_headers)


async def test_item_owner_can_be_updated(client, auth_headers):
    user, _ = await _create_user_and_login(client, auth_headers, "itemowner")
    subtype_id = await _subtype_id(client, auth_headers, "Book")

    resp = await client.post(
        "/api/v1/media",
        json={"title": "Owned Book", "media_subtype_id": subtype_id},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    item = resp.json()

    resp = await client.put(
        f"/api/v1/media/{item['id']}",
        json={"owner_id": user["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["owner_id"] == user["id"]
    assert resp.json()["owner_username"] == "itemowner"

    await client.delete(f"/api/v1/media/{item['id']}", headers=auth_headers)


async def test_owner_filter_returns_only_matching_items(client, auth_headers):
    user, _ = await _create_user_and_login(client, auth_headers, "filterowner")
    subtype_id = await _subtype_id(client, auth_headers, "Book")

    resp = await client.post(
        "/api/v1/media",
        json={"title": "Filter Test Book", "media_subtype_id": subtype_id, "owner_id": user["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    item = resp.json()

    resp = await client.get(
        f"/api/v1/media?owner_id={user['id']}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()["items"]]
    assert item["id"] in ids

    await client.delete(f"/api/v1/media/{item['id']}", headers=auth_headers)


async def test_created_list_gets_shared_owner(client, auth_headers):
    resp = await client.post(
        "/api/v1/lists",
        json={"name": "Ownership List Test", "category": "books"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    lst = resp.json()
    assert lst["owner_username"] == "shared"

    await client.delete(f"/api/v1/lists/{lst['id']}", headers=auth_headers)


async def test_plex_rating_key_in_item_response(client, auth_headers):
    subtype_id = await _subtype_id(client, auth_headers, "Film")
    resp = await client.post(
        "/api/v1/media",
        json={"title": "Plex Key Test Film", "media_subtype_id": subtype_id},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    item = resp.json()
    assert "plex_rating_key" in item

    await client.delete(f"/api/v1/media/{item['id']}", headers=auth_headers)


async def test_user_summary_available_to_all_users(client, auth_headers):
    _, headers = await _create_user_and_login(client, auth_headers, "summaryuser")
    resp = await client.get("/api/v1/users/summary", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    usernames = [u["username"] for u in data]
    assert "summaryuser" in usernames
    assert "shared" not in usernames
