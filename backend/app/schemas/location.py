from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class LocationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    parent_id: Optional[int] = None
    icon_key: Optional[str] = Field(None, max_length=50)
    sort_order: int = 0


class LocationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    parent_id: Optional[int] = None
    icon_key: Optional[str] = Field(None, max_length=50)
    sort_order: Optional[int] = None


class LocationResponse(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None
    icon_key: Optional[str] = None
    icon_url: Optional[str] = None
    sort_order: int = 0
    children: List["LocationResponse"] = []
    item_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


LocationResponse.model_rebuild()
