from pathlib import Path
from typing import Optional, Sequence

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.location import Location
from ..models.media import MediaItem
from ..schemas.location import LocationResponse
from .base import BaseRepository


def location_icon_url(icon_path: Optional[str]) -> Optional[str]:
    return f"/location-icons/{Path(icon_path).name}" if icon_path else None


class LocationRepository(BaseRepository[Location]):
    model = Location

    async def flat_rows(self) -> Sequence:
        """Fetch every location as plain (id, name, parent_id, ...) rows.

        Avoids the ORM `Location.children`/`Location.parent` relationships —
        those are only eager-loaded to a fixed depth via selectinload(), and
        accessing them beyond that depth raises MissingGreenlet.
        """
        return (
            await self.db.execute(
                select(
                    Location.id, Location.name, Location.parent_id,
                    Location.icon_key, Location.icon_path, Location.sort_order,
                    Location.created_at, Location.updated_at,
                )
                .order_by(Location.sort_order, Location.name)
            )
        ).all()

    @staticmethod
    def build_tree(rows, count_map: dict):
        """Build LocationResponse trees from flat rows, returning (roots, by_id)."""
        by_parent = {}
        for row in rows:
            by_parent.setdefault(row.parent_id, []).append(row)

        by_id = {}

        def build(row) -> LocationResponse:
            node = LocationResponse(
                id=row.id,
                name=row.name,
                parent_id=row.parent_id,
                icon_key=row.icon_key,
                icon_url=location_icon_url(row.icon_path),
                sort_order=row.sort_order,
                created_at=row.created_at,
                updated_at=row.updated_at,
                item_count=count_map.get(row.id, 0),
                children=[build(c) for c in by_parent.get(row.id, [])],
            )
            by_id[row.id] = node
            return node

        roots = [build(r) for r in by_parent.get(None, [])]
        return roots, by_id

    async def item_count_map(self) -> dict:
        rows = await self.db.execute(
            select(MediaItem.location_id, func.count(MediaItem.id))
            .where(MediaItem.location_id.is_not(None))
            .group_by(MediaItem.location_id)
        )
        return {row[0]: row[1] for row in rows}

    async def has_children(self, loc_id: int) -> bool:
        child = (await self.db.execute(select(Location.id).where(Location.parent_id == loc_id))).scalars().first()
        return child is not None

    async def would_create_cycle(self, loc_id: int, new_parent_id: int) -> bool:
        """True if setting `loc_id`'s parent to `new_parent_id` would make
        `loc_id` its own ancestor (i.e. `new_parent_id` is `loc_id` itself or
        one of its descendants), which would recurse forever when building
        the location tree.

        `visited` also bounds the walk if a cycle already exists in the data
        for an unrelated branch.
        """
        ancestor_id = new_parent_id
        visited = set()
        while ancestor_id is not None and ancestor_id not in visited:
            if ancestor_id == loc_id:
                return True
            visited.add(ancestor_id)
            ancestor_id = (
                await self.db.execute(select(Location.parent_id).where(Location.id == ancestor_id))
            ).scalar_one_or_none()
        return False

    async def unlink_items(self, loc_id: int) -> None:
        items = (await self.db.execute(select(MediaItem).where(MediaItem.location_id == loc_id))).scalars().all()
        for item in items:
            item.location_id = None


async def get_location_repository(db: AsyncSession = Depends(get_db)) -> LocationRepository:
    return LocationRepository(db)
