from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum
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
    category = Column(SQLEnum(MediaCategory), nullable=False)

    last_synced_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
