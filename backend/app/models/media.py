from sqlalchemy import CheckConstraint, Column, Float, Integer, String, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base


class MediaItem(Base):
    __tablename__ = "media_items"
    __table_args__ = (
        CheckConstraint("user_rating IS NULL OR (user_rating BETWEEN 1 AND 5)", name="ck_media_items_user_rating_range"),
    )

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    year = Column(Integer, index=True)
    genres = Column(String(500))       # comma-separated
    description = Column(Text)
    cover_image_path = Column(String(500))   # local cached file path
    cover_image_url = Column(String(1000))   # original external URL
    barcode = Column(String(50), index=True)
    edition = Column(String(200))            # e.g. "4K UHD", "Special Edition"
    notes = Column(Text)
    user_rating = Column(Integer, nullable=True)  # personal 1-5 star rating, all categories

    # Music / CD
    artist = Column(String(300))
    label = Column(String(300))
    track_count = Column(Integer)

    # Film / DVD / Blu-ray
    director = Column(String(300))
    studio = Column(String(300))
    runtime_minutes = Column(Integer)
    rating = Column(String(20))
    tmdb_rating = Column(Float, nullable=True)  # TMDB vote_average (0-10), films_tv only
    cast_list = Column(Text)   # JSON array stored as string

    # Book
    author = Column(String(300))
    publisher = Column(String(300))
    page_count = Column(Integer)
    isbn = Column(String(20), index=True)
    language = Column(String(50))

    # External IDs
    musicbrainz_id = Column(String(100), index=True)
    tmdb_id = Column(Integer, index=True)
    openlibrary_id = Column(String(50), index=True)

    # Location
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True)
    location = relationship("Location", back_populates="items", lazy="selectin")

    # Media subtype (Physical/Digital x Music/Films & TV/Books)
    media_subtype_id = Column(Integer, ForeignKey("media_subtypes.id", ondelete="RESTRICT"), nullable=False, index=True)
    media_subtype = relationship("MediaSubtype", lazy="selectin")

    # Digital platform (e.g. Netflix, Plex, Spotify)
    platform_id = Column(Integer, ForeignKey("platforms.id", ondelete="RESTRICT"), nullable=True, index=True)
    platform = relationship("Platform", lazy="selectin")

    # Films & TV — seasons/episodes owned (physical box sets or digital)
    seasons_owned = Column(String(100))
    episode_count = Column(Integer)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())
