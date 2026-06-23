from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

# Letters, numbers, underscore, hyphen — avoids characters that are awkward in
# URLs/logs and keeps usernames easy to type.
USERNAME_PATTERN = r"^[A-Za-z0-9_-]{3,50}$"


class LoginRequest(BaseModel):
    username: str = Field(..., max_length=150)
    password: str = Field(..., max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    username: str = Field(..., pattern=USERNAME_PATTERN)
    # No password here by design — new users are invited by email and set
    # their own password via the link (see api/v1/users.create_user).
    email: EmailStr
    display_name: Optional[str] = Field(None, max_length=100)
    is_admin: bool = False
    is_read_only: bool = False
    can_add_items: bool = True
    can_manage_locations: bool = True
    can_manage_platforms: bool = True
    can_manage_media_types: bool = False
    can_manage_lists: bool = True
    can_manage_schedules: bool = True


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, pattern=USERNAME_PATTERN)
    email: Optional[EmailStr] = None
    display_name: Optional[str] = Field(None, max_length=100)
    theme_preference: Optional[str] = Field(None, pattern=r"^(auto|light|dark)$")
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None
    is_read_only: Optional[bool] = None
    can_add_items: Optional[bool] = None
    can_manage_locations: Optional[bool] = None
    can_manage_platforms: Optional[bool] = None
    can_manage_media_types: Optional[bool] = None
    can_manage_lists: Optional[bool] = None
    can_manage_schedules: Optional[bool] = None


class UserSummary(BaseModel):
    """Minimal user representation used by owner pickers and filter dropdowns."""
    id: int
    username: str
    display_name: Optional[str] = None
    is_system: bool = False

    model_config = {"from_attributes": True}


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    theme_preference: str = 'auto'
    is_admin: bool
    is_active: bool
    is_system: bool
    is_read_only: bool
    can_add_items: bool
    can_manage_locations: bool
    can_manage_platforms: bool
    can_manage_media_types: bool
    can_manage_lists: bool
    can_manage_schedules: bool
    # False while a set-password link is outstanding (invited or
    # force-reset, see models/user.py).
    password_set: bool
    # The env-defined super-admin (settings.admin_username) — computed, not
    # stored. Frontend uses this to disable the force-password-reset action
    # for that one account; the backend enforces it regardless.
    is_protected_super_admin: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class ForgotPasswordRequest(BaseModel):
    username_or_email: str = Field(..., max_length=255)


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class ResetTokenValidityResponse(BaseModel):
    valid: bool
