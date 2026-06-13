from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pathlib import Path
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from ...database import get_db
from ...models.enums import MediaCategory, Supertype
from ...models.item_link import ItemLink
from ...models.media import MediaItem
from ...models.media_subtype import MediaSubtype
from ...models.platform import Platform
from ...models.plex_config import PlexConfig
from ...models.plex_library_mapping import PlexLibraryMapping
from ...schemas.media import PlatformSummary
from ...schemas.plex import (
    PlexConflict,
    PlexConfigResponse,
    PlexConfigUpdate,
    PlexMappingCreate,
    PlexMappingResponse,
    PlexRemoveStaleRequest,
    PlexResolveRequest,
    PlexSectionResponse,
    PlexSyncItem,
    PlexSyncResult,
    PlexTestRequest,
)
from ...services import plex as plex_service
from ...services.auth import get_current_admin, require_permission
from ...services.cover_art import delete_cover_files, optimise_and_save
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

    mapping = PlexLibraryMapping(
        section_key=section["key"],
        section_title=section["title"],
        section_type=section["type"],
        category=_SECTION_CATEGORY[section["type"]],
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


async def _resolve_target_subtype(db: AsyncSession, mapping: PlexLibraryMapping) -> MediaSubtype:
    name = _SECTION_SUBTYPE_NAME[mapping.section_type]
    subtype = (
        await db.execute(
            select(MediaSubtype).where(
                MediaSubtype.category == mapping.category,
                MediaSubtype.supertype == Supertype.DIGITAL,
                MediaSubtype.name == name,
            )
        )
    ).scalar_one_or_none()
    if subtype is None:
        raise HTTPException(
            status_code=400,
            detail=f"Expected media type '{name}' not found — it may have been renamed or deleted",
        )
    return subtype


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


@router.post("/mappings/{mapping_id}/sync", response_model=PlexSyncResult)
async def sync_mapping(
    mapping_id: int,
    _=Depends(require_permission("can_add_items")),
    db: AsyncSession = Depends(get_db),
):
    mapping = await _get_mapping_or_404(db, mapping_id)
    config = await _require_plex_config(db)
    subtype = await _resolve_target_subtype(db, mapping)

    plex_items = await plex_service.list_section_items(config.base_url, config.token, mapping.section_key, mapping.section_type)

    created = 0
    updated = 0
    conflicts: list[PlexConflict] = []
    seen_source_ids: set[str] = set()

    for raw_item in plex_items:
        guid = raw_item.get("guid")
        if not guid or not raw_item.get("title"):
            continue

        source_id = f"{mapping.id}:{guid}"
        seen_source_ids.add(source_id)
        fields = _to_sync_fields(raw_item, mapping.section_type)
        sync_item = PlexSyncItem(guid=guid, cover_thumb=raw_item.get("thumb"), **fields)

        existing = (
            await db.execute(
                select(MediaItem).where(MediaItem.source == "plex", MediaItem.source_id == source_id)
            )
        ).scalar_one_or_none()

        if existing is not None:
            for field, value in fields.items():
                setattr(existing, field, value)
            await _apply_cover(db, config, existing, raw_item.get("thumb"))
            updated += 1
            continue

        matches = await _find_matches(db, mapping, sync_item)
        # A duplicate is when platform and item match — same identity, same
        # configured Plex platform. Anything else (a different digital
        # platform, or a physical copy) is a related copy to link, not a
        # conflict.
        duplicate = next((m for m in matches if m.platform_id == config.platform_id), None)
        if duplicate is not None:
            conflicts.append(PlexConflict(existing_item=await _build_response(db, duplicate), plex_item=sync_item))
            continue

        item = MediaItem(
            media_subtype_id=subtype.id,
            platform_id=config.platform_id,
            source="plex",
            source_id=source_id,
            **fields,
        )
        db.add(item)
        await db.flush()
        await _apply_cover(db, config, item, raw_item.get("thumb"))
        await db.flush()
        await _link_unlinked(db, item, matches)
        created += 1

    stale_items = (
        await db.execute(
            select(MediaItem).where(MediaItem.source == "plex", MediaItem.source_id.like(f"{mapping.id}:%"))
        )
    ).scalars().all()
    stale_items = [i for i in stale_items if i.source_id not in seen_source_ids]

    mapping.last_synced_at = datetime.utcnow()
    await db.commit()

    return PlexSyncResult(
        created=created,
        updated=updated,
        conflicts=conflicts,
        stale_items=await _build_responses(db, stale_items) if stale_items else [],
    )


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
    subtype = await _resolve_target_subtype(db, mapping)

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
        item.media_subtype_id = subtype.id
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
