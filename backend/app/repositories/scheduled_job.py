from typing import List, Optional

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.scheduled_job import ScheduledJob, PLEX_JOB_TYPE


class ScheduledJobRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_all(self) -> List[ScheduledJob]:
        result = await self.db.execute(select(ScheduledJob).order_by(ScheduledJob.id))
        return list(result.scalars().all())

    async def get(self, job_id: int) -> Optional[ScheduledJob]:
        return await self.db.get(ScheduledJob, job_id)

    async def find_by_type(self, job_type: str) -> Optional[ScheduledJob]:
        """Return the singleton admin job of a given type (no target_id)."""
        result = await self.db.execute(
            select(ScheduledJob).where(
                ScheduledJob.job_type == job_type,
                ScheduledJob.target_id.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def find_plex_schedule(self, mapping_id: int) -> Optional[ScheduledJob]:
        result = await self.db.execute(
            select(ScheduledJob).where(
                ScheduledJob.job_type == PLEX_JOB_TYPE,
                ScheduledJob.target_id == mapping_id,
            )
        )
        return result.scalar_one_or_none()

    def add(self, job: ScheduledJob) -> None:
        self.db.add(job)

    async def delete(self, job: ScheduledJob) -> None:
        await self.db.delete(job)

    async def commit(self) -> None:
        await self.db.commit()

    async def refresh(self, job: ScheduledJob) -> None:
        await self.db.refresh(job)


def get_scheduled_job_repository(db: AsyncSession = Depends(get_db)) -> ScheduledJobRepository:
    return ScheduledJobRepository(db)
