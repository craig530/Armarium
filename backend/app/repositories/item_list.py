from typing import Optional, Sequence

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.enums import MediaCategory
from ..models.item_list import ItemList, media_item_lists
from .base import BaseRepository


class ItemListRepository(BaseRepository[ItemList]):
    model = ItemList

    async def list_ordered(self) -> Sequence[ItemList]:
        return (await self.db.execute(select(ItemList).order_by(ItemList.category, ItemList.name))).scalars().all()

    async def item_count_map(self) -> dict:
        rows = await self.db.execute(
            select(media_item_lists.c.item_list_id, func.count(media_item_lists.c.media_item_id))
            .group_by(media_item_lists.c.item_list_id)
        )
        return {row[0]: row[1] for row in rows}

    async def find_by_name(
        self,
        category: MediaCategory,
        name: str,
        owner_id: Optional[int] = None,
        exclude_id: Optional[int] = None,
    ) -> Optional[int]:
        stmt = select(ItemList.id).where(ItemList.category == category, ItemList.name == name)
        if owner_id is not None:
            stmt = stmt.where(ItemList.owner_id == owner_id)
        else:
            stmt = stmt.where(ItemList.owner_id.is_(None))
        if exclude_id is not None:
            stmt = stmt.where(ItemList.id != exclude_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()


async def get_item_list_repository(db: AsyncSession = Depends(get_db)) -> ItemListRepository:
    return ItemListRepository(db)
