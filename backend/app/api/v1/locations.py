from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from pathlib import Path

from ...database import get_db
from ...models.location import Location
from ...models.media import MediaItem
from ...schemas.location import LocationCreate, LocationUpdate, LocationResponse
from ...services.auth import get_current_user, require_permission
from ...services.asset_upload import save_asset, remove_asset
from ...config import settings

router = APIRouter()

ALLOWED_ICON_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp"}
MAX_ICON_UPLOAD_BYTES = 2 * 1024 * 1024  # 2 MB


def _icon_url(icon_path: Optional[str]) -> Optional[str]:
    return f"/location-icons/{Path(icon_path).name}" if icon_path else None


async def _location_rows(db: AsyncSession):
    """Fetch every location as plain (id, name, parent_id, ...) rows.

    Avoids the ORM `Location.children`/`Location.parent` relationships —
    those are only eager-loaded to a fixed depth via selectinload(), and
    accessing them beyond that depth raises MissingGreenlet.
    """
    return (
        await db.execute(
            select(
                Location.id, Location.name, Location.parent_id,
                Location.icon_key, Location.icon_path,
                Location.created_at, Location.updated_at,
            )
            .order_by(Location.name)
        )
    ).all()


def _build_tree(rows, count_map: dict):
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
            icon_url=_icon_url(row.icon_path),
            created_at=row.created_at,
            updated_at=row.updated_at,
            item_count=count_map.get(row.id, 0),
            children=[build(c) for c in by_parent.get(row.id, [])],
        )
        by_id[row.id] = node
        return node

    roots = [build(r) for r in by_parent.get(None, [])]
    return roots, by_id


async def _count_map(db: AsyncSession) -> dict:
    count_rows = await db.execute(
        select(MediaItem.location_id, func.count(MediaItem.id))
        .where(MediaItem.location_id.is_not(None))
        .group_by(MediaItem.location_id)
    )
    return {row[0]: row[1] for row in count_rows}


@router.get("", response_model=List[LocationResponse])
async def list_locations(response: Response, _=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    response.headers["Cache-Control"] = "private, max-age=60"
    count_map = await _count_map(db)
    rows = await _location_rows(db)
    roots, _by_id = _build_tree(rows, count_map)
    return roots


@router.post("", response_model=LocationResponse, status_code=201)
async def create_location(
    payload: LocationCreate,
    _=Depends(require_permission("can_manage_locations")),
    db: AsyncSession = Depends(get_db),
):
    if payload.parent_id:
        parent = (await db.execute(select(Location).where(Location.id == payload.parent_id))).scalar_one_or_none()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent location not found")

    loc = Location(name=payload.name, parent_id=payload.parent_id, icon_key=payload.icon_key)
    db.add(loc)
    await db.commit()
    await db.refresh(loc)
    return LocationResponse(
        id=loc.id, name=loc.name, parent_id=loc.parent_id,
        icon_key=loc.icon_key, icon_url=_icon_url(loc.icon_path),
        created_at=loc.created_at, updated_at=loc.updated_at,
        item_count=0, children=[],
    )


@router.get("/{loc_id}", response_model=LocationResponse)
async def get_location(
    loc_id: int,
    _=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = await _location_rows(db)
    if not any(row.id == loc_id for row in rows):
        raise HTTPException(status_code=404, detail="Location not found")

    count_map = await _count_map(db)
    _roots, by_id = _build_tree(rows, count_map)
    return by_id[loc_id]


@router.put("/{loc_id}", response_model=LocationResponse)
async def update_location(
    loc_id: int,
    payload: LocationUpdate,
    _=Depends(require_permission("can_manage_locations")),
    db: AsyncSession = Depends(get_db),
):
    loc = (await db.execute(select(Location).where(Location.id == loc_id))).scalar_one_or_none()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    if payload.name is not None:
        loc.name = payload.name
    if "icon_key" in payload.model_fields_set:
        loc.icon_key = payload.icon_key
    if payload.parent_id is not None:
        if payload.parent_id == loc_id:
            raise HTTPException(status_code=400, detail="Location cannot be its own parent")

        # Walk up from the proposed parent toward the root. If loc_id appears in
        # that chain, reparenting would make loc_id its own ancestor, creating a
        # cycle that would recurse forever when building the location tree.
        # `visited` also bounds the walk if a cycle already exists in the data
        # for an unrelated branch.
        ancestor_id = payload.parent_id
        visited = set()
        while ancestor_id is not None and ancestor_id not in visited:
            if ancestor_id == loc_id:
                raise HTTPException(status_code=400, detail="Cannot move a location under one of its own descendants")
            visited.add(ancestor_id)
            ancestor_id = (
                await db.execute(select(Location.parent_id).where(Location.id == ancestor_id))
            ).scalar_one_or_none()

        loc.parent_id = payload.parent_id
    elif "parent_id" in payload.model_fields_set:
        loc.parent_id = None

    await db.commit()
    await db.refresh(loc)
    return LocationResponse(
        id=loc.id, name=loc.name, parent_id=loc.parent_id,
        icon_key=loc.icon_key, icon_url=_icon_url(loc.icon_path),
        created_at=loc.created_at, updated_at=loc.updated_at,
        item_count=0, children=[],
    )


@router.delete("/{loc_id}", status_code=204)
async def delete_location(
    loc_id: int,
    _=Depends(require_permission("can_manage_locations")),
    db: AsyncSession = Depends(get_db),
):
    loc = (await db.execute(select(Location).where(Location.id == loc_id))).scalar_one_or_none()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    child = (await db.execute(select(Location.id).where(Location.parent_id == loc_id))).scalars().first()
    if child is not None:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a location that has child locations. Move or delete them first.",
        )

    items = (await db.execute(select(MediaItem).where(MediaItem.location_id == loc_id))).scalars().all()
    for item in items:
        item.location_id = None

    remove_asset(settings.location_icons_dir, loc.icon_path)
    await db.delete(loc)
    await db.commit()


@router.post("/{loc_id}/icon", response_model=LocationResponse)
async def upload_location_icon(
    loc_id: int,
    file: UploadFile = File(...),
    _=Depends(require_permission("can_manage_locations")),
    db: AsyncSession = Depends(get_db),
):
    loc = (await db.execute(select(Location).where(Location.id == loc_id))).scalar_one_or_none()
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    if file.content_type not in ALLOWED_ICON_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported image type. Use JPEG, PNG, WebP, GIF or BMP.")

    data = await file.read()
    if len(data) > MAX_ICON_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Icon too large (max 2 MB)")

    filename = await save_asset(data, file.content_type, settings.location_icons_dir, f"location_{loc_id}")
    if filename is None:
        raise HTTPException(status_code=400, detail="File is not a valid image")

    if loc.icon_path and loc.icon_path != filename:
        remove_asset(settings.location_icons_dir, loc.icon_path)

    loc.icon_path = filename
    await db.commit()

    rows = await _location_rows(db)
    count_map = await _count_map(db)
    _roots, by_id = _build_tree(rows, count_map)
    return by_id[loc_id]
