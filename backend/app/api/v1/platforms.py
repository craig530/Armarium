from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import List, Optional
from pathlib import Path

from ...models.platform import Platform
from ...repositories.platform import PlatformRepository, get_platform_repository
from ...schemas.platform import PlatformCreate, PlatformUpdate, PlatformResponse
from ...services.auth import get_current_user, require_permission
from ...services.asset_upload import save_asset, remove_asset
from ...config import settings

router = APIRouter()

ALLOWED_LOGO_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp"}
MAX_LOGO_UPLOAD_BYTES = 2 * 1024 * 1024  # 2 MB


def _logo_url(platform: Platform) -> Optional[str]:
    return f"/platform-logos/{Path(platform.logo_path).name}" if platform.logo_path else None


def _to_response(platform: Platform, item_count: int = 0, locked_reason: str = None) -> PlatformResponse:
    return PlatformResponse(
        id=platform.id,
        name=platform.name,
        logo_key=platform.logo_key,
        logo_url=_logo_url(platform),
        item_count=item_count,
        locked=locked_reason is not None,
        locked_reason=locked_reason,
        created_at=platform.created_at,
        updated_at=platform.updated_at,
    )


@router.get("", response_model=List[PlatformResponse])
async def list_platforms(
    _=Depends(get_current_user),
    repo: PlatformRepository = Depends(get_platform_repository),
):
    rows = await repo.list_ordered()
    counts = await repo.item_count_map()
    locked = await repo.locked_map()
    return [_to_response(p, counts.get(p.id, 0), locked.get(p.id)) for p in rows]


@router.post("", response_model=PlatformResponse, status_code=201)
async def create_platform(
    payload: PlatformCreate,
    _=Depends(require_permission("can_manage_platforms")),
    repo: PlatformRepository = Depends(get_platform_repository),
):
    existing = await repo.find_by_name(payload.name)
    if existing is not None:
        raise HTTPException(status_code=409, detail="A platform with this name already exists")

    platform = Platform(name=payload.name, logo_key=payload.logo_key)
    repo.add(platform)
    await repo.commit()
    await repo.refresh(platform)
    return _to_response(platform, 0)


@router.put("/{platform_id}", response_model=PlatformResponse)
async def update_platform(
    platform_id: int,
    payload: PlatformUpdate,
    _=Depends(require_permission("can_manage_platforms")),
    repo: PlatformRepository = Depends(get_platform_repository),
):
    platform = await repo.get(platform_id)
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")

    if payload.name is not None and payload.name != platform.name:
        existing = await repo.find_by_name(payload.name, exclude_id=platform_id)
        if existing is not None:
            raise HTTPException(status_code=409, detail="A platform with this name already exists")
        platform.name = payload.name

    if "logo_key" in payload.model_fields_set:
        platform.logo_key = payload.logo_key

    await repo.commit()
    await repo.refresh(platform)
    counts = await repo.item_count_map()
    return _to_response(platform, counts.get(platform.id, 0))


@router.delete("/{platform_id}", status_code=204)
async def delete_platform(
    platform_id: int,
    _=Depends(require_permission("can_manage_platforms")),
    repo: PlatformRepository = Depends(get_platform_repository),
):
    platform = await repo.get(platform_id)
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")

    count = await repo.item_count(platform_id)
    if count > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete: {count} item(s) use this platform")

    locked = await repo.locked_map()
    reason = locked.get(platform_id)
    if reason is not None:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete: {reason}. Change it in Settings → Plex Sync first.",
        )

    remove_asset(settings.platform_logos_dir, platform.logo_path)
    await repo.delete(platform)
    await repo.commit()


@router.post("/{platform_id}/logo", response_model=PlatformResponse)
async def upload_platform_logo(
    platform_id: int,
    file: UploadFile = File(...),
    _=Depends(require_permission("can_manage_platforms")),
    repo: PlatformRepository = Depends(get_platform_repository),
):
    platform = await repo.get(platform_id)
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
    await repo.commit()
    await repo.refresh(platform)
    counts = await repo.item_count_map()
    return _to_response(platform, counts.get(platform.id, 0))
