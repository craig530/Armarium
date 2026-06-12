from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from ...database import get_db
from ...models.user import User
from ...schemas.user import UserCreate, UserUpdate, UserResponse
from ...services.auth import hash_password, get_current_admin

router = APIRouter()


async def _count_admins(db: AsyncSession) -> int:
    return (
        await db.execute(select(func.count(User.id)).where(User.is_admin.is_(True)))
    ).scalar_one()


@router.get("", response_model=List[UserResponse])
async def list_users(
    _=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).order_by(User.created_at))
    return result.scalars().all()


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    payload: UserCreate,
    _=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(User).where(User.username == payload.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already exists")

    user = User(
        username=payload.username,
        hashed_password=hash_password(payload.password),
        is_admin=payload.is_admin,
        is_read_only=payload.is_read_only,
        can_add_items=payload.can_add_items,
        can_manage_locations=payload.can_manage_locations,
        can_manage_platforms=payload.can_manage_platforms,
        can_manage_media_types=payload.can_manage_media_types,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.username is not None:
        user.username = payload.username
    if payload.password is not None:
        user.hashed_password = hash_password(payload.password)
    if payload.is_admin is not None:
        # Prevent removing own admin status
        if user.id == current_user.id and not payload.is_admin:
            raise HTTPException(status_code=400, detail="Cannot remove your own admin role")
        if user.is_admin and not payload.is_admin and await _count_admins(db) <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove the last administrator account")
        user.is_admin = payload.is_admin
    if payload.is_active is not None:
        if user.id == current_user.id and not payload.is_active:
            raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
        if user.is_admin and not payload.is_active and await _count_admins(db) <= 1:
            raise HTTPException(status_code=400, detail="Cannot deactivate the last administrator account")
        user.is_active = payload.is_active
    if payload.is_read_only is not None:
        user.is_read_only = payload.is_read_only
    if payload.can_add_items is not None:
        user.can_add_items = payload.can_add_items
    if payload.can_manage_locations is not None:
        user.can_manage_locations = payload.can_manage_locations
    if payload.can_manage_platforms is not None:
        user.can_manage_platforms = payload.can_manage_platforms
    if payload.can_manage_media_types is not None:
        user.can_manage_media_types = payload.can_manage_media_types

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    if user.is_admin and await _count_admins(db) <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the last administrator account")

    await db.delete(user)
    await db.commit()
