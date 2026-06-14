from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from ..config import settings
from ..repositories.user import UserRepository, get_user_repository

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# auto_error=False: a missing Bearer header isn't fatal on its own —
# get_current_user falls back to the access_token cookie before rejecting.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

# httpOnly cookie the browser SPA authenticates with, set by POST /auth/login
# and cleared by POST /auth/logout. API clients can instead send
# `Authorization: Bearer <token>` using the same token from the login response.
ACCESS_TOKEN_COOKIE_NAME = "access_token"

_credentials_exc = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(username: str, is_admin: bool) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": username, "is_admin": is_admin, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    repo: UserRepository = Depends(get_user_repository),
):
    token = token or request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)
    if not token:
        raise _credentials_exc

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        username: Optional[str] = payload.get("sub")
        if not username:
            raise _credentials_exc
    except JWTError:
        raise _credentials_exc

    user = await repo.get_by_username(username)
    if not user or not user.is_active:
        raise _credentials_exc
    return user


async def get_current_admin(current_user=Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


def require_permission(permission: str):
    """Dependency factory: only admins, or non-read-only users with the
    given `permission` flag set, may proceed.

    Admins bypass all checks. `is_read_only` overrides every other flag.
    """
    async def checker(current_user=Depends(get_current_user)):
        if current_user.is_admin:
            return current_user
        if current_user.is_read_only or not getattr(current_user, permission, False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to perform this action",
            )
        return current_user

    return checker
