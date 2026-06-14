import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pathlib import Path
from typing import List, Optional

from ...database import AsyncSessionLocal
from ...models.enums import MediaCategory, Supertype
from ...models.media import MediaItem
from ...models.platform import Platform
from ...models.plex_config import PlexConfig
from ...models.plex_library_mapping import PlexLibraryMapping
from ...schemas.media import PlatformSummary
from ...schemas.plex import (
    MediaSubtypeSummary,
    PlexConfigResponse,
    PlexConfigUpdate,
    PlexMappingCreate,
    PlexMappingResponse,
    PlexMappingUpdate,
    PlexRemoveStaleRequest,
    PlexSectionResponse,
    PlexSyncItem,
    PlexSyncResult,
    PlexSyncStatus,
    PlexTestRequest,
)
from ...services import plex as plex_service
from ...services.auth import get_current_admin, require_permission
from ...services.cover_art import delete_cover_files, optimise_and_save
from ...services.plex_sync_jobs import PlexSyncJob, get_job, set_job
from ...repositories.media_item import MediaItemRepository, get_media_item_repository
from ...repositories.media_subtype import MediaSubtypeRepository, get_media_subtype_repository
from ...repositories.platform import PlatformRepository, get_platform_repository
from ...repositories.plex import (
    PlexConfigRepository,
    PlexLibraryMappingRepository,
    get_plex_config_repository,
    get_plex_library_mapping_repository,
)
from .media import _build_responses

router = APIRouter()

# Plex section `type` -> our category. Movie and show libraries both map to
# Films & TV; artist (music) libraries map to Music. Plex has no native book
# library type, so books are out of scope.
_SECTION_CATEGORY = {
    "movie": MediaCategory.FILMS_TV,
    "show": MediaCategory.FILMS_TV,
    "artist": MediaCategory.MUSIC,
}

# Plex section `type` -> the seeded digital MediaSubtype that synced items
# are filed under.
_SECTION_SUBTYPE_NAME = {
    "movie": "Film",
    "show": "TV Series",
    "artist": "Music",
}


def _platform_summary(platform: Platform) -> PlatformSummary:
    return PlatformSummary(
        id=platform.id,
        name=platform.name,
        logo_key=platform.logo_key,
        logo_url=f"/platform-logos/{Path(platform.logo_path).name}" if platform.logo_path else None,
    )


def _to_mapping_response(mapping: PlexLibraryMapping) -> PlexMappingResponse:
    return PlexMappingResponse(
        id=mapping.id,
        section_key=mapping.section_key,
        section_title=mapping.section_title,
        section_type=mapping.section_type,
        category=mapping.category,
        media_subtype=MediaSubtypeSummary.model_validate(mapping.media_subtype) if mapping.media_subtype else None,
        last_synced_at=mapping.last_synced_at,
    )


@router.get("/config", response_model=PlexConfigResponse)
async def get_config(_=Depends(get_current_admin), repo: PlexConfigRepository = Depends(get_plex_config_repository)):
    config = await repo.get_singleton()
    if config is None:
        return PlexConfigResponse(configured=False, enabled=False, base_url=None)
    return PlexConfigResponse(
        configured=True,
        enabled=config.enabled,
        base_url=config.base_url,
        platform=_platform_summary(config.platform),
    )


@router.put("/config", response_model=PlexConfigResponse)
async def update_config(
    payload: PlexConfigUpdate,
    _=Depends(get_current_admin),
    config_repo: PlexConfigRepository = Depends(get_plex_config_repository),
    platform_repo: PlatformRepository = Depends(get_platform_repository),
):
    platform = await platform_repo.get(payload.platform_id)
    if platform is None:
        raise HTTPException(status_code=404, detail="Platform not found")

    config = await config_repo.upsert(
        base_url=payload.base_url, token=payload.token, enabled=payload.enabled, platform_id=platform.id
    )
    await config_repo.commit()
    return PlexConfigResponse(configured=True, enabled=config.enabled, base_url=config.base_url, platform=_platform_summary(platform))


@router.delete("/config", status_code=204)
async def delete_config(_=Depends(get_current_admin), repo: PlexConfigRepository = Depends(get_plex_config_repository)):
    await repo.delete_singleton()


@router.post("/test")
async def test_connection(payload: PlexTestRequest, _=Depends(get_current_admin)):
    try:
        return await plex_service.test_connection(payload.base_url, payload.token)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not connect to Plex: {e}")


