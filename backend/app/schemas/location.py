from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class LocationCreate(BaseModel):
    name: str
    parent_id: Optional[int] = None


class LocationUpdate(BaseModel):
    name: Optional[str] = None
    parent_id: Optional[int] = None


class LocationResponse(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None
    children: List["LocationResponse"] = []
    item_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


LocationResponse.model_rebuild()
