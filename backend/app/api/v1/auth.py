from fastapi import APIRouter, Depends, HTTPException, Request, status

from ...models.user import User
from ...repositories.user import UserRepository, get_user_repository
from ...schemas.user import LoginRequest, TokenResponse, UserResponse
from ...services.auth import verify_password, create_access_token, get_current_user
from ...services.rate_limit import SlidingWindowRateLimiter

router = APIRouter()

# In-memory rate limiter for login attempts, keyed by client IP.
login_limiter = SlidingWindowRateLimiter(max_attempts=10, window_seconds=300)


@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest, request: Request, repo: UserRepository = Depends(get_user_repository)):
    client_ip = request.client.host if request.client else "unknown"
    login_limiter.check(client_ip, "Too many login attempts. Please wait a few minutes and try again.")

    user = await repo.get_by_username(credentials.username)

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
