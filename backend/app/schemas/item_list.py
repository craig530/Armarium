from pydantic import BaseModel, Field
from datetime import datetime

from ..models.enums import MediaCategory


class ItemListCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    category: MediaCategory


class ItemListUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)


class ItemListResponse(BaseModel):
    id: int
    name: str
    category: MediaCategory
    item_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
