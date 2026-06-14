from typing import Optional, Sequence

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.plex_config import PlexConfig
from ..models.plex_library_mapping import PlexLibraryMapping
from .base import BaseRepository


class PlexConfigRepository(BaseRepository[PlexConfig]):
    model = PlexConfig

    async def get_singleton(self) -> Optional[PlexConfig]:
        return (await self.db.execute(select(PlexConfig))).scalars().first()

    async def require_enabled(self) -> PlexConfig:
        config = await self.get_singleton()
        if config is None or not config.enabled:
            raise HTTPException(status_code=400, detail="Plex integration is not configured or not enabled")
        return config

    async def upsert(self, *, base_url: str, token: Optional[str], enabled: bool, platform_id: int) -> PlexConfig:
        config = await self.get_singleton()
        if config is None:
            if not token:
                raise HTTPException(status_code=400, detail="Token is required for initial setup")
            config = PlexConfig(base_url=base_url, token=token, enabled=enabled, platform_id=platform_id)
            self.add(config)
        else:
            config.base_url = base_url
            config.enabled = enabled
            config.platform_id = platform_id
            if token:
                config.token = token
        return config

    async def delete_singleton(self) -> None:
        config = await self.get_singleton()
        if config is not None:
            await self.delete(config)
            await self.commit()


class PlexLibraryMappingRepository(BaseRepository[PlexLibraryMapping]):
    model = PlexLibraryMapping

    async def list_all(self) -> Sequence[PlexLibraryMapping]:
        return (await self.db.execute(select(PlexLibraryMapping))).scalars().all()

    async def mapped_section_keys(self) -> set:
        return set((await self.db.execute(select(PlexLibraryMapping.section_key))).scalars().all())

    async def find_by_section_key(self, section_key: str) -> Optional[PlexLibraryMapping]:
        return (
            await self.db.execute(
                select(PlexLibraryMapping).where(PlexLibraryMapping.section_key == section_key)
            )
        ).scalar_one_or_none()

    async def get_or_404(self, mapping_id: int) -> PlexLibraryMapping:
        mapping = await self.get(mapping_id)
        if mapping is None:
            raise HTTPException(status_code=404, detail="Mapping not found")
        return mapping


async def get_plex_config_repository(db: AsyncSession = Depends(get_db)) -> PlexConfigRepository:
    return PlexConfigRepository(db)


async def get_plex_library_mapping_repository(db: AsyncSession = Depends(get_db)) -> PlexLibraryMappingRepository:
    return PlexLibraryMappingRepository(db)
