import shutil
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ...database import get_db, AsyncSessionLocal
from ...migrations import seed_media_subtypes
from ...models.item_link import ItemLink
from ...models.location import Location
from ...models.media import MediaItem
from ...models.media_subtype import MediaSubtype
from ...models.platform import Platform
from ...services.auth import get_current_admin
from ...services.cover_art import download_cover

router = APIRouter()


def _reset_dir(path: str) -> None:
    p = Path(path)
    if p.exists():
        shutil.rmtree(p)
    p.mkdir(parents=True, exist_ok=True)


@router.post("/reset-database")
async def reset_database(
    _=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Wipe all catalogue data (media, locations, platforms, links) and cover
    image files, then reseed the default media subtypes. User accounts are
    left untouched.
    """
    await db.execute(delete(ItemLink))
    await db.execute(delete(MediaItem))
    await db.execute(delete(Location))
    await db.execute(delete(MediaSubtype))
    await db.execute(delete(Platform))
    await db.commit()

    _reset_dir(settings.covers_dir)
    _reset_dir(settings.location_icons_dir)
    _reset_dir(settings.platform_logos_dir)

    await seed_media_subtypes(db)

    return {"status": "ok"}


async def _redownload_covers(item_ids: list[int]) -> None:
    """Re-download and re-optimise covers for the given items.

    Runs as a background task with its own session, since the request's
    session is closed by the time this completes for any but the first item.
    """
    async with AsyncSessionLocal() as db:
        for item_id in item_ids:
            item = (await db.execute(select(MediaItem).where(MediaItem.id == item_id))).scalar_one_or_none()
            if item is None or not item.cover_image_url:
                continue
            local_path = await download_cover(item.cover_image_url, item_id, force=True)
            if local_path:
                item.cover_image_path = local_path
                await db.commit()
            else:
                await db.rollback()


@router.post("/covers/redownload-all")
async def redownload_all_covers(
    background_tasks: BackgroundTasks,
    _=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Re-download and re-optimise every item's cover from its `cover_image_url`.

    Runs in the background so the request returns immediately. Admin only.
    """
    item_ids = (
        await db.execute(select(MediaItem.id).where(MediaItem.cover_image_url.isnot(None)))
    ).scalars().all()

    background_tasks.add_task(_redownload_covers, list(item_ids))
    return {"queued": len(item_ids)}


@router.post("/covers/purge-orphans")
async def purge_orphan_covers(
    _=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete cover image files on disk that no item references (admin only)."""
    covers_dir = Path(settings.covers_dir)
    if not covers_dir.exists():
        return {"deleted": 0}

    referenced: set[str] = set()
    paths = (
        await db.execute(select(MediaItem.cover_image_path).where(MediaItem.cover_image_path.isnot(None)))
    ).scalars().all()
    for cover_image_path in paths:
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
