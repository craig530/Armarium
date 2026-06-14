from typing import Optional, Sequence

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.enums import MediaCategory, Supertype
from ..models.media import MediaItem
from ..models.media_subtype import MediaSubtype
from ..models.plex_library_mapping import PlexLibraryMapping
from .base import BaseRepository


class MediaSubtypeRepository(BaseRepository[MediaSubtype]):
    model = MediaSubtype

    async def list_ordered(self) -> Sequence[MediaSubtype]:
        return (
            await self.db.execute(
                select(MediaSubtype).order_by(
                    MediaSubtype.category, MediaSubtype.supertype, MediaSubtype.sort_order, MediaSubtype.name
                )
            )
        ).scalars().all()

    async def item_count_map(self) -> dict:
        rows = await self.db.execute(
            select(MediaItem.media_subtype_id, func.count(MediaItem.id))
            .where(MediaItem.media_subtype_id.is_not(None))
            .group_by(MediaItem.media_subtype_id)
        )
        return {row[0]: row[1] for row in rows}

    async def item_count(self, subtype_id: int) -> int:
        return (
            await self.db.execute(
                select(func.count(MediaItem.id)).where(MediaItem.media_subtype_id == subtype_id)
            )
        ).scalar_one()

    async def locked_map(self) -> dict:
        """Media subtypes referenced by a Plex library mapping — locked
        (undeletable) until the admin repoints or removes that mapping."""
        rows = await self.db.execute(
            select(PlexLibraryMapping.media_subtype_id, PlexLibraryMapping.section_title)
            .where(PlexLibraryMapping.media_subtype_id.is_not(None))
        )
        return {
            subtype_id: f'Used by Plex sync library "{section_title}"'
            for subtype_id, section_title in rows
        }

    async def find_by_name_in_category(
        self, category: MediaCategory, supertype: Supertype, name: str, exclude_id: Optional[int] = None
    ) -> Optional[int]:
        stmt = select(MediaSubtype.id).where(
            MediaSubtype.category == category,
            MediaSubtype.supertype == supertype,
            MediaSubtype.name == name,
        )
        if exclude_id is not None:
            stmt = stmt.where(MediaSubtype.id != exclude_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()


async def get_media_subtype_repository(db: AsyncSession = Depends(get_db)) -> MediaSubtypeRepository:
    return MediaSubtypeRepository(db)
