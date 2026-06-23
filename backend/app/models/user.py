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

    # Nullable: existing accounts, the env-defined super-admin, and the
    # "shared" system user predate/don't need this. Required (at the schema
    # level, not here) for newly invited users — it's their only way to
    # receive a set-password link.
    email = Column(String(255), nullable=True, unique=True, index=True)

    # False while a user is mid-invite or mid-forced-reset: hashed_password
    # is an unusable random placeholder and only the emailed link can set a
    # real one. True (the default) for existing accounts, which already log
    # in with a real password today.
    password_set = Column(Boolean, nullable=False, default=True, server_default=true())
    # SHA-256 hex digest of the current outstanding set-password token (the
    # token itself is a high-entropy secrets.token_urlsafe value, so an
    # unsalted hash is fine here — this isn't a password). One token at a
    # time per user; issuing a new one overwrites the previous.
    password_reset_token_hash = Column(String(64), nullable=True, unique=True, index=True)
    password_reset_expires_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())
