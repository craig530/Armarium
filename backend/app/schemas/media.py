from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from ..models.media import MediaType


class MediaItemCreate(BaseModel):
    title: str
    media_type: MediaType
    year: Optional[int] = None
    genres: Optional[str] = None
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
    barcode: Optional[str] = None
    edition: Optional[str] = None
    notes: Optional[str] = None

    # Music / CD
    artist: Optional[str] = None
    label: Optional[str] = None
    track_count: Optional[int] = None

    # Film / DVD / Blu-ray
    director: Optional[str] = None
    studio: Optional[str] = None
    runtime_minutes: Optional[int] = None
    rating: Optional[str] = None
    cast_list: Optional[str] = None

    # Book
    author: Optional[str] = None
    publisher: Optional[str] = None
    page_count: Optional[int] = None
    isbn: Optional[str] = None
    language: Optional[str] = None

    # External IDs
    musicbrainz_id: Optional[str] = None
    tmdb_id: Optional[int] = None
    openlibrary_id: Optional[str] = None

    # Location
    location_id: Optional[int] = None


class MediaItemUpdate(BaseModel):
    title: Optional[str] = None
    media_type: Optional[MediaType] = None
    year: Optional[int] = None
    genres: Optional[str] = None
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
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
    author: Optional[str] = None
    publisher: Optional[str] = None
    page_count: Optional[int] = None
    isbn: Optional[str] = None
    language: Optional[str] = None
    musicbrainz_id: Optional[str] = None
    tmdb_id: Optional[int] = None
    openlibrary_id: Optional[str] = None
    location_id: Optional[int] = None


class MediaItemResponse(BaseModel):
    id: int
    title: str
    media_type: MediaType
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
    author: Optional[str] = None
    publisher: Optional[str] = None
    page_count: Optional[int] = None
    isbn: Optional[str] = None
    language: Optional[str] = None
    musicbrainz_id: Optional[str] = None
    tmdb_id: Optional[int] = None
    openlibrary_id: Optional[str] = None
    location_id: Optional[int] = None
    location_name: Optional[str] = None   # computed
    location_path: Optional[str] = None   # computed: "A → B → C"
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MediaListResponse(BaseModel):
    items: List[MediaItemResponse]
    total: int
    page: int
    per_page: int
    pages: int


class LookupCandidate(BaseModel):
    external_id: str
    source: str
    title: str
    year: Optional[int] = None
    media_type: MediaType
    edition: Optional[str] = None
    creator: Optional[str] = None
    cover_url: Optional[str] = None
    metadata: dict = {}


class LibraryStats(BaseModel):
    total: int
    by_type: dict
    recent_additions: List[MediaItemResponse]
