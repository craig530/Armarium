from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, UniqueConstraint
from datetime import datetime
from ..database import Base
from .enums import MediaCategory, Supertype


class MediaSubtype(Base):
    __tablename__ = "media_subtypes"
    __table_args__ = (
        UniqueConstraint("category", "supertype", "name", name="uq_media_subtype_category_supertype_name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    category = Column(SQLEnum(MediaCategory), nullable=False, index=True)
    supertype = Column(SQLEnum(Supertype), nullable=False, index=True)
    sort_order = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
