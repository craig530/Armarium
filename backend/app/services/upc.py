import httpx
import logging
import re
from typing import List, Optional

from . import tmdb
from ..schemas.media import LookupCandidate

logger = logging.getLogger("armarium")

# Free trial endpoint, no API key required. Fixed/hardcoded host — same SSRF
# posture as the other lookup providers (musicbrainz.org, openlibrary.org,
# api.themoviedb.org): no `_is_safe_url` needed.
UPCITEMDB_URL = "https://api.upcitemdb.com/prod/trial/lookup"

# Strips bracketed/parenthesised format or region tags UPCitemdb titles tend
# to carry, e.g. "Steins;Gate: The Complete Series [Blu-ray]" or
# "The Lion King (2019) [Blu-ray] [Region Free]".
_BRACKETS_RE = re.compile(r"\[[^\]]*\]|\([^)]*\)")


def _clean_title(raw_title: str) -> str:
    """Turn a UPCitemdb product title into something worth searching TMDB
    for: drop bracketed format/region tags, then drop everything from the
    first comma onward (UPCitemdb often appends cast/edition/UPC text after
    a comma), and trim leftover separators."""
    title = _BRACKETS_RE.sub("", raw_title)
    title = title.split(",")[0]
    return title.strip(" -:")


async def lookup_films_tv_by_barcode(barcode: str, limit: int = 5) -> List[LookupCandidate]:
    """TMDB has no barcode lookup of its own, so look the barcode up on
    UPCitemdb for a product title, clean it, and search TMDB by title.

    Only used for single-item barcode lookups, not bulk search — each call
    costs an extra HTTP round-trip to UPCitemdb's trial endpoint.
    """
    title = await _lookup_title(barcode)
    if not title:
        return []

    candidates = await tmdb.search_titles(title, limit)
    if not candidates and ":" in title:
        # Box-set/edition titles (e.g. "Steins;Gate: The Complete Series")
        # often don't match TMDB's search verbatim — retry with just the
        # part before the colon, which is usually the show/film's own title.
        candidates = await tmdb.search_titles(title.split(":")[0].strip(), limit)

    return candidates


async def _lookup_title(barcode: str) -> Optional[str]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(UPCITEMDB_URL, params={"upc": barcode})
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning("UPCitemdb lookup failed for barcode=%s: %s", barcode, e)
            return None

    items = data.get("items") or []
    if not items:
        return None

    return _clean_title(items[0].get("title", "")) or None
