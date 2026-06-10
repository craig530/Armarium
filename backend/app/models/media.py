from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from ..database import Base


class MediaType(str, enum.Enum):
    CD = "cd"
    DVD = "dvd"
    BLURAY = "bluray"
    BOOK = "book"


class MediaItem(Base):
    __tablename__ = "media_items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    media_type = Column(SQLEnum(MediaType), nullable=False, index=True)
    year = Column(Integer, index=True)
    genres = Column(String(500))       # comma-separated
    description = Column(Text)
    cover_image_path = Column(String(500))   # local cached file path
    cover_image_url = Column(String(1000))   # original external URL
    barcode = Column(String(50), index=True)
    edition = Column(String(200))            # e.g. "4K UHD", "Special Edition"
    notes = Column(Text)

    # Music / CD
    artist = Column(String(300))
    label = Column(String(300))
    track_count = Column(Integer)

    # Film / DVD / Blu-ray
    director = Column(String(300))
    studio = Column(String(300))
    runtime_minutes = Column(Integer)
    rating = Column(String(20))
    cast_list = Column(Text)   # JSON array stored as string

    # Book
    author = Column(String(300))
    publisher = Column(String(300))
    page_count = Column(Integer)
    isbn = Column(String(20))
    language = Column(String(50))

    # External IDs
    musicbrainz_id = Column(String(100))
    tmdb_id = Column(Integer)
    openlibrary_id = Column(String(50))

    # Location
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)
    location = relationship("Location", back_populates="items", lazy="selectin")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
