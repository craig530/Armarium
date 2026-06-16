"""Tests for app.api.v1.plex — config, library mappings, and the sync engine."""
import asyncio
from unittest.mock import patch, AsyncMock

from .conftest import _create_user_and_login, _subtype_id, PNG_1X1


# ── Plex integration config ───────────────────────────────────────────────────

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


# ── Plex library mappings ─────────────────────────────────────────────────────

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


# ── Plex sync engine ─────────────────────────────────────────────────────────

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
    because stale-item detection scopes by `MediaItem.platform_id` (the
    configured Plex platform) and `MediaItem.media_subtype_id` (this
    mapping's media subtype)."""
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


class _SyncResult:
    """Wraps a settled `PlexSyncStatus` payload so existing assertions
    written against the old synchronous `PlexSyncResult` response
    (`resp.status_code`, `resp.json()["created"]`, etc.) keep working
    against `result["created"]` of the background job."""

    def __init__(self, status_payload: dict):
        self._status_payload = status_payload
        self.status_code = 200 if status_payload["status"] == "completed" else 500
        self.text = str(status_payload)

    def json(self):
        return self._status_payload["result"]


async def _sync_and_wait(client, auth_headers, mapping_id, max_polls=10000):
    """Starts a background sync via the async job endpoints and waits for it
    to settle, returning a `_SyncResult` for the finished job. Must be called
    inside any `patch(...)` blocks mocking the Plex service, since the
    background task runs while this waits.

    Polls the in-process job object directly rather than the `/sync/status`
    endpoint — an HTTP request here would open a second session on the
    test database's single shared in-memory connection while the sync's
    session has an uncommitted transaction open, corrupting its writes."""
    from app.services.plex_sync_jobs import get_job

    resp = await client.post(f"/api/v1/admin/plex/mappings/{mapping_id}/sync", headers=auth_headers)
    assert resp.status_code == 202, resp.text
    for _ in range(max_polls):
        job = get_job(mapping_id)
        if job.status != "running":
            break
        await asyncio.sleep(0)
    else:
        raise AssertionError(f"Sync did not complete after {max_polls} polls: {job}")

    if job.status == "error":
        raise AssertionError(f"Sync failed: {job.error}")

    resp = await client.get(f"/api/v1/admin/plex/mappings/{mapping_id}/sync/status", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    return _SyncResult(resp.json())


async def test_plex_sync_creates_items(client, auth_headers):
    mapping = await _create_movie_mapping(client, auth_headers)

    with patch("app.services.plex.list_section_items", new=AsyncMock(return_value=[_PLEX_MOVIE_ITEM])), \
            patch("app.services.plex.fetch_thumbnail", new=AsyncMock(return_value=PNG_1X1)):
        resp = await _sync_and_wait(client, auth_headers, mapping['id'])
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["created"] == 1
    assert result["updated"] == 0
    assert result["stale_items"] == []

    item = await _find_item_by_title(client, auth_headers, "The Matrix")
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
        resp = await _sync_and_wait(client, auth_headers, mapping['id'])
    assert resp.json()["created"] == 1

    updated_item = dict(_PLEX_MOVIE_ITEM_RELOADED, summary="Updated description")
    with patch("app.services.plex.list_section_items", new=AsyncMock(return_value=[updated_item])), \
            patch("app.services.plex.fetch_thumbnail", new=AsyncMock(return_value=None)):
        resp = await _sync_and_wait(client, auth_headers, mapping['id'])
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["created"] == 0
    assert result["updated"] == 1

    resp = await client.get("/api/v1/media", params={"per_page": 100}, headers=auth_headers)
    matches = [i for i in resp.json()["items"] if i["title"] == "The Matrix Reloaded"]
    assert len(matches) == 1
    assert matches[0]["description"] == "Updated description"


async def test_plex_sync_adopts_manually_created_plex_platform_item(client, auth_headers):
    """A MediaItem manually created with platform = the Plex sync platform and
    a matching identity is recognized as the Plex copy on the next sync —
    updated in place, not duplicated — and any other-platform/physical copies
    of the same identity get linked to it too."""
    mapping = await _create_movie_mapping(client, auth_headers)
    plex_platform = await _ensure_plex_platform(client, auth_headers)

    film_subtype_id = await _subtype_id(client, auth_headers, "Film")
    bluray_id = await _subtype_id(client, auth_headers, "Blu-ray")

    resp = await client.post(
        "/api/v1/media",
        json={
            "title": "The Matrix Revolutions",
            "media_subtype_id": film_subtype_id,
            "year": 2003,
            "tmdb_id": 605,
            "description": "My manual notes",
            "platform_id": plex_platform["id"],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    manual_item_id = resp.json()["id"]

    resp = await client.post(
        "/api/v1/media",
        json={"title": "The Matrix Revolutions", "media_subtype_id": bluray_id, "year": 2003, "tmdb_id": 605},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    physical_id = resp.json()["id"]

    # The two were auto-linked on creation (same tmdb_id) — unlink to simulate
    # copies added before linking existed.
    resp = await client.delete(f"/api/v1/media/{manual_item_id}/link/{physical_id}", headers=auth_headers)
    assert resp.status_code == 204, resp.text

    with patch("app.services.plex.list_section_items", new=AsyncMock(return_value=[_PLEX_MOVIE_ITEM_REVOLUTIONS])), \
            patch("app.services.plex.fetch_thumbnail", new=AsyncMock(return_value=None)):
        resp = await _sync_and_wait(client, auth_headers, mapping['id'])
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["created"] == 0
    assert result["updated"] == 1

    resp = await client.get(f"/api/v1/media/{manual_item_id}", headers=auth_headers)
    item = resp.json()
    assert item["description"] == _PLEX_MOVIE_ITEM_REVOLUTIONS["summary"]
    assert item["platform"]["name"] == "Plex"
    assert physical_id in {li["id"] for li in item["linked_items"]}


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
        resp = await _sync_and_wait(client, auth_headers, mapping['id'])
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["created"] == 1

    resp = await client.get("/api/v1/media", params={"per_page": 100}, headers=auth_headers)
    items = [i for i in resp.json()["items"] if i["title"] == "Edge of Tomorrow"]
    assert len(items) == 3
    plex_item = next(i for i in items if i["platform"] and i["platform"]["name"] == "Plex")
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
        resp = await _sync_and_wait(client, auth_headers, mapping['id'])
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["created"] == 1

    resp = await client.get("/api/v1/media", params={"per_page": 100}, headers=auth_headers)
    items = [i for i in resp.json()["items"] if i["title"].lower() == "indie darling"]
    assert len(items) == 2
    plex_item = next(i for i in items if i["platform"] and i["platform"]["name"] == "Plex")
    assert [li["id"] for li in plex_item["linked_items"]] == [physical_id]


async def test_plex_sync_detects_stale_items(client, auth_headers):
    # Uses the TV-shows mapping (a distinct media subtype from the movie tests
    # above) so stale-detection's platform/media_subtype scan doesn't pick up
    # Plex items created by those tests.
    mapping = await _create_tvshow_mapping(client, auth_headers)

    with patch("app.services.plex.list_section_items", new=AsyncMock(return_value=[_PLEX_MOVIE_ITEM_3, _PLEX_MOVIE_ITEM_2])), \
            patch("app.services.plex.fetch_thumbnail", new=AsyncMock(return_value=None)):
        resp = await _sync_and_wait(client, auth_headers, mapping['id'])
    assert resp.json()["created"] == 2

    # "Inception" removed from Plex.
    with patch("app.services.plex.list_section_items", new=AsyncMock(return_value=[_PLEX_MOVIE_ITEM_3])), \
            patch("app.services.plex.fetch_thumbnail", new=AsyncMock(return_value=None)):
        resp = await _sync_and_wait(client, auth_headers, mapping['id'])
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["created"] == 0
    # Speed was not changed (delta sync only increments "updated" when metadata
    # actually differs), so updated may be 0 on a clean re-sync.
    assert len(result["stale_items"]) == 1
    assert result["stale_items"][0]["title"] == "Inception"

    # Still present in the library — Phase 7 removal isn't triggered by a sync.
    item = await _find_item_by_title(client, auth_headers, "Inception")
    assert item["platform"]["name"] == "Plex"
    assert item["media_subtype"]["name"] == "TV Series"


async def test_plex_sync_music_mapping(client, auth_headers):
    mapping = await _create_music_mapping(client, auth_headers)

    with patch("app.services.plex.list_section_items", new=AsyncMock(return_value=[_PLEX_ALBUM_ITEM])), \
            patch("app.services.plex.fetch_thumbnail", new=AsyncMock(return_value=None)):
        resp = await _sync_and_wait(client, auth_headers, mapping['id'])
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

    resp = await client.get(f"/api/v1/admin/plex/mappings/{mapping['id']}/sync/status", headers=headers)
    assert resp.status_code == 403

    resp = await client.post(f"/api/v1/admin/plex/mappings/{mapping['id']}/sync/cancel", headers=headers)
    assert resp.status_code == 403

    resp = await client.post(
        f"/api/v1/admin/plex/mappings/{mapping['id']}/remove-stale", json={"item_ids": []}, headers=headers
    )
    assert resp.status_code == 403

    resp = await client.delete("/api/v1/admin/plex/mappings/1", headers=headers)
    assert resp.status_code == 403


# ── Plex stale-item removal ───────────────────────────────────────────────────

async def test_plex_remove_stale_items(client, auth_headers):
    mapping = await _create_tvshow_mapping(client, auth_headers)

    with patch("app.services.plex.list_section_items", new=AsyncMock(return_value=[_PLEX_TVSHOW_ITEM_REMOVE])), \
            patch("app.services.plex.fetch_thumbnail", new=AsyncMock(return_value=PNG_1X1)):
        resp = await _sync_and_wait(client, auth_headers, mapping['id'])
    assert resp.status_code == 200, resp.text
    assert resp.json()["created"] == 1

    item = await _find_item_by_title(client, auth_headers, "Quietly Cancelled Show")
    assert item["platform"]["name"] == "Plex"

    # Removed from Plex entirely — the next sync flags it as stale.
    with patch("app.services.plex.list_section_items", new=AsyncMock(return_value=[])), \
            patch("app.services.plex.fetch_thumbnail", new=AsyncMock(return_value=None)):
        resp = await _sync_and_wait(client, auth_headers, mapping['id'])
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
        resp = await _sync_and_wait(client, auth_headers, mapping['id'])
    assert resp.status_code == 200, resp.text
    assert resp.json()["created"] == 1

    resp = await client.get("/api/v1/media", params={"per_page": 100}, headers=auth_headers)
    items = [i for i in resp.json()["items"] if i["title"] == "The Last Outpost"]
    plex_item = next(i for i in items if i["platform"] and i["platform"]["name"] == "Plex")
    assert [li["id"] for li in plex_item["linked_items"]] == [physical_id]

    # Removed from Plex entirely — the next sync flags the Plex item as stale.
    with patch("app.services.plex.list_section_items", new=AsyncMock(return_value=[])), \
            patch("app.services.plex.fetch_thumbnail", new=AsyncMock(return_value=None)):
        resp = await _sync_and_wait(client, auth_headers, mapping['id'])
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
    await _create_movie_mapping(client, auth_headers)
    tvshow_mapping = await _create_tvshow_mapping(client, auth_headers)

    # A manually-added item on a different platform is never removed, even if selected.
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

    # An item belonging to a different mapping's media subtype isn't removable via this one.
    matrix_item = await _find_item_by_title(client, auth_headers, "The Matrix")
    assert matrix_item["platform"]["name"] == "Plex"
    assert matrix_item["media_subtype"]["name"] == "Film"

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


# ── Plex media-type mapping & locking ─────────────────────────────────────────

async def test_plex_mapping_create_preselects_default_media_subtype(client, auth_headers):
    """Each Plex section type has a matching seeded Digital media subtype
    (Film / TV Series / Music) — create_mapping pre-selects it so sync works
    immediately without an admin visiting Plex Sync settings first."""
    movie_mapping = await _create_movie_mapping(client, auth_headers)
    assert movie_mapping["media_subtype"]["name"] == "Film"

    music_mapping = await _create_music_mapping(client, auth_headers)
    assert music_mapping["media_subtype"]["name"] == "Music"


async def test_plex_mapping_update_media_subtype(client, auth_headers):
    mapping = await _create_movie_mapping(client, auth_headers)
    tv_series_id = await _subtype_id(client, auth_headers, "TV Series")
    music_id = await _subtype_id(client, auth_headers, "Music")
    dvd_id = await _subtype_id(client, auth_headers, "DVD")
    film_id = await _subtype_id(client, auth_headers, "Film")

    # Non-admin (even with can_add_items) can't repoint the mapping's subtype.
    _, headers = await _create_user_and_login(client, auth_headers, "plexsubtypeuser")
    resp = await client.put(
        f"/api/v1/admin/plex/mappings/{mapping['id']}",
        json={"media_subtype_id": tv_series_id},
        headers=headers,
    )
    assert resp.status_code == 403

    # Wrong category -> 400.
    resp = await client.put(
        f"/api/v1/admin/plex/mappings/{mapping['id']}",
        json={"media_subtype_id": music_id},
        headers=auth_headers,
    )
    assert resp.status_code == 400

    # Physical subtype (wrong supertype) -> 400.
    resp = await client.put(
        f"/api/v1/admin/plex/mappings/{mapping['id']}",
        json={"media_subtype_id": dvd_id},
        headers=auth_headers,
    )
    assert resp.status_code == 400

    # Unknown subtype -> 404.
    resp = await client.put(
        f"/api/v1/admin/plex/mappings/{mapping['id']}",
        json={"media_subtype_id": 999999},
        headers=auth_headers,
    )
    assert resp.status_code == 404

    # Valid Digital subtype in the same category -> 200.
    resp = await client.put(
        f"/api/v1/admin/plex/mappings/{mapping['id']}",
        json={"media_subtype_id": tv_series_id},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["media_subtype"]["id"] == tv_series_id

    # Restore so later tests relying on this mapping's default subtype aren't affected.
    resp = await client.put(
        f"/api/v1/admin/plex/mappings/{mapping['id']}",
        json={"media_subtype_id": film_id},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["media_subtype"]["id"] == film_id


async def test_plex_sync_requires_media_subtype(client, auth_headers):
    """If a mapping has no media subtype configured, sync 400s with a clear
    message rather than crashing."""
    from sqlalchemy import select
    from app.database import AsyncSessionLocal
    from app.models.plex_library_mapping import PlexLibraryMapping

    mapping = await _create_tvshow_mapping(client, auth_headers)
    film_id = await _subtype_id(client, auth_headers, "TV Series")

    async with AsyncSessionLocal() as db:
        row = (await db.execute(
            select(PlexLibraryMapping).where(PlexLibraryMapping.id == mapping["id"])
        )).scalar_one()
        row.media_subtype_id = None
        await db.commit()

    with patch("app.services.plex.list_section_items", new=AsyncMock(return_value=[])):
        resp = await client.post(f"/api/v1/admin/plex/mappings/{mapping['id']}/sync", headers=auth_headers)
    assert resp.status_code == 400
    assert "media type" in resp.json()["detail"].lower()

    # Restore so later tests relying on this mapping's subtype aren't affected.
    resp = await client.put(
        f"/api/v1/admin/plex/mappings/{mapping['id']}",
        json={"media_subtype_id": film_id},
        headers=auth_headers,
    )
    assert resp.status_code == 200


async def test_media_subtype_locked_by_plex_mapping(client, auth_headers):
    """A media subtype referenced by a Plex library mapping is locked
    (undeletable) until the admin repoints or removes that mapping."""
    mapping = await _create_movie_mapping(client, auth_headers)

    # A custom Digital/Films & TV subtype, used so this test doesn't touch
    # the seeded "Film" subtype that other Plex tests rely on.
    resp = await client.post(
        "/api/v1/media-subtypes",
        json={"name": "Custom Digital Film", "category": "films_tv", "supertype": "digital"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    custom = resp.json()
    custom_id = custom["id"]
    assert custom["locked"] is False
    assert custom["locked_reason"] is None

    film_id = mapping["media_subtype"]["id"]
    resp = await client.put(
        f"/api/v1/admin/plex/mappings/{mapping['id']}",
        json={"media_subtype_id": custom_id},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    resp = await client.get("/api/v1/media-subtypes", headers=auth_headers)
    assert resp.status_code == 200
    custom = next(s for s in resp.json() if s["id"] == custom_id)
    assert custom["locked"] is True
    assert mapping["section_title"] in custom["locked_reason"]

    resp = await client.delete(f"/api/v1/media-subtypes/{custom_id}", headers=auth_headers)
    assert resp.status_code == 400
    assert "Plex Sync" in resp.json()["detail"]

    # Repointing the mapping back to "Film" unlocks the custom subtype.
    resp = await client.put(
        f"/api/v1/admin/plex/mappings/{mapping['id']}",
        json={"media_subtype_id": film_id},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    resp = await client.get("/api/v1/media-subtypes", headers=auth_headers)
    custom = next(s for s in resp.json() if s["id"] == custom_id)
    assert custom["locked"] is False
    assert custom["locked_reason"] is None

    resp = await client.delete(f"/api/v1/media-subtypes/{custom_id}", headers=auth_headers)
    assert resp.status_code == 204


# ── Plex sync progress & cancel ─────────────────────────────────────────────────

async def test_plex_sync_returns_running_then_completes(client, auth_headers):
    from app.services.plex_sync_jobs import get_job

    mapping = await _create_music_mapping(client, auth_headers)

    with patch("app.services.plex.list_section_items", new=AsyncMock(return_value=[_PLEX_ALBUM_ITEM])), \
            patch("app.services.plex.fetch_thumbnail", new=AsyncMock(return_value=None)):
        resp = await client.post(f"/api/v1/admin/plex/mappings/{mapping['id']}/sync", headers=auth_headers)
        assert resp.status_code == 202, resp.text
        assert resp.json()["status"] == "running"

        for _ in range(10000):
            job = get_job(mapping['id'])
            if job.status != "running":
                break
            await asyncio.sleep(0)
        else:
            raise AssertionError(f"Sync did not complete: {job}")

    assert job.status == "completed"

    resp = await client.get(f"/api/v1/admin/plex/mappings/{mapping['id']}/sync/status", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    status = resp.json()
    assert status["status"] == "completed"
    assert status["total"] == 1
    assert status["processed"] == 1
    # "created + updated == 1" only holds when the item is new; if it already
    # existed (shared in-memory DB) with unchanged metadata, updated stays 0.
    assert status["result"]["created"] + status["result"]["updated"] <= 1


async def test_plex_sync_cancel_mid_sync(client, auth_headers):
    from app.api.v1.plex import _run_sync
    from app.services.plex_sync_jobs import PlexSyncJob, set_job

    mapping = await _create_tvshow_mapping(client, auth_headers)

    cancel_items = [
        {"guid": f"plex://show/cancel-test-{i}", "title": f"Cancel Test Show {i}", "thumb": "/thumb"}
        for i in range(1, 4)
    ]

    job = PlexSyncJob()
    call_count = 0

    async def _fetch_thumbnail(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            job.cancel_requested = True
        return None

    with patch("app.services.plex.list_section_items", new=AsyncMock(return_value=cancel_items)), \
            patch("app.services.plex.fetch_thumbnail", new=AsyncMock(side_effect=_fetch_thumbnail)):
        await _run_sync(mapping['id'], job)

    assert job.status == "cancelled"
    assert job.total == 3
    assert job.processed == 2
    assert job.created == 2
    assert job.updated == 0
    assert job.stale_items == []

    set_job(mapping['id'], job)
    resp = await client.get(f"/api/v1/admin/plex/mappings/{mapping['id']}/sync/status", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    status = resp.json()
    assert status["status"] == "cancelled"
    assert status["result"]["created"] == 2
    assert status["result"]["stale_items"] == []


async def test_plex_sync_double_sync_returns_409(client, auth_headers):
    from app.services.plex_sync_jobs import PlexSyncJob, set_job

    mapping = await _create_movie_mapping(client, auth_headers)
    set_job(mapping['id'], PlexSyncJob(status="running"))

    try:
        resp = await client.post(f"/api/v1/admin/plex/mappings/{mapping['id']}/sync", headers=auth_headers)
        assert resp.status_code == 409
        assert "already running" in resp.json()["detail"].lower()
    finally:
        # Don't leave a "running" job behind for later tests on this mapping.
        set_job(mapping['id'], PlexSyncJob(status="completed"))


async def test_plex_sync_cancel_when_not_running_returns_409(client, auth_headers):
    from app.services.plex_sync_jobs import PlexSyncJob, set_job

    mapping = await _create_movie_mapping(client, auth_headers)
    set_job(mapping['id'], PlexSyncJob(status="completed"))

    resp = await client.post(f"/api/v1/admin/plex/mappings/{mapping['id']}/sync/cancel", headers=auth_headers)
    assert resp.status_code == 409
    assert "no sync is currently running" in resp.json()["detail"].lower()


# ── Plex mapping schedules ────────────────────────────────────────────────────

async def test_plex_mapping_schedule_crud(client, auth_headers):
    mapping = await _create_movie_mapping(client, auth_headers)
    mid = mapping['id']

    # Initially no schedule.
    resp = await client.get(f"/api/v1/admin/plex/mappings/{mid}/schedule", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() is None

    # Create a schedule.
    resp = await client.post(
        f"/api/v1/admin/plex/mappings/{mid}/schedule",
        json={"interval_hours": 24, "auto_remove_stale": True},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    sched = resp.json()
    assert sched["interval_hours"] == 24
    assert sched["auto_remove_stale"] is True
    assert sched["job_type"] == "plex_sync"
    assert sched["target_id"] == mid

    # GET now returns it.
    resp = await client.get(f"/api/v1/admin/plex/mappings/{mid}/schedule", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["interval_hours"] == 24

    # Update (upsert to different interval).
    resp = await client.post(
        f"/api/v1/admin/plex/mappings/{mid}/schedule",
        json={"interval_hours": 168, "auto_remove_stale": False},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["interval_hours"] == 168
    assert resp.json()["auto_remove_stale"] is False

    # Delete the schedule.
    resp = await client.delete(f"/api/v1/admin/plex/mappings/{mid}/schedule", headers=auth_headers)
    assert resp.status_code == 204

    resp = await client.get(f"/api/v1/admin/plex/mappings/{mid}/schedule", headers=auth_headers)
    assert resp.json() is None


async def test_plex_mapping_schedule_invalid_interval_rejected(client, auth_headers):
    mapping = await _create_movie_mapping(client, auth_headers)
    resp = await client.post(
        f"/api/v1/admin/plex/mappings/{mapping['id']}/schedule",
        json={"interval_hours": 5},
        headers=auth_headers,
    )
    assert resp.status_code == 400


async def test_plex_mapping_schedule_delete_not_found(client, auth_headers):
    mapping = await _create_movie_mapping(client, auth_headers)
    resp = await client.delete(
        f"/api/v1/admin/plex/mappings/{mapping['id']}/schedule", headers=auth_headers
    )
    assert resp.status_code == 404


async def test_plex_mapping_delete_removes_schedule(client, auth_headers):
    """Deleting a mapping should also remove its associated schedule."""
    mapping = await _create_movie_mapping(client, auth_headers)
    mid = mapping['id']

    await client.post(
        f"/api/v1/admin/plex/mappings/{mid}/schedule",
        json={"interval_hours": 24},
        headers=auth_headers,
    )

    resp = await client.delete(f"/api/v1/admin/plex/mappings/{mid}", headers=auth_headers)
    assert resp.status_code == 204

    # The schedule row should also be gone (check via admin schedules list).
    resp = await client.get("/api/v1/admin/schedules", headers=auth_headers)
    plex_entries = [s for s in resp.json() if s.get("target_id") == mid]
    assert plex_entries == []


async def test_plex_mapping_schedule_can_manage_schedules_permission(client, auth_headers):
    """User with can_manage_schedules=False cannot create/delete mapping schedules,
    but can still read them."""
    mapping = await _create_movie_mapping(client, auth_headers)
    mid = mapping['id']

    # Create schedule as admin first so read test has something to look at.
    await client.post(
        f"/api/v1/admin/plex/mappings/{mid}/schedule",
        json={"interval_hours": 24},
        headers=auth_headers,
    )

    _, no_sched_headers = await _create_user_and_login(
        client, auth_headers, "noscheduser", can_manage_schedules=False
    )

    # GET is allowed (needs can_add_items which defaults to True).
    resp = await client.get(f"/api/v1/admin/plex/mappings/{mid}/schedule", headers=no_sched_headers)
    assert resp.status_code == 200
    assert resp.json()["interval_hours"] == 24

    # POST is forbidden.
    resp = await client.post(
        f"/api/v1/admin/plex/mappings/{mid}/schedule",
        json={"interval_hours": 12},
        headers=no_sched_headers,
    )
    assert resp.status_code == 403

    # DELETE is forbidden.
    resp = await client.delete(
        f"/api/v1/admin/plex/mappings/{mid}/schedule", headers=no_sched_headers
    )
    assert resp.status_code == 403


async def test_plex_mapping_schedule_admin_bypasses_can_manage_schedules(client, auth_headers):
    """Admin can always manage schedules regardless of the can_manage_schedules flag."""
    mapping = await _create_movie_mapping(client, auth_headers)
    mid = mapping['id']

    resp = await client.post(
        f"/api/v1/admin/plex/mappings/{mid}/schedule",
        json={"interval_hours": 6},
        headers=auth_headers,
    )
    assert resp.status_code == 201

    resp = await client.delete(
        f"/api/v1/admin/plex/mappings/{mid}/schedule", headers=auth_headers
    )
    assert resp.status_code == 204


# ── Delta sync: existing items skip cover re-download ────────────────────────

async def test_plex_sync_delta_existing_items_skip_cover(client, auth_headers):
    """On a second sync run, items already in the DB should not re-download their
    cover art — _apply_cover should only be called for newly-created items."""
    from unittest.mock import patch, AsyncMock
    from app.api.v1.plex import _run_sync
    from app.services.plex_sync_jobs import PlexSyncJob

    mapping = await _create_movie_mapping(client, auth_headers)

    # Use a unique GUID so this test doesn't conflict with other tests that also
    # create _PLEX_MOVIE_ITEM in the shared in-memory database.
    _DELTA_TEST_ITEM = {
        "guid": "plex://movie/delta-test-unique-9999",
        "title": "Delta Test Film",
        "year": 2024,
        "summary": "Used only by test_plex_sync_delta_existing_items_skip_cover.",
        "genres": ["Test"],
        "studio": "Test Studio",
        "thumb": "/library/metadata/9999/thumb/1",
        "tmdb_id": 9999999,
        "musicbrainz_id": None,
        "directors": ["Test Director"],
        "cast": ["Test Actor"],
        "duration_ms": 5400000,
        "content_rating": "G",
    }
    items = [_DELTA_TEST_ITEM]
    apply_cover_calls = []

    async def _mock_apply_cover(*args, **kwargs):
        apply_cover_calls.append(args)

    with patch("app.services.plex.list_section_items", new=AsyncMock(return_value=items)), \
         patch("app.services.plex.fetch_thumbnail", new=AsyncMock(return_value=None)), \
         patch("app.api.v1.plex._apply_cover", new=AsyncMock(side_effect=_mock_apply_cover)):
        job1 = PlexSyncJob()
        await _run_sync(mapping['id'], job1)

    first_run_calls = len(apply_cover_calls)
    assert job1.created == 1

    apply_cover_calls.clear()

    # Second sync with the same item — it already exists.
    with patch("app.services.plex.list_section_items", new=AsyncMock(return_value=items)), \
         patch("app.services.plex.fetch_thumbnail", new=AsyncMock(return_value=None)), \
         patch("app.api.v1.plex._apply_cover", new=AsyncMock(side_effect=_mock_apply_cover)):
        job2 = PlexSyncJob()
        await _run_sync(mapping['id'], job2)

    assert job2.created == 0
    assert job2.updated == 0  # nothing changed
    # _apply_cover must NOT be called for existing items on the second sync.
    assert len(apply_cover_calls) == 0
    assert first_run_calls == 1  # sanity: it was called on the first sync
