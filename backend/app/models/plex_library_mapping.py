from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Enum as SQLEnum, func
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base
from .enums import MediaCategory


class PlexLibraryMapping(Base):
    """Links a Plex library section to one of our categories, and tracks when
    it was last synced. Synced items are filed under the platform configured
    on `PlexConfig`, shared across all mappings."""

    __tablename__ = "plex_library_mappings"

    id = Column(Integer, primary_key=True, index=True)
    section_key = Column(String(50), nullable=False, unique=True)
    section_title = Column(String(300), nullable=False)
    section_type = Column(String(20), nullable=False)  # movie | show | artist
    # create_type=False: the `mediacategory` Postgres enum type is already
    # created by MediaSubtype.category (the first table in creation order to
    # use it) — without this, Alembic would try to CREATE TYPE it again here
    # and fail with "type already exists" on PostgreSQL. No effect on SQLite.
    category = Column(SQLEnum(MediaCategory, create_type=False), nullable=False)

    # The media subtype synced items are filed under. Admin-set only — locked
    # (undeletable) on the media subtype while referenced here, so a sync can't
    # silently start filing items under a different type than the admin chose.
    media_subtype_id = Column(Integer, ForeignKey("media_subtypes.id", ondelete="RESTRICT"), nullable=True)
    media_subtype = relationship("MediaSubtype", lazy="selectin")

    last_synced_at = Column(DateTime, nullable=True)

    # Persisted result of the most recent completed sync (manual or scheduled)
    last_sync_status = Column(String(20), nullable=True)   # completed | error | cancelled
    last_sync_created = Column(Integer, nullable=True)
    last_sync_updated = Column(Integer, nullable=True)
    last_sync_removed = Column(Integer, nullable=True)
    last_sync_error = Column(String(1000), nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())
