"""Tests for app.api.v1.auth — login, current-user, and auth enforcement."""
import re

from .conftest import _create_user_and_login


def _token_from_email(sent_email: dict) -> str:
    match = re.search(r"token=([\w-]+)", sent_email["text"])
    assert match, f"No token found in email body: {sent_email['text']!r}"
    return match.group(1)


async def test_login_success(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "testpass123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


async def test_login_wrong_password(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


async def test_me(client, auth_headers):
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin"
    assert resp.json()["is_admin"] is True


# ── Cookie-based auth (browser SPA) ─────────────────────────────────────────

async def test_login_sets_httponly_cookie(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "testpass123"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.cookies

    set_cookie = resp.headers["set-cookie"]
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie


async def test_me_via_cookie_only(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "testpass123"},
    )
    assert resp.status_code == 200

    # No Authorization header — the cookie set above authenticates this request.
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin"


async def test_logout_clears_cookie(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "testpass123"},
    )
    assert resp.status_code == 200

    resp = await client.post("/api/v1/auth/logout")
    assert resp.status_code == 200

    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


# ── Auth enforcement ────────────────────────────────────────────────────────

async def test_media_requires_auth(client):
    resp = await client.get("/api/v1/media")
    assert resp.status_code == 401


async def test_locations_requires_auth(client):
    resp = await client.get("/api/v1/locations")
    assert resp.status_code == 401


# ── Forgot password / reset password ────────────────────────────────────────

GENERIC_FORGOT_PASSWORD_MSG = "If that account exists and has an email on file, a reset link has been sent."


async def test_forgot_password_unknown_account_generic_response(client):
    resp = await client.post("/api/v1/auth/forgot-password", json={"username_or_email": "nobody-home"})
    assert resp.status_code == 200
    assert resp.json()["detail"] == GENERIC_FORGOT_PASSWORD_MSG


async def test_forgot_password_super_admin_is_exempt(client, sent_emails):
    """Requesting a reset for the env-defined super-admin gets the same
    generic response and issues no token/email — see ARCHITECTURE.md §4.4."""
    resp = await client.post("/api/v1/auth/forgot-password", json={"username_or_email": "admin"})
    assert resp.status_code == 200
    assert resp.json()["detail"] == GENERIC_FORGOT_PASSWORD_MSG
    assert sent_emails == []

    # The admin's existing password still works — nothing was reset.
    resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "testpass123"})
    assert resp.status_code == 200


async def test_forgot_password_requires_email_configured(client, monkeypatch):
    from app.services import email as email_service

    monkeypatch.setattr(email_service, "is_configured", lambda: False)

    resp = await client.post("/api/v1/auth/forgot-password", json={"username_or_email": "admin"})
    assert resp.status_code == 503


async def test_forgot_password_rate_limited(client):
    from app.api.v1.auth import forgot_password_limiter

    for _ in range(5):
        forgot_password_limiter.check("127.0.0.1", "limited")

    resp = await client.post("/api/v1/auth/forgot-password", json={"username_or_email": "nobody-home"})
    assert resp.status_code == 429
    forgot_password_limiter.reset()


async def test_forgot_password_and_reset_round_trip(client, auth_headers, sent_emails):
    """Full flow: an existing user's old password keeps working until they
    actually redeem the reset link (self-service forgot-password must never
    lock someone out just because someone else requested it)."""
    user, _ = await _create_user_and_login(client, auth_headers, "forgotpassworduser")
    sent_emails.clear()  # drop the invite email triggered by creating the user above

    resp = await client.post(
        "/api/v1/auth/forgot-password", json={"username_or_email": "forgotpassworduser@example.com"}
    )
    assert resp.status_code == 200
    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == "forgotpassworduser@example.com"
    token = _token_from_email(sent_emails[0])

    # Old password still works — forgot-password doesn't invalidate it.
    resp = await client.post(
        "/api/v1/auth/login", json={"username": "forgotpassworduser", "password": "userpass123"}
    )
    assert resp.status_code == 200

    resp = await client.get(f"/api/v1/auth/reset-password/{token}")
    assert resp.status_code == 200
    assert resp.json()["valid"] is True

    resp = await client.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": "brandnewpass456"}
    )
    assert resp.status_code == 200

    # Old password no longer works; the new one does.
    resp = await client.post(
        "/api/v1/auth/login", json={"username": "forgotpassworduser", "password": "userpass123"}
    )
    assert resp.status_code == 401
    resp = await client.post(
        "/api/v1/auth/login", json={"username": "forgotpassworduser", "password": "brandnewpass456"}
    )
    assert resp.status_code == 200

    # The token is single-use.
    resp = await client.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": "anotherpass789"}
    )
    assert resp.status_code == 400

    resp = await client.delete(f"/api/v1/users/{user['id']}", headers=auth_headers)
    assert resp.status_code == 204


async def test_reset_password_invalid_token(client):
    resp = await client.get("/api/v1/auth/reset-password/not-a-real-token")
    assert resp.status_code == 200
    assert resp.json()["valid"] is False

    resp = await client.post(
        "/api/v1/auth/reset-password", json={"token": "not-a-real-token", "new_password": "whatever123"}
    )
    assert resp.status_code == 400


async def test_login_rejects_pending_invite(client, auth_headers):
    """A user who hasn't completed their invite (no usable password yet)
    can't log in with any password, including the placeholder hash."""
    resp = await client.post(
        "/api/v1/users",
        json={"username": "pendinguser", "email": "pendinguser@example.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    user = resp.json()
    assert user["password_set"] is False

    resp = await client.post(
        "/api/v1/auth/login", json={"username": "pendinguser", "password": "anything-at-all"}
    )
    assert resp.status_code == 401

    resp = await client.delete(f"/api/v1/users/{user['id']}", headers=auth_headers)
    assert resp.status_code == 204
