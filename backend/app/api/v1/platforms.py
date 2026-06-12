from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from pathlib import Path

from ...database import get_db
from ...models.platform import Platform
from ...models.media import MediaItem
from ...schemas.platform import PlatformCreate, PlatformUpdate, PlatformResponse
from ...services.auth import get_current_user, require_permission
from ...services.asset_upload import save_asset, remove_asset
from ...config import settings

router = APIRouter()

ALLOWED_LOGO_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp"}
MAX_LOGO_UPLOAD_BYTES = 2 * 1024 * 1024  # 2 MB


def _logo_url(platform: Platform) -> Optional[str]:
    return f"/platform-logos/{Path(platform.logo_path).name}" if platform.logo_path else None


def _to_response(platform: Platform, item_count: int = 0) -> PlatformResponse:
    return PlatformResponse(
        id=platform.id,
        name=platform.name,
        logo_key=platform.logo_key,
        logo_url=_logo_url(platform),
        item_count=item_count,
        created_at=platform.created_at,
        updated_at=platform.updated_at,
    )


async def _item_count_map(db: AsyncSession) -> dict:
    rows = await db.execute(
        select(MediaItem.platform_id, func.count(MediaItem.id))
        .where(MediaItem.platform_id.is_not(None))
        .group_by(MediaItem.platform_id)
    )
    return {row[0]: row[1] for row in rows}


@router.get("", response_model=List[PlatformResponse])
async def list_platforms(_=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Platform).order_by(Platform.name))).scalars().all()
    counts = await _item_count_map(db)
    return [_to_response(p, counts.get(p.id, 0)) for p in rows]


@router.post("", response_model=PlatformResponse, status_code=201)
async def create_platform(
    payload: PlatformCreate,
    _=Depends(require_permission("can_manage_platforms")),
    db: AsyncSession = Depends(get_db),
):
    existing = (await db.execute(select(Platform.id).where(Platform.name == payload.name))).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="A platform with this name already exists")

    platform = Platform(name=payload.name, logo_key=payload.logo_key)
    db.add(platform)
    await db.commit()
    await db.refresh(platform)
    return _to_response(platform, 0)


@router.put("/{platform_id}", response_model=PlatformResponse)
async def update_platform(
    platform_id: int,
    payload: PlatformUpdate,
    _=Depends(require_permission("can_manage_platforms")),
    db: AsyncSession = Depends(get_db),
):
    platform = (await db.execute(select(Platform).where(Platform.id == platform_id))).scalar_one_or_none()
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")

    if payload.name is not None and payload.name != platform.name:
        existing = (
            await db.execute(select(Platform.id).where(Platform.name == payload.name, Platform.id != platform_id))
        ).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(status_code=409, detail="A platform with this name already exists")
        platform.name = payload.name

    if "logo_key" in payload.model_fields_set:
        platform.logo_key = payload.logo_key

    await db.commit()
    await db.refresh(platform)
    counts = await _item_count_map(db)
    return _to_response(platform, counts.get(platform.id, 0))


@router.delete("/{platform_id}", status_code=204)
async def delete_platform(
    platform_id: int,
    _=Depends(require_permission("can_manage_platforms")),
    db: AsyncSession = Depends(get_db),
):
    platform = (await db.execute(select(Platform).where(Platform.id == platform_id))).scalar_one_or_none()
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")

    count = (
        await db.execute(select(func.count(MediaItem.id)).where(MediaItem.platform_id == platform_id))
    ).scalar_one()
    if count > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete: {count} item(s) use this platform")

    remove_asset(settings.platform_logos_dir, platform.logo_path)
    await db.delete(platform)
    await db.commit()


@router.post("/{platform_id}/logo", response_model=PlatformResponse)
async def upload_platform_logo(
    platform_id: int,
    file: UploadFile = File(...),
    _=Depends(require_permission("can_manage_platforms")),
    db: AsyncSession = Depends(get_db),
):
    platform = (await db.execute(select(Platform).where(Platform.id == platform_id))).scalar_one_or_none()
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")

    if file.content_type not in ALLOWED_LOGO_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported image type. Use JPEG, PNG, WebP, GIF or BMP.")

    data = await file.read()
    if len(data) > MAX_LOGO_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Logo too large (max 2 MB)")

    filename = await save_asset(data, file.content_type, settings.platform_logos_dir, f"platform_{platform_id}")
    if filename is None:
        raise HTTPException(status_code=400, detail="File is not a valid image")

    if platform.logo_path and platform.logo_path != filename:
        remove_asset(settings.platform_logos_dir, platform.logo_path)

    platform.logo_path = filename
    await db.commit()
    await db.refresh(platform)
    counts = await _item_count_map(db)
    return _to_response(platform, counts.get(platform.id, 0))
