import shutil
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends

from ...config import settings, APP_VERSION
from ...database import AsyncSessionLocal
from ...services.default_locations import seed_default_locations
from ...services.default_platforms import seed_default_platforms
from ...services.media_subtypes import seed_default_media_subtypes
from ...services.auth import get_current_admin
from ...services.cover_art import download_cover
from ...repositories.location import LocationRepository, get_location_repository
from ...repositories.media_item import AUTO_LINK_FIELD, MediaItemRepository, get_media_item_repository
from ...repositories.media_subtype import MediaSubtypeRepository, get_media_subtype_repository
from ...repositories.platform import PlatformRepository, get_platform_repository
from ...repositories.plex import (
    PlexConfigRepository,
    PlexLibraryMappingRepository,
    get_plex_config_repository,
    get_plex_library_mapping_repository,
)
from ...repositories.scheduled_job import ScheduledJobRepository, get_scheduled_job_repository
from ...services.scheduler import scheduler_service

router = APIRouter()


@router.get("/system-info")
async def system_info(_=Depends(get_current_admin)):
    """Build/runtime info for the Admin panel's system info box."""
    database = "PostgreSQL" if settings.database_url.startswith("postgresql") else "SQLite"
    return {
        "version": APP_VERSION,
        "database": database,
        "cors_origins": settings.cors_origins,
        "configured_port": settings.port,
        "apis": {
            "tmdb": bool(settings.tmdb_api_key),
            "igdb": bool(settings.igdb_client_id and settings.igdb_client_secret),
            "upcdatabase": bool(settings.upcdatabase_api_key),
        },
    }


def _reset_dir(path: str) -> None:
    p = Path(path)
    if p.exists():
        shutil.rmtree(p)
    p.mkdir(parents=True, exist_ok=True)


@router.post("/reset-database")
async def reset_database(
    _=Depends(get_current_admin),
    media_repo: MediaItemRepository = Depends(get_media_item_repository),
    location_repo: LocationRepository = Depends(get_location_repository),
    subtype_repo: MediaSubtypeRepository = Depends(get_media_subtype_repository),
    platform_repo: PlatformRepository = Depends(get_platform_repository),
    plex_config_repo: PlexConfigRepository = Depends(get_plex_config_repository),
    plex_mapping_repo: PlexLibraryMappingRepository = Depends(get_plex_library_mapping_repository),
    schedule_repo: ScheduledJobRepository = Depends(get_scheduled_job_repository),
):
    """Wipe all catalogue data (media, locations, platforms, links) and cover
    image files, then reseed the default media subtypes, platforms, and
    locations. User accounts are left untouched.
    """
    # Plex config/mappings hold RESTRICT foreign keys into media_subtypes and
    # platforms (so a sync can't silently repoint mid-flight) - on Postgres
    # those block the deletes below unless cleared first, same as the
    # individual delete_mapping/delete_config endpoints do.
    for mapping in await plex_mapping_repo.list_all():
        sched = await schedule_repo.find_plex_schedule(mapping.id)
        if sched:
            scheduler_service.remove(sched.id)
            await schedule_repo.delete(sched)
        await plex_mapping_repo.delete(mapping)
    config = await plex_config_repo.get_singleton()
    if config is not None:
        await plex_config_repo.delete(config)

    await media_repo.delete_all()
    await location_repo.delete_all()
    await subtype_repo.delete_all()
    await platform_repo.delete_all()
    await media_repo.commit()

    _reset_dir(settings.covers_dir)
    _reset_dir(settings.location_icons_dir)
    _reset_dir(settings.platform_logos_dir)

    await seed_default_media_subtypes(media_repo.db)
    await seed_default_platforms(media_repo.db)
    await seed_default_locations(media_repo.db)

    return {"status": "ok"}


async def _redownload_covers(item_ids: list[int]) -> None:
    """Re-download and re-optimise covers for the given items.

    Runs as a background task with its own session, since the request's
    session is closed by the time this completes for any but the first item.
    """
    async with AsyncSessionLocal() as db:
        repo = MediaItemRepository(db)
        for item_id in item_ids:
            item = await repo.get(item_id)
            if item is None or not item.cover_image_url:
                continue
            local_path = await download_cover(item.cover_image_url, item_id, force=True)
            if local_path:
                item.cover_image_path = local_path
                await repo.commit()
            else:
                await db.rollback()


@router.post("/covers/redownload-all")
async def redownload_all_covers(
    background_tasks: BackgroundTasks,
    _=Depends(get_current_admin),
    repo: MediaItemRepository = Depends(get_media_item_repository),
):
    """Re-download and re-optimise every item's cover from its `cover_image_url`.

    Runs in the background so the request returns immediately. Admin only.
    """
    item_ids = await repo.ids_with_cover_url()

    background_tasks.add_task(_redownload_covers, list(item_ids))
    return {"queued": len(item_ids)}


@router.post("/auto-link")
async def auto_link_items(
    _=Depends(get_current_admin),
    repo: MediaItemRepository = Depends(get_media_item_repository),
):
    """Scan the whole library and link items that share an external id
    (tmdb_id / musicbrainz_id / isbn) but aren't linked yet — e.g. duplicate
    copies on other platforms or locations added before linking existed.
    Idempotent: rerunning links nothing further. Admin only.
    """
    items = await repo.list()

    linked = 0
    for item in items:
        subtype = item.media_subtype
        if subtype is None or subtype.category not in AUTO_LINK_FIELD:
            continue
        linked += await repo.auto_link_item(item, subtype)

    return {"linked": linked}


@router.post("/covers/purge-orphans")
async def purge_orphan_covers(
    _=Depends(get_current_admin),
    repo: MediaItemRepository = Depends(get_media_item_repository),
):
    """Delete cover image files on disk that no item references (admin only)."""
    covers_dir = Path(settings.covers_dir)
    if not covers_dir.exists():
        return {"deleted": 0}

    referenced: set[str] = set()
    for cover_image_path in await repo.cover_paths():
        rel = cover_image_path.removeprefix("/covers/")
        referenced.add(rel)
        p = Path(rel)
        referenced.add(str(p.with_name(f"{p.stem}_thumb{p.suffix}")))

    deleted = 0
    for file in covers_dir.rglob("*"):
        if not file.is_file():
            continue
        if str(file.relative_to(covers_dir)) not in referenced:
            file.unlink()
            deleted += 1

    return {"deleted": deleted}
