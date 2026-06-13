from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base


class PlexConfig(Base):
    """Singleton table holding the optional Plex server integration config.

    A single row (if present) represents the configured connection. Absence
    of a row means Plex integration has never been configured.
    """

    __tablename__ = "plex_config"

    id = Column(Integer, primary_key=True, index=True)
    base_url = Column(String(500), nullable=False)
    token = Column(String(500), nullable=False)
    enabled = Column(Boolean, nullable=False, default=False)

    # Platform that all synced digital media is filed under, e.g. "Plex".
    # Required so every sync run knows what counts as a duplicate vs. a
    # related copy on a different platform.
    platform_id = Column(Integer, ForeignKey("platforms.id", ondelete="RESTRICT"), nullable=False)
    platform = relationship("Platform", lazy="selectin")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
