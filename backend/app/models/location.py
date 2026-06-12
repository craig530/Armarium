from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    parent_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)
    icon_key = Column(String(50), nullable=True)     # key into the built-in icon set
    icon_path = Column(String(500), nullable=True)   # custom-uploaded icon, takes priority over icon_key
    sort_order = Column(Integer, nullable=False, default=0)

    parent = relationship("Location", remote_side=[id], back_populates="children", lazy="selectin")
    children = relationship("Location", back_populates="parent", lazy="selectin", order_by="Location.sort_order, Location.name")
    items = relationship("MediaItem", back_populates="location", lazy="select")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
