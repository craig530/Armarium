from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import update

from ...models.media import MediaItem
from ...models.item_list import ItemList
from ...models.plex_library_mapping import PlexLibraryMapping
from ...repositories.app_config import AppConfigRepository, get_app_config_repository
from ...repositories.user import UserRepository, get_user_repository
from ...schemas.app_config import AppConfigResponse, AppConfigUpdate, OwnershipMigrateRequest
from ...services.auth import get_current_admin

router = APIRouter()


@router.get("", response_model=AppConfigResponse)
async def get_config(
    _=Depends(get_current_admin),
    repo: AppConfigRepository = Depends(get_app_config_repository),
):
    return await repo.get_singleton()


@router.put("", response_model=AppConfigResponse)
async def update_config(
    payload: AppConfigUpdate,
    _=Depends(get_current_admin),
    repo: AppConfigRepository = Depends(get_app_config_repository),
    user_repo: UserRepository = Depends(get_user_repository),
):
    cfg = await repo.get_singleton()
    if payload.ownership_mode == "by_login" and cfg.ownership_mode == "shared":
        # Require migration first — caller must POST /migrate-ownership before
        # switching mode so all existing items get assigned to a real user.
        raise HTTPException(
            status_code=400,
            detail="Use POST /admin/config/migrate-ownership to assign existing items to a user before switching to 'by_login' mode.",
        )
    return await repo.set_ownership_mode(payload.ownership_mode)


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
    return await repo.set_ownership_mode("by_login")
