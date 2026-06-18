from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, CheckConstraint, func
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base


class PlexConfig(Base):
    """Singleton table holding the optional Plex server integration config.

    A single row (if present) represents the configured connection. Absence
    of a row means Plex integration has never been configured.
    """

    __tablename__ = "plex_config"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_plex_config_singleton"),
    )

    id = Column(Integer, primary_key=True, index=True)
    base_url = Column(String(500), nullable=False)
    token = Column(String(500), nullable=False)
    enabled = Column(Boolean, nullable=False, default=False)

    # Platform that all synced digital media is filed under, e.g. "Plex".
    # Required so every sync run knows what counts as a duplicate vs. a
    # related copy on a different platform.
    platform_id = Column(Integer, ForeignKey("platforms.id", ondelete="RESTRICT"), nullable=False)
    platform = relationship("Platform", lazy="selectin")

    # Plex server machine identifier — used to construct deep-link URLs.
    # Fetched from /identity at config-save time; None for configs saved before v1.4.2.
    machine_identifier = Column(String(100), nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())
