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


class PlexMappingResponse(BaseModel):
    id: int
    section_key: str
    section_title: str
    section_type: str
    category: MediaCategory
    last_synced_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PlexSyncItem(BaseModel):
    """Normalized fields for a single Plex library item, used both to
    create/update a MediaItem during sync and to show conflicting Plex data
    alongside an existing item for the user to compare."""

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


class PlexConflict(BaseModel):
    existing_item: MediaItemResponse
    plex_item: PlexSyncItem


class PlexSyncResult(BaseModel):
    created: int
    updated: int
    conflicts: List[PlexConflict]
    stale_items: List[MediaItemResponse]


class PlexConflictResolution(BaseModel):
    """How to resolve one `PlexConflict` from a prior sync. Either way, the
    existing item is "adopted" — tagged as Plex-sourced so it stops
    re-appearing as a conflict and becomes eligible for stale-detection.
    `use_plex` additionally overwrites its content fields and cover with the
    Plex data; `keep_mine` leaves them untouched."""

    existing_item_id: int
    plex_item: PlexSyncItem
    resolution: Literal["keep_mine", "use_plex"]


class PlexResolveRequest(BaseModel):
    resolutions: List[PlexConflictResolution]


class PlexRemoveStaleRequest(BaseModel):
    item_ids: List[int]
