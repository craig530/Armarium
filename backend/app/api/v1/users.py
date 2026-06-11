from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from ...database import get_db
from ...models.user import User
from ...schemas.user import UserCreate, UserUpdate, UserResponse
from ...services.auth import hash_password, get_current_admin

router = APIRouter()


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
        user.is_admin = payload.is_admin
    if payload.is_active is not None:
        if user.id == current_user.id and not payload.is_active:
            raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
        user.is_active = payload.is_active

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

    await db.delete(user)
    await db.commit()
