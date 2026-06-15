from pathlib import Path
from typing import Optional, Sequence

from fastapi import Depends, HTTPException
from sqlalchemy import and_, column, delete, func, or_, select, table, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models.enums import LinkMatchType, MediaCategory, Supertype
from ..models.item_link import ItemLink
from ..models.location import Location
from ..models.media import MediaItem
from ..models.media_subtype import MediaSubtype
from ..models.platform import Platform
from ..services import search as search_service
from .base import BaseRepository

# Category -> external-id field used to auto-match a physical/digital pair.
AUTO_LINK_FIELD = {
    MediaCategory.FILMS_TV: "tmdb_id",
    MediaCategory.MUSIC: "musicbrainz_id",
    MediaCategory.BOOKS: "isbn",
}


def _editions_compatible(a: Optional[str], b: Optional[str]) -> bool:
    """Whether two items' `edition` fields conflict. Either side being blank
    means "no information", so it's treated as compatible — this only
    suppresses a title/year match when both sides explicitly disagree (e.g.
    "Remastered" vs "Anniversary Edition")."""
    if not a or not b:
        return True
    return a.strip().lower() == b.strip().lower()


class MediaItemRepository(BaseRepository[MediaItem]):
    model = MediaItem

    # ---- Fetching ----

    async def get_with_location(self, item_id: int) -> Optional[MediaItem]:
        stmt = select(MediaItem).where(MediaItem.id == item_id).options(selectinload(MediaItem.location))
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_by_ids(self, ids) -> Sequence[MediaItem]:
        return (await self.db.execute(select(MediaItem).where(MediaItem.id.in_(ids)))).scalars().all()

    async def reload(self, item_id: int) -> MediaItem:
        """Re-fetch an item with its relationships freshly loaded.

        `populate_existing` is required: with `expire_on_commit=False`, an
        item already in the session's identity map keeps its stale
        relationship values from before this request's edits unless we force
        a re-population.
        """
        stmt = (
            select(MediaItem)
            .where(MediaItem.id == item_id)
            .options(
                selectinload(MediaItem.location),
                selectinload(MediaItem.media_subtype),
                selectinload(MediaItem.platform),
            )
            .execution_options(populate_existing=True)
        )
        return (await self.db.execute(stmt)).scalar_one()

    async def ids_exist(self, ids) -> set:
        rows = (await self.db.execute(select(MediaItem.id).where(MediaItem.id.in_(ids)))).scalars().all()
        return set(rows)

    async def ids_with_cover_url(self) -> Sequence[int]:
        return (
            await self.db.execute(select(MediaItem.id).where(MediaItem.cover_image_url.isnot(None)))
        ).scalars().all()

    async def cover_paths(self) -> Sequence[str]:
        return (
            await self.db.execute(
                select(MediaItem.cover_image_path).where(MediaItem.cover_image_path.isnot(None))
            )
        ).scalars().all()

    async def set_cover_path(self, item_id: int, cover_image_path: str) -> None:
        await self.db.execute(
            update(MediaItem).where(MediaItem.id == item_id).values(cover_image_path=cover_image_path)
        )

    # ---- Listing / search ----

    async def search(
        self,
        *,
        q: Optional[str] = None,
        category: Optional[MediaCategory] = None,
        supertype: Optional[Supertype] = None,
        media_subtype_id: Optional[int] = None,
        platform_id: Optional[int] = None,
        genre: Optional[str] = None,
        year: Optional[int] = None,
        location_ids: Optional[set[int]] = None,
        sort: str = "created_at",
        order: str = "desc",
        page: int = 1,
        per_page: int = 24,
    ) -> tuple[Sequence[MediaItem], int]:
        stmt = select(MediaItem)

        filters = []
        if q:
            fts_query = search_service.build_match_query(q) if search_service.FTS5_ENABLED else None
            if fts_query:
                fts_table = table("media_items_fts", column("rowid"))
                match_clause = text("media_items_fts MATCH :fts_q").bindparams(fts_q=fts_query)
                filters.append(MediaItem.id.in_(select(fts_table.c.rowid).where(match_clause)))
            else:
                term = f"%{q}%"
                filters.append(
                    or_(
                        MediaItem.title.ilike(term),
                        MediaItem.artist.ilike(term),
                        MediaItem.author.ilike(term),
                        MediaItem.director.ilike(term),
                        MediaItem.genres.ilike(term),
                        MediaItem.description.ilike(term),
                        MediaItem.studio.ilike(term),
                        MediaItem.label.ilike(term),
                        MediaItem.publisher.ilike(term),
                        MediaItem.cast_list.ilike(term),
                        MediaItem.isbn.ilike(term),
                        MediaItem.barcode.ilike(term),
                        MediaItem.edition.ilike(term),
                        MediaItem.notes.ilike(term),
                        MediaItem.rating.ilike(term),
                    )
                )
        if genre:
            filters.append(MediaItem.genres.ilike(f"%{genre}%"))
        if year:
            filters.append(MediaItem.year == year)
        if location_ids:
            filters.append(MediaItem.location_id.in_(location_ids))
        if media_subtype_id:
            filters.append(MediaItem.media_subtype_id == media_subtype_id)
        if platform_id:
            filters.append(MediaItem.platform_id == platform_id)

        if category is not None or supertype is not None:
            stmt = stmt.join(MediaSubtype, MediaItem.media_subtype_id == MediaSubtype.id)
            if category is not None:
                filters.append(MediaSubtype.category == category)
            if supertype is not None:
                filters.append(MediaSubtype.supertype == supertype)

        if filters:
            stmt = stmt.where(and_(*filters))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one()

        sort_col = getattr(MediaItem, sort)
        stmt = stmt.order_by(sort_col.desc() if order == "desc" else sort_col.asc())
        stmt = stmt.offset((page - 1) * per_page).limit(per_page)
        stmt = stmt.options(selectinload(MediaItem.location))

        items = (await self.db.execute(stmt)).scalars().all()
        return items, total

    async def recent(self, limit: int = 6) -> Sequence[MediaItem]:
        stmt = (
            select(MediaItem)
            .options(selectinload(MediaItem.location))
            .order_by(MediaItem.created_at.desc())
            .limit(limit)
        )
        return (await self.db.execute(stmt)).scalars().all()

    # ---- Response-shaping lookup maps ----

    async def location_maps(self) -> tuple[dict, dict]:
        """Build a `({location_id: "A → B → C"}, {location_id: {icon_key, icon_url}})`
        pair from a single flat (id, name, parent_id, icon_key, icon_path) query.

        Built from a flat query rather than by walking the ORM `Location.parent`
        relationship — that relationship isn't eagerly loaded alongside
        `MediaItem.location`, and accessing it lazily outside an AsyncSession call
        raises MissingGreenlet.
        """
        rows = (
            await self.db.execute(
                select(Location.id, Location.name, Location.parent_id, Location.icon_key, Location.icon_path)
            )
        ).all()
        by_id = {row.id: (row.name, row.parent_id) for row in rows}
        icon_map = {
            row.id: {
                "icon_key": row.icon_key,
                "icon_url": f"/location-icons/{Path(row.icon_path).name}" if row.icon_path else None,
            }
            for row in rows
        }

        paths: dict = {}

        def build(loc_id: int, visited: frozenset) -> str:
            if loc_id in paths:
                return paths[loc_id]
            name, parent_id = by_id[loc_id]
            if parent_id is None or parent_id not in by_id or parent_id in visited:
                path = name
            else:
                path = f"{build(parent_id, visited | {loc_id})} → {name}"
            paths[loc_id] = path
            return path

        for loc_id in by_id:
            build(loc_id, frozenset())
        return paths, icon_map

    async def subtype_map(self) -> dict:
        rows = (await self.db.execute(select(MediaSubtype))).scalars().all()
        return {
            s.id: {"id": s.id, "name": s.name, "category": s.category, "supertype": s.supertype}
            for s in rows
        }

    async def platform_map(self) -> dict:
        rows = (await self.db.execute(select(Platform))).scalars().all()
        return {
            p.id: {
                "id": p.id,
                "name": p.name,
                "logo_key": p.logo_key,
                "logo_url": f"/platform-logos/{Path(p.logo_path).name}" if p.logo_path else None,
            }
            for p in rows
        }

    async def link_map(self, item_ids: list) -> dict:
        """{item_id: [connected_item_ids...]} via connected components over `ItemLink`.

        An item can be linked to several others (e.g. a physical disc plus
        digital copies on multiple platforms), so this walks the link graph
        outward from `item_ids` until no new nodes are discovered, then returns
        each requested item's full connected component (excluding itself).
        """
        if not item_ids:
            return {}

        adjacency: dict = {}
        seen_nodes = set(item_ids)
        frontier = set(item_ids)

        while frontier:
            links = (
                await self.db.execute(
                    select(ItemLink).where(
                        or_(ItemLink.item_a_id.in_(frontier), ItemLink.item_b_id.in_(frontier))
                    )
                )
            ).scalars().all()

            new_nodes = set()
            for link in links:
                a, b = link.item_a_id, link.item_b_id
                adjacency.setdefault(a, set()).add(b)
                adjacency.setdefault(b, set()).add(a)
                for node in (a, b):
                    if node not in seen_nodes:
                        new_nodes.add(node)

            seen_nodes |= new_nodes
            frontier = new_nodes

        result: dict = {}
        for item_id in item_ids:
            if item_id not in adjacency:
                continue
            visited = {item_id}
            queue = [item_id]
            while queue:
                current = queue.pop(0)
                for neighbor in adjacency.get(current, ()):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
            visited.discard(item_id)
            if visited:
                result[item_id] = sorted(visited)
        return result

    # ---- Validation (raise on not-found) ----

    async def resolve_subtype(self, media_subtype_id: int) -> MediaSubtype:
        subtype = (
            await self.db.execute(select(MediaSubtype).where(MediaSubtype.id == media_subtype_id))
        ).scalar_one_or_none()
        if not subtype:
            raise HTTPException(status_code=404, detail="Media subtype not found")
        return subtype

    async def check_location_exists(self, location_id: Optional[int]) -> None:
        if location_id is None:
            return
        location = (await self.db.execute(select(Location).where(Location.id == location_id))).scalar_one_or_none()
        if not location:
            raise HTTPException(status_code=404, detail="Location not found")

    async def check_platform_exists(self, platform_id: Optional[int]) -> None:
        if platform_id is None:
            return
        platform = (await self.db.execute(select(Platform).where(Platform.id == platform_id))).scalar_one_or_none()
        if not platform:
            raise HTTPException(status_code=404, detail="Platform not found")

    # ---- Stats ----

    async def count_total(self) -> int:
        return (await self.db.execute(select(func.count(MediaItem.id)))).scalar_one()

    async def count_by_barcode_or_isbn(self, values: set) -> int:
        """Count items already catalogued under any of the given
        barcode/ISBN values (used to flag library duplicates in lookup
        results)."""
        stmt = select(func.count(MediaItem.id)).where(
            or_(MediaItem.barcode.in_(values), MediaItem.isbn.in_(values))
        )
        return (await self.db.execute(stmt)).scalar_one()

    async def count_by_subtype(self) -> dict:
        rows = await self.db.execute(
            select(MediaSubtype.name, func.count(MediaItem.id))
            .join(MediaItem, MediaItem.media_subtype_id == MediaSubtype.id)
            .group_by(MediaSubtype.name)
        )
        return {row[0]: row[1] for row in rows}

    async def count_by_category(self) -> dict:
        rows = await self.db.execute(
            select(MediaSubtype.category, func.count(MediaItem.id))
            .join(MediaItem, MediaItem.media_subtype_id == MediaSubtype.id)
            .group_by(MediaSubtype.category)
        )
        return {row[0].value: row[1] for row in rows}

    async def count_by_supertype(self) -> dict:
        rows = await self.db.execute(
            select(MediaSubtype.supertype, func.count(MediaItem.id))
            .join(MediaItem, MediaItem.media_subtype_id == MediaSubtype.id)
            .group_by(MediaSubtype.supertype)
        )
        return {row[0].value: row[1] for row in rows}

    # ---- Links ----

    async def get_link(self, item_a_id: int, item_b_id: int) -> Optional[ItemLink]:
        a, b = sorted((item_a_id, item_b_id))
        return (
            await self.db.execute(select(ItemLink).where(ItemLink.item_a_id == a, ItemLink.item_b_id == b))
        ).scalar_one_or_none()

    async def links_for_item(self, item_id: int) -> Sequence[ItemLink]:
        return (
            await self.db.execute(
                select(ItemLink).where(or_(ItemLink.item_a_id == item_id, ItemLink.item_b_id == item_id))
            )
        ).scalars().all()

    def create_link(self, item_a_id: int, item_b_id: int, matched_via: LinkMatchType) -> ItemLink:
        a, b = sorted((item_a_id, item_b_id))
        link = ItemLink(item_a_id=a, item_b_id=b, matched_via=matched_via)
        self.db.add(link)
        return link

    async def delete_link(self, link: ItemLink) -> None:
        await self.db.delete(link)

    async def link_unlinked(self, item: MediaItem, candidates: Sequence[MediaItem]) -> int:
        """Create an `ItemLink` between `item` and each candidate not already
        directly linked to it (and not `item` itself). Returns the number of new
        links created. Commits if any were created.
        """
        if not candidates:
            return 0

        existing_links = await self.links_for_item(item.id)
        linked_ids = set()
        for link in existing_links:
            linked_ids.add(link.item_a_id)
            linked_ids.add(link.item_b_id)
        linked_ids.discard(item.id)

        created = 0
        for candidate in candidates:
            if candidate.id == item.id or candidate.id in linked_ids:
                continue
            self.create_link(item.id, candidate.id, LinkMatchType.AUTO)
            linked_ids.add(candidate.id)
            created += 1

        if created:
            await self.db.commit()
        return created

    async def auto_link_item(self, item: MediaItem, subtype: MediaSubtype) -> int:
        """Find other items in the same category that are clearly the same
        title and link any not already linked. Returns the number of new
        links created.

        Primary match is `item`'s auto-link field (tmdb_id/musicbrainz_id/
        isbn) — an exact external-id match is a strong enough signal to link
        regardless of other metadata. If that finds nothing (e.g. a
        Plex-synced item with no musicbrainz_id), fall back to a same-category
        title+year match, guarded by `_editions_compatible` so an explicit
        edition mismatch (e.g. "Remastered" vs "Anniversary Edition") doesn't
        produce a false-positive link.
        """
        field = AUTO_LINK_FIELD.get(subtype.category)
        candidates: Sequence[MediaItem] = []

        if field is not None:
            value = getattr(item, field)
            if value:
                candidates = (
                    await self.db.execute(
                        select(MediaItem)
                        .join(MediaSubtype, MediaItem.media_subtype_id == MediaSubtype.id)
                        .where(
                            MediaSubtype.category == subtype.category,
                            getattr(MediaItem, field) == value,
                            MediaItem.id != item.id,
                        )
                    )
                ).scalars().all()

        if not candidates and item.title and item.year is not None:
            title_year_matches = (
                await self.db.execute(
                    select(MediaItem)
                    .join(MediaSubtype, MediaItem.media_subtype_id == MediaSubtype.id)
                    .where(
                        MediaSubtype.category == subtype.category,
                        MediaItem.title.ilike(item.title),
                        MediaItem.year == item.year,
                        MediaItem.id != item.id,
                    )
                )
            ).scalars().all()
            candidates = [c for c in title_year_matches if _editions_compatible(item.edition, c.edition)]

        return await self.link_unlinked(item, candidates)

    # ---- Plex sync ----

    @staticmethod
    def _identity_filter(stmt, tmdb_id, musicbrainz_id, title, year):
        """Narrow a `select(MediaItem)` statement to items matching the given
        identity — tmdb_id/musicbrainz_id when present, otherwise
        case-insensitive title + year."""
        if tmdb_id is not None:
            return stmt.where(MediaItem.tmdb_id == tmdb_id)
        if musicbrainz_id is not None:
            return stmt.where(MediaItem.musicbrainz_id == musicbrainz_id)
        return stmt.where(MediaItem.title.ilike(title), MediaItem.year == year)

    async def find_plex_duplicate(
        self,
        *,
        platform_id: int,
        media_subtype_id: Optional[int],
        tmdb_id: Optional[int],
        musicbrainz_id: Optional[str],
        title: str,
        year: Optional[int],
    ) -> Optional[MediaItem]:
        """The item that *is* the Plex copy of a synced item: filed under the
        configured Plex platform and library's media subtype, with a matching
        identity. This is the item to update in place."""
        stmt = select(MediaItem).where(
            MediaItem.platform_id == platform_id,
            MediaItem.media_subtype_id == media_subtype_id,
        )
        stmt = self._identity_filter(stmt, tmdb_id, musicbrainz_id, title, year)
        return (await self.db.execute(stmt)).scalars().first()

    async def find_link_candidates(
        self,
        *,
        category: MediaCategory,
        platform_id: int,
        media_subtype_id: Optional[int],
        tmdb_id: Optional[int],
        musicbrainz_id: Optional[str],
        title: str,
        year: Optional[int],
        exclude_id: Optional[int] = None,
    ) -> Sequence[MediaItem]:
        """Other items matching the given identity that are *not* the Plex
        copy — other-platform digital copies or physical copies the user
        already owns, to be linked to the Plex copy."""
        stmt = (
            select(MediaItem)
            .join(MediaSubtype, MediaItem.media_subtype_id == MediaSubtype.id)
            .where(
                MediaSubtype.category == category,
                or_(
                    MediaItem.platform_id != platform_id,
                    MediaItem.platform_id.is_(None),
                    MediaItem.media_subtype_id != media_subtype_id,
                ),
            )
        )
        if exclude_id is not None:
            stmt = stmt.where(MediaItem.id != exclude_id)
        stmt = self._identity_filter(stmt, tmdb_id, musicbrainz_id, title, year)
        return (await self.db.execute(stmt)).scalars().all()

    async def list_by_platform_and_subtype(
        self, platform_id: int, media_subtype_id: Optional[int], exclude_ids: Optional[set] = None
    ) -> Sequence[MediaItem]:
        stmt = select(MediaItem).where(
            MediaItem.platform_id == platform_id,
            MediaItem.media_subtype_id == media_subtype_id,
        )
        if exclude_ids:
            stmt = stmt.where(MediaItem.id.notin_(exclude_ids))
        return (await self.db.execute(stmt)).scalars().all()

    # ---- Bulk ----

    async def delete_all(self) -> None:
        await self.db.execute(delete(ItemLink))
        await super().delete_all()


async def get_media_item_repository(db: AsyncSession = Depends(get_db)) -> MediaItemRepository:
    return MediaItemRepository(db)