@router.get("/sections", response_model=List[PlexSectionResponse])
async def get_sections(
    _=Depends(require_permission("can_add_items")),
    config_repo: PlexConfigRepository = Depends(get_plex_config_repository),
    mapping_repo: PlexLibraryMappingRepository = Depends(get_plex_library_mapping_repository),
):
    config = await config_repo.require_enabled()
    sections = await plex_service.list_sections(config.base_url, config.token)

    mapped_keys = await mapping_repo.mapped_section_keys()
    return [
        PlexSectionResponse(key=s["key"], title=s["title"], type=s["type"], mapped=s["key"] in mapped_keys)
        for s in sections
    ]


@router.get("/mappings", response_model=List[PlexMappingResponse])
async def list_mappings(
    _=Depends(require_permission("can_add_items")),
    repo: PlexLibraryMappingRepository = Depends(get_plex_library_mapping_repository),
):
    mappings = await repo.list_all()
    return [_to_mapping_response(m) for m in mappings]


@router.post("/mappings", response_model=PlexMappingResponse, status_code=201)
async def create_mapping(
    payload: PlexMappingCreate,
    _=Depends(require_permission("can_add_items")),
    config_repo: PlexConfigRepository = Depends(get_plex_config_repository),
    mapping_repo: PlexLibraryMappingRepository = Depends(get_plex_library_mapping_repository),
    subtype_repo: MediaSubtypeRepository = Depends(get_media_subtype_repository),
):
    config = await config_repo.require_enabled()

    if await mapping_repo.find_by_section_key(payload.section_key) is not None:
        raise HTTPException(status_code=409, detail="This library is already mapped")

    sections = await plex_service.list_sections(config.base_url, config.token)
    section = next((s for s in sections if s["key"] == payload.section_key), None)
    if section is None:
        raise HTTPException(status_code=404, detail="Plex library section not found")

    category = _SECTION_CATEGORY[section["type"]]
    default_subtype_id = await subtype_repo.find_by_name_in_category(
        category, Supertype.DIGITAL, _SECTION_SUBTYPE_NAME[section["type"]]
    )

    mapping = PlexLibraryMapping(
        section_key=section["key"],
        section_title=section["title"],
        section_type=section["type"],
        category=category,
        media_subtype_id=default_subtype_id,
    )
    mapping_repo.add(mapping)
    await mapping_repo.commit()
    await mapping_repo.refresh(mapping)
    return _to_mapping_response(mapping)


@router.delete("/mappings/{mapping_id}", status_code=204)
async def delete_mapping(
    mapping_id: int,
    _=Depends(require_permission("can_add_items")),
    repo: PlexLibraryMappingRepository = Depends(get_plex_library_mapping_repository),
):
    mapping = await repo.get_or_404(mapping_id)
    await repo.delete(mapping)
    await repo.commit()


@router.put("/mappings/{mapping_id}", response_model=PlexMappingResponse)
async def update_mapping(
    mapping_id: int,
    payload: PlexMappingUpdate,
    _=Depends(get_current_admin),
    mapping_repo: PlexLibraryMappingRepository = Depends(get_plex_library_mapping_repository),
    subtype_repo: MediaSubtypeRepository = Depends(get_media_subtype_repository),
):
    mapping = await mapping_repo.get_or_404(mapping_id)

    subtype = await subtype_repo.get(payload.media_subtype_id)
    if subtype is None:
        raise HTTPException(status_code=404, detail="Media subtype not found")
    if subtype.category != mapping.category or subtype.supertype != Supertype.DIGITAL:
        raise HTTPException(
            status_code=400,
            detail="Media subtype must be a Digital subtype in this library's category",
        )

    mapping.media_subtype_id = subtype.id
    await mapping_repo.commit()
    await mapping_repo.refresh(mapping)
    return _to_mapping_response(mapping)


