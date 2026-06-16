import asyncio
import logging
import re
import time
from typing import List, Optional

import httpx

from ..config import settings
from ..models.enums import MediaCategory
from ..schemas.media import LookupCandidate

logger = logging.getLogger("armarium")

TOKEN_URL = "https://id.twitch.tv/oauth2/token"
BASE_URL = "https://api.igdb.com/v4"

# In-process token cache. IGDB tokens last ~60 days; we refresh on expiry.
_token: Optional[str] = None
_token_expires_at: float = 0.0
_token_lock = asyncio.Lock()


async def _get_token() -> Optional[str]:
    global _token, _token_expires_at
    if not settings.igdb_client_id or not settings.igdb_client_secret:
        return None

    async with _token_lock:
        if _token and time.monotonic() < _token_expires_at - 60:
            return _token

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    TOKEN_URL,
                    params={
                        "client_id": settings.igdb_client_id,
                        "client_secret": settings.igdb_client_secret,
                        "grant_type": "client_credentials",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
            _token = data["access_token"]
            _token_expires_at = time.monotonic() + data.get("expires_in", 3600)
            return _token
        except Exception as e:
            logger.warning("IGDB token fetch failed: %s", e)
            _token = None
            return None


async def _igdb_post(endpoint: str, body: str) -> Optional[list]:
    token = await _get_token()
    if not token or not settings.igdb_client_id:
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{BASE_URL}/{endpoint}",
                content=body,
                headers={
                    "Client-ID": settings.igdb_client_id,
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning("IGDB %s request failed: %s", endpoint, e)
        return None


def _cover_url(cover: Optional[dict]) -> Optional[str]:
    if not cover:
        return None
    url = cover.get("url", "")
    if not url:
        return None
    # IGDB returns //images.igdb.com/... — prepend https and upgrade to t_cover_big
    url = url.replace("//", "https://", 1).replace("t_thumb", "t_cover_big")
    return url


def _developer_from_companies(companies: list) -> Optional[str]:
    devs = [c["company"]["name"] for c in companies if c.get("developer") and c.get("company")]
    if devs:
        return ", ".join(devs)
    # Fall back to any named company if none flagged as developer
    names = [c["company"]["name"] for c in companies if c.get("company")]
    return ", ".join(names[:2]) if names else None


def _result_to_candidate(game: dict) -> LookupCandidate:
    title = game.get("name", "")
    year = None
    release_ts = game.get("first_release_date")
    if release_ts:
        from datetime import datetime, timezone
        year = datetime.fromtimestamp(release_ts, tz=timezone.utc).year

    cover_url = _cover_url(game.get("cover"))
    companies = game.get("involved_companies") or []
    developer = _developer_from_companies(companies)
    genres = ", ".join(g["name"] for g in (game.get("genres") or []))
    igdb_id = game.get("id")

    metadata = {
        "title": title,
        "year": year,
        "igdb_id": igdb_id,
        "cover_image_url": cover_url,
        "description": game.get("summary"),
        "developer": developer,
        "genres": genres,
    }

    return LookupCandidate(
        external_id=str(igdb_id) if igdb_id is not None else "",
        source="igdb",
        title=title,
        year=year,
        category=MediaCategory.GAMES,
        creator=developer,
        cover_url=cover_url,
        metadata=metadata,
    )


# Strips trailing platform/format names that UPCitemdb appends to game titles,
# e.g. "Indiana Jones and the Great Circle - Nintendo Switch 2" or
# "Elden Ring [PlayStation 5]" (brackets already handled by upc._clean_title).
_PLATFORM_SUFFIX_RE = re.compile(
    r"\s*[-–]\s*(Nintendo Switch\s*\d*|PlayStation\s*\d*|PS\s*\d+|Xbox\s*(?:One|Series\s*[XS])?|"
    r"PC|Windows|Steam|Nintendo\s*\d+DS|Game\s*Boy|Nintendo\s*64|Wii\s*U?)\s*$",
    re.IGNORECASE,
)


def _clean_game_title(title: str) -> str:
    return _PLATFORM_SUFFIX_RE.sub("", title).strip(" -:")


_GAME_FIELDS = (
    "id,name,first_release_date,cover.url,genres.name,"
    "involved_companies.developer,involved_companies.company.name,summary"
)


async def search_games(query: str, limit: int = 10) -> List[LookupCandidate]:
    if not settings.igdb_client_id or not settings.igdb_client_secret:
        return []

    body = f'search "{query}"; fields {_GAME_FIELDS}; limit {limit};'
    games = await _igdb_post("games", body)
    if not games:
        return []

    return [_result_to_candidate(g) for g in games if g.get("name")]


async def get_game_details(igdb_id: int) -> Optional[LookupCandidate]:
    if not settings.igdb_client_id or not settings.igdb_client_secret:
        return None

    body = f"where id = {igdb_id}; fields {_GAME_FIELDS}; limit 1;"
    games = await _igdb_post("games", body)
    if not games:
        return None

    return _result_to_candidate(games[0])


async def lookup_by_barcode(barcode: str) -> List[LookupCandidate]:
    """Resolve a game barcode via UPCitemdb → product title → IGDB title search.

    IGDB's external_games table stores platform-storefront IDs (Steam, eShop,
    etc.), not physical barcodes, so there is no direct barcode lookup in the
    IGDB API. Instead we use the same UPCitemdb-then-search approach that the
    films/TV flow uses for TMDB.
    """
    if not settings.igdb_client_id or not settings.igdb_client_secret:
        return []

    from . import upc  # local import to avoid circular at module load
    raw_title = await upc.lookup_title(barcode)
    if not raw_title:
        return []

    title = _clean_game_title(raw_title)
    if not title:
        return []

    results = await search_games(title, limit=5)
    if not results and ":" in title:
        results = await search_games(title.split(":")[0].strip(), limit=5)
    return results
