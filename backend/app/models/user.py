from sqlalchemy import Column, Integer, String, Boolean, DateTime, false, true, func
from datetime import datetime
from ..database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(200), nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    # System accounts (e.g. the "shared" pseudo-user) cannot log in and are
    # hidden from user-management UIs. is_active=False prevents JWT auth.
    is_system = Column(Boolean, nullable=False, default=False, server_default=false())

    # Granular permissions for non-admin users. Admins bypass all of these.
    # `is_read_only` overrides the others — when set, every write action is
    # blocked regardless of the can_* flags.
    is_read_only = Column(Boolean, nullable=False, default=False, server_default=false())
    can_add_items = Column(Boolean, nullable=False, default=True, server_default=true())
    can_manage_locations = Column(Boolean, nullable=False, default=True, server_default=true())
    can_manage_platforms = Column(Boolean, nullable=False, default=True, server_default=true())
    can_manage_media_types = Column(Boolean, nullable=False, default=False, server_default=false())
    can_manage_lists = Column(Boolean, nullable=False, default=True, server_default=true())
    # Allows non-admin users to add/edit/remove Plex sync schedules;
    # without it they can still see schedule info and trigger manual syncs.
    can_manage_schedules = Column(Boolean, nullable=False, default=True, server_default=true())

    # Optional display name shown in ownership labels and pickers. Falls back
    # to username when NULL.
    display_name = Column(String(100), nullable=True)

    # Per-user theme preference: 'auto' (follow OS), 'light', or 'dark'.
    theme_preference = Column(String(10), nullable=False, default='auto', server_default='auto')

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())
