import io

from fastapi import APIRouter, Query, HTTPException, Depends, Request, UploadFile, File
from fastapi.responses import Response
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from ...database import get_db
from ...models.media import MediaItem
from ...models.enums import MediaCategory
from ...schemas.media import LookupCandidate
from ...models.user import User
from ...services import openlibrary, musicbrainz, tmdb
from ...services.barcode import process_barcode
from ...services.cache import lookup_cache
from ...services.cover_art import fetch_remote_image
from ...services.auth import get_current_user
from ...services.rate_limit import SlidingWindowRateLimiter
from ...config import settings

router = APIRouter()

# External lookup providers (TMDB/MusicBrainz/OpenLibrary) have their own,
# much stricter rate limits — this just stops a single user from hammering
# them (and the shared `lookup_cache`) badly enough to get this server's IP
# throttled or banned upstream.
lookup_limiter = SlidingWindowRateLimiter(max_attempts=30, window_seconds=60)

# The camera scanner polls /scan every ~200ms while open — much more
# frequent than the external-API lookups above, but still bounded so a
# misbehaving client can't peg the server decoding images indefinitely.
scan_limiter = SlidingWindowRateLimiter(max_attempts=600, window_seconds=60)

# Cover thumbnails for a single search's results all load at once (up to 20),
# and the browser may re-request on re-renders before caching kicks in.
# Unauthenticated (an <img> tag can't send the Authorization header), so this
# is keyed by client IP rather than username.
cover_proxy_limiter = SlidingWindowRateLimiter(max_attempts=180, window_seconds=60)

ALLOWED_SCAN_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_SCAN_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB


async def _rate_limited_user(current_user: User = Depends(get_current_user)) -> User:
    lookup_limiter.check(current_user.username, "Too many lookup requests. Please wait a moment and try again.")
    return current_user


async def _scan_rate_limited_user(current_user: User = Depends(get_current_user)) -> User:
    scan_limiter.check(current_user.username, "Too many scan requests. Please wait a moment and try again.")
    return current_user


async def _library_count(db: AsyncSession, processed: dict) -> int:
    """Count items already catalogued under this barcode (or ISBN)."""
    lookups = processed["lookups"]
    values = {processed["raw_cleaned"]}
    for key in ("isbn13", "upc_a", "ean13", "ean13_from_upc"):
        if lookups.get(key):
            values.add(lookups[key])
    stmt = select(func.count(MediaItem.id)).where(
        or_(MediaItem.barcode.in_(values), MediaItem.isbn.in_(values))
    )
    return (await db.execute(stmt)).scalar_one()


@router.post("/scan")
async def scan_barcode_image(
    file: UploadFile = File(...),
    _: User = Depends(_scan_rate_limited_user),
):
    """Decode barcodes from a single camera frame using zxing-cpp.

    The camera scanner POSTs cropped JPEG frames here at a steady interval
    while open. zxing-cpp's binarizer and rotation handling are far more
    robust on real camera frames than decoding client-side in the browser.
    """
    if file.content_type not in ALLOWED_SCAN_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported image type. Use JPEG, PNG or WebP.")

    data = await file.read()
    if len(data) > MAX_SCAN_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image too large (max 5 MB)")

    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail="File is not a valid image")

    import zxingcpp

    barcodes = zxingcpp.read_barcodes(image)
    return {"results": [{"text": b.text, "format": str(b.format)} for b in barcodes]}


@router.get("/cover-proxy")
async def cover_proxy(request: Request, url: str = Query(..., min_length=1)):
    """Proxy an external cover-art image (TMDB/Cover Art Archive/Open
    Library) for display in lookup search results, before an item is saved.

    Saved items get their cover downloaded server-side and served from
    `/covers/...`, but search-result thumbnails point straight at the
    third-party host — on setups where the client's network/DNS can't reach
    that host (even though the server, with its own DNS, can), those
    thumbnails fail to load. Routing them through here keeps the request on
    the server's network path.

    No auth required — an `<img>` tag can't send the Authorization header,
    and this only proxies publicly-readable image URLs (same risk profile as
    the unauthenticated `/covers/` static mount).
    """
    client_ip = request.client.host if request.client else "unknown"
    cover_proxy_limiter.check(client_ip, "Too many image requests. Please wait a moment and try again.")

    result = await fetch_remote_image(url)
    if result is None:
        raise HTTPException(status_code=404, detail="Image not available")

    data, content_type = result
    return Response(content=data, media_type=content_type, headers={"Cache-Control": "public, max-age=86400"})


