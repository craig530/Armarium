import shutil
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ...database import get_db
from ...migrations import seed_media_subtypes
from ...models.item_link import ItemLink
from ...models.location import Location
from ...models.media import MediaItem
from ...models.media_subtype import MediaSubtype
from ...models.platform import Platform
from ...services.auth import get_current_admin

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
