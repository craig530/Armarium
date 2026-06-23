"""Tests for the IGDB lookup service and the games lookup endpoints."""
from unittest.mock import patch, AsyncMock

from app.models.enums import MediaCategory
from app.schemas.media import LookupCandidate
from app.services.cache import lookup_cache

from .conftest import _subtype_id


# ── IGDB service unit tests ───────────────────────────────────────────────────

async def test_igdb_search_returns_empty_when_not_configured():
    from app.services import igdb
    with patch("app.services.igdb.settings") as mock_settings:
        mock_settings.igdb_client_id = None
        mock_settings.igdb_client_secret = None
        results = await igdb.search_games("The Legend of Zelda")
    assert results == []


async def test_igdb_search_maps_response_fields():
    from app.services import igdb

    fake_game = {
        "id": 1020,
        "name": "Hollow Knight",
        "first_release_date": 1487289600,  # 2017-02-17
        "cover": {"url": "//images.igdb.com/igdb/image/upload/t_thumb/abc123.jpg"},
        "genres": [{"name": "Platformer"}, {"name": "Metroidvania"}],
        "involved_companies": [
            {"developer": True, "company": {"name": "Team Cherry"}},
        ],
        "summary": "A challenging underground kingdom adventure.",
    }

    with patch("app.services.igdb._igdb_post", new=AsyncMock(return_value=[fake_game])):
        with patch("app.services.igdb.settings") as mock_settings:
            mock_settings.igdb_client_id = "test_id"
            mock_settings.igdb_client_secret = "test_secret"
            results = await igdb.search_games("Hollow Knight")

    assert len(results) == 1
    c = results[0]
    assert c.title == "Hollow Knight"
    assert c.year == 2017
    assert c.creator == "Team Cherry"
    assert c.category == MediaCategory.GAMES
    assert c.source == "igdb"
    assert c.external_id == "1020"
    assert "t_cover_big" in c.cover_url
    assert c.metadata["genres"] == "Platformer, Metroidvania"


async def test_igdb_lookup_by_barcode_uses_upc_then_title_search():
    """Barcode lookup uses UPCitemdb to resolve a title, then searches IGDB
    by that title — IGDB has no barcode database of its own."""
    from app.services import igdb

    fake_game = {
        "id": 999,
        "name": "Indiana Jones and the Great Circle",
        "first_release_date": 1734307200,
        "cover": {"url": "//images.igdb.com/igdb/image/upload/t_thumb/indy.jpg"},
        "genres": [{"name": "Action-Adventure"}],
        "involved_companies": [{"developer": True, "company": {"name": "MachineGames"}}],
        "summary": "An epic adventure.",
    }

    with patch("app.services.upc.lookup_title", new=AsyncMock(return_value="Indiana Jones and the Great Circle - Nintendo Switch 2")), \
            patch("app.services.igdb._igdb_post", new=AsyncMock(return_value=[fake_game])) as mock_post:
        with patch("app.services.igdb.settings") as mock_settings:
            mock_settings.igdb_client_id = "test_id"
            mock_settings.igdb_client_secret = "test_secret"
            results = await igdb.lookup_by_barcode("196388816279")

    assert len(results) == 1
    assert results[0].title == "Indiana Jones and the Great Circle"
    # Platform suffix must be stripped before the IGDB search
    call_body = mock_post.call_args[0][1]
    assert "Nintendo Switch 2" not in call_body
    assert "Indiana Jones" in call_body


async def test_igdb_lookup_by_barcode_returns_empty_when_upc_finds_nothing():
    from app.services import igdb

    with patch("app.services.upc.lookup_title", new=AsyncMock(return_value=None)):
        with patch("app.services.igdb.settings") as mock_settings:
            mock_settings.igdb_client_id = "test_id"
            mock_settings.igdb_client_secret = "test_secret"
            results = await igdb.lookup_by_barcode("045496590475")

    assert results == []


async def test_igdb_get_game_details_returns_none_when_not_found():
    from app.services import igdb

    with patch("app.services.igdb._igdb_post", new=AsyncMock(return_value=None)):
        with patch("app.services.igdb.settings") as mock_settings:
            mock_settings.igdb_client_id = "test_id"
            mock_settings.igdb_client_secret = "test_secret"
            result = await igdb.get_game_details(9999)

    assert result is None


