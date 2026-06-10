from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from ..models.enums import MediaCategory, Supertype

# Limits mirror the DB column sizes (backend/app/models/media.py). SQLite does not
# enforce VARCHAR length itself, so these are the only guard against oversized values.
TEXT_FIELD_MAX = 10000


class MediaItemCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    media_subtype_id: int
    year: Optional[int] = Field(None, ge=0, le=2100)
    genres: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = Field(None, max_length=TEXT_FIELD_MAX)
    cover_image_url: Optional[str] = Field(None, max_length=1000)
    barcode: Optional[str] = Field(None, max_length=50)
    edition: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = Field(None, max_length=TEXT_FIELD_MAX)

    # Music
    artist: Optional[str] = Field(None, max_length=300)
    label: Optional[str] = Field(None, max_length=300)
    track_count: Optional[int] = Field(None, ge=0, le=999)

    # Films & TV
    director: Optional[str] = Field(None, max_length=300)
    studio: Optional[str] = Field(None, max_length=300)
    runtime_minutes: Optional[int] = Field(None, ge=0, le=10000)
    rating: Optional[str] = Field(None, max_length=20)
    cast_list: Optional[str] = Field(None, max_length=TEXT_FIELD_MAX)
    seasons_owned: Optional[str] = Field(None, max_length=100)
    episode_count: Optional[int] = Field(None, ge=0, le=100000)

    # Books
    author: Optional[str] = Field(None, max_length=300)
    publisher: Optional[str] = Field(None, max_length=300)
    page_count: Optional[int] = Field(None, ge=0, le=100000)
    isbn: Optional[str] = Field(None, max_length=20)
    language: Optional[str] = Field(None, max_length=50)

    # External IDs
    musicbrainz_id: Optional[str] = Field(None, max_length=100)
    tmdb_id: Optional[int] = Field(None, ge=0)
    openlibrary_id: Optional[str] = Field(None, max_length=50)

    # Ownership — physical items use location_id, digital items use
    # platform_id. Validated against the resolved subtype's supertype.
    location_id: Optional[int] = None
    platform_id: Optional[int] = None


class MediaItemUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    media_subtype_id: Optional[int] = None
    year: Optional[int] = Field(None, ge=0, le=2100)
    genres: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = Field(None, max_length=TEXT_FIELD_MAX)
    cover_image_url: Optional[str] = Field(None, max_length=1000)
    barcode: Optional[str] = Field(None, max_length=50)
    edition: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = Field(None, max_length=TEXT_FIELD_MAX)
    artist: Optional[str] = Field(None, max_length=300)
    label: Optional[str] = Field(None, max_length=300)
    track_count: Optional[int] = Field(None, ge=0, le=999)
    director: Optional[str] = Field(None, max_length=300)
    studio: Optional[str] = Field(None, max_length=300)
    runtime_minutes: Optional[int] = Field(None, ge=0, le=10000)
    rating: Optional[str] = Field(None, max_length=20)
    cast_list: Optional[str] = Field(None, max_length=TEXT_FIELD_MAX)
    seasons_owned: Optional[str] = Field(None, max_length=100)
    episode_count: Optional[int] = Field(None, ge=0, le=100000)
    author: Optional[str] = Field(None, max_length=300)
    publisher: Optional[str] = Field(None, max_length=300)
    page_count: Optional[int] = Field(None, ge=0, le=100000)
    isbn: Optional[str] = Field(None, max_length=20)
    language: Optional[str] = Field(None, max_length=50)
    musicbrainz_id: Optional[str] = Field(None, max_length=100)
    tmdb_id: Optional[int] = Field(None, ge=0)
    openlibrary_id: Optional[str] = Field(None, max_length=50)
    location_id: Optional[int] = None
    platform_id: Optional[int] = None


class MediaSubtypeSummary(BaseModel):
    id: int
    name: str
    category: MediaCategory
    supertype: Supertype

    model_config = {"from_attributes": True}


class PlatformSummary(BaseModel):
    id: int
    name: str
    logo_key: Optional[str] = None
    logo_url: Optional[str] = None

    model_config = {"from_attributes": True}


class LinkedItemSummary(BaseModel):
    id: int
    title: str
    cover_url: Optional[str] = None
    media_subtype: MediaSubtypeSummary
    category: MediaCategory
    supertype: Supertype
    location_id: Optional[int] = None
    location_name: Optional[str] = None
    location_path: Optional[str] = None
    location_icon_key: Optional[str] = None
    location_icon_url: Optional[str] = None
    platform: Optional[PlatformSummary] = None


class MediaItemResponse(BaseModel):
    id: int
    title: str
    year: Optional[int] = None
    genres: Optional[str] = None
    description: Optional[str] = None
    cover_image_path: Optional[str] = None
    cover_image_url: Optional[str] = None
    cover_url: Optional[str] = None       # computed: local path takes priority
    barcode: Optional[str] = None
    edition: Optional[str] = None
    notes: Optional[str] = None
    artist: Optional[str] = None
    label: Optional[str] = None
    track_count: Optional[int] = None
    director: Optional[str] = None
    studio: Optional[str] = None
    runtime_minutes: Optional[int] = None
    rating: Optional[str] = None
    cast_list: Optional[str] = None
    seasons_owned: Optional[str] = None
    episode_count: Optional[int] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    page_count: Optional[int] = None
    isbn: Optional[str] = None
    language: Optional[str] = None
    musicbrainz_id: Optional[str] = None
    tmdb_id: Optional[int] = None
    openlibrary_id: Optional[str] = None

    media_subtype_id: Optional[int] = None
    media_subtype: Optional[MediaSubtypeSummary] = None    # computed
    category: Optional[MediaCategory] = None               # computed, from subtype
    supertype: Optional[Supertype] = None                  # computed, from subtype

    location_id: Optional[int] = None
    location_name: Optional[str] = None   # computed
    location_path: Optional[str] = None   # computed: "A → B → C"
    location_icon_key: Optional[str] = None   # computed
    location_icon_url: Optional[str] = None   # computed

    platform_id: Optional[int] = None
    platform: Optional[PlatformSummary] = None   # computed

    linked_item: Optional[LinkedItemSummary] = None   # computed
    ownership: str = "physical"                       # computed: physical | digital | both

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MediaListResponse(BaseModel):
    items: List[MediaItemResponse]
    total: int
    page: int
    per_page: int
    pages: int


class ItemLinkCreate(BaseModel):
    item_a_id: int
    item_b_id: int


class LookupCandidate(BaseModel):
    external_id: str
    source: str
    title: str
    year: Optional[int] = None
    category: MediaCategory
    edition: Optional[str] = None
    creator: Optional[str] = None
    cover_url: Optional[str] = None
    metadata: dict = {}


class LibraryStats(BaseModel):
    total: int
    by_category: dict
    by_supertype: dict
    by_subtype: dict
    recent_additions: List[MediaItemResponse]