def _to_sync_fields(item: dict, section_type: str) -> dict:
    """Map a normalized `services.plex.list_section_items` entry to the
    MediaItem fields it should populate, varying by section type."""
    fields = {
        "title": item["title"],
        "year": item.get("year"),
        "genres": ", ".join(item.get("genres") or []) or None,
        "description": item.get("summary"),
        "tmdb_id": item.get("tmdb_id"),
        "musicbrainz_id": item.get("musicbrainz_id"),
    }
    if section_type == "artist":
        fields["artist"] = item.get("artist_name")
        fields["label"] = item.get("studio")
        fields["track_count"] = item.get("leaf_count")
    else:
        fields["director"] = ", ".join(item.get("directors") or []) or None
        fields["cast_list"] = ", ".join(item.get("cast") or []) or None
        fields["studio"] = item.get("studio")
        fields["rating"] = item.get("content_rating")
        duration_ms = item.get("duration_ms")
        fields["runtime_minutes"] = duration_ms // 60000 if duration_ms else None
        if section_type == "show":
            child_count = item.get("child_count")
            fields["seasons_owned"] = str(child_count) if child_count else None
            fields["episode_count"] = item.get("leaf_count")
    return fields


async def _apply_cover(config: PlexConfig, item: MediaItem, thumb: Optional[str]) -> None:
    if not thumb:
        return
    data = await plex_service.fetch_thumbnail(config.base_url, config.token, thumb)
    if not data:
        return
    local_path = await optimise_and_save(data, item.id, "plex")
    if local_path:
        item.cover_image_path = local_path
        item.cover_image_url = None


async def _run_sync(mapping_id: int, job: PlexSyncJob) -> None:
    """Runs a full library sync in the background, updating `job` so
    `GET /mappings/{id}/sync/status` can report progress. Runs detached from
    the request that started it, so it opens its own session and re-loads
    everything it needs."""
    async with AsyncSessionLocal() as db:
        repo = MediaItemRepository(db)
        config_repo = PlexConfigRepository(db)
        mapping_repo = PlexLibraryMappingRepository(db)
        try:
            mapping = await mapping_repo.get(mapping_id)
            config = await config_repo.get_singleton()
            if mapping is None or config is None or not config.enabled:
                job.status = "error"
                job.error = "Plex integration is not configured or not enabled"
                return
            if mapping.media_subtype_id is None:
                job.status = "error"
                job.error = "No media type configured for this library — an admin must set one in Plex Sync settings"
                return

            section_key = mapping.section_key
            section_type = mapping.section_type

            plex_items = await plex_service.list_section_items(config.base_url, config.token, section_key, section_type)
            job.total = len(plex_items)

            seen_item_ids: set[int] = set()

            for raw_item in plex_items:
                if job.cancel_requested:
                    job.status = "cancelled"
                    break

                guid = raw_item.get("guid")
                if not guid or not raw_item.get("title"):
                    job.processed += 1
                    continue

                fields = _to_sync_fields(raw_item, section_type)
                sync_item = PlexSyncItem(guid=guid, cover_thumb=raw_item.get("thumb"), **fields)

                existing = await repo.find_plex_duplicate(
                    platform_id=config.platform_id,
                    media_subtype_id=mapping.media_subtype_id,
                    tmdb_id=sync_item.tmdb_id,
                    musicbrainz_id=sync_item.musicbrainz_id,
                    title=sync_item.title,
                    year=sync_item.year,
                )

                if existing is not None:
                    for field_name, value in fields.items():
                        setattr(existing, field_name, value)
                    await _apply_cover(config, existing, raw_item.get("thumb"))
                    candidates = await repo.find_link_candidates(
                        category=mapping.category,
                        platform_id=config.platform_id,
                        media_subtype_id=mapping.media_subtype_id,
                        tmdb_id=sync_item.tmdb_id,
                        musicbrainz_id=sync_item.musicbrainz_id,
                        title=sync_item.title,
                        year=sync_item.year,
                        exclude_id=existing.id,
                    )
                    await repo.link_unlinked(existing, candidates)
                    seen_item_ids.add(existing.id)
                    job.updated += 1
                    job.processed += 1
                    await db.commit()
                    continue

                candidates = await repo.find_link_candidates(
                    category=mapping.category,
                    platform_id=config.platform_id,
                    media_subtype_id=mapping.media_subtype_id,
                    tmdb_id=sync_item.tmdb_id,
                    musicbrainz_id=sync_item.musicbrainz_id,
                    title=sync_item.title,
                    year=sync_item.year,
                )
                item = MediaItem(
                    media_subtype_id=mapping.media_subtype_id,
                    platform_id=config.platform_id,
                    **fields,
                )
                db.add(item)
                await db.flush()
                await _apply_cover(config, item, raw_item.get("thumb"))
                await db.flush()
                await repo.link_unlinked(item, candidates)
                seen_item_ids.add(item.id)
                job.created += 1
                job.processed += 1
                await db.commit()

            if job.status == "cancelled":
                # seen_item_ids is incomplete, so stale-item detection would
                # incorrectly flag items the loop hasn't reached yet.
                job.stale_items = []
                return

            stale_items = await repo.list_by_platform_and_subtype(
                config.platform_id, mapping.media_subtype_id, exclude_ids=seen_item_ids
            )
            job.stale_items = await _build_responses(repo, stale_items) if stale_items else []

            mapping.last_synced_at = datetime.utcnow()
            await db.commit()
            job.status = "completed"
        except Exception as e:
            job.status = "error"
            job.error = str(e)


