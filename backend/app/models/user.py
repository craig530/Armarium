from sqlalchemy import Column, Integer, String, Boolean, DateTime, text, func
from datetime import datetime
from ..database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(200), nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Granular permissions for non-admin users. Admins bypass all of these.
    # `is_read_only` overrides the others — when set, every write action is
    # blocked regardless of the can_* flags.
    is_read_only = Column(Boolean, nullable=False, default=False, server_default=text("0"))
    can_add_items = Column(Boolean, nullable=False, default=True, server_default=text("1"))
    can_manage_locations = Column(Boolean, nullable=False, default=True, server_default=text("1"))
    can_manage_platforms = Column(Boolean, nullable=False, default=True, server_default=text("1"))
    can_manage_media_types = Column(Boolean, nullable=False, default=False, server_default=text("0"))

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())
