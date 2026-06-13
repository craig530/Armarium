from fastapi import APIRouter, Depends, HTTPException
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from ...database import get_db
from ...models.enums import MediaCategory
from ...models.platform import Platform
from ...models.plex_config import PlexConfig
from ...models.plex_library_mapping import PlexLibraryMapping
from ...schemas.media import PlatformSummary
from ...schemas.plex import (
    PlexConfigResponse,
    PlexConfigUpdate,
    PlexMappingCreate,
    PlexMappingResponse,
    PlexSectionResponse,
    PlexTestRequest,
)
from ...services import plex as plex_service
from ...services.auth import get_current_admin, require_permission

router = APIRouter()

# Plex section `type` -> our category. Movie and show libraries both map to
# Films & TV; artist (music) libraries map to Music. Plex has no native book
# library type, so books are out of scope.
_SECTION_CATEGORY = {
    "movie": MediaCategory.FILMS_TV,
    "show": MediaCategory.FILMS_TV,
    "artist": MediaCategory.MUSIC,
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


def _to_mapping_response(mapping: PlexLibraryMapping, platform: Platform | None = None) -> PlexMappingResponse:
    return PlexMappingResponse(
        id=mapping.id,
        section_key=mapping.section_key,
        section_title=mapping.section_title,
        section_type=mapping.section_type,
        category=mapping.category,
        platform=_platform_summary(platform or mapping.platform),
        last_synced_at=mapping.last_synced_at,
    )


@router.get("/config", response_model=PlexConfigResponse)
async def get_config(_=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    config = await _get_config(db)
    if config is None:
        return PlexConfigResponse(configured=False, enabled=False, base_url=None)
    return PlexConfigResponse(configured=True, enabled=config.enabled, base_url=config.base_url)


@router.put("/config", response_model=PlexConfigResponse)
async def update_config(
    payload: PlexConfigUpdate,
    _=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    config = await _get_config(db)
    if config is None:
        if not payload.token:
            raise HTTPException(status_code=400, detail="Token is required for initial setup")
        config = PlexConfig(base_url=payload.base_url, token=payload.token, enabled=payload.enabled)
        db.add(config)
    else:
        config.base_url = payload.base_url
        config.enabled = payload.enabled
        if payload.token:
            config.token = payload.token

    await db.commit()
    return PlexConfigResponse(configured=True, enabled=config.enabled, base_url=config.base_url)


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


async def _get_or_create_plex_platform(db: AsyncSession) -> Platform:
    platform = (await db.execute(select(Platform).where(Platform.name == "Plex"))).scalar_one_or_none()
    if platform is None:
        platform = Platform(name="Plex", logo_key="plex")
        db.add(platform)
        await db.flush()
    return platform


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

    if payload.platform_id is not None:
        platform = (await db.execute(select(Platform).where(Platform.id == payload.platform_id))).scalar_one_or_none()
        if platform is None:
            raise HTTPException(status_code=404, detail="Platform not found")
    else:
        platform = await _get_or_create_plex_platform(db)

    mapping = PlexLibraryMapping(
        section_key=section["key"],
        section_title=section["title"],
        section_type=section["type"],
        category=_SECTION_CATEGORY[section["type"]],
        platform_id=platform.id,
    )
    db.add(mapping)
    await db.commit()
    await db.refresh(mapping)
    return _to_mapping_response(mapping, platform)


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
