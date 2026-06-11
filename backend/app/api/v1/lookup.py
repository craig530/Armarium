from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from ...database import get_db
from ...models.media import MediaItem
from ...models.enums import MediaCategory
from ...schemas.media import LookupCandidate
from ...models.user import User
from ...services import openlibrary, musicbrainz, tmdb
from ...services.cache import lookup_cache
from ...services.auth import get_current_user
from ...services.rate_limit import SlidingWindowRateLimiter
from ...config import settings

router = APIRouter()

_ISBN_PREFIXES = {"978", "979"}

# External lookup providers (TMDB/MusicBrainz/OpenLibrary) have their own,
# much stricter rate limits — this just stops a single user from hammering
# them (and the shared `lookup_cache`) badly enough to get this server's IP
# throttled or banned upstream.
lookup_limiter = SlidingWindowRateLimiter(max_attempts=30, window_seconds=60)


async def _rate_limited_user(current_user: User = Depends(get_current_user)) -> User:
    lookup_limiter.check(current_user.username, "Too many lookup requests. Please wait a moment and try again.")
    return current_user


def _guess_category(barcode: str) -> MediaCategory:
    clean = barcode.replace("-", "").strip()
    if len(clean) in (10, 13) and (len(clean) == 10 or clean[:3] in _ISBN_PREFIXES):
        return MediaCategory.BOOKS
    return MediaCategory.MUSIC


async def _library_count(db: AsyncSession, barcode: str) -> int:
    """Count items already catalogued under this barcode (or ISBN)."""
    clean = barcode.replace("-", "").strip()
    values = {barcode, clean}
    stmt = select(func.count(MediaItem.id)).where(
        or_(MediaItem.barcode.in_(values), MediaItem.isbn.in_(values))
    )
    return (await db.execute(stmt)).scalar_one()


@router.get("/barcode/{barcode}", response_model=List[LookupCandidate])
async def lookup_barcode(
    barcode: str,
    category: Optional[MediaCategory] = Query(None),
    _=Depends(_rate_limited_user),
    db: AsyncSession = Depends(get_db),
):
    cache_key = f"barcode:{barcode}:{category}"
    candidates = lookup_cache.get(cache_key, ttl=3600)

    if candidates is None:
        detected = category or _guess_category(barcode)
        candidates = []

        if detected == MediaCategory.BOOKS:
            candidates = await openlibrary.lookup_by_isbn(barcode)
        elif detected == MediaCategory.MUSIC:
            candidates = await musicbrainz.lookup_by_barcode(barcode)
            if not candidates:
                candidates = await openlibrary.lookup_by_isbn(barcode)

        if candidates:
            lookup_cache.set(cache_key, candidates)

    if candidates:
        # Computed fresh on every call (not cached) so it reflects items
        # added to the library since the lookup result was first cached.
        count = await _library_count(db, barcode)
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