@router.get("/barcode/{barcode}", response_model=List[LookupCandidate])
async def lookup_barcode(
    barcode: str,
    category: Optional[MediaCategory] = Query(None),
    _=Depends(_rate_limited_user),
    db: AsyncSession = Depends(get_db),
):
    processed = process_barcode(barcode)
    if not processed["valid"]:
        raise HTTPException(status_code=400, detail=processed["error"])

    lookups = processed["lookups"]
    is_book = category == MediaCategory.BOOKS or (category is None and processed["media_hint"] == "book")

    # A book lookup needs an ISBN-13 (prefix 978/979) — a barcode that's
    # merely the right length but doesn't start with that prefix (e.g. a
    # foreign/CD EAN-13) must be rejected here, before any external API call.
    if is_book and not lookups["isbn13"]:
        raise HTTPException(
            status_code=400,
            detail=(
                f"'{processed['raw_cleaned']}' is not a valid ISBN — book barcodes must "
                f"start with 978 or 979."
            ),
        )

    cache_key = f"barcode:{processed['raw_cleaned']}:{category}"
    candidates = lookup_cache.get(cache_key, ttl=3600)

    if candidates is None:
        if is_book:
            candidates = await openlibrary.lookup_by_isbn(lookups["open_library"])
        elif category in (None, MediaCategory.MUSIC) and lookups["musicbrainz"]:
            # MusicBrainz only knows about music releases — a UPC/EAN-13 scanned
            # while adding a film/TV item has no matching provider here, so
            # don't return mismatched (category=music) candidates for it.
            candidates = await musicbrainz.lookup_by_barcode(lookups["musicbrainz"])
        else:
            candidates = []

        if candidates:
            lookup_cache.set(cache_key, candidates)

    if candidates:
        # Computed fresh on every call (not cached) so it reflects items
        # added to the library since the lookup result was first cached.
        count = await _library_count(db, processed)
        for c in candidates:
            c.metadata["library_count"] = count

    return candidates


@router.get("/search", response_model=List[LookupCandidate])
async def search_lookup(
    q: str = Query(..., min_length=1),
    category: MediaCategory = Query(...),
    limit: int = Query(10, ge=1, le=20),
    media_kind: Optional[str] = Query(None, pattern="^(movie|tv)$"),
    _=Depends(_rate_limited_user),
):
    cache_key = f"search:{q}:{category}:{limit}:{media_kind}"
    cached = lookup_cache.get(cache_key, ttl=3600)
    if cached is not None:
        return cached

    if category == MediaCategory.BOOKS:
        results = await openlibrary.search_books(q, limit)
    elif category == MediaCategory.MUSIC:
        results = await musicbrainz.search_releases(q, limit)
    elif category == MediaCategory.FILMS_TV:
        if not settings.tmdb_api_key:
            raise HTTPException(
                status_code=503,
                detail="TMDB_API_KEY is not configured. Add it to your .env file to enable film/TV lookup.",
            )
        results = await tmdb.search_titles(q, limit, media_kind=media_kind)
    else:
        results = []

    if results:
        lookup_cache.set(cache_key, results)
    return results


@router.get("/tmdb/{tmdb_id}", response_model=LookupCandidate)
async def get_tmdb_details(
    tmdb_id: int,
    media_kind: str = Query("movie", pattern="^(movie|tv)$"),
    _=Depends(_rate_limited_user),
):
    if not settings.tmdb_api_key:
        raise HTTPException(status_code=503, detail="TMDB_API_KEY not configured")

    cache_key = f"tmdb:{tmdb_id}:{media_kind}"
    cached = lookup_cache.get(cache_key, ttl=7200)
    if cached is not None:
        return cached

    if media_kind == "tv":
        details = await tmdb.get_tv_details(tmdb_id)
    else:
        details = await tmdb.get_movie_details(tmdb_id)
    if not details:
        raise HTTPException(status_code=404, detail="TMDB item not found")

    result = LookupCandidate(
        external_id=str(tmdb_id),
        source="tmdb",
        title=details.get("title", ""),
        year=details.get("year"),
        category=MediaCategory.FILMS_TV,
        creator=details.get("director"),
        cover_url=details.get("cover_image_url"),
        media_kind=media_kind,
        metadata=details,
    )
    lookup_cache.set(cache_key, result)
    return result
