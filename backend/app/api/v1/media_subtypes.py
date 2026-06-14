from fastapi import APIRouter, Depends, HTTPException
from typing import List

from ...models.media_subtype import MediaSubtype
from ...repositories.media_subtype import MediaSubtypeRepository, get_media_subtype_repository
from ...schemas.media_subtype import MediaSubtypeCreate, MediaSubtypeUpdate, MediaSubtypeResponse
from ...services.auth import get_current_user, require_permission

router = APIRouter()


def _to_response(subtype: MediaSubtype, item_count: int = 0, locked_reason: str = None) -> MediaSubtypeResponse:
    return MediaSubtypeResponse(
        id=subtype.id,
        name=subtype.name,
        category=subtype.category,
        supertype=subtype.supertype,
        sort_order=subtype.sort_order,
        item_count=item_count,
        locked=locked_reason is not None,
        locked_reason=locked_reason,
        created_at=subtype.created_at,
        updated_at=subtype.updated_at,
    )


async def _check_unique(repo: MediaSubtypeRepository, category, supertype, name: str, exclude_id: int = None) -> None:
    existing = await repo.find_by_name_in_category(category, supertype, name, exclude_id=exclude_id)
    if existing is not None:
        raise HTTPException(status_code=409, detail="A media subtype with this name already exists in this category")


@router.get("", response_model=List[MediaSubtypeResponse])
async def list_media_subtypes(
    _=Depends(get_current_user),
    repo: MediaSubtypeRepository = Depends(get_media_subtype_repository),
):
    rows = await repo.list_ordered()
    counts = await repo.item_count_map()
    locked = await repo.locked_map()
    return [_to_response(s, counts.get(s.id, 0), locked.get(s.id)) for s in rows]


@router.post("", response_model=MediaSubtypeResponse, status_code=201)
async def create_media_subtype(
    payload: MediaSubtypeCreate,
    _=Depends(require_permission("can_manage_media_types")),
    repo: MediaSubtypeRepository = Depends(get_media_subtype_repository),
):
    await _check_unique(repo, payload.category, payload.supertype, payload.name)

    subtype = MediaSubtype(**payload.model_dump())
    repo.add(subtype)
    await repo.commit()
    await repo.refresh(subtype)
    return _to_response(subtype, 0)


@router.put("/{subtype_id}", response_model=MediaSubtypeResponse)
async def update_media_subtype(
    subtype_id: int,
    payload: MediaSubtypeUpdate,
    _=Depends(require_permission("can_manage_media_types")),
    repo: MediaSubtypeRepository = Depends(get_media_subtype_repository),
):
    subtype = await repo.get(subtype_id)
    if not subtype:
        raise HTTPException(status_code=404, detail="Media subtype not found")

    if payload.name is not None and payload.name != subtype.name:
        await _check_unique(repo, subtype.category, subtype.supertype, payload.name, exclude_id=subtype_id)
        subtype.name = payload.name

    if payload.sort_order is not None:
        subtype.sort_order = payload.sort_order

    await repo.commit()
    await repo.refresh(subtype)
    counts = await repo.item_count_map()
    return _to_response(subtype, counts.get(subtype.id, 0))


@router.delete("/{subtype_id}", status_code=204)
async def delete_media_subtype(
    subtype_id: int,
    _=Depends(require_permission("can_manage_media_types")),
    repo: MediaSubtypeRepository = Depends(get_media_subtype_repository),
):
    subtype = await repo.get(subtype_id)
    if not subtype:
        raise HTTPException(status_code=404, detail="Media subtype not found")

    count = await repo.item_count(subtype_id)
    if count > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete: {count} item(s) use this media subtype")

    locked = await repo.locked_map()
    reason = locked.get(subtype_id)
    if reason is not None:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete: {reason}. Change or remove it in Settings → Plex Sync first.",
        )

    await repo.delete(subtype)
    await repo.commit()
