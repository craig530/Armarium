from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from ..database import Base


class ItemLink(Base):
    __tablename__ = "item_links"

    id = Column(Integer, primary_key=True, index=True)
    item_a_id = Column(Integer, ForeignKey("media_items.id", ondelete="CASCADE"), nullable=False, index=True)
    item_b_id = Column(Integer, ForeignKey("media_items.id", ondelete="CASCADE"), nullable=False, index=True)
    matched_via = Column(String(20), nullable=False, default="manual")  # "auto" | "manual"

    created_at = Column(DateTime, default=datetime.utcnow)
