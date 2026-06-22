"""Tests for app.api.v1.admin — library-wide maintenance operations."""
from unittest.mock import AsyncMock, patch

from app.config import APP_VERSION

from .conftest import _create_user_and_login, _subtype_id
from .test_plex import _PLEX_SECTIONS, _configure_plex


async def test_admin_system_info_returns_version_and_api_status(client, auth_headers, monkeypatch):
    from app.api.v1 import admin as admin_module

    monkeypatch.setattr(admin_module.settings, "tmdb_api_key", "test-key")
    monkeypatch.setattr(admin_module.settings, "igdb_client_id", None)
    monkeypatch.setattr(admin_module.settings, "igdb_client_secret", None)
    monkeypatch.setattr(admin_module.settings, "upcdatabase_api_key", "test-key")
    monkeypatch.setattr(admin_module.settings, "port", "9090")

    resp = await client.get("/api/v1/admin/system-info", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["version"] == APP_VERSION
    assert body["database"] == "SQLite"
    assert body["configured_port"] == "9090"
    assert body["apis"] == {"tmdb": True, "igdb": False, "upcdatabase": True}


async def test_admin_system_info_requires_admin(client, auth_headers):
    _, headers = await _create_user_and_login(client, auth_headers, "sysinfouser")
    resp = await client.get("/api/v1/admin/system-info", headers=headers)
    assert resp.status_code == 403


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


async def test_reset_database_clears_plex_config_and_mappings(client, auth_headers):
    """PlexConfig.platform_id and PlexLibraryMapping.media_subtype_id are
    ON DELETE RESTRICT foreign keys (see those models), so deleting platforms
    and media subtypes out from under a configured Plex integration without
    clearing it first raises a foreign key violation — always enforced on
    Postgres, and also enforced here since SQLite FK checks are on (see
    test_database.py). Reset must clear Plex state before wiping the
    catalogue."""
    await _configure_plex(client, auth_headers)
    with patch("app.services.plex.list_sections", new=AsyncMock(return_value=_PLEX_SECTIONS)):
        resp = await client.post(
            "/api/v1/admin/plex/mappings", json={"section_key": "1"}, headers=auth_headers
        )
    assert resp.status_code == 201, resp.text

    resp = await client.post("/api/v1/admin/reset-database", headers=auth_headers)
    assert resp.status_code == 200, resp.text

    resp = await client.get("/api/v1/admin/plex/config", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["configured"] is False

    resp = await client.get("/api/v1/admin/plex/mappings", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []
