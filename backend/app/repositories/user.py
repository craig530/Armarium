from typing import Optional, Sequence

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.user import User
from .base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def list_ordered(self) -> Sequence[User]:
        return (await self.db.execute(select(User).order_by(User.created_at))).scalars().all()

    async def get_by_username(self, username: str) -> Optional[User]:
        return (await self.db.execute(select(User).where(User.username == username))).scalar_one_or_none()

    async def count_admins(self) -> int:
        return (
            await self.db.execute(select(func.count(User.id)).where(User.is_admin.is_(True)))
        ).scalar_one()

    async def any_exist(self) -> bool:
        return (await self.db.execute(select(User.id).limit(1))).scalar_one_or_none() is not None


async def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)
