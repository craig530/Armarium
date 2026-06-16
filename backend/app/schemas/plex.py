from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Literal, Optional

from ..models.enums import MediaCategory
from .media import MediaItemResponse, PlatformSummary


class PlexConfigResponse(BaseModel):
    configured: bool
    enabled: bool
    base_url: Optional[str] = None
    platform: Optional[PlatformSummary] = None
    # Never includes the token.


class PlexConfigUpdate(BaseModel):
    base_url: str = Field(..., min_length=1, max_length=500)
    token: Optional[str] = Field(None, min_length=1, max_length=500)
    enabled: bool = True
    platform_id: int


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


class MediaSubtypeSummary(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class PlexMappingResponse(BaseModel):
    id: int
    section_key: str
    section_title: str
    section_type: str
    category: MediaCategory
    media_subtype: Optional[MediaSubtypeSummary] = None
    last_synced_at: Optional[datetime] = None
    last_sync_status: Optional[str] = None
    last_sync_created: Optional[int] = None
    last_sync_updated: Optional[int] = None
    last_sync_removed: Optional[int] = None
    last_sync_error: Optional[str] = None

    model_config = {"from_attributes": True}


class PlexMappingUpdate(BaseModel):
    media_subtype_id: int


class PlexSyncRequest(BaseModel):
    """Optional body for POST /mappings/{id}/sync — omitting the body is fine."""
    auto_remove_stale: bool = False


class PlexSyncItem(BaseModel):
    """Normalized fields for a single Plex library item, used to create or
    update a MediaItem during sync."""

    guid: str
    title: str
    year: Optional[int] = None
    genres: Optional[str] = None
    description: Optional[str] = None
    director: Optional[str] = None
    studio: Optional[str] = None
    runtime_minutes: Optional[int] = None
    rating: Optional[str] = None
    cast_list: Optional[str] = None
    seasons_owned: Optional[str] = None
    episode_count: Optional[int] = None
    artist: Optional[str] = None
    label: Optional[str] = None
    track_count: Optional[int] = None
    tmdb_id: Optional[int] = None
    musicbrainz_id: Optional[str] = None
    cover_thumb: Optional[str] = None


class PlexSyncResult(BaseModel):
    created: int
    updated: int
    removed: int = 0
    stale_items: List[MediaItemResponse]


class PlexSyncStatus(BaseModel):
    """Snapshot of an in-flight or just-finished background sync job."""

    status: Literal["idle", "running", "completed", "cancelled", "error"]
    total: Optional[int] = None
    processed: int = 0
    created: int = 0
    updated: int = 0
    removed: int = 0
    error: Optional[str] = None
    result: Optional[PlexSyncResult] = None


class PlexRemoveStaleRequest(BaseModel):
    item_ids: List[int]
