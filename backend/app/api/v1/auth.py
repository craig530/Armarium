import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status

from ...config import settings
from ...models.user import User
from ...repositories.user import UserRepository, get_user_repository
from ...schemas.user import (
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    ResetTokenValidityResponse,
    TokenResponse,
    UserResponse,
)
from ...services import email as email_service
from ...services.auth import (
    ACCESS_TOKEN_COOKIE_NAME,
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)
from ...services.rate_limit import SlidingWindowRateLimiter

router = APIRouter()
logger = logging.getLogger("armarium.auth")

# In-memory rate limiter for login attempts, keyed by client IP.
login_limiter = SlidingWindowRateLimiter(max_attempts=10, window_seconds=300)
# Same idea for forgot-password requests — a few per IP per window is
# plenty for legitimate use and limits enumeration/spam.
forgot_password_limiter = SlidingWindowRateLimiter(max_attempts=5, window_seconds=300)


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

    if (
        not user
        or not user.is_active
        or not user.password_set
        or not verify_password(credentials.password, user.hashed_password)
    ):
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
    resp = UserResponse.model_validate(current_user)
    resp.is_protected_super_admin = current_user.username == settings.admin_username
    return resp


async def _send_reset_email(to: str, username: str, base_url: str, token: str) -> None:
    link = f"{base_url}/set-password?token={token}"
    subject, text, html = email_service.build_reset_email(username, link)
    await email_service.send_email_logged(to, subject, text, html)


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    repo: UserRepository = Depends(get_user_repository),
):
    """Always responds the same way regardless of whether the account
    exists, to avoid leaking which usernames/emails are registered. The
    env-defined super-admin and system accounts are never eligible — see
    ARCHITECTURE.md §4.4.
    """
    client_ip = request.client.host if request.client else "unknown"
    forgot_password_limiter.check(client_ip, "Too many requests. Please wait a few minutes and try again.")

    if not email_service.is_configured():
        raise HTTPException(status_code=503, detail="Email is not configured on this server")

    generic_response = {"detail": "If that account exists and has an email on file, a reset link has been sent."}

    identifier = payload.username_or_email.strip()
    user = await repo.get_by_username(identifier) or await repo.get_by_email(identifier)
    if (
        user is None
        or user.username == settings.admin_username
        or user.is_system
        or not user.is_active
        or not user.email
    ):
        return generic_response

    token = repo.issue_reset_token(user)
    await repo.commit()

    base_url = email_service.resolve_base_url(str(request.base_url))
    background_tasks.add_task(_send_reset_email, user.email, user.username, base_url, token)

    return generic_response


@router.get("/reset-password/{token}", response_model=ResetTokenValidityResponse)
async def check_reset_token(token: str, repo: UserRepository = Depends(get_user_repository)):
    user = await repo.find_by_valid_reset_token(token)
    return ResetTokenValidityResponse(valid=user is not None)


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, repo: UserRepository = Depends(get_user_repository)):
    user = await repo.find_by_valid_reset_token(payload.token)
    if user is None:
        raise HTTPException(status_code=400, detail="This link is invalid or has expired")

    repo.complete_password_set(user, hash_password(payload.new_password))
    await repo.commit()
    return {"detail": "Password updated"}