# ── Lookup API endpoint tests ─────────────────────────────────────────────────

async def test_lookup_search_games_returns_503_when_not_configured(client, auth_headers):
    resp = await client.get(
        "/api/v1/lookup/search?q=Zelda&category=games",
        headers=auth_headers,
    )
    assert resp.status_code == 503
    assert "IGDB" in resp.json()["detail"]


async def test_lookup_search_games_returns_results(client, auth_headers):
    lookup_cache.clear()

    fake_candidate = LookupCandidate(
        external_id="1020",
        source="igdb",
        title="Hollow Knight",
        year=2017,
        category=MediaCategory.GAMES,
        creator="Team Cherry",
    )

    with patch("app.services.igdb.search_games", new=AsyncMock(return_value=[fake_candidate])):
        with patch("app.api.v1.lookup.settings") as mock_settings:
            mock_settings.igdb_client_id = "test_id"
            mock_settings.igdb_client_secret = "test_secret"
            resp = await client.get(
                "/api/v1/lookup/search?q=Hollow+Knight&category=games",
                headers=auth_headers,
            )

    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["title"] == "Hollow Knight"


async def test_lookup_barcode_games_category_queries_igdb(client, auth_headers):
    lookup_cache.clear()

    fake_candidate = LookupCandidate(
        external_id="1234",
        source="igdb",
        title="Some Game",
        category=MediaCategory.GAMES,
    )

    with patch("app.services.igdb.lookup_by_barcode", new=AsyncMock(return_value=[fake_candidate])) as mock_igdb, \
            patch("app.services.musicbrainz.lookup_by_barcode", new=AsyncMock(return_value=[])):
        resp = await client.get(
            "/api/v1/lookup/barcode/045496590475?category=games",
            headers=auth_headers,
        )

    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["source"] == "igdb"
    mock_igdb.assert_awaited_once()


async def test_igdb_details_endpoint_returns_404_when_not_found(client, auth_headers):
    with patch("app.services.igdb.get_game_details", new=AsyncMock(return_value=None)):
        with patch("app.api.v1.lookup.settings") as mock_settings:
            mock_settings.igdb_client_id = "test_id"
            mock_settings.igdb_client_secret = "test_secret"
            resp = await client.get("/api/v1/lookup/igdb/9999", headers=auth_headers)

    assert resp.status_code == 404


# ── Game media items CRUD ─────────────────────────────────────────────────────

async def test_create_game_item_with_developer_and_igdb_id(client, auth_headers):
    subtype_id = await _subtype_id(client, auth_headers, "Disc")

    resp = await client.post(
        "/api/v1/media",
        json={
            "title": "Hollow Knight",
            "media_subtype_id": subtype_id,
            "year": 2018,
            "developer": "Team Cherry",
            "igdb_id": 1020,
            "genres": "Metroidvania",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Hollow Knight"
    assert data["developer"] == "Team Cherry"
    assert data["igdb_id"] == 1020
    assert data["category"] == "games"

    # cleanup
    await client.delete(f"/api/v1/media/{data['id']}", headers=auth_headers)


async def test_game_item_appears_in_games_category_list(client, auth_headers):
    subtype_id = await _subtype_id(client, auth_headers, "Disc")

    resp = await client.post(
        "/api/v1/media",
        json={"title": "Metroid Dread", "media_subtype_id": subtype_id, "developer": "Mercury Steam"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    item_id = resp.json()["id"]

    resp = await client.get("/api/v1/media?category=games", headers=auth_headers)
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()["items"]]
    assert item_id in ids

    await client.delete(f"/api/v1/media/{item_id}", headers=auth_headers)


async def test_game_subtypes_seeded_by_migration(client, auth_headers):
    resp = await client.get("/api/v1/media-subtypes", headers=auth_headers)
    assert resp.status_code == 200
    subtypes = resp.json()
    game_subtypes = [s for s in subtypes if s["category"] == "games"]
    names = {s["name"] for s in game_subtypes}
    assert {"Disc", "Cartridge", "Game"}.issubset(names)
