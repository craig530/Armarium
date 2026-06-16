"""Tests for app.api.v1.media — CRUD, ownership validation, cover handling,
filters/search, linking, and stats."""
from .conftest import _subtype_id, PNG_1X1, SVG_PAYLOAD


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


# ── Cover image handling ──────────────────────────────────────────────────────

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


async def test_auto_link_falls_back_to_title_and_year_match(client, auth_headers):
    cd_subtype_id = await _subtype_id(client, auth_headers, "CD")
    music_digital_subtype_id = await _subtype_id(client, auth_headers, "Music")

    # Simulates a Plex-synced digital item, which has no musicbrainz_id.
    digital_resp = await client.post(
        "/api/v1/media",
        json={
            "title": "Number Ones", "media_subtype_id": music_digital_subtype_id,
            "artist": "Michael Jackson", "year": 2003,
        },
        headers=auth_headers,
    )
    assert digital_resp.status_code == 201
    digital_id = digital_resp.json()["id"]
    assert digital_resp.json()["ownership"] == "digital"
    assert digital_resp.json()["linked_items"] == []

    # A scanned CD with a populated musicbrainz_id (which doesn't match the
    # digital item's NULL musicbrainz_id) but the same title and year — the
    # title/year fallback should still link them.
    cd_resp = await client.post(
        "/api/v1/media",
        json={
            "title": "Number Ones", "media_subtype_id": cd_subtype_id,
            "artist": "Michael Jackson", "year": 2003,
            "musicbrainz_id": "11111111-1111-1111-1111-111111111111",
        },
        headers=auth_headers,
    )
    assert cd_resp.status_code == 201
    cd_item_id = cd_resp.json()["id"]
    assert cd_resp.json()["ownership"] == "both"
    assert [li["id"] for li in cd_resp.json()["linked_items"]] == [digital_id]

    resp = await client.get(f"/api/v1/media/{digital_id}", headers=auth_headers)
    assert resp.json()["ownership"] == "both"
    assert [li["id"] for li in resp.json()["linked_items"]] == [cd_item_id]

    # Cleanup
    resp = await client.delete(f"/api/v1/media/{cd_item_id}", headers=auth_headers)
    assert resp.status_code == 204
    resp = await client.delete(f"/api/v1/media/{digital_id}", headers=auth_headers)
    assert resp.status_code == 204


async def test_auto_link_title_year_fallback_skips_edition_mismatch(client, auth_headers):
    cd_subtype_id = await _subtype_id(client, auth_headers, "CD")
    music_digital_subtype_id = await _subtype_id(client, auth_headers, "Music")

    digital_resp = await client.post(
        "/api/v1/media",
        json={
            "title": "Number Ones", "media_subtype_id": music_digital_subtype_id,
            "artist": "Michael Jackson", "year": 2003, "edition": "Remastered",
        },
        headers=auth_headers,
    )
    assert digital_resp.status_code == 201
    digital_id = digital_resp.json()["id"]

    # Same title/year, but an explicitly different edition — the title/year
    # fallback must not link these.
    cd_resp = await client.post(
        "/api/v1/media",
        json={
            "title": "Number Ones", "media_subtype_id": cd_subtype_id,
            "artist": "Michael Jackson", "year": 2003,
            "edition": "Anniversary Edition",
            "musicbrainz_id": "22222222-2222-2222-2222-222222222222",
        },
        headers=auth_headers,
    )
    assert cd_resp.status_code == 201
    cd_item_id = cd_resp.json()["id"]
    assert cd_resp.json()["ownership"] == "physical"
    assert cd_resp.json()["linked_items"] == []

    resp = await client.get(f"/api/v1/media/{digital_id}", headers=auth_headers)
    assert resp.json()["ownership"] == "digital"
    assert resp.json()["linked_items"] == []

    # Cleanup
    resp = await client.delete(f"/api/v1/media/{cd_item_id}", headers=auth_headers)
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


# ── Stats ────────────────────────────────────────────────────────────────────

