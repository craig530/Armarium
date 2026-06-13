from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional

from ..models.enums import MediaCategory
from .media import PlatformSummary


class PlexConfigResponse(BaseModel):
    configured: bool
    enabled: bool
    base_url: Optional[str] = None
    # Never includes the token.


class PlexConfigUpdate(BaseModel):
    base_url: str = Field(..., min_length=1, max_length=500)
    token: Optional[str] = Field(None, min_length=1, max_length=500)
    enabled: bool = True


class PlexTestRequest(BaseModel):
    base_url: str = Field(..., min_length=1, max_length=500)
    token: str = Field(..., min_length=1, max_length=500)


class PlexSectionResponse(BaseModel):
    key: str
    title: str
    type: str
    mapped: bool


class PlexMappingCreate(BaseModel):
    section_key: str
    platform_id: Optional[int] = None


class PlexMappingResponse(BaseModel):
    id: int
    section_key: str
    section_title: str
    section_type: str
    category: MediaCategory
    platform: PlatformSummary
    last_synced_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
