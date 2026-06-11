import httpx
import logging
from typing import List, Optional
from ..schemas.media import LookupCandidate
from ..models.enums import MediaCategory
from ..config import settings

logger = logging.getLogger("armarium")

BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"


async def search_titles(query: str, limit: int = 10, media_kind: Optional[str] = None) -> List[LookupCandidate]:
    if not settings.tmdb_api_key:
        return []

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(
                f"{BASE_URL}/search/multi",
                params={"api_key": settings.tmdb_api_key, "query": query, "include_adult": False},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning("TMDB search failed for %r: %s", query, e)
            return []

    candidates = []
    for result in data.get("results", []):
        mt = result.get("media_type")
        if mt not in ("movie", "tv"):
            continue
        if media_kind and mt != media_kind:
            continue
        c = _result_to_candidate(result, mt)
        if c:
            candidates.append(c)
        if len(candidates) >= limit:
            break

    return candidates


async def get_movie_details(tmdb_id: int) -> Optional[dict]:
    if not settings.tmdb_api_key:
        return None

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(
                f"{BASE_URL}/movie/{tmdb_id}",
                params={"api_key": settings.tmdb_api_key, "append_to_response": "credits"},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning("TMDB movie details lookup failed for id=%s: %s", tmdb_id, e)
            return None

    credits = data.get("credits", {})
    cast = [c["name"] for c in credits.get("cast", [])[:10]]
    directors = [c["name"] for c in credits.get("crew", []) if c.get("job") == "Director"]
    genres = ", ".join(g["name"] for g in data.get("genres", []))
    studios = [c["name"] for c in data.get("production_companies", [])]

    return {
        "title": data.get("title"),
        "year": _year(data.get("release_date")),
        "director": ", ".join(directors),
        "studio": ", ".join(studios[:2]),
        "genres": genres,
        "description": data.get("overview"),
        "runtime_minutes": data.get("runtime"),
        "cast_list": str(cast),
        "tmdb_id": tmdb_id,
        "media_kind": "movie",
        "cover_image_url": (IMAGE_BASE + data["poster_path"]) if data.get("poster_path") else None,
    }


async def get_tv_details(tmdb_id: int) -> Optional[dict]:
    if not settings.tmdb_api_key:
        return None

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(
                f"{BASE_URL}/tv/{tmdb_id}",
                params={"api_key": settings.tmdb_api_key, "append_to_response": "credits"},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning("TMDB TV details lookup failed for id=%s: %s", tmdb_id, e)
            return None

    credits = data.get("credits", {})
    cast = [c["name"] for c in credits.get("cast", [])[:10]]
    creators = [c["name"] for c in data.get("created_by", [])]
    genres = ", ".join(g["name"] for g in data.get("genres", []))
    networks = [n["name"] for n in data.get("networks", [])]
    runtimes = data.get("episode_run_time") or []
    num_seasons = data.get("number_of_seasons")

    return {
        "title": data.get("name"),
        "year": _year(data.get("first_air_date")),
        "director": ", ".join(creators),
        "studio": ", ".join(networks[:2]),
        "genres": genres,
        "description": data.get("overview"),
        "runtime_minutes": runtimes[0] if runtimes else None,
        "seasons_owned": f"1–{num_seasons}" if num_seasons else "",
        "episode_count": data.get("number_of_episodes"),
        "cast_list": str(cast),
        "tmdb_id": tmdb_id,
        "media_kind": "tv",
        "cover_image_url": (IMAGE_BASE + data["poster_path"]) if data.get("poster_path") else None,
    }


def _result_to_candidate(result: dict, mt: str) -> Optional[LookupCandidate]:
    if mt == "movie":
        title = result.get("title") or result.get("original_title")
        year = _year(result.get("release_date"))
    else:
        title = result.get("name") or result.get("original_name")
        year = _year(result.get("first_air_date"))

    if not title:
        return None

    poster = result.get("poster_path")
    cover_url = (IMAGE_BASE + poster) if poster else None
    tmdb_id = result.get("id")

    metadata = {
        "title": title,
        "year": year,
        "tmdb_id": tmdb_id,
        "cover_image_url": cover_url,
        "description": result.get("overview"),
        "media_kind": mt,
    }

    return LookupCandidate(
        external_id=str(tmdb_id),
        source="tmdb",
        title=title,
        year=year,
        category=MediaCategory.FILMS_TV,
        creator=None,
        cover_url=cover_url,
        media_kind=mt,
        metadata=metadata,
    )


def _year(date_str: Optional[str]) -> Optional[int]:
    if date_str and len(date_str) >= 4:
        try:
            return int(date_str[:4])
        except ValueError:
            pass
    return None