async def test_stats(client, auth_headers):
    resp = await client.get("/api/v1/media/stats", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "total" in body
    assert "by_category" in body
    assert "by_supertype" in body
    assert "by_subtype" in body


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


# ── Facets endpoint ───────────────────────────────────────────────────────────

async def test_facets_returns_empty_when_no_items(client, auth_headers):
    resp = await client.get("/api/v1/media/facets", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["location_ids"] == []
    assert body["platform_ids"] == []


async def test_facets_reflects_items_in_library(client, auth_headers):
    # Use a digital subtype — physical items cannot have a platform_id.
    music_digital_id = await _subtype_id(client, auth_headers, "Music")

    resp = await client.post("/api/v1/platforms", json={"name": "Facet Platform"}, headers=auth_headers)
    plat_id = resp.json()["id"]

    resp = await client.post(
        "/api/v1/media",
        json={"title": "Facet Track", "media_subtype_id": music_digital_id, "platform_id": plat_id},
        headers=auth_headers,
    )
    item_id = resp.json()["id"]

    resp = await client.get("/api/v1/media/facets?category=music", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert plat_id in body["platform_ids"]

    await client.delete(f"/api/v1/media/{item_id}", headers=auth_headers)
    await client.delete(f"/api/v1/platforms/{plat_id}", headers=auth_headers)


async def test_facets_category_filter_scopes_results(client, auth_headers):
    """Facets for category=books should not include platform_ids from music items."""
    music_digital_id = await _subtype_id(client, auth_headers, "Music")
    book_id = await _subtype_id(client, auth_headers, "Book")

    resp = await client.post("/api/v1/platforms", json={"name": "Music Only Platform"}, headers=auth_headers)
    plat_id = resp.json()["id"]

    resp = await client.post(
        "/api/v1/media",
        json={"title": "Category Scoped Track", "media_subtype_id": music_digital_id, "platform_id": plat_id},
        headers=auth_headers,
    )
    music_id = resp.json()["id"]

    resp = await client.post(
        "/api/v1/media",
        json={"title": "Category Scoped Book", "media_subtype_id": book_id},
        headers=auth_headers,
    )
    book_item_id = resp.json()["id"]

    # facets scoped to books should not include the music-only platform
    resp = await client.get("/api/v1/media/facets?category=books", headers=auth_headers)
    assert resp.status_code == 200
    assert plat_id not in resp.json()["platform_ids"]

    await client.delete(f"/api/v1/media/{music_id}", headers=auth_headers)
    await client.delete(f"/api/v1/media/{book_item_id}", headers=auth_headers)
    await client.delete(f"/api/v1/platforms/{plat_id}", headers=auth_headers)


async def test_facets_requires_auth(client):
    resp = await client.get("/api/v1/media/facets")
    assert resp.status_code == 401


# ── Rating filter ────────────────────────────────────────────────────────────

async def test_min_rating_filter(client, auth_headers):
    cd_id = await _subtype_id(client, auth_headers, "CD")

    rated5 = (await client.post("/api/v1/media", json={"title": "Five Stars", "media_subtype_id": cd_id, "user_rating": 5}, headers=auth_headers)).json()["id"]
    rated3 = (await client.post("/api/v1/media", json={"title": "Three Stars", "media_subtype_id": cd_id, "user_rating": 3}, headers=auth_headers)).json()["id"]
    unrated = (await client.post("/api/v1/media", json={"title": "No Rating", "media_subtype_id": cd_id}, headers=auth_headers)).json()["id"]

    # unrated filter
    resp = await client.get("/api/v1/media?min_rating=unrated", headers=auth_headers)
    ids = [i["id"] for i in resp.json()["items"]]
    assert unrated in ids
    assert rated5 not in ids
    assert rated3 not in ids

    # 4 star or more
    resp = await client.get("/api/v1/media?min_rating=4", headers=auth_headers)
    ids = [i["id"] for i in resp.json()["items"]]
    assert rated5 in ids
    assert rated3 not in ids
    assert unrated not in ids

    # 3 star or more
    resp = await client.get("/api/v1/media?min_rating=3", headers=auth_headers)
    ids = [i["id"] for i in resp.json()["items"]]
    assert rated5 in ids
    assert rated3 in ids
    assert unrated not in ids

    # invalid value rejected
    resp = await client.get("/api/v1/media?min_rating=bad", headers=auth_headers)
    assert resp.status_code == 422

    for item_id in (rated5, rated3, unrated):
        await client.delete(f"/api/v1/media/{item_id}", headers=auth_headers)
