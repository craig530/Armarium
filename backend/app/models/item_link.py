from sqlalchemy import Column, Integer, DateTime, ForeignKey, Enum as SQLEnum, CheckConstraint, UniqueConstraint, func
from datetime import datetime
from ..database import Base
from .enums import LinkMatchType


class ItemLink(Base):
    __tablename__ = "item_links"
    __table_args__ = (
        # Also rules out self-links (item_a_id == item_b_id).
        CheckConstraint("item_a_id < item_b_id", name="ck_item_links_ordered"),
        UniqueConstraint("item_a_id", "item_b_id", name="uq_item_links_pair"),
    )

    id = Column(Integer, primary_key=True, index=True)
    item_a_id = Column(Integer, ForeignKey("media_items.id", ondelete="CASCADE"), nullable=False, index=True)
    item_b_id = Column(Integer, ForeignKey("media_items.id", ondelete="CASCADE"), nullable=False, index=True)
    matched_via = Column(SQLEnum(LinkMatchType), nullable=False, default=LinkMatchType.MANUAL)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())
