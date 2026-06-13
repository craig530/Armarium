from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from ...database import get_db
from ...models.media_subtype import MediaSubtype
from ...models.media import MediaItem
from ...models.plex_library_mapping import PlexLibraryMapping
from ...schemas.media_subtype import MediaSubtypeCreate, MediaSubtypeUpdate, MediaSubtypeResponse
from ...services.auth import get_current_user, require_permission

router = APIRouter()


async def _item_count_map(db: AsyncSession) -> dict:
    rows = await db.execute(
        select(MediaItem.media_subtype_id, func.count(MediaItem.id))
        .where(MediaItem.media_subtype_id.is_not(None))
        .group_by(MediaItem.media_subtype_id)
    )
    return {row[0]: row[1] for row in rows}


async def _locked_map(db: AsyncSession) -> dict:
    """Media subtypes referenced by a Plex library mapping — locked
    (undeletable) until the admin repoints or removes that mapping."""
    rows = await db.execute(
        select(PlexLibraryMapping.media_subtype_id, PlexLibraryMapping.section_title)
        .where(PlexLibraryMapping.media_subtype_id.is_not(None))
    )
    return {
        subtype_id: f'Used by Plex sync library "{section_title}"'
        for subtype_id, section_title in rows
    }


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


async def _check_unique(db: AsyncSession, category, supertype, name: str, exclude_id: int = None) -> None:
    stmt = select(MediaSubtype.id).where(
        MediaSubtype.category == category,
        MediaSubtype.supertype == supertype,
        MediaSubtype.name == name,
    )
    if exclude_id is not None:
        stmt = stmt.where(MediaSubtype.id != exclude_id)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="A media subtype with this name already exists in this category")


@router.get("", response_model=List[MediaSubtypeResponse])
async def list_media_subtypes(_=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(MediaSubtype).order_by(
                MediaSubtype.category, MediaSubtype.supertype, MediaSubtype.sort_order, MediaSubtype.name
            )
        )
    ).scalars().all()
    counts = await _item_count_map(db)
    locked = await _locked_map(db)
    return [_to_response(s, counts.get(s.id, 0), locked.get(s.id)) for s in rows]


@router.post("", response_model=MediaSubtypeResponse, status_code=201)
async def create_media_subtype(
    payload: MediaSubtypeCreate,
    _=Depends(require_permission("can_manage_media_types")),
    db: AsyncSession = Depends(get_db),
):
    await _check_unique(db, payload.category, payload.supertype, payload.name)

    subtype = MediaSubtype(**payload.model_dump())
    db.add(subtype)
    await db.commit()
    await db.refresh(subtype)
    return _to_response(subtype, 0)


@router.put("/{subtype_id}", response_model=MediaSubtypeResponse)
async def update_media_subtype(
    subtype_id: int,
    payload: MediaSubtypeUpdate,
    _=Depends(require_permission("can_manage_media_types")),
    db: AsyncSession = Depends(get_db),
):
    subtype = (await db.execute(select(MediaSubtype).where(MediaSubtype.id == subtype_id))).scalar_one_or_none()
    if not subtype:
        raise HTTPException(status_code=404, detail="Media subtype not found")

    if payload.name is not None and payload.name != subtype.name:
        await _check_unique(db, subtype.category, subtype.supertype, payload.name, exclude_id=subtype_id)
        subtype.name = payload.name

    if payload.sort_order is not None:
        subtype.sort_order = payload.sort_order

    await db.commit()
    await db.refresh(subtype)
    counts = await _item_count_map(db)
    return _to_response(subtype, counts.get(subtype.id, 0))


@router.delete("/{subtype_id}", status_code=204)
async def delete_media_subtype(
    subtype_id: int,
    _=Depends(require_permission("can_manage_media_types")),
    db: AsyncSession = Depends(get_db),
):
    subtype = (await db.execute(select(MediaSubtype).where(MediaSubtype.id == subtype_id))).scalar_one_or_none()
    if not subtype:
        raise HTTPException(status_code=404, detail="Media subtype not found")

    count = (
        await db.execute(select(func.count(MediaItem.id)).where(MediaItem.media_subtype_id == subtype_id))
    ).scalar_one()
    if count > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete: {count} item(s) use this media subtype")

    locked = await _locked_map(db)
    reason = locked.get(subtype_id)
    if reason is not None:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete: {reason}. Change or remove it in Settings → Plex Sync first.",
        )

    await db.delete(subtype)
    await db.commit()
