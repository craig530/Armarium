from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Table, UniqueConstraint, func
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base
from .enums import MediaCategory

# Many-to-many association between MediaItem and ItemList.
media_item_lists = Table(
    "media_item_lists",
    Base.metadata,
    Column("media_item_id", Integer, ForeignKey("media_items.id", ondelete="CASCADE"), primary_key=True),
    Column("item_list_id", Integer, ForeignKey("item_lists.id", ondelete="CASCADE"), primary_key=True, index=True),
)


class ItemList(Base):
    __tablename__ = "item_lists"
    __table_args__ = (
        UniqueConstraint("category", "owner_id", "name", name="uq_item_lists_category_owner_name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    category = Column(SQLEnum(MediaCategory), nullable=False, index=True)

    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    owner = relationship("User", foreign_keys=[owner_id], lazy="selectin")

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())
