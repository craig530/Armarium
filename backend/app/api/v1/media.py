from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import selectinload
from typing import Optional
import math
import shutil
from pathlib import Path

from ...database import get_db
from ...models.media import MediaItem, MediaType
from ...models.location import Location
from ...schemas.media import MediaItemCreate, MediaItemUpdate, MediaItemResponse, MediaListResponse, LibraryStats
from ...services.cover_art import download_cover
from ...services.auth import get_current_user
from ...config import settings

router = APIRouter()

ALLOWED_COVER_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp"}
MAX_COVER_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


async def _location_path_map(db: AsyncSession) -> dict[int, str]:
    """Build a {location_id: "A → B → C"} breadcrumb map for every location.

    Built from a flat (id, name, parent_id) query rather than by walking the
    ORM `Location.parent` relationship — that relationship isn't eagerly
    loaded alongside `MediaItem.location`, and accessing it lazily outside an
    AsyncSession call raises MissingGreenlet.
    """
    rows = (await db.execute(select(Location.id, Location.name, Location.parent_id))).all()
    by_id = {row.id: (row.name, row.parent_id) for row in rows}

    paths: dict[int, str] = {}

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
    return paths


async def _reload_with_location(db: AsyncSession, item_id: int) -> MediaItem:
    # populate_existing is required: with expire_on_commit=False, `item` (already
    # in the session's identity map) keeps its stale `location` relationship
    # value from before this request's edits unless we force a re-population.
    stmt = (
        select(MediaItem)
        .where(MediaItem.id == item_id)
        .options(selectinload(MediaItem.location))
        .execution_options(populate_existing=True)
    )
    return (await db.execute(stmt)).scalar_one()


def _item_to_response(item: MediaItem, path_map: dict[int, str]) -> MediaItemResponse:
    cover_url = (
        f"/covers/{Path(item.cover_image_path).name}"
        if item.cover_image_path
        else item.cover_image_url
    )
    return MediaItemResponse(
        **{
            col: getattr(item, col)
            for col in [
                "id", "title", "media_type", "year", "genres", "description",
                "cover_image_path", "cover_image_url", "barcode", "edition", "notes",
                "artist", "label", "track_count", "director", "studio",
                "runtime_minutes", "rating", "cast_list", "author", "publisher",
                "page_count", "isbn", "language", "musicbrainz_id", "tmdb_id",
                "openlibrary_id", "location_id", "created_at", "updated_at",
            ]
        },
        cover_url=cover_url,
        location_name=item.location.name if item.location else None,
        location_path=path_map.get(item.location_id) if item.location_id is not None else None,
    )


@router.get("", response_model=MediaListResponse)
async def list_media(
    page: int = Query(1, ge=1),
    per_page: int = Query(24, ge=1, le=100),
    q: Optional[str] = None,
    media_type: Optional[MediaType] = None,
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
        term = f"%{q}%"
        filters.append(
            or_(
                MediaItem.title.ilike(term),
                MediaItem.artist.ilike(term),
                MediaItem.author.ilike(term),
                MediaItem.director.ilike(term),
                MediaItem.genres.ilike(term),
                MediaItem.description.ilike(term),
            )
        )
    if media_type:
        filters.append(MediaItem.media_type == media_type)
    if genre:
        filters.append(MediaItem.genres.ilike(f"%{genre}%"))
    if year:
        filters.append(MediaItem.year == year)
    if location_id:
        filters.append(MediaItem.location_id == location_id)

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
    path_map = await _location_path_map(db)

    return MediaListResponse(
        items=[_item_to_response(i, path_map) for i in items],
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


@router.post("", response_model=MediaItemResponse, status_code=201)
async def create_media(
    payload: MediaItemCreate,
    _=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _check_location_exists(db, payload.location_id)

    item = MediaItem(**payload.model_dump())
    db.add(item)
    await db.flush()

    if item.cover_image_url:
        local_path = await download_cover(item.cover_image_url, item.id)
        if local_path:
            item.cover_image_path = local_path

    await db.commit()
    item = await _reload_with_location(db, item.id)
    path_map = await _location_path_map(db)
    return _item_to_response(item, path_map)


@router.get("/stats", response_model=LibraryStats)
async def get_stats(_=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(func.count(MediaItem.id)))).scalar_one()

    by_type_rows = await db.execute(
        select(MediaItem.media_type, func.count(MediaItem.id)).group_by(MediaItem.media_type)
    )
    by_type = {row[0].value: row[1] for row in by_type_rows}

    recent_stmt = (
        select(MediaItem)
        .options(selectinload(MediaItem.location))
        .order_by(MediaItem.created_at.desc())
        .limit(6)
    )
    recent_items = (await db.execute(recent_stmt)).scalars().all()
    path_map = await _location_path_map(db)

    return LibraryStats(
        total=total,
        by_type=by_type,
        recent_additions=[_item_to_response(i, path_map) for i in recent_items],
    )


@router.get("/{item_id}", response_model=MediaItemResponse)
async def get_media(item_id: int, _=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(MediaItem).where(MediaItem.id == item_id).options(selectinload(MediaItem.location))
    item = (await db.execute(stmt)).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    path_map = await _location_path_map(db)
    return _item_to_response(item, path_map)


@router.put("/{item_id}", response_model=MediaItemResponse)
async def update_media(
    item_id: int,
    payload: MediaItemUpdate,
    _=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(MediaItem).where(MediaItem.id == item_id).options(selectinload(MediaItem.location))
    item = (await db.execute(stmt)).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if "location_id" in payload.model_fields_set:
        await _check_location_exists(db, payload.location_id)

    old_url = item.cover_image_url
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    if payload.cover_image_url and payload.cover_image_url != old_url:
        local_path = await download_cover(payload.cover_image_url, item.id)
        if local_path:
            item.cover_image_path = local_path

    await db.commit()
    item = await _reload_with_location(db, item.id)
    path_map = await _location_path_map(db)
    return _item_to_response(item, path_map)


@router.delete("/{item_id}", status_code=204)
async def delete_media(item_id: int, _=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(MediaItem).where(MediaItem.id == item_id)
    item = (await db.execute(stmt)).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if item.cover_image_path:
        cover_file = Path(settings.covers_dir) / Path(item.cover_image_path).name
        cover_file.unlink(missing_ok=True)

    await db.delete(item)
    await db.commit()


@router.post("/{item_id}/cover", response_model=MediaItemResponse)
async def upload_cover(
    item_id: int,
    file: UploadFile = File(...),
    _=Depends(get_current_user),
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

    from ...services.cover_art import optimise_and_save
    local_path = await optimise_and_save(data, item_id, "custom")
    if local_path is None:
        raise HTTPException(status_code=400, detail="File is not a valid image")

    item.cover_image_path = local_path
    await db.commit()
    item = await _reload_with_location(db, item.id)
    path_map = await _location_path_map(db)
    return _item_to_response(item, path_map)
