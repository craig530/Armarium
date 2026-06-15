import httpx
import logging
import re
from typing import List, Optional
from ..schemas.media import LookupCandidate
from ..models.enums import MediaCategory

logger = logging.getLogger("armarium")

BASE_URL = "https://musicbrainz.org/ws/2"
HEADERS = {
    "User-Agent": "Armarium/1.0 (+https://github.com/craig530/Armarium)",
    "Accept": "application/json",
}


async def lookup_by_barcode(barcode: str) -> List[LookupCandidate]:
    async with httpx.AsyncClient(headers=HEADERS, timeout=10.0) as client:
        try:
            resp = await client.get(
                f"{BASE_URL}/release",
                params={
                    "query": f"barcode:{barcode}",
                    "fmt": "json",
                    "limit": 10,
                    "inc": "artist-credits labels release-groups",
                },
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning("MusicBrainz barcode lookup failed for %s: %s", barcode, e)
            return []

        candidates = []
        for release in data.get("releases", []):
            candidate = _release_to_candidate(release)
            if not candidate:
                continue
            await _apply_cover_art_fallback(client, candidate, release)
            candidates.append(candidate)

    return candidates


async def _apply_cover_art_fallback(client: httpx.AsyncClient, candidate: LookupCandidate, release: dict) -> None:
    """Cover Art Archive often has art at the release-group level even when
    the specific release has none. Probe the release-level front cover and
    fall back to the release-group's front cover on a miss."""
    release_group_id = release.get("release-group", {}).get("id")
    if not release_group_id or not candidate.cover_url:
        return

    try:
        resp = await client.head(candidate.cover_url, timeout=5.0)
        if resp.status_code == 200:
            return
    except Exception as e:
        logger.debug("CAA release-level cover probe failed for %s: %s", candidate.cover_url, e)

    fallback_url = f"https://coverartarchive.org/release-group/{release_group_id}/front-250"
    candidate.cover_url = fallback_url
    candidate.metadata["cover_image_url"] = fallback_url


def _escape_lucene_phrase(value: str) -> str:
    """Escape characters that would break out of a Lucene quoted phrase."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


async def search_releases(query: str, limit: int = 10) -> List[LookupCandidate]:
    escaped = _escape_lucene_phrase(query)
    async with httpx.AsyncClient(headers=HEADERS, timeout=10.0) as client:
        try:
            resp = await client.get(
                f"{BASE_URL}/release",
                params={
                    "query": f'release:"{escaped}"',
                    "fmt": "json",
                    "limit": limit,
                    "inc": "artist-credits labels",
                },
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning("MusicBrainz search failed for %r: %s", query, e)
            return []

    return [c for c in (_release_to_candidate(r) for r in data.get("releases", [])) if c][:limit]


def _release_to_candidate(release: dict) -> Optional[LookupCandidate]:
    title = release.get("title")
    if not title:
        return None

    release_id = release.get("id", "")

    credits = release.get("artist-credit", [])
    artists = [
        c["artist"]["name"]
        for c in credits
        if isinstance(c, dict) and "artist" in c
    ]
    artist = " & ".join(artists) if artists else None

    date = release.get("date", "")
    year = None
    m = re.match(r"^(\d{4})", date)
    if m:
        year = int(m.group(1))

    label_info = release.get("label-info", [])
    label = None
    if label_info and isinstance(label_info[0], dict):
        lbl = label_info[0].get("label")
        if lbl:
            label = lbl.get("name")

    media = release.get("media", [])
    track_count = sum(m.get("track-count", 0) for m in media) if media else None

    disambiguation = release.get("disambiguation", "")
    status = release.get("status", "")
    edition = disambiguation or (status if status != "Official" else None)

    cover_url = f"https://coverartarchive.org/release/{release_id}/front-250"

    metadata = {
        "title": title,
        "artist": artist,
        "label": label,
        "year": year,
        "track_count": track_count,
        "edition": edition,
        "musicbrainz_id": release_id,
        "cover_image_url": cover_url,
        "barcode": release.get("barcode"),
    }

    return LookupCandidate(
        external_id=release_id,
        source="musicbrainz",
        title=title,
        year=year,
        category=MediaCategory.MUSIC,
        edition=edition,
        creator=artist,
        cover_url=cover_url,
        metadata=metadata,
    )
