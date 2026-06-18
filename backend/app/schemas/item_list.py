from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from ..models.enums import MediaCategory


class ItemListCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    category: MediaCategory
    owner_id: Optional[int] = None


class ItemListUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    owner_id: Optional[int] = None


class ItemListResponse(BaseModel):
    id: int
    name: str
    category: MediaCategory
    item_count: int = 0
    owner_id: Optional[int] = None
    owner_username: Optional[str] = None    # computed from owner relationship
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
