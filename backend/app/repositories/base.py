from typing import Generic, Optional, Sequence, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    """Common CRUD operations shared by all per-model repositories.

    Subclasses set `model` to their ORM class and add model-specific query
    methods on top of these primitives.
    """

    model: type[ModelT]

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, id: int) -> Optional[ModelT]:
        return (await self.db.execute(select(self.model).where(self.model.id == id))).scalar_one_or_none()

    async def list(self, *order_by) -> Sequence[ModelT]:
        stmt = select(self.model)
        if order_by:
            stmt = stmt.order_by(*order_by)
        return (await self.db.execute(stmt)).scalars().all()

    def add(self, obj: ModelT) -> ModelT:
        self.db.add(obj)
        return obj

    async def delete(self, obj: ModelT) -> None:
        await self.db.delete(obj)

    async def commit(self) -> None:
        await self.db.commit()

    async def refresh(self, obj: ModelT) -> None:
        await self.db.refresh(obj)
