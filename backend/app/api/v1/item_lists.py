from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional

from ...models.enums import MediaCategory
from ...models.item_list import ItemList
from ...repositories.app_config import AppConfigRepository, get_app_config_repository
from ...repositories.item_list import ItemListRepository, get_item_list_repository
from ...repositories.user import UserRepository, get_user_repository
from ...schemas.item_list import ItemListCreate, ItemListUpdate, ItemListResponse
from ...services.auth import get_current_user, require_permission

router = APIRouter()


def _to_response(item_list: ItemList, item_count: int = 0) -> ItemListResponse:
    return ItemListResponse(
        id=item_list.id,
        name=item_list.name,
        category=item_list.category,
        item_count=item_count,
        owner_id=item_list.owner_id,
        owner_username=item_list.owner.username if item_list.owner else None,
        created_at=item_list.created_at,
        updated_at=item_list.updated_at,
    )


@router.get("", response_model=List[ItemListResponse])
async def list_lists(
    category: Optional[MediaCategory] = None,
    _=Depends(get_current_user),
    repo: ItemListRepository = Depends(get_item_list_repository),
):
    rows = await repo.list_ordered()
    if category is not None:
        rows = [r for r in rows if r.category == category]
    counts = await repo.item_count_map()
    return [_to_response(r, counts.get(r.id, 0)) for r in rows]


@router.post("", response_model=ItemListResponse, status_code=201)
async def create_list(
    payload: ItemListCreate,
    current_user=Depends(require_permission("can_manage_lists")),
    repo: ItemListRepository = Depends(get_item_list_repository),
    user_repo: UserRepository = Depends(get_user_repository),
    config_repo: AppConfigRepository = Depends(get_app_config_repository),
):
    if payload.owner_id is not None:
        effective_owner_id = payload.owner_id
    else:
        cfg = await config_repo.get_singleton()
        if cfg.ownership_mode == "by_login":
            effective_owner_id = current_user.id
        else:
            shared = await user_repo.get_shared_user()
            effective_owner_id = shared.id if shared else None

    existing = await repo.find_by_name(payload.category, payload.name, owner_id=effective_owner_id)
    if existing is not None:
        raise HTTPException(status_code=409, detail="A list with this name already exists for this owner and category")

    item_list = ItemList(name=payload.name, category=payload.category, owner_id=effective_owner_id)
    repo.add(item_list)
    await repo.commit()
    await repo.refresh(item_list)
    return _to_response(item_list, 0)


@router.put("/{list_id}", response_model=ItemListResponse)
async def update_list(
    list_id: int,
    payload: ItemListUpdate,
    _=Depends(require_permission("can_manage_lists")),
    repo: ItemListRepository = Depends(get_item_list_repository),
):
    item_list = await repo.get(list_id)
    if not item_list:
        raise HTTPException(status_code=404, detail="List not found")

    new_name = payload.name
    new_owner_id = payload.owner_id if payload.owner_id is not None else item_list.owner_id

    if new_name != item_list.name or new_owner_id != item_list.owner_id:
        existing = await repo.find_by_name(
            item_list.category, new_name, owner_id=new_owner_id, exclude_id=list_id
        )
        if existing is not None:
            raise HTTPException(status_code=409, detail="A list with this name already exists for this owner and category")

    item_list.name = new_name
    if payload.owner_id is not None:
        item_list.owner_id = payload.owner_id

    await repo.commit()
    await repo.refresh(item_list)
    counts = await repo.item_count_map()
    return _to_response(item_list, counts.get(item_list.id, 0))


@router.delete("/{list_id}", status_code=204)
async def delete_list(
    list_id: int,
    _=Depends(require_permission("can_manage_lists")),
    repo: ItemListRepository = Depends(get_item_list_repository),
):
    item_list = await repo.get(list_id)
    if not item_list:
        raise HTTPException(status_code=404, detail="List not found")

    await repo.delete(item_list)
    await repo.commit()
