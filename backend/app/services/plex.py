import logging
import re
from typing import Optional

import httpx

logger = logging.getLogger("armarium")

# Plex sections we can sync — movie libraries map to films/tv, show libraries
# map to films/tv (TV series), artist (music) libraries map to music.
SUPPORTED_SECTION_TYPES = {"movie", "show", "artist"}

_TMDB_GUID = re.compile(r"tmdb://(\d+)")
_MBID_GUID = re.compile(r"mbid://([0-9a-fA-F-]+)")


def _headers(token: str) -> dict:
    return {"X-Plex-Token": token, "Accept": "application/json"}


async def test_connection(base_url: str, token: str) -> dict:
    """Check connectivity to a Plex server, raising on failure.

    Returns `{"ok": True, "name": ..., "version": ...}` on success — callers
    (the `/admin/plex/test` endpoint) catch exceptions to surface a clear
    error to the admin before they save the configuration.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{base_url.rstrip('/')}/identity", headers=_headers(token))
        resp.raise_for_status()
        data = resp.json()

    container = data.get("MediaContainer", {})
    return {
        "ok": True,
        "name": container.get("friendlyName"),
        "version": container.get("version"),
        "machine_identifier": container.get("machineIdentifier"),
    }


async def list_sections(base_url: str, token: str) -> list[dict]:
    """List Plex library sections we support syncing (movie/show/artist).

    Returns `[]` on any connection error — callers treat an empty result as
    "nothing available" rather than a hard failure.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{base_url.rstrip('/')}/library/sections", headers=_headers(token))
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, ValueError) as e:
        logger.warning("Plex list_sections failed: %s", e)
        return []

    sections = []
    for d in data.get("MediaContainer", {}).get("Directory", []):
        if d.get("type") not in SUPPORTED_SECTION_TYPES:
            continue
        sections.append({"key": d.get("key"), "title": d.get("title"), "type": d.get("type")})
    return sections


def _parse_guids(entry: dict) -> tuple[Optional[int], Optional[str]]:
    """Extract `(tmdb_id, musicbrainz_id)` from a Plex item's `Guid[]` list."""
    tmdb_id = None
    musicbrainz_id = None
    for g in entry.get("Guid", []) or []:
        gid = g.get("id", "")
        if (m := _TMDB_GUID.match(gid)):
            tmdb_id = int(m.group(1))
        elif (m := _MBID_GUID.match(gid)):
            musicbrainz_id = m.group(1)
    return tmdb_id, musicbrainz_id


def _normalize_item(entry: dict, section_type: str) -> dict:
    tmdb_id, musicbrainz_id = _parse_guids(entry)

    rating_key = entry.get("ratingKey")
    normalized = {
        "guid": entry.get("guid"),
        "title": entry.get("title"),
        "year": entry.get("year"),
        "summary": entry.get("summary"),
        "genres": [g.get("tag") for g in entry.get("Genre", []) or [] if g.get("tag")],
        "studio": entry.get("studio"),
        "thumb": entry.get("thumb"),
        "tmdb_id": tmdb_id,
        "musicbrainz_id": musicbrainz_id,
        "rating_key": str(rating_key) if rating_key is not None else None,
    }

    if section_type == "movie":
        normalized["directors"] = [d.get("tag") for d in entry.get("Director", []) or [] if d.get("tag")]
        normalized["cast"] = [r.get("tag") for r in (entry.get("Role", []) or [])[:10] if r.get("tag")]
        normalized["duration_ms"] = entry.get("duration")
        normalized["content_rating"] = entry.get("contentRating")
    elif section_type == "show":
        normalized["directors"] = [d.get("tag") for d in entry.get("Director", []) or [] if d.get("tag")]
        normalized["cast"] = [r.get("tag") for r in (entry.get("Role", []) or [])[:10] if r.get("tag")]
        normalized["duration_ms"] = entry.get("duration")
        normalized["content_rating"] = entry.get("contentRating")
        normalized["child_count"] = entry.get("childCount")
        normalized["leaf_count"] = entry.get("leafCount")
    elif section_type == "artist":
        normalized["artist_name"] = entry.get("parentTitle")
        normalized["leaf_count"] = entry.get("leafCount")

    return normalized


async def list_section_items(base_url: str, token: str, section_key: str, section_type: str) -> list[dict]:
    """List items in a Plex library section, normalized for sync.

    For `artist` (music) libraries, requests `type=9` (albums) so the result
    is at album granularity rather than artist granularity. Returns `[]` on
    any connection error.
    """
    params = {}
    if section_type == "artist":
        params["type"] = "9"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{base_url.rstrip('/')}/library/sections/{section_key}/all",
                headers=_headers(token),
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, ValueError) as e:
        logger.warning("Plex list_section_items failed for section %s: %s", section_key, e)
        return []

    return [_normalize_item(entry, section_type) for entry in data.get("MediaContainer", {}).get("Metadata", []) or []]


async def fetch_thumbnail(base_url: str, token: str, thumb_path: str) -> Optional[bytes]:
    """Fetch a Plex thumbnail's raw bytes for the given relative `thumb` path.

    Intentionally bypasses `services.cover_art._is_safe_url` — `base_url` is
    an admin-configured, trusted local-network address (the whole point of
    the "assuming local server" Plex integration), unlike user-supplied
    `cover_image_url` values which that check protects against. Returns the
    raw bytes for `optimise_and_save()`, or None on any error.
    """
    if not thumb_path:
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{base_url.rstrip('/')}{thumb_path}",
                headers={"X-Plex-Token": token},
            )
            resp.raise_for_status()
            return resp.content
    except httpx.HTTPError as e:
        logger.warning("Plex fetch_thumbnail failed for %s: %s", thumb_path, e)
        return None
