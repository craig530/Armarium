from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class PlatformCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    logo_key: Optional[str] = Field(None, max_length=100)


class PlatformUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    logo_key: Optional[str] = Field(None, max_length=100)


class PlatformResponse(BaseModel):
    id: int
    name: str
    logo_key: Optional[str] = None
    logo_url: Optional[str] = None
    item_count: int = 0
    locked: bool = False
    locked_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
