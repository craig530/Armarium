from fastapi import Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.app_config import AppConfig
from .base import BaseRepository


class AppConfigRepository(BaseRepository[AppConfig]):
    model = AppConfig

    async def get_singleton(self) -> AppConfig:
        row = (await self.db.execute(select(AppConfig).where(AppConfig.id == 1))).scalar_one_or_none()
        if row is None:
            row = AppConfig(id=1, ownership_mode="shared")
            self.db.add(row)
            await self.db.flush()
        return row

    async def set_ownership_mode(self, mode: str) -> AppConfig:
        await self.db.execute(
            update(AppConfig).where(AppConfig.id == 1).values(ownership_mode=mode)
        )
        return await self.get_singleton()


async def get_app_config_repository(db: AsyncSession = Depends(get_db)) -> AppConfigRepository:
    return AppConfigRepository(db)
