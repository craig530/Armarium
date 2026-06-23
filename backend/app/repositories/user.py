import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Sequence

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.user import User
from .base import BaseRepository

# How long a set-password link (invite, admin force-reset, or self-service
# forgot-password) stays valid. Issuing a new one (e.g. re-requesting
# forgot-password) overwrites/invalidates whatever was previously pending.
RESET_TOKEN_TTL = timedelta(hours=24)


def _hash_token(token: str) -> str:
    # The token is a high-entropy secrets.token_urlsafe value, not a
    # password, so an unsalted SHA-256 digest is fine here — this is for
    # safe-at-rest storage/lookup, not the same threat model as bcrypt.
    return hashlib.sha256(token.encode()).hexdigest()


class UserRepository(BaseRepository[User]):
    model = User

    async def list_ordered(self) -> Sequence[User]:
        return (await self.db.execute(select(User).order_by(User.created_at))).scalars().all()

    async def list_non_system(self) -> Sequence[User]:
        """All users except hidden system accounts (e.g. the shared pseudo-user)."""
        return (
            await self.db.execute(
                select(User).where(User.is_system.is_(False)).order_by(User.created_at)
            )
        ).scalars().all()

    async def get_by_username(self, username: str) -> Optional[User]:
        return (await self.db.execute(select(User).where(User.username == username))).scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        return (await self.db.execute(select(User).where(User.email == email))).scalar_one_or_none()

    async def find_by_valid_reset_token(self, token: str) -> Optional[User]:
        """The user whose current outstanding set-password token matches
        `token` and hasn't expired, or None."""
        user = (
            await self.db.execute(
                select(User).where(User.password_reset_token_hash == _hash_token(token))
            )
        ).scalar_one_or_none()
        if user is None or user.password_reset_expires_at is None:
            return None
        if user.password_reset_expires_at < datetime.utcnow():
            return None
        return user

    def issue_reset_token(self, user: User) -> str:
        """Generate a new set-password token for `user`, invalidating any
        previously issued one. Returns the raw token — only its hash is
        persisted, so this is the caller's only chance to see it (e.g. to
        build the link in the email)."""
        token = secrets.token_urlsafe(32)
        user.password_reset_token_hash = _hash_token(token)
        user.password_reset_expires_at = datetime.utcnow() + RESET_TOKEN_TTL
        return token

    def invalidate_password(self, user: User, placeholder_hashed_password: str) -> None:
        """Mark `user` as not having a usable password (mid-invite or
        mid-forced-reset) — the caller supplies an already-hashed unguessable
        placeholder (see services.auth.generate_unusable_password_hash)."""
        user.hashed_password = placeholder_hashed_password
        user.password_set = False

    def complete_password_set(self, user: User, hashed_password: str) -> None:
        """The user has successfully set their own password via a
        set-password link — caller supplies the already-hashed value."""
        user.hashed_password = hashed_password
        user.password_set = True
        user.password_reset_token_hash = None
        user.password_reset_expires_at = None

    async def get_shared_user(self) -> Optional[User]:
        return (
            await self.db.execute(
                select(User).where(User.username == "shared", User.is_system.is_(True))
            )
        ).scalar_one_or_none()

    async def count_admins(self) -> int:
        return (
            await self.db.execute(select(func.count(User.id)).where(User.is_admin.is_(True)))
        ).scalar_one()

    async def any_exist(self) -> bool:
        """True if any non-system user account exists (excludes the shared pseudo-user)."""
        return (
            await self.db.execute(
                select(User.id).where(User.is_system.is_(False)).limit(1)
            )
        ).scalar_one_or_none() is not None


async def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)
