import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pathlib import Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from ...database import AsyncSessionLocal, get_db
from ...models.enums import MediaCategory, Supertype
from ...models.item_link import ItemLink
from ...models.media import MediaItem
from ...models.media_subtype import MediaSubtype
from ...models.platform import Platform
from ...models.plex_config import PlexConfig
from ...models.plex_library_mapping import PlexLibraryMapping
from ...schemas.media import PlatformSummary
from ...schemas.plex import (
    MediaSubtypeSummary,
    PlexConflict,
    PlexConfigResponse,
    PlexConfigUpdate,
    PlexMappingCreate,
    PlexMappingResponse,
    PlexMappingUpdate,
    PlexRemoveStaleRequest,
    PlexResolveRequest,
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
from .media import _build_response, _build_responses, _link_unlinked

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


async def _get_config(db: AsyncSession) -> PlexConfig | None:
    return (await db.execute(select(PlexConfig))).scalars().first()


async def _require_plex_config(db: AsyncSession) -> PlexConfig:
    config = await _get_config(db)
    if config is None or not config.enabled:
        raise HTTPException(status_code=400, detail="Plex integration is not configured or not enabled")
    return config


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
async def get_config(_=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    config = await _get_config(db)
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
    db: AsyncSession = Depends(get_db),
):
    platform = (await db.execute(select(Platform).where(Platform.id == payload.platform_id))).scalar_one_or_none()
    if platform is None:
        raise HTTPException(status_code=404, detail="Platform not found")

    config = await _get_config(db)
    if config is None:
        if not payload.token:
            raise HTTPException(status_code=400, detail="Token is required for initial setup")
        config = PlexConfig(base_url=payload.base_url, token=payload.token, enabled=payload.enabled, platform_id=platform.id)
        db.add(config)
    else:
        config.base_url = payload.base_url
        config.enabled = payload.enabled
        config.platform_id = platform.id
        if payload.token:
            config.token = payload.token

    await db.commit()
    return PlexConfigResponse(configured=True, enabled=config.enabled, base_url=config.base_url, platform=_platform_summary(platform))


@router.delete("/config", status_code=204)
async def delete_config(_=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    config = await _get_config(db)
    if config is not None:
        await db.delete(config)
        await db.commit()


@router.post("/test")
async def test_connection(payload: PlexTestRequest, _=Depends(get_current_admin)):
    try:
        return await plex_service.test_connection(payload.base_url, payload.token)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not connect to Plex: {e}")


@router.get("/sections", response_model=List[PlexSectionResponse])
async def get_sections(
    _=Depends(require_permission("can_add_items")),
    db: AsyncSession = Depends(get_db),
):
    config = await _require_plex_config(db)
    sections = await plex_service.list_sections(config.base_url, config.token)

    mapped_keys = set(
        (await db.execute(select(PlexLibraryMapping.section_key))).scalars().all()
    )
    return [
        PlexSectionResponse(key=s["key"], title=s["title"], type=s["type"], mapped=s["key"] in mapped_keys)
        for s in sections
    ]


@router.get("/mappings", response_model=List[PlexMappingResponse])
async def list_mappings(
    _=Depends(require_permission("can_add_items")),
    db: AsyncSession = Depends(get_db),
):
    mappings = (await db.execute(select(PlexLibraryMapping))).scalars().all()
    return [_to_mapping_response(m) for m in mappings]


@router.post("/mappings", response_model=PlexMappingResponse, status_code=201)
async def create_mapping(
    payload: PlexMappingCreate,
    _=Depends(require_permission("can_add_items")),
    db: AsyncSession = Depends(get_db),
):
    config = await _require_plex_config(db)

    existing = (
        await db.execute(select(PlexLibraryMapping).where(PlexLibraryMapping.section_key == payload.section_key))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="This library is already mapped")

    sections = await plex_service.list_sections(config.base_url, config.token)
    section = next((s for s in sections if s["key"] == payload.section_key), None)
    if section is None:
        raise HTTPException(status_code=404, detail="Plex library section not found")

    category = _SECTION_CATEGORY[section["type"]]
    default_subtype = (
        await db.execute(
            select(MediaSubtype).where(
                MediaSubtype.category == category,
                MediaSubtype.supertype == Supertype.DIGITAL,
                MediaSubtype.name == _SECTION_SUBTYPE_NAME[section["type"]],
            )
        )
    ).scalar_one_or_none()

    mapping = PlexLibraryMapping(
        section_key=section["key"],
        section_title=section["title"],
        section_type=section["type"],
        category=category,
        media_subtype_id=default_subtype.id if default_subtype else None,
    )
    db.add(mapping)
    await db.commit()
    await db.refresh(mapping)
    return _to_mapping_response(mapping)


@router.delete("/mappings/{mapping_id}", status_code=204)
async def delete_mapping(
    mapping_id: int,
    _=Depends(require_permission("can_add_items")),
    db: AsyncSession = Depends(get_db),
):
    mapping = (await db.execute(select(PlexLibraryMapping).where(PlexLibraryMapping.id == mapping_id))).scalar_one_or_none()
    if mapping is None:
        raise HTTPException(status_code=404, detail="Mapping not found")

    await db.delete(mapping)
    await db.commit()


async def _get_mapping_or_404(db: AsyncSession, mapping_id: int) -> PlexLibraryMapping:
    mapping = (await db.execute(select(PlexLibraryMapping).where(PlexLibraryMapping.id == mapping_id))).scalar_one_or_none()
    if mapping is None:
        raise HTTPException(status_code=404, detail="Mapping not found")
    return mapping


@router.put("/mappings/{mapping_id}", response_model=PlexMappingResponse)
async def update_mapping(
    mapping_id: int,
    payload: PlexMappingUpdate,
    _=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    mapping = await _get_mapping_or_404(db, mapping_id)

    subtype = (
        await db.execute(select(MediaSubtype).where(MediaSubtype.id == payload.media_subtype_id))
    ).scalar_one_or_none()
    if subtype is None:
        raise HTTPException(status_code=404, detail="Media subtype not found")
    if subtype.category != mapping.category or subtype.supertype != Supertype.DIGITAL:
        raise HTTPException(
            status_code=400,
            detail="Media subtype must be a Digital subtype in this library's category",
        )

    mapping.media_subtype_id = subtype.id
    await db.commit()
    await db.refresh(mapping)
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


async def _find_matches(db: AsyncSession, mapping: PlexLibraryMapping, sync_item: PlexSyncItem) -> list[MediaItem]:
    """Look for existing, non-Plex-sourced items that look like the same
    title — matched by tmdb_id/musicbrainz_id when the Plex item has one,
    otherwise by case-insensitive title + year. Includes both digital
    (other-platform) and physical items — both are link candidates; the
    caller decides which (if any) is a same-platform duplicate."""
    stmt = (
        select(MediaItem)
        .join(MediaSubtype, MediaItem.media_subtype_id == MediaSubtype.id)
        .where(
            MediaSubtype.category == mapping.category,
            or_(MediaItem.source != "plex", MediaItem.source.is_(None)),
        )
    )
    if sync_item.tmdb_id is not None:
        stmt = stmt.where(MediaItem.tmdb_id == sync_item.tmdb_id)
    elif sync_item.musicbrainz_id is not None:
        stmt = stmt.where(MediaItem.musicbrainz_id == sync_item.musicbrainz_id)
    else:
        stmt = stmt.where(MediaItem.title.ilike(sync_item.title), MediaItem.year == sync_item.year)
    return (await db.execute(stmt)).scalars().all()


async def _apply_cover(db: AsyncSession, config: PlexConfig, item: MediaItem, thumb: Optional[str]) -> None:
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
        try:
            mapping = (
                await db.execute(select(PlexLibraryMapping).where(PlexLibraryMapping.id == mapping_id))
            ).scalar_one_or_none()
            config = await _get_config(db)
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
            media_subtype_id = mapping.media_subtype_id
            platform_id = config.platform_id

            plex_items = await plex_service.list_section_items(config.base_url, config.token, section_key, section_type)
            job.total = len(plex_items)

            conflicts: list[PlexConflict] = []
            seen_source_ids: set[str] = set()

            for raw_item in plex_items:
                if job.cancel_requested:
                    job.status = "cancelled"
                    break

                guid = raw_item.get("guid")
                if not guid or not raw_item.get("title"):
                    job.processed += 1
                    continue

                source_id = f"{mapping_id}:{guid}"
                seen_source_ids.add(source_id)
                fields = _to_sync_fields(raw_item, section_type)
                sync_item = PlexSyncItem(guid=guid, cover_thumb=raw_item.get("thumb"), **fields)

                existing = (
                    await db.execute(
                        select(MediaItem).where(MediaItem.source == "plex", MediaItem.source_id == source_id)
                    )
                ).scalar_one_or_none()

                if existing is not None:
                    for field_name, value in fields.items():
                        setattr(existing, field_name, value)
                    await _apply_cover(db, config, existing, raw_item.get("thumb"))
                    job.updated += 1
                    job.processed += 1
                    await db.commit()
                    continue

                matches = await _find_matches(db, mapping, sync_item)
                # A duplicate is when platform and item match — same identity, same
                # configured Plex platform. Anything else (a different digital
                # platform, or a physical copy) is a related copy to link, not a
                # conflict.
                duplicate = next((m for m in matches if m.platform_id == platform_id), None)
                if duplicate is not None:
                    conflicts.append(PlexConflict(existing_item=await _build_response(db, duplicate), plex_item=sync_item))
                    job.processed += 1
                    await db.commit()
                    continue

                item = MediaItem(
                    media_subtype_id=media_subtype_id,
                    platform_id=platform_id,
                    source="plex",
                    source_id=source_id,
                    **fields,
                )
                db.add(item)
                await db.flush()
                await _apply_cover(db, config, item, raw_item.get("thumb"))
                await db.flush()
                await _link_unlinked(db, item, matches)
                job.created += 1
                job.processed += 1
                await db.commit()

            job.conflicts = conflicts

            if job.status == "cancelled":
                # seen_source_ids is incomplete, so stale-item detection
                # would incorrectly flag items the loop hasn't reached yet.
                job.stale_items = []
                return

            stale_items = (
                await db.execute(
                    select(MediaItem).where(MediaItem.source == "plex", MediaItem.source_id.like(f"{mapping_id}:%"))
                )
            ).scalars().all()
            stale_items = [i for i in stale_items if i.source_id not in seen_source_ids]
            job.stale_items = await _build_responses(db, stale_items) if stale_items else []

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
        result = PlexSyncResult(created=job.created, updated=job.updated, conflicts=job.conflicts, stale_items=job.stale_items)
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
    db: AsyncSession = Depends(get_db),
):
    mapping = await _get_mapping_or_404(db, mapping_id)
    await _require_plex_config(db)
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
    db: AsyncSession = Depends(get_db),
):
    await _get_mapping_or_404(db, mapping_id)
    return _job_status(get_job(mapping_id))


@router.post("/mappings/{mapping_id}/sync/cancel", response_model=PlexSyncStatus)
async def cancel_sync(
    mapping_id: int,
    _=Depends(require_permission("can_add_items")),
    db: AsyncSession = Depends(get_db),
):
    await _get_mapping_or_404(db, mapping_id)
    job = get_job(mapping_id)
    if job is None or job.status != "running":
        raise HTTPException(status_code=409, detail="No sync is currently running for this library")
    job.cancel_requested = True
    return _job_status(job)


# Fields a `PlexSyncItem` carries over onto an adopted `MediaItem` when the
# user chooses "use_plex" for a conflict.
_SYNC_CONTENT_FIELDS = [
    "title", "year", "genres", "description", "director", "studio",
    "runtime_minutes", "rating", "cast_list", "seasons_owned", "episode_count",
    "artist", "label", "track_count", "tmdb_id", "musicbrainz_id",
]


@router.post("/mappings/{mapping_id}/resolve-conflicts")
async def resolve_conflicts(
    mapping_id: int,
    payload: PlexResolveRequest,
    _=Depends(require_permission("can_add_items")),
    db: AsyncSession = Depends(get_db),
):
    mapping = await _get_mapping_or_404(db, mapping_id)
    config = await _require_plex_config(db)
    if mapping.media_subtype_id is None:
        raise HTTPException(
            status_code=400,
            detail="No media type configured for this library — an admin must set one in Plex Sync settings",
        )

    resolved = 0
    for res in payload.resolutions:
        item = (
            await db.execute(select(MediaItem).where(MediaItem.id == res.existing_item_id))
        ).scalar_one_or_none()
        if item is None:
            raise HTTPException(status_code=404, detail=f"Item {res.existing_item_id} not found")

        # Adopt the existing item: tag it as Plex-sourced so it stops
        # re-appearing as a conflict and becomes eligible for stale-detection.
        item.source = "plex"
        item.source_id = f"{mapping.id}:{res.plex_item.guid}"
        item.media_subtype_id = mapping.media_subtype_id
        item.platform_id = config.platform_id

        if res.resolution == "use_plex":
            for field in _SYNC_CONTENT_FIELDS:
                setattr(item, field, getattr(res.plex_item, field))
            await _apply_cover(db, config, item, res.plex_item.cover_thumb)

        # The user may also own this item on other digital platforms or
        # physically — link those copies to the now-adopted Plex item.
        await db.flush()
        matches = await _find_matches(db, mapping, res.plex_item)
        await _link_unlinked(db, item, [m for m in matches if m.platform_id != config.platform_id])

        resolved += 1

    await db.commit()
    return {"resolved": resolved}


@router.post("/mappings/{mapping_id}/remove-stale")
async def remove_stale_items(
    mapping_id: int,
    payload: PlexRemoveStaleRequest,
    _=Depends(require_permission("can_add_items")),
    db: AsyncSession = Depends(get_db),
):
    mapping = await _get_mapping_or_404(db, mapping_id)
    prefix = f"{mapping.id}:"

    removed = 0
    for item_id in payload.item_ids:
        item = (await db.execute(select(MediaItem).where(MediaItem.id == item_id))).scalar_one_or_none()
        if item is None or item.source != "plex" or not (item.source_id or "").startswith(prefix):
            continue

        links = (
            await db.execute(
                select(ItemLink).where(or_(ItemLink.item_a_id == item_id, ItemLink.item_b_id == item_id))
            )
        ).scalars().all()
        for link in links:
            await db.delete(link)

        delete_cover_files(item.cover_image_path)
        await db.delete(item)
        removed += 1

    await db.commit()
    return {"removed": removed}
