from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from ..models.enums import MediaCategory, Supertype


class MediaSubtypeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    category: MediaCategory
    supertype: Supertype
    sort_order: int = 0


class MediaSubtypeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    sort_order: Optional[int] = None


class MediaSubtypeResponse(BaseModel):
    id: int
    name: str
    category: MediaCategory
    supertype: Supertype
    sort_order: int
    item_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
