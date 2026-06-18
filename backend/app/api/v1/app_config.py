from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import update

from ...models.media import MediaItem
from ...models.item_list import ItemList
from ...models.plex_library_mapping import PlexLibraryMapping
from ...repositories.app_config import AppConfigRepository, get_app_config_repository
from ...repositories.user import UserRepository, get_user_repository
from ...schemas.app_config import (
    AppConfigResponse, AppConfigUpdate, OwnershipMigrateRequest,
    _VALID_CATEGORIES,
)
from ...services.auth import get_current_user, get_current_admin

router = APIRouter()


@router.get("", response_model=AppConfigResponse)
async def get_config(
    _=Depends(get_current_user),
    repo: AppConfigRepository = Depends(get_app_config_repository),
):
    """Return global app configuration. Available to all authenticated users
    so the UI can hide disabled categories without an admin check."""
    return await repo.get_singleton()


@router.put("", response_model=AppConfigResponse)
async def update_config(
    payload: AppConfigUpdate,
    _=Depends(get_current_admin),
    repo: AppConfigRepository = Depends(get_app_config_repository),
    user_repo: UserRepository = Depends(get_user_repository),
):
    cfg = await repo.get_singleton()

    if payload.ownership_mode is not None:
        if payload.ownership_mode == "by_login" and cfg.ownership_mode == "shared":
            raise HTTPException(
                status_code=400,
                detail="Use POST /admin/config/migrate-ownership to assign existing items to a user before switching to 'by_login' mode.",
            )
        await repo.set_ownership_mode(payload.ownership_mode)

    if payload.disabled_categories is not None:
        invalid = set(payload.disabled_categories) - _VALID_CATEGORIES
        if invalid:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown categories: {sorted(invalid)}. Valid values: {sorted(_VALID_CATEGORIES)}",
            )
        await repo.set_disabled_categories(payload.disabled_categories)

    await repo.commit()
    return await repo.get_singleton()


@router.post("/migrate-ownership", response_model=AppConfigResponse)
async def migrate_ownership(
    payload: OwnershipMigrateRequest,
    _=Depends(get_current_admin),
    repo: AppConfigRepository = Depends(get_app_config_repository),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """Reassign all items/lists/mappings from the shared system user to
    `target_user_id`, then switch ownership_mode to 'by_login'."""
    target = await user_repo.get(payload.target_user_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target user not found")
    if target.is_system:
        raise HTTPException(status_code=400, detail="Cannot migrate to a system account")

    shared = await user_repo.get_shared_user()
    if shared is None:
        raise HTTPException(status_code=500, detail="Shared system user not found in database")

    db = repo.db
    await db.execute(
        update(MediaItem).where(MediaItem.owner_id == shared.id).values(owner_id=target.id)
    )
    await db.execute(
        update(ItemList).where(ItemList.owner_id == shared.id).values(owner_id=target.id)
    )
    await db.execute(
        update(PlexLibraryMapping).where(PlexLibraryMapping.owner_id == shared.id).values(owner_id=target.id)
    )
    result = await repo.set_ownership_mode("by_login")
    await repo.commit()
    return result
