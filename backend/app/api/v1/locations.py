from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import List

from ...models.location import Location
from ...repositories.location import LocationRepository, get_location_repository, location_icon_url
from ...schemas.location import LocationCreate, LocationUpdate, LocationResponse
from ...services.auth import get_current_user, require_permission
from ...services.asset_upload import save_asset, remove_asset
from ...config import settings

router = APIRouter()

ALLOWED_ICON_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp"}
MAX_ICON_UPLOAD_BYTES = 2 * 1024 * 1024  # 2 MB


@router.get("", response_model=List[LocationResponse])
async def list_locations(
    _=Depends(get_current_user),
    repo: LocationRepository = Depends(get_location_repository),
):
    count_map = await repo.item_count_map()
    rows = await repo.flat_rows()
    roots, _by_id = repo.build_tree(rows, count_map)
    return roots


@router.post("", response_model=LocationResponse, status_code=201)
async def create_location(
    payload: LocationCreate,
    _=Depends(require_permission("can_manage_locations")),
    repo: LocationRepository = Depends(get_location_repository),
):
    if payload.parent_id:
        parent = await repo.get(payload.parent_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Parent location not found")

    loc = Location(name=payload.name, parent_id=payload.parent_id, icon_key=payload.icon_key, sort_order=payload.sort_order)
    repo.add(loc)
    await repo.commit()
    await repo.refresh(loc)
    return LocationResponse(
        id=loc.id, name=loc.name, parent_id=loc.parent_id,
        icon_key=loc.icon_key, icon_url=location_icon_url(loc.icon_path), sort_order=loc.sort_order,
        created_at=loc.created_at, updated_at=loc.updated_at,
        item_count=0, children=[],
    )


@router.get("/{loc_id}", response_model=LocationResponse)
async def get_location(
    loc_id: int,
    _=Depends(get_current_user),
    repo: LocationRepository = Depends(get_location_repository),
):
    rows = await repo.flat_rows()
    if not any(row.id == loc_id for row in rows):
        raise HTTPException(status_code=404, detail="Location not found")

    count_map = await repo.item_count_map()
    _roots, by_id = repo.build_tree(rows, count_map)
    return by_id[loc_id]


@router.put("/{loc_id}", response_model=LocationResponse)
async def update_location(
    loc_id: int,
    payload: LocationUpdate,
    _=Depends(require_permission("can_manage_locations")),
    repo: LocationRepository = Depends(get_location_repository),
):
    loc = await repo.get(loc_id)
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    if payload.name is not None:
        loc.name = payload.name
    if "icon_key" in payload.model_fields_set:
        loc.icon_key = payload.icon_key
    if payload.sort_order is not None:
        loc.sort_order = payload.sort_order
    if payload.parent_id is not None:
        if payload.parent_id == loc_id:
            raise HTTPException(status_code=400, detail="Location cannot be its own parent")

        if await repo.would_create_cycle(loc_id, payload.parent_id):
            raise HTTPException(status_code=400, detail="Cannot move a location under one of its own descendants")

        loc.parent_id = payload.parent_id
    elif "parent_id" in payload.model_fields_set:
        loc.parent_id = None

    await repo.commit()
    await repo.refresh(loc)
    return LocationResponse(
        id=loc.id, name=loc.name, parent_id=loc.parent_id,
        icon_key=loc.icon_key, icon_url=location_icon_url(loc.icon_path), sort_order=loc.sort_order,
        created_at=loc.created_at, updated_at=loc.updated_at,
        item_count=0, children=[],
    )


@router.delete("/{loc_id}", status_code=204)
async def delete_location(
    loc_id: int,
    _=Depends(require_permission("can_manage_locations")),
    repo: LocationRepository = Depends(get_location_repository),
):
    loc = await repo.get(loc_id)
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    if await repo.has_children(loc_id):
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a location that has child locations. Move or delete them first.",
        )

    await repo.unlink_items(loc_id)

    remove_asset(settings.location_icons_dir, loc.icon_path)
    await repo.delete(loc)
    await repo.commit()


@router.post("/{loc_id}/icon", response_model=LocationResponse)
async def upload_location_icon(
    loc_id: int,
    file: UploadFile = File(...),
    _=Depends(require_permission("can_manage_locations")),
    repo: LocationRepository = Depends(get_location_repository),
):
    loc = await repo.get(loc_id)
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
    await repo.commit()

    rows = await repo.flat_rows()
    count_map = await repo.item_count_map()
    _roots, by_id = repo.build_tree(rows, count_map)
    return by_id[loc_id]
