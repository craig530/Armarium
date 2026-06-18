"""Tests for the disabled_categories feature on app_config."""
from .conftest import _create_user_and_login


async def test_disabled_categories_default_empty(client, auth_headers):
    resp = await client.get("/api/v1/admin/config", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["disabled_categories"] == []


async def test_disabled_categories_non_admin_can_read(client, auth_headers):
    _, headers = await _create_user_and_login(client, auth_headers, "catreader")
    resp = await client.get("/api/v1/admin/config", headers=headers)
    assert resp.status_code == 200
    assert "disabled_categories" in resp.json()


async def test_disabled_categories_admin_can_set(client, auth_headers):
    resp = await client.put(
        "/api/v1/admin/config",
        json={"disabled_categories": ["books", "music"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert set(data["disabled_categories"]) == {"books", "music"}

    # Reset
    await client.put("/api/v1/admin/config", json={"disabled_categories": []}, headers=auth_headers)


async def test_disabled_categories_non_admin_cannot_update(client, auth_headers):
    _, headers = await _create_user_and_login(client, auth_headers, "catupdater")
    resp = await client.put(
        "/api/v1/admin/config",
        json={"disabled_categories": ["books"]},
        headers=headers,
    )
    assert resp.status_code == 403


async def test_disabled_categories_invalid_value_rejected(client, auth_headers):
    resp = await client.put(
        "/api/v1/admin/config",
        json={"disabled_categories": ["movies", "podcasts"]},
        headers=auth_headers,
    )
    assert resp.status_code == 422


async def test_disabled_categories_update_preserves_ownership_mode(client, auth_headers):
    initial = await client.get("/api/v1/admin/config", headers=auth_headers)
    initial_mode = initial.json()["ownership_mode"]

    resp = await client.put(
        "/api/v1/admin/config",
        json={"disabled_categories": ["games"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ownership_mode"] == initial_mode
    assert "games" in data["disabled_categories"]

    # Reset
    await client.put("/api/v1/admin/config", json={"disabled_categories": []}, headers=auth_headers)


async def test_ownership_mode_update_preserves_disabled_categories(client, auth_headers):
    # Set some disabled categories first
    await client.put(
        "/api/v1/admin/config",
        json={"disabled_categories": ["music"]},
        headers=auth_headers,
    )

    # Switch ownership_mode — disabled_categories should be unchanged
    resp = await client.put(
        "/api/v1/admin/config",
        json={"ownership_mode": "shared"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert "music" in resp.json()["disabled_categories"]

    # Reset
    await client.put("/api/v1/admin/config", json={"disabled_categories": []}, headers=auth_headers)


async def test_disabled_categories_empty_list_clears(client, auth_headers):
    await client.put(
        "/api/v1/admin/config",
        json={"disabled_categories": ["books"]},
        headers=auth_headers,
    )
    resp = await client.put(
        "/api/v1/admin/config",
        json={"disabled_categories": []},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["disabled_categories"] == []


async def test_disabled_categories_all_valid_values(client, auth_headers):
    resp = await client.put(
        "/api/v1/admin/config",
        json={"disabled_categories": ["music", "films_tv", "books", "games"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert set(resp.json()["disabled_categories"]) == {"music", "films_tv", "books", "games"}

    # Reset
    await client.put("/api/v1/admin/config", json={"disabled_categories": []}, headers=auth_headers)
