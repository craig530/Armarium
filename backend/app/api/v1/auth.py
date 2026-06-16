import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from ...config import settings
from ...models.user import User
from ...repositories.user import UserRepository, get_user_repository
from ...schemas.user import LoginRequest, TokenResponse, UserResponse
from ...services.auth import (
    ACCESS_TOKEN_COOKIE_NAME,
    verify_password,
    create_access_token,
    get_current_user,
)
from ...services.rate_limit import SlidingWindowRateLimiter

router = APIRouter()
logger = logging.getLogger("armarium.auth")

# In-memory rate limiter for login attempts, keyed by client IP.
login_limiter = SlidingWindowRateLimiter(max_attempts=10, window_seconds=300)


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: LoginRequest,
    request: Request,
    response: Response,
    repo: UserRepository = Depends(get_user_repository),
):
    client_ip = request.client.host if request.client else "unknown"
    login_limiter.check(client_ip, "Too many login attempts. Please wait a few minutes and try again.")

    user = await repo.get_by_username(credentials.username)

    if not user or not user.is_active or not verify_password(credentials.password, user.hashed_password):
        logger.warning("Failed login attempt for username=%r from ip=%s", credentials.username, client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = create_access_token(user.username, user.is_admin)

    # The browser SPA authenticates via this httpOnly cookie; the token is
    # also returned in the body for API clients (see README import/backup
    # examples), which send it as an `Authorization: Bearer` header instead.
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        value=token,
        max_age=settings.jwt_expire_minutes * 60,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )
    return TokenResponse(access_token=token)


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(ACCESS_TOKEN_COOKIE_NAME, path="/")
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
