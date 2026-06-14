from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, update, table, column, text
from sqlalchemy.orm import selectinload
from typing import Optional
import math
from pathlib import Path

from ...database import get_db, AsyncSessionLocal
from ...models.media import MediaItem
from ...models.location import Location
from ...models.media_subtype import MediaSubtype
from ...models.platform import Platform
from ...models.item_link import ItemLink
from ...models.enums import LinkMatchType, MediaCategory, Supertype
from ...schemas.media import (
    MediaItemCreate, MediaItemUpdate, MediaItemResponse, MediaListResponse, LibraryStats,
    MediaSubtypeSummary, PlatformSummary, LinkedItemSummary, ItemLinkCreate,
)
from ...services.cover_art import download_cover, cover_urls, delete_cover_files, optimise_and_save
from ...services.auth import get_current_user, require_permission
from ...services import search as search_service

router = APIRouter()

ALLOWED_COVER_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp"}
MAX_COVER_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

# Category -> external-id field used to auto-match a physical/digital pair.
_AUTO_LINK_FIELD = {
    MediaCategory.FILMS_TV: "tmdb_id",
    MediaCategory.MUSIC: "musicbrainz_id",
    MediaCategory.BOOKS: "isbn",
}


async def _location_maps(db: AsyncSession) -> tuple:
    """Build a `({location_id: "A → B → C"}, {location_id: {icon_key, icon_url}})`
    pair from a single flat (id, name, parent_id, icon_key, icon_path) query.

    Built from a flat query rather than by walking the ORM `Location.parent`
    relationship — that relationship isn't eagerly loaded alongside
    `MediaItem.location`, and accessing it lazily outside an AsyncSession call
    raises MissingGreenlet.
    """
    rows = (
        await db.execute(
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


async def _subtype_map(db: AsyncSession) -> dict:
    rows = (await db.execute(select(MediaSubtype))).scalars().all()
    return {
        s.id: {"id": s.id, "name": s.name, "category": s.category, "supertype": s.supertype}
        for s in rows
    }


async def _platform_map(db: AsyncSession) -> dict:
    rows = (await db.execute(select(Platform))).scalars().all()
    return {
        p.id: {
            "id": p.id,
            "name": p.name,
            "logo_key": p.logo_key,
            "logo_url": f"/platform-logos/{Path(p.logo_path).name}" if p.logo_path else None,
        }
        for p in rows
    }


async def _link_map(db: AsyncSession, item_ids: list) -> dict:
    """{item_id: [connected_item_ids...]} via connected components over `ItemLink`.

    An item can now be linked to several others (e.g. a physical disc plus
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
            await db.execute(
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


async def _link_summaries(
    db: AsyncSession,
    item_ids: list,
    subtype_map: dict,
    platform_map: dict,
    path_map: dict,
    icon_map: dict,
) -> dict:
    link_map = await _link_map(db, item_ids)
    if not link_map:
        return {}

    all_partner_ids = {pid for partner_ids in link_map.values() for pid in partner_ids}
    partners = (
        await db.execute(select(MediaItem).where(MediaItem.id.in_(all_partner_ids)))
    ).scalars().all()
    partner_by_id = {p.id: p for p in partners}

    def _summary(partner: MediaItem):
        subtype_info = subtype_map.get(partner.media_subtype_id)
        if subtype_info is None:
            return None

        platform_info = platform_map.get(partner.platform_id)
        icon_info = icon_map.get(partner.location_id, {})
        cover_url, cover_thumb_url = cover_urls(partner.cover_image_path, partner.cover_image_url)

        return LinkedItemSummary(
            id=partner.id,
            title=partner.title,
            cover_url=cover_url,
            cover_thumb_url=cover_thumb_url,
            media_subtype=MediaSubtypeSummary(**subtype_info),
            category=subtype_info["category"],
            supertype=subtype_info["supertype"],
            location_id=partner.location_id,
            location_name=partner.location.name if partner.location else None,
            location_path=path_map.get(partner.location_id) if partner.location_id is not None else None,
            location_icon_key=icon_info.get("icon_key"),
            location_icon_url=icon_info.get("icon_url"),
            platform=PlatformSummary(**platform_info) if platform_info else None,
        )

    summaries: dict = {}
    for item_id, partner_ids in link_map.items():
        result = []
        for partner_id in partner_ids:
            partner = partner_by_id.get(partner_id)
            if partner is None:
                continue
            summary = _summary(partner)
            if summary is not None:
                result.append(summary)
        if result:
            summaries[item_id] = result
    return summaries


def _item_to_response(
    item: MediaItem,
    path_map: dict,
    subtype_map: dict,
    platform_map: dict,
    icon_map: dict,
    link_summaries: dict,
) -> MediaItemResponse:
    cover_url, cover_thumb_url = cover_urls(item.cover_image_path, item.cover_image_url)

    subtype_info = subtype_map.get(item.media_subtype_id)
    platform_info = platform_map.get(item.platform_id)
    icon_info = icon_map.get(item.location_id, {})
    linked = link_summaries.get(item.id, [])

    own_supertype = subtype_info["supertype"] if subtype_info else None
    group_supertypes = {l.supertype for l in linked}
    if own_supertype is not None:
        group_supertypes.add(own_supertype)

    if Supertype.PHYSICAL in group_supertypes and Supertype.DIGITAL in group_supertypes:
        ownership = "both"
    elif own_supertype is not None:
        ownership = own_supertype.value
    else:
        ownership = "physical"

    return MediaItemResponse(
        **{
            col: getattr(item, col)
            for col in [
                "id", "title", "year", "genres", "description",
                "cover_image_path", "cover_image_url", "barcode", "edition", "notes",
                "artist", "label", "track_count", "director", "studio",
                "runtime_minutes", "rating", "cast_list", "seasons_owned", "episode_count",
                "author", "publisher", "page_count", "isbn", "language",
                "musicbrainz_id", "tmdb_id", "openlibrary_id",
                "media_subtype_id", "location_id", "platform_id",
                "created_at", "updated_at",
            ]
        },
        cover_url=cover_url,
        cover_thumb_url=cover_thumb_url,
        media_subtype=MediaSubtypeSummary(**subtype_info) if subtype_info else None,
        category=subtype_info["category"] if subtype_info else None,
        supertype=subtype_info["supertype"] if subtype_info else None,
        location_name=item.location.name if item.location else None,
        location_path=path_map.get(item.location_id) if item.location_id is not None else None,
        location_icon_key=icon_info.get("icon_key"),
        location_icon_url=icon_info.get("icon_url"),
        platform=PlatformSummary(**platform_info) if platform_info else None,
        linked_items=linked,
        ownership=ownership,
    )


async def _build_responses(db: AsyncSession, items: list) -> list:
    path_map, icon_map = await _location_maps(db)
    subtype_map = await _subtype_map(db)
    platform_map = await _platform_map(db)
    item_ids = [i.id for i in items]
    link_summaries = await _link_summaries(db, item_ids, subtype_map, platform_map, path_map, icon_map)
    return [
        _item_to_response(i, path_map, subtype_map, platform_map, icon_map, link_summaries)
        for i in items
    ]


async def _build_response(db: AsyncSession, item: MediaItem) -> MediaItemResponse:
    return (await _build_responses(db, [item]))[0]


async def _reload_item(db: AsyncSession, item_id: int) -> MediaItem:
    # populate_existing is required: with expire_on_commit=False, `item` (already
    # in the session's identity map) keeps its stale relationship values from
    # before this request's edits unless we force a re-population.
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
    return (await db.execute(stmt)).scalar_one()


@router.get("", response_model=MediaListResponse)
async def list_media(
    page: int = Query(1, ge=1),
    per_page: int = Query(24, ge=1, le=100),
    q: Optional[str] = None,
    category: Optional[MediaCategory] = None,
    supertype: Optional[Supertype] = None,
    media_subtype_id: Optional[int] = None,
    platform_id: Optional[int] = None,
    genre: Optional[str] = None,
    year: Optional[int] = None,
    location_id: Optional[int] = None,
    sort: str = Query("created_at", pattern="^(title|year|created_at)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    _=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
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
    if location_id:
        filters.append(MediaItem.location_id == location_id)
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
    total = (await db.execute(count_stmt)).scalar_one()

    sort_col = getattr(MediaItem, sort)
    stmt = stmt.order_by(sort_col.desc() if order == "desc" else sort_col.asc())
    stmt = stmt.offset((page - 1) * per_page).limit(per_page)
    stmt = stmt.options(selectinload(MediaItem.location))

    result = await db.execute(stmt)
    items = result.scalars().all()

    return MediaListResponse(
        items=await _build_responses(db, items),
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total else 0,
    )


async def _check_location_exists(db: AsyncSession, location_id: Optional[int]) -> None:
    if location_id is None:
        return
    location = (await db.execute(select(Location).where(Location.id == location_id))).scalar_one_or_none()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")


async def _check_platform_exists(db: AsyncSession, platform_id: Optional[int]) -> None:
    if platform_id is None:
        return
    platform = (await db.execute(select(Platform).where(Platform.id == platform_id))).scalar_one_or_none()
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")


async def _resolve_subtype(db: AsyncSession, media_subtype_id: int) -> MediaSubtype:
    subtype = (
        await db.execute(select(MediaSubtype).where(MediaSubtype.id == media_subtype_id))
    ).scalar_one_or_none()
    if not subtype:
        raise HTTPException(status_code=404, detail="Media subtype not found")
    return subtype


def _validate_ownership_fields(supertype: Supertype, location_id: Optional[int], platform_id: Optional[int]) -> None:
    if supertype == Supertype.PHYSICAL and platform_id is not None:
        raise HTTPException(status_code=400, detail="Physical items cannot have a platform")
    if supertype == Supertype.DIGITAL and location_id is not None:
        raise HTTPException(status_code=400, detail="Digital items cannot have a location")


async def _link_unlinked(db: AsyncSession, item: MediaItem, candidates: list) -> int:
    """Create an `ItemLink` between `item` and each candidate not already
    directly linked to it (and not `item` itself). Returns the number of new
    links created. Commits if any were created.
    """
    if not candidates:
        return 0

    existing_links = (
        await db.execute(
            select(ItemLink).where(or_(ItemLink.item_a_id == item.id, ItemLink.item_b_id == item.id))
        )
    ).scalars().all()
    linked_ids = set()
    for link in existing_links:
        linked_ids.add(link.item_a_id)
        linked_ids.add(link.item_b_id)
    linked_ids.discard(item.id)

    created = 0
    for candidate in candidates:
        if candidate.id == item.id or candidate.id in linked_ids:
            continue
        a, b = sorted((item.id, candidate.id))
        db.add(ItemLink(item_a_id=a, item_b_id=b, matched_via=LinkMatchType.AUTO))
        linked_ids.add(candidate.id)
        created += 1

    if created:
        await db.commit()
    return created


async def _auto_link_item(db: AsyncSession, item: MediaItem, subtype: MediaSubtype) -> int:
    """Find other items in the same category sharing `item`'s auto-link field
    (tmdb_id/musicbrainz_id/isbn) and link any not already linked. Returns the
    number of new links created."""
    field = _AUTO_LINK_FIELD.get(subtype.category)
    if field is None:
        return 0

    value = getattr(item, field)
    if not value:
        return 0

    candidates = (
        await db.execute(
            select(MediaItem)
            .join(MediaSubtype, MediaItem.media_subtype_id == MediaSubtype.id)
            .where(
                MediaSubtype.category == subtype.category,
                getattr(MediaItem, field) == value,
                MediaItem.id != item.id,
            )
        )
    ).scalars().all()

    return await _link_unlinked(db, item, candidates)


async def _fetch_cover_in_background(item_id: int, url: str) -> None:
    """Download + optimise a cover image and attach it to the item.

    Runs after the response has been sent (via `BackgroundTasks`) so cover
    downloads never add latency to create/update requests. Uses its own
    session since the request's session is closed by the time this runs.
    Until this completes, `cover_url` falls back to the remote
    `cover_image_url`.
    """
    local_path = await download_cover(url, item_id)
    if not local_path:
        return
    async with AsyncSessionLocal() as db:
        await db.execute(update(MediaItem).where(MediaItem.id == item_id).values(cover_image_path=local_path))
        await db.commit()


@router.post("", response_model=MediaItemResponse, status_code=201)
async def create_media(
    payload: MediaItemCreate,
    background_tasks: BackgroundTasks,
    _=Depends(require_permission("can_add_items")),
    db: AsyncSession = Depends(get_db),
):
    subtype = await _resolve_subtype(db, payload.media_subtype_id)
    await _check_location_exists(db, payload.location_id)
    await _check_platform_exists(db, payload.platform_id)
    _validate_ownership_fields(subtype.supertype, payload.location_id, payload.platform_id)

    item = MediaItem(**payload.model_dump())
    db.add(item)
    await db.flush()

    if item.cover_image_url:
        background_tasks.add_task(_fetch_cover_in_background, item.id, item.cover_image_url)

    await db.commit()
    await _auto_link_item(db, item, subtype)

    item = await _reload_item(db, item.id)
    return await _build_response(db, item)


@router.get("/stats", response_model=LibraryStats)
async def get_stats(_=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(func.count(MediaItem.id)))).scalar_one()

    by_subtype_rows = await db.execute(
        select(MediaSubtype.name, func.count(MediaItem.id))
        .join(MediaItem, MediaItem.media_subtype_id == MediaSubtype.id)
        .group_by(MediaSubtype.name)
    )
    by_subtype = {row[0]: row[1] for row in by_subtype_rows}

    by_category_rows = await db.execute(
        select(MediaSubtype.category, func.count(MediaItem.id))
        .join(MediaItem, MediaItem.media_subtype_id == MediaSubtype.id)
        .group_by(MediaSubtype.category)
    )
    by_category = {row[0].value: row[1] for row in by_category_rows}

    by_supertype_rows = await db.execute(
        select(MediaSubtype.supertype, func.count(MediaItem.id))
        .join(MediaItem, MediaItem.media_subtype_id == MediaSubtype.id)
        .group_by(MediaSubtype.supertype)
    )
    by_supertype = {row[0].value: row[1] for row in by_supertype_rows}

    recent_stmt = (
        select(MediaItem)
        .options(selectinload(MediaItem.location))
        .order_by(MediaItem.created_at.desc())
        .limit(6)
    )
    recent_items = (await db.execute(recent_stmt)).scalars().all()

    return LibraryStats(
        total=total,
        by_category=by_category,
        by_supertype=by_supertype,
        by_subtype=by_subtype,
        recent_additions=await _build_responses(db, recent_items),
    )


@router.post("/link", response_model=MediaItemResponse, status_code=201)
async def link_items(
    payload: ItemLinkCreate,
    _=Depends(require_permission("can_add_items")),
    db: AsyncSession = Depends(get_db),
):
    if payload.item_a_id == payload.item_b_id:
        raise HTTPException(status_code=400, detail="Cannot link an item to itself")

    ids = (
        await db.execute(select(MediaItem.id).where(MediaItem.id.in_([payload.item_a_id, payload.item_b_id])))
    ).scalars().all()
    if payload.item_a_id not in ids or payload.item_b_id not in ids:
        raise HTTPException(status_code=404, detail="Item not found")

    a, b = sorted((payload.item_a_id, payload.item_b_id))

    existing = (
        await db.execute(
            select(ItemLink.id).where(ItemLink.item_a_id == a, ItemLink.item_b_id == b)
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=400, detail="These items are already linked")

    db.add(ItemLink(item_a_id=a, item_b_id=b, matched_via=LinkMatchType.MANUAL))
    await db.commit()

    item_a = await _reload_item(db, payload.item_a_id)
    return await _build_response(db, item_a)


@router.get("/{item_id}", response_model=MediaItemResponse)
async def get_media(item_id: int, _=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(MediaItem).where(MediaItem.id == item_id).options(selectinload(MediaItem.location))
    item = (await db.execute(stmt)).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return await _build_response(db, item)


@router.put("/{item_id}", response_model=MediaItemResponse)
async def update_media(
    item_id: int,
    payload: MediaItemUpdate,
    background_tasks: BackgroundTasks,
    _=Depends(require_permission("can_add_items")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(MediaItem).where(MediaItem.id == item_id).options(selectinload(MediaItem.location))
    item = (await db.execute(stmt)).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if "location_id" in payload.model_fields_set:
        await _check_location_exists(db, payload.location_id)
    if "platform_id" in payload.model_fields_set:
        await _check_platform_exists(db, payload.platform_id)

    if "media_subtype_id" in payload.model_fields_set and payload.media_subtype_id is not None:
        subtype = await _resolve_subtype(db, payload.media_subtype_id)
    else:
        subtype = await _resolve_subtype(db, item.media_subtype_id)

    new_location_id = payload.location_id if "location_id" in payload.model_fields_set else item.location_id
    new_platform_id = payload.platform_id if "platform_id" in payload.model_fields_set else item.platform_id
    _validate_ownership_fields(subtype.supertype, new_location_id, new_platform_id)

    old_url = item.cover_image_url
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    if payload.cover_image_url and payload.cover_image_url != old_url:
        background_tasks.add_task(_fetch_cover_in_background, item.id, payload.cover_image_url)

    await db.commit()
    item = await _reload_item(db, item.id)
    return await _build_response(db, item)


@router.delete("/{item_id}", status_code=204)
async def delete_media(item_id: int, _=Depends(require_permission("can_add_items")), db: AsyncSession = Depends(get_db)):
    stmt = select(MediaItem).where(MediaItem.id == item_id)
    item = (await db.execute(stmt)).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    links = (
        await db.execute(
            select(ItemLink).where(or_(ItemLink.item_a_id == item_id, ItemLink.item_b_id == item_id))
        )
    ).scalars().all()
    for link in links:
        await db.delete(link)

    delete_cover_files(item.cover_image_path)

    await db.delete(item)
    await db.commit()


@router.delete("/{item_id}/link/{other_id}", status_code=204)
async def unlink_item(
    item_id: int,
    other_id: int,
    _=Depends(require_permission("can_add_items")),
    db: AsyncSession = Depends(get_db),
):
    link = (
        await db.execute(
            select(ItemLink).where(
                or_(
                    and_(ItemLink.item_a_id == item_id, ItemLink.item_b_id == other_id),
                    and_(ItemLink.item_a_id == other_id, ItemLink.item_b_id == item_id),
                )
            )
        )
    ).scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=404, detail="These items are not linked")

    await db.delete(link)
    await db.commit()


@router.post("/{item_id}/cover", response_model=MediaItemResponse)
async def upload_cover(
    item_id: int,
    file: UploadFile = File(...),
    _=Depends(require_permission("can_add_items")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(MediaItem).where(MediaItem.id == item_id).options(selectinload(MediaItem.location))
    item = (await db.execute(stmt)).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if file.content_type not in ALLOWED_COVER_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported image type. Use JPEG, PNG, WebP, GIF or BMP.")

    data = await file.read()
    if len(data) > MAX_COVER_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image too large (max 10 MB)")

    local_path = await optimise_and_save(data, item_id, "custom")
    if local_path is None:
        raise HTTPException(status_code=400, detail="File is not a valid image")

    item.cover_image_path = local_path
    item.cover_image_url = None
    await db.commit()
    item = await _reload_item(db, item.id)
    return await _build_response(db, item)


@router.delete("/{item_id}/cover", response_model=MediaItemResponse)
async def delete_cover(
    item_id: int,
    _=Depends(require_permission("can_add_items")),
    db: AsyncSession = Depends(get_db),
):
    """Remove a locally-stored cover (uploaded or downloaded), falling back
    to `cover_image_url` (if set) for `cover_url`."""
    stmt = select(MediaItem).where(MediaItem.id == item_id).options(selectinload(MediaItem.location))
    item = (await db.execute(stmt)).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    delete_cover_files(item.cover_image_path)
    item.cover_image_path = None
    await db.commit()
    item = await _reload_item(db, item.id)
    return await _build_response(db, item)


@router.post("/{item_id}/cover/refresh", response_model=MediaItemResponse)
async def refresh_cover(
    item_id: int,
    _=Depends(require_permission("can_add_items")),
    db: AsyncSession = Depends(get_db),
):
    """Re-download and re-optimise an item's cover from its `cover_image_url`."""
    stmt = select(MediaItem).where(MediaItem.id == item_id).options(selectinload(MediaItem.location))
    item = (await db.execute(stmt)).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if not item.cover_image_url:
        raise HTTPException(status_code=400, detail="Item has no cover URL to refresh from")

    local_path = await download_cover(item.cover_image_url, item_id, force=True)
    if local_path is None:
        raise HTTPException(status_code=502, detail="Failed to download cover image")

    item.cover_image_path = local_path
    await db.commit()
    item = await _reload_item(db, item.id)
    return await _build_response(db, item)
