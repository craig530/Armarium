"""Tests for app.api.v1.lookup — barcode lookup, cover proxy, and image scan."""
import io

import httpx
import pytest
from unittest.mock import patch, AsyncMock

from .conftest import _subtype_id, PNG_1X1


# ── Barcode lookup ────────────────────────────────────────────────────────────

async def test_lookup_barcode_flags_existing_library_item(client, auth_headers):
    from app.models.enums import MediaCategory
    from app.schemas.media import LookupCandidate

    isbn = "9780134685991"
    book_id = await _subtype_id(client, auth_headers, "Book")

    resp = await client.post(
        "/api/v1/media",
        json={"title": "Effective Java", "media_subtype_id": book_id, "isbn": isbn},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    item_id = resp.json()["id"]

    fake_candidate = LookupCandidate(
        external_id=isbn,
        source="openlibrary",
        title="Effective Java",
        category=MediaCategory.BOOKS,
    )

    with patch("app.services.openlibrary.lookup_by_isbn", new=AsyncMock(return_value=[fake_candidate])):
        resp = await client.get(f"/api/v1/lookup/barcode/{isbn}", headers=auth_headers)

    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["metadata"]["library_count"] == 1

    resp = await client.delete(f"/api/v1/media/{item_id}", headers=auth_headers)
    assert resp.status_code == 204


async def test_lookup_barcode_rejects_invalid_barcode(client, auth_headers):
    # A 5-digit EAN-5 price extension is not a valid product barcode.
    resp = await client.get("/api/v1/lookup/barcode/51995", headers=auth_headers)

    assert resp.status_code == 400
    assert "barcode" in resp.json()["detail"].lower()


async def test_lookup_barcode_rejects_non_isbn_for_books_category(client, auth_headers):
    # 13-digit EAN-13 that doesn't start with 978/979 — not a valid ISBN, so
    # a category=books lookup must reject it before calling Open Library.
    with patch("app.services.openlibrary.lookup_by_isbn", new=AsyncMock(return_value=[])) as mock_lookup:
        resp = await client.get(
            "/api/v1/lookup/barcode/3916681812733?category=books", headers=auth_headers
        )

    assert resp.status_code == 400
    assert "isbn" in resp.json()["detail"].lower()
    mock_lookup.assert_not_awaited()


async def test_lookup_barcode_cd_queries_musicbrainz_with_ean13_from_upc(client, auth_headers):
    with patch("app.services.musicbrainz.lookup_by_barcode", new=AsyncMock(return_value=[])) as mock_lookup:
        resp = await client.get("/api/v1/lookup/barcode/075678563598", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json() == []
    # The 12-digit UPC-A is converted to its 13-digit EAN-13 form before
    # being passed to MusicBrainz.
    mock_lookup.assert_awaited_once_with("0075678563598")


async def test_lookup_barcode_music_category_queries_musicbrainz(client, auth_headers):
    with patch("app.services.musicbrainz.lookup_by_barcode", new=AsyncMock(return_value=[])) as mock_lookup:
        resp = await client.get("/api/v1/lookup/barcode/075678563598?category=music", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json() == []
    mock_lookup.assert_awaited_once_with("0075678563598")


async def test_lookup_barcode_films_tv_category_does_not_query_musicbrainz(client, auth_headers):
    # MusicBrainz only knows about music releases — a UPC/EAN-13 scanned while
    # adding a film/TV item must not return mismatched (category=music)
    # candidates, and must not even call MusicBrainz.
    with patch("app.services.musicbrainz.lookup_by_barcode", new=AsyncMock(return_value=[])) as mock_musicbrainz, \
            patch("app.services.upc.lookup_films_tv_by_barcode", new=AsyncMock(return_value=[])) as mock_upc:
        resp = await client.get("/api/v1/lookup/barcode/075678563598?category=films_tv", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json() == []
    mock_musicbrainz.assert_not_awaited()
    mock_upc.assert_awaited_once_with("075678563598")


async def test_lookup_barcode_films_tv_category_queries_upc_fallback(client, auth_headers):
    from app.models.enums import MediaCategory
    from app.schemas.media import LookupCandidate
    from app.services.cache import lookup_cache

    lookup_cache.clear()

    fake_candidate = LookupCandidate(
        external_id="603",
        source="tmdb",
        title="Steins;Gate: The Complete Series",
        category=MediaCategory.FILMS_TV,
        media_kind="tv",
    )

    with patch("app.services.musicbrainz.lookup_by_barcode", new=AsyncMock(return_value=[])) as mock_musicbrainz, \
            patch("app.services.upc.lookup_films_tv_by_barcode", new=AsyncMock(return_value=[fake_candidate])) as mock_upc:
        resp = await client.get("/api/v1/lookup/barcode/5022366813549?category=films_tv", headers=auth_headers)

    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["title"] == "Steins;Gate: The Complete Series"
    # 13-digit EAN-13 -> tmdb_barcode == ean13.
    mock_upc.assert_awaited_once_with("5022366813549")
    # category=films_tv -> MusicBrainz must not be queried.
    mock_musicbrainz.assert_not_awaited()


async def test_lookup_barcode_unspecified_category_falls_back_to_upc_when_musicbrainz_empty(client, auth_headers):
    from app.models.enums import MediaCategory
    from app.schemas.media import LookupCandidate
    from app.services.cache import lookup_cache

    lookup_cache.clear()

    fake_candidate = LookupCandidate(
        external_id="362",
        source="tmdb",
        title="The Lion King",
        category=MediaCategory.FILMS_TV,
        media_kind="movie",
    )

    with patch("app.services.musicbrainz.lookup_by_barcode", new=AsyncMock(return_value=[])) as mock_musicbrainz, \
            patch("app.services.upc.lookup_films_tv_by_barcode", new=AsyncMock(return_value=[fake_candidate])) as mock_upc:
        resp = await client.get("/api/v1/lookup/barcode/8717418440374", headers=auth_headers)

    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["title"] == "The Lion King"
    mock_musicbrainz.assert_awaited_once_with("8717418440374")
    mock_upc.assert_awaited_once_with("8717418440374")


async def test_lookup_barcode_music_category_does_not_query_upc_fallback(client, auth_headers):
    # category=music must not fall back to the films/TV (UPCitemdb->TMDB)
    # path even when MusicBrainz finds nothing.
    with patch("app.services.musicbrainz.lookup_by_barcode", new=AsyncMock(return_value=[])) as mock_musicbrainz, \
            patch("app.services.upc.lookup_films_tv_by_barcode", new=AsyncMock(return_value=[])) as mock_upc:
        resp = await client.get("/api/v1/lookup/barcode/075678563598?category=music", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json() == []
    mock_musicbrainz.assert_awaited_once_with("0075678563598")
    mock_upc.assert_not_awaited()


async def test_lookup_barcode_isbn_queries_open_library(client, auth_headers):
    from app.models.enums import MediaCategory
    from app.schemas.media import LookupCandidate
    from app.services.cache import lookup_cache

    # Avoid a cache hit from another test's lookup of the same ISBN.
    lookup_cache.clear()

    fake_candidate = LookupCandidate(
        external_id="9780134685991",
        source="openlibrary",
        title="Effective Java",
        category=MediaCategory.BOOKS,
    )

    with patch("app.services.openlibrary.lookup_by_isbn", new=AsyncMock(return_value=[fake_candidate])) as mock_lookup:
        resp = await client.get("/api/v1/lookup/barcode/978-0-13-468599-1", headers=auth_headers)

    assert resp.status_code == 200
    assert len(resp.json()) == 1
    # Hyphens stripped server-side before querying Open Library.
    mock_lookup.assert_awaited_once_with("9780134685991")


# ── Cover proxy ──────────────────────────────────────────────────────────────

async def test_cover_proxy_streams_remote_image(client):
    fake_bytes = b"\xff\xd8\xfake-jpeg-data"
    with patch("app.api.v1.lookup.fetch_remote_image", new=AsyncMock(return_value=(fake_bytes, "image/jpeg"))) as mock_fetch:
        resp = await client.get(
            "/api/v1/lookup/cover-proxy",
            params={"url": "https://image.tmdb.org/t/p/w500/poster.jpg"},
        )

    assert resp.status_code == 200
    assert resp.content == fake_bytes
    assert resp.headers["content-type"] == "image/jpeg"
    mock_fetch.assert_awaited_once_with("https://image.tmdb.org/t/p/w500/poster.jpg")


async def test_cover_proxy_404_when_unavailable(client):
    with patch("app.api.v1.lookup.fetch_remote_image", new=AsyncMock(return_value=None)):
        resp = await client.get(
            "/api/v1/lookup/cover-proxy",
            params={"url": "https://image.tmdb.org/t/p/w500/missing.jpg"},
        )

    assert resp.status_code == 404


async def test_cover_proxy_does_not_require_auth(client):
    # <img> tags can't send the Authorization header, so this endpoint must
    # be reachable without auth_headers.
    with patch("app.api.v1.lookup.fetch_remote_image", new=AsyncMock(return_value=(b"data", "image/png"))):
        resp = await client.get(
            "/api/v1/lookup/cover-proxy",
            params={"url": "https://covers.openlibrary.org/b/id/12345-L.jpg"},
        )

    assert resp.status_code == 200


async def test_cover_proxy_rejects_private_addresses(client):
    # The same SSRF guard used by download_cover applies here — a
    # loopback/link-local target must be rejected before any request is made,
    # without needing to mock httpx (resolves instantly, no network access).
    resp = await client.get("/api/v1/lookup/cover-proxy", params={"url": "http://127.0.0.1/secret.jpg"})
    assert resp.status_code == 404

    resp = await client.get("/api/v1/lookup/cover-proxy", params={"url": "http://169.254.169.254/latest/meta-data/"})
    assert resp.status_code == 404


# ── Barcode image scan ───────────────────────────────────────────────────────

# EAN-13 module width tables, used to render a real decodable barcode image
# for /lookup/scan tests (mirrors the encoding the camera scanner is reading).
_EAN13_L_CODES = ['0001101', '0011001', '0010011', '0111101', '0100011', '0110001', '0101111', '0111011', '0110111', '0001011']
_EAN13_G_CODES = ['0100111', '0110011', '0011011', '0100001', '0011101', '0111001', '0000101', '0010001', '0001001', '0010111']
_EAN13_R_CODES = ['1110010', '1100110', '1101100', '1000010', '1011100', '1001110', '1010000', '1000100', '1001000', '1110100']
_EAN13_PARITY = {
    0: 'LLLLLL', 1: 'LLGLGG', 2: 'LLGGLG', 3: 'LLGGGL', 4: 'LGLLGG',
    5: 'LGGLLG', 6: 'LGGGLL', 7: 'LGLGLG', 8: 'LGLGGL', 9: 'LGGLGL',
}


def _ean13_png(digits: str) -> bytes:
    from PIL import Image as PILImage

    parity = _EAN13_PARITY[int(digits[0])]
    left_bits = ''.join(
        _EAN13_L_CODES[int(d)] if p == 'L' else _EAN13_G_CODES[int(d)]
        for d, p in zip(digits[1:7], parity)
    )
    right_bits = ''.join(_EAN13_R_CODES[int(d)] for d in digits[7:13])
    bits = '101' + left_bits + '01010' + right_bits + '101'

    module_width, quiet, height = 4, 10, 100
    width = (len(bits) + 2 * quiet) * module_width
    img = PILImage.new('L', (width, height), 255)
    px = img.load()
    for m, b in enumerate(bits):
        if b == '1':
            for w in range(module_width):
                x = (quiet + m) * module_width + w
                for y in range(height):
                    px[x, y] = 0

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


async def test_scan_decodes_barcode_image(client, auth_headers):
    pytest.importorskip("zxingcpp")

    files = {"file": ("frame.png", _ean13_png("9781529052008"), "image/png")}
    resp = await client.post("/api/v1/lookup/scan", files=files, headers=auth_headers)

    assert resp.status_code == 200, resp.text
    results = resp.json()["results"]
    assert any(r["text"] == "9781529052008" for r in results)


async def test_scan_returns_no_results_for_blank_image(client, auth_headers):
    pytest.importorskip("zxingcpp")
    from PIL import Image as PILImage

    buf = io.BytesIO()
    PILImage.new('L', (200, 100), 255).save(buf, format='PNG')

    files = {"file": ("frame.png", buf.getvalue(), "image/png")}
    resp = await client.post("/api/v1/lookup/scan", files=files, headers=auth_headers)

    assert resp.status_code == 200, resp.text
    assert resp.json()["results"] == []


async def test_scan_rejects_unsupported_content_type(client, auth_headers):
    files = {"file": ("frame.txt", b"not an image", "text/plain")}
    resp = await client.post("/api/v1/lookup/scan", files=files, headers=auth_headers)
    assert resp.status_code == 400


async def test_scan_requires_auth(client):
    files = {"file": ("frame.png", PNG_1X1, "image/png")}
    resp = await client.post("/api/v1/lookup/scan", files=files)
    assert resp.status_code == 401


# ── Cover fallbacks & TMDB rating (service layer) ───────────────────────────

def _patched_client(module_path, handler):
    transport = httpx.MockTransport(handler)

    class _Client(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    return patch(f"{module_path}.httpx.AsyncClient", _Client)


async def test_tmdb_movie_details_falls_back_to_backdrop_and_includes_rating(monkeypatch):
    from app.config import settings
    from app.services import tmdb

    monkeypatch.setattr(settings, "tmdb_api_key", "test-key")

    def handler(request):
        return httpx.Response(200, json={
            "title": "No Poster Movie",
            "release_date": "2020-01-01",
            "backdrop_path": "/backdrop.jpg",
            "vote_average": 7.8,
            "genres": [],
            "production_companies": [],
            "credits": {"cast": [], "crew": []},
        })

    with _patched_client("app.services.tmdb", handler):
        details = await tmdb.get_movie_details(123)

    assert details["cover_image_url"] == f"{tmdb.IMAGE_BASE}/backdrop.jpg"
    assert details["tmdb_rating"] == 7.8


async def test_tmdb_tv_details_falls_back_to_backdrop_and_includes_rating(monkeypatch):
    from app.config import settings
    from app.services import tmdb

    monkeypatch.setattr(settings, "tmdb_api_key", "test-key")

    def handler(request):
        return httpx.Response(200, json={
            "name": "No Poster Show",
            "first_air_date": "2020-01-01",
            "backdrop_path": "/tv-backdrop.jpg",
            "vote_average": 8.2,
            "genres": [],
            "networks": [],
            "created_by": [],
            "credits": {"cast": []},
        })

    with _patched_client("app.services.tmdb", handler):
        details = await tmdb.get_tv_details(456)

    assert details["cover_image_url"] == f"{tmdb.IMAGE_BASE}/tv-backdrop.jpg"
    assert details["tmdb_rating"] == 8.2


async def test_tmdb_search_falls_back_to_backdrop_for_results_without_poster(monkeypatch):
    from app.config import settings
    from app.services import tmdb

    monkeypatch.setattr(settings, "tmdb_api_key", "test-key")

    def handler(request):
        return httpx.Response(200, json={
            "results": [{
                "media_type": "movie",
                "title": "No Poster Movie",
                "release_date": "2020-01-01",
                "backdrop_path": "/search-backdrop.jpg",
                "id": 789,
            }],
        })

    with _patched_client("app.services.tmdb", handler):
        candidates = await tmdb.search_titles("no poster")

    assert candidates[0].cover_url == f"{tmdb.IMAGE_BASE}/search-backdrop.jpg"


async def test_musicbrainz_barcode_falls_back_to_release_group_cover():
    from app.services import musicbrainz

    release_id = "11111111-1111-1111-1111-111111111111"
    release_group_id = "22222222-2222-2222-2222-222222222222"
    release_front_url = f"https://coverartarchive.org/release/{release_id}/front-250"
    fallback_url = f"https://coverartarchive.org/release-group/{release_group_id}/front-250"

    def handler(request):
        url = str(request.url)
        if "musicbrainz.org" in url:
            return httpx.Response(200, json={"releases": [{
                "id": release_id,
                "title": "Some Album",
                "release-group": {"id": release_group_id},
            }]})
        if url == release_front_url:
            return httpx.Response(404)
        raise AssertionError(f"unexpected request to {url}")

    with _patched_client("app.services.musicbrainz", handler):
        candidates = await musicbrainz.lookup_by_barcode("0123456789012")

    assert candidates[0].cover_url == fallback_url
    assert candidates[0].metadata["cover_image_url"] == fallback_url


async def test_musicbrainz_barcode_keeps_release_cover_when_available():
    from app.services import musicbrainz

    release_id = "11111111-1111-1111-1111-111111111111"
    release_group_id = "22222222-2222-2222-2222-222222222222"
    release_front_url = f"https://coverartarchive.org/release/{release_id}/front-250"

    def handler(request):
        url = str(request.url)
        if "musicbrainz.org" in url:
            return httpx.Response(200, json={"releases": [{
                "id": release_id,
                "title": "Some Album",
                "release-group": {"id": release_group_id},
            }]})
        if url == release_front_url:
            return httpx.Response(200)
        raise AssertionError(f"unexpected request to {url}")

    with _patched_client("app.services.musicbrainz", handler):
        candidates = await musicbrainz.lookup_by_barcode("0123456789012")

    assert candidates[0].cover_url == release_front_url


async def test_openlibrary_isbn_falls_back_to_google_books_cover():
    from app.services import openlibrary

    isbn = "9780356521657"

    def handler(request):
        url = str(request.url)
        if "openlibrary.org/api/books" in url:
            return httpx.Response(200, json={
                f"ISBN:{isbn}": {
                    "title": "Some Book",
                    "authors": [],
                    "publishers": [],
                },
            })
        if "googleapis.com/books" in url:
            return httpx.Response(200, json={
                "items": [{"volumeInfo": {"imageLinks": {"thumbnail": "http://books.google.com/cover.jpg"}}}],
            })
        raise AssertionError(f"unexpected request to {url}")

    with _patched_client("app.services.openlibrary", handler):
        candidates = await openlibrary.lookup_by_isbn(isbn)

    assert candidates[0].cover_url == "http://books.google.com/cover.jpg"
    assert candidates[0].metadata["cover_image_url"] == "http://books.google.com/cover.jpg"


# ── Films/TV barcode lookup via UPCitemdb -> TMDB (service layer) ──────────

def test_clean_title_strips_brackets_and_trailing_text():
    from app.services.upc import _clean_title

    assert _clean_title("Steins;Gate: The Complete Series [Blu-ray]") == "Steins;Gate: The Complete Series"
    assert _clean_title("The Lion King (2019) [Blu-ray] [Region Free]") == "The Lion King"
    assert _clean_title("The Lion King, Walt Disney Studios, Blu-ray + DVD") == "The Lion King"


async def test_upc_lookup_films_tv_by_barcode_searches_tmdb_with_cleaned_title():
    from app.models.enums import MediaCategory
    from app.schemas.media import LookupCandidate
    from app.services import upc

    def upc_handler(request):
        assert request.url.params["upc"] == "5022366813549"
        return httpx.Response(200, json={
            "code": "OK",
            "items": [{"title": "Steins;Gate: The Complete Series [Blu-ray]"}],
        })

    fake_candidate = LookupCandidate(
        external_id="100", source="tmdb", title="Steins;Gate",
        category=MediaCategory.FILMS_TV, media_kind="tv",
    )

    with _patched_client("app.services.upc", upc_handler), \
            patch("app.services.upc.tmdb.search_titles", new=AsyncMock(return_value=[fake_candidate])) as mock_search:
        candidates = await upc.lookup_films_tv_by_barcode("5022366813549")

    assert candidates == [fake_candidate]
    mock_search.assert_awaited_once_with("Steins;Gate: The Complete Series", 5)


async def test_upc_lookup_films_tv_by_barcode_retries_without_colon_suffix_when_first_search_empty():
    """TMDB has no match for "Steins;Gate: The Complete Series" verbatim
    (real-world finding), so a second search for just "Steins;Gate" — the
    part before the colon — must be tried before giving up."""
    from app.models.enums import MediaCategory
    from app.schemas.media import LookupCandidate
    from app.services import upc

    def upc_handler(request):
        return httpx.Response(200, json={
            "code": "OK",
            "items": [{"title": "Steins;Gate: The Complete Series [Blu-ray]"}],
        })

    fake_candidate = LookupCandidate(
        external_id="100", source="tmdb", title="Steins;Gate",
        category=MediaCategory.FILMS_TV, media_kind="tv",
    )

    async def fake_search(query, limit):
        return [fake_candidate] if query == "Steins;Gate" else []

    with _patched_client("app.services.upc", upc_handler), \
            patch("app.services.upc.tmdb.search_titles", new=AsyncMock(side_effect=fake_search)) as mock_search:
        candidates = await upc.lookup_films_tv_by_barcode("5022366813549")

    assert candidates == [fake_candidate]
    mock_search.assert_awaited_with("Steins;Gate", 5)
    assert mock_search.await_count == 2


async def test_upc_lookup_films_tv_by_barcode_returns_empty_when_no_upcitemdb_match():
    from app.services import upc

    def upc_handler(request):
        return httpx.Response(200, json={"code": "OK", "items": []})

    with _patched_client("app.services.upc", upc_handler):
        candidates = await upc.lookup_films_tv_by_barcode("0000000000000")

    assert candidates == []


async def test_upc_lookup_films_tv_by_barcode_returns_empty_on_upcitemdb_error():
    from app.services import upc

    def upc_handler(request):
        return httpx.Response(500)

    with _patched_client("app.services.upc", upc_handler):
        candidates = await upc.lookup_films_tv_by_barcode("8717418440374")

    assert candidates == []


async def test_openlibrary_isbn_does_not_query_google_books_when_cover_present():
    from app.services import openlibrary

    isbn = "9780134685991"

    def handler(request):
        url = str(request.url)
        if "openlibrary.org/api/books" in url:
            return httpx.Response(200, json={
                f"ISBN:{isbn}": {
                    "title": "Effective Java",
                    "authors": [],
                    "publishers": [],
                    "cover": {"large": "https://covers.openlibrary.org/b/id/1-L.jpg"},
                },
            })
        raise AssertionError(f"unexpected request to {url}")

    with _patched_client("app.services.openlibrary", handler):
        candidates = await openlibrary.lookup_by_isbn(isbn)

    assert candidates[0].cover_url == "https://covers.openlibrary.org/b/id/1-L.jpg"