def _job_status(job: Optional[PlexSyncJob]) -> PlexSyncStatus:
    if job is None:
        return PlexSyncStatus(status="idle")
    result = None
    if job.status in ("completed", "cancelled"):
        result = PlexSyncResult(created=job.created, updated=job.updated, stale_items=job.stale_items)
    return PlexSyncStatus(
        status=job.status,
        total=job.total,
        processed=job.processed,
        created=job.created,
        updated=job.updated,
        error=job.error,
        result=result,
    )


# Keeps a strong reference to in-flight sync tasks so they aren't garbage
# collected mid-run — asyncio only weakly tracks tasks created this way.
_background_tasks: set[asyncio.Task] = set()


@router.post("/mappings/{mapping_id}/sync", response_model=PlexSyncStatus, status_code=202)
async def sync_mapping(
    mapping_id: int,
    _=Depends(require_permission("can_add_items")),
    mapping_repo: PlexLibraryMappingRepository = Depends(get_plex_library_mapping_repository),
    config_repo: PlexConfigRepository = Depends(get_plex_config_repository),
):
    mapping = await mapping_repo.get_or_404(mapping_id)
    await config_repo.require_enabled()
    if mapping.media_subtype_id is None:
        raise HTTPException(
            status_code=400,
            detail="No media type configured for this library — an admin must set one in Plex Sync settings",
        )

    existing_job = get_job(mapping_id)
    if existing_job is not None and existing_job.status == "running":
        raise HTTPException(status_code=409, detail="A sync is already running for this library")

    job = PlexSyncJob()
    set_job(mapping_id, job)
    task = asyncio.create_task(_run_sync(mapping_id, job))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return _job_status(job)


@router.get("/mappings/{mapping_id}/sync/status", response_model=PlexSyncStatus)
async def get_sync_status(
    mapping_id: int,
    _=Depends(require_permission("can_add_items")),
    repo: PlexLibraryMappingRepository = Depends(get_plex_library_mapping_repository),
):
    await repo.get_or_404(mapping_id)
    return _job_status(get_job(mapping_id))


@router.post("/mappings/{mapping_id}/sync/cancel", response_model=PlexSyncStatus)
async def cancel_sync(
    mapping_id: int,
    _=Depends(require_permission("can_add_items")),
    repo: PlexLibraryMappingRepository = Depends(get_plex_library_mapping_repository),
):
    await repo.get_or_404(mapping_id)
    job = get_job(mapping_id)
    if job is None or job.status != "running":
        raise HTTPException(status_code=409, detail="No sync is currently running for this library")
    job.cancel_requested = True
    return _job_status(job)


@router.post("/mappings/{mapping_id}/remove-stale")
async def remove_stale_items(
    mapping_id: int,
    payload: PlexRemoveStaleRequest,
    _=Depends(require_permission("can_add_items")),
    mapping_repo: PlexLibraryMappingRepository = Depends(get_plex_library_mapping_repository),
    config_repo: PlexConfigRepository = Depends(get_plex_config_repository),
    repo: MediaItemRepository = Depends(get_media_item_repository),
):
    mapping = await mapping_repo.get_or_404(mapping_id)
    config = await config_repo.require_enabled()

    removed = 0
    for item_id in payload.item_ids:
        item = await repo.get(item_id)
        if (
            item is None
            or item.platform_id != config.platform_id
            or item.media_subtype_id != mapping.media_subtype_id
        ):
            continue

        for link in await repo.links_for_item(item_id):
            await repo.delete_link(link)

        delete_cover_files(item.cover_image_path)
        await repo.delete(item)
        removed += 1

    await repo.commit()
    return {"removed": removed}
