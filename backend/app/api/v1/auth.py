import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...database import get_db
from ...models.user import User
from ...schemas.user import LoginRequest, TokenResponse, UserResponse
from ...services.auth import verify_password, create_access_token, get_current_user

router = APIRouter()

# Simple in-memory rate limiter for login attempts, keyed by client IP.
_LOGIN_WINDOW_SECONDS = 300
_LOGIN_MAX_ATTEMPTS = 10
_login_attempts: dict[str, list[float]] = defaultdict(list)


def _check_login_rate_limit(ip: str) -> None:
    now = time.monotonic()

    # Opportunistic cleanup so the dict doesn't grow unboundedly.
    if len(_login_attempts) > 1000:
        for key in list(_login_attempts):
            if all(now - t >= _LOGIN_WINDOW_SECONDS for t in _login_attempts[key]):
                del _login_attempts[key]

    attempts = [t for t in _login_attempts[ip] if now - t < _LOGIN_WINDOW_SECONDS]
    if len(attempts) >= _LOGIN_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please wait a few minutes and try again.",
        )
    attempts.append(now)
    _login_attempts[ip] = attempts


@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    _check_login_rate_limit(client_ip)

    result = await db.execute(select(User).where(User.username == credentials.username))
    user = result.scalar_one_or_none()

    if not user or not user.is_active or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = create_access_token(user.username, user.is_admin)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
