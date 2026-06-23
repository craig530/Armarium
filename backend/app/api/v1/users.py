from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from typing import List

from ...config import settings
from ...models.user import User
from ...repositories.user import UserRepository, get_user_repository
from ...schemas.user import UserCreate, UserUpdate, UserResponse, UserSummary
from ...services import email as email_service
from ...services.auth import generate_unusable_password_hash, get_current_admin, get_current_user

router = APIRouter()


def _to_response(user: User) -> UserResponse:
    resp = UserResponse.model_validate(user)
    resp.is_protected_super_admin = user.username == settings.admin_username
    return resp


async def _send_set_password_email(to: str, username: str, base_url: str, token: str, invite: bool) -> None:
    link = f"{base_url}/set-password?token={token}"
    builder = email_service.build_invite_email if invite else email_service.build_reset_email
    subject, text, html = builder(username, link)
    await email_service.send_email_logged(to, subject, text, html)


@router.get("/summary", response_model=List[UserSummary])
async def list_users_summary(
    _=Depends(get_current_user),
    repo: UserRepository = Depends(get_user_repository),
):
    """Non-admin endpoint: returns all non-system users for owner pickers."""
    return await repo.list_non_system()


@router.get("", response_model=List[UserResponse])
async def list_users(_=Depends(get_current_admin), repo: UserRepository = Depends(get_user_repository)):
    return [_to_response(u) for u in await repo.list_non_system()]


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    payload: UserCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    _=Depends(get_current_admin),
    repo: UserRepository = Depends(get_user_repository),
):
    """Create a user and email them a link to set their own password —
    admins don't set passwords directly. Requires SMTP to be configured,
    since an account created without one would have no way to ever become
    usable.
    """
    if not email_service.is_configured():
        raise HTTPException(status_code=503, detail="Email is not configured — set SMTP_HOST etc. in .env before adding users")
    if await repo.get_by_username(payload.username):
        raise HTTPException(status_code=409, detail="Username already exists")
    if await repo.get_by_email(payload.email):
        raise HTTPException(status_code=409, detail="Email already in use")

    user = User(
        username=payload.username,
        hashed_password=generate_unusable_password_hash(),
        password_set=False,
        email=payload.email,
        display_name=payload.display_name,
        is_admin=payload.is_admin,
        is_read_only=payload.is_read_only,
        can_add_items=payload.can_add_items,
        can_manage_locations=payload.can_manage_locations,
        can_manage_platforms=payload.can_manage_platforms,
        can_manage_media_types=payload.can_manage_media_types,
        can_manage_lists=payload.can_manage_lists,
        can_manage_schedules=payload.can_manage_schedules,
    )
    repo.add(user)
    token = repo.issue_reset_token(user)
    await repo.commit()
    await repo.refresh(user)

    base_url = email_service.resolve_base_url(str(request.base_url))
    background_tasks.add_task(_send_set_password_email, user.email, user.username, base_url, token, True)

    return _to_response(user)


@router.post("/{user_id}/force-password-reset", response_model=UserResponse)
async def force_password_reset(
    user_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    _=Depends(get_current_admin),
    repo: UserRepository = Depends(get_user_repository),
):
    """Immediately invalidate a user's current password and email them a
    link to set a new one. Not available for the env-defined super-admin or
    system accounts — see models/user.py and ARCHITECTURE.md §4.4.
    """
    user = await repo.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.username == settings.admin_username:
        raise HTTPException(status_code=403, detail="The default admin account's password is managed via .env, not this UI")
    if user.is_system:
        raise HTTPException(status_code=403, detail="Cannot reset a system account's password")
    if not user.email:
        raise HTTPException(status_code=400, detail="This user has no email on file")
    if not email_service.is_configured():
        raise HTTPException(status_code=503, detail="Email is not configured — set SMTP_HOST etc. in .env")

    repo.invalidate_password(user, generate_unusable_password_hash())
    token = repo.issue_reset_token(user)
    await repo.commit()
    await repo.refresh(user)

    base_url = email_service.resolve_base_url(str(request.base_url))
    background_tasks.add_task(_send_set_password_email, user.email, user.username, base_url, token, False)

    return _to_response(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, payload: UserUpdate, current_user: User = Depends(get_current_admin), repo: UserRepository = Depends(get_user_repository)):
    user = await repo.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.username is not None:
        user.username = payload.username
    if payload.email is not None:
        existing = await repo.get_by_email(payload.email)
        if existing and existing.id != user.id:
            raise HTTPException(status_code=409, detail="Email already in use")
        user.email = payload.email
    if "display_name" in payload.model_fields_set:
        user.display_name = payload.display_name
    if payload.theme_preference is not None:
        user.theme_preference = payload.theme_preference
    if payload.is_admin is not None:
        # Prevent removing own admin status
        if user.id == current_user.id and not payload.is_admin:
            raise HTTPException(status_code=400, detail="Cannot remove your own admin role")
        if user.is_admin and not payload.is_admin and await repo.count_admins() <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove the last administrator account")
        user.is_admin = payload.is_admin
    if payload.is_active is not None:
        if user.id == current_user.id and not payload.is_active:
            raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
        if user.is_admin and not payload.is_active and await repo.count_admins() <= 1:
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
    if payload.can_manage_lists is not None:
        user.can_manage_lists = payload.can_manage_lists
    if payload.can_manage_schedules is not None:
        user.can_manage_schedules = payload.can_manage_schedules

    await repo.commit()
    await repo.refresh(user)
    return _to_response(user)


@router.delete("/{user_id}", status_code=204)
async def delete_user(user_id: int, current_user: User = Depends(get_current_admin), repo: UserRepository = Depends(get_user_repository)):
    user = await repo.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    if user.is_admin and await repo.count_admins() <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the last administrator account")

    await repo.delete(user)
    await repo.commit()
