from typing import Optional, Sequence

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.media import MediaItem
from ..models.platform import Platform
from ..models.plex_config import PlexConfig
from .base import BaseRepository


class PlatformRepository(BaseRepository[Platform]):
    model = Platform

    async def list_ordered(self) -> Sequence[Platform]:
        return (await self.db.execute(select(Platform).order_by(Platform.name))).scalars().all()

    async def item_count_map(self) -> dict:
        rows = await self.db.execute(
            select(MediaItem.platform_id, func.count(MediaItem.id))
            .where(MediaItem.platform_id.is_not(None))
            .group_by(MediaItem.platform_id)
        )
        return {row[0]: row[1] for row in rows}

    async def item_count(self, platform_id: int) -> int:
        return (
            await self.db.execute(
                select(func.count(MediaItem.id)).where(MediaItem.platform_id == platform_id)
            )
        ).scalar_one()

    async def locked_map(self) -> dict:
        """The platform configured for Plex sync — locked (undeletable) until
        the admin reconfigures or removes the Plex integration."""
        platform_id = (await self.db.execute(select(PlexConfig.platform_id))).scalars().first()
        if platform_id is None:
            return {}
        return {platform_id: "Configured as the Plex sync platform"}

    async def find_by_name(self, name: str, exclude_id: Optional[int] = None) -> Optional[int]:
        stmt = select(Platform.id).where(Platform.name == name)
        if exclude_id is not None:
            stmt = stmt.where(Platform.id != exclude_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()


async def get_platform_repository(db: AsyncSession = Depends(get_db)) -> PlatformRepository:
    return PlatformRepository(db)
