from pydantic import BaseModel, Field
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
    password: str = Field(..., min_length=8, max_length=128)
    is_admin: bool = False
    is_read_only: bool = False
    can_add_items: bool = True
    can_manage_locations: bool = True
    can_manage_platforms: bool = True
    can_manage_media_types: bool = False


class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, pattern=USERNAME_PATTERN)
    password: Optional[str] = Field(None, min_length=8, max_length=128)
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None
    is_read_only: Optional[bool] = None
    can_add_items: Optional[bool] = None
    can_manage_locations: Optional[bool] = None
    can_manage_platforms: Optional[bool] = None
    can_manage_media_types: Optional[bool] = None


class UserResponse(BaseModel):
    id: int
    username: str
    is_admin: bool
    is_active: bool
    is_read_only: bool
    can_add_items: bool
    can_manage_locations: bool
    can_manage_platforms: bool
    can_manage_media_types: bool
    created_at: datetime

    model_config = {"from_attributes": True}
