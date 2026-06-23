"""Tests for app.api.v1.users — CRUD, permissions, and admin safeguards."""
from .conftest import _create_user_and_login, _set_password_directly, _subtype_id


async def test_create_user_default_permissions(client, auth_headers):
    resp = await client.post(
        "/api/v1/users",
        json={"username": "defaultuser", "email": "defaultuser@example.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    user = resp.json()
    assert user["email"] == "defaultuser@example.com"
    # No password is set at creation — the user gets one via the emailed
    # set-password link (see test_create_user_requires_email_configured and
    # the force-password-reset tests for the token flow itself).
    assert user["password_set"] is False
    assert user["is_admin"] is False
    assert user["is_system"] is False
    assert user["is_read_only"] is False
    assert user["can_add_items"] is True
    assert user["can_manage_locations"] is True
    assert user["can_manage_platforms"] is True
    assert user["can_manage_media_types"] is False
    assert user["can_manage_lists"] is True
    assert user["can_manage_schedules"] is True

    resp = await client.delete(f"/api/v1/users/{user['id']}", headers=auth_headers)
    assert resp.status_code == 204


async def test_create_user_requires_email_configured(client, auth_headers, monkeypatch):
    """Creating a user with no way to ever invite them (SMTP unconfigured)
    is rejected outright rather than leaving a permanently unusable account."""
    from app.services import email as email_service

    monkeypatch.setattr(email_service, "is_configured", lambda: False)

    resp = await client.post(
        "/api/v1/users",
        json={"username": "noemailservice", "email": "noemailservice@example.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 503


async def test_create_user_duplicate_email_rejected(client, auth_headers):
    resp = await client.post(
        "/api/v1/users",
        json={"username": "dupemail1", "email": "dupe@example.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    user = resp.json()

    resp = await client.post(
        "/api/v1/users",
        json={"username": "dupemail2", "email": "dupe@example.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 409

    resp = await client.delete(f"/api/v1/users/{user['id']}", headers=auth_headers)
    assert resp.status_code == 204


async def test_force_password_reset(client, auth_headers):
    resp = await client.post(
        "/api/v1/users",
        json={"username": "resettarget", "email": "resettarget@example.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    user = resp.json()
    await _set_password_directly("resettarget", "originalpass123")

    resp = await client.post(f"/api/v1/users/{user['id']}/force-password-reset", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["password_set"] is False

    # The old password no longer works.
    resp = await client.post(
        "/api/v1/auth/login", json={"username": "resettarget", "password": "originalpass123"}
    )
    assert resp.status_code == 401

    resp = await client.delete(f"/api/v1/users/{user['id']}", headers=auth_headers)
    assert resp.status_code == 204


async def test_force_password_reset_unknown_user_404(client, auth_headers):
    resp = await client.post("/api/v1/users/999999/force-password-reset", headers=auth_headers)
    assert resp.status_code == 404


async def test_force_password_reset_rejects_super_admin(client, auth_headers):
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    admin_id = resp.json()["id"]
    assert resp.json()["is_protected_super_admin"] is True

    resp = await client.post(f"/api/v1/users/{admin_id}/force-password-reset", headers=auth_headers)
    assert resp.status_code == 403


async def test_force_password_reset_rejects_system_user(client, auth_headers):
    resp = await client.get("/api/v1/users", headers=auth_headers)
    # The "shared" system user is excluded from /users entirely (it's
    # filtered out of list_non_system), so resolve its id via a raw lookup.
    from app.database import AsyncSessionLocal
    from app.repositories.user import UserRepository

    async with AsyncSessionLocal() as db:
        shared = await UserRepository(db).get_shared_user()
        shared_id = shared.id

    resp = await client.post(f"/api/v1/users/{shared_id}/force-password-reset", headers=auth_headers)
    assert resp.status_code == 403


async def test_force_password_reset_requires_admin(client, auth_headers):
    _, headers = await _create_user_and_login(client, auth_headers, "notanadmin")
    resp = await client.get("/api/v1/users", headers=auth_headers)
    target = next(u for u in resp.json() if u["username"] == "notanadmin")

    resp = await client.post(f"/api/v1/users/{target['id']}/force-password-reset", headers=headers)
    assert resp.status_code == 403

    resp = await client.delete(f"/api/v1/users/{target['id']}", headers=auth_headers)
    assert resp.status_code == 204


async def test_user_summary_excludes_system_users(client, auth_headers):
    resp = await client.get("/api/v1/users/summary", headers=auth_headers)
    assert resp.status_code == 200
    usernames = [u["username"] for u in resp.json()]
    assert "shared" not in usernames


async def test_admin_user_list_excludes_system_users(client, auth_headers):
    resp = await client.get("/api/v1/users", headers=auth_headers)
    assert resp.status_code == 200
    usernames = [u["username"] for u in resp.json()]
    assert "shared" not in usernames


async def test_create_user_custom_permissions(client, auth_headers):
    resp = await client.post(
        "/api/v1/users",
        json={
            "username": "customuser",
            "email": "customuser@example.com",
            "is_read_only": True,
            "can_add_items": False,
            "can_manage_locations": False,
            "can_manage_platforms": False,
            "can_manage_media_types": True,
            "can_manage_lists": False,
            "can_manage_schedules": False,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    user = resp.json()
    assert user["is_read_only"] is True
    assert user["can_add_items"] is False
    assert user["can_manage_locations"] is False
    assert user["can_manage_platforms"] is False
    assert user["can_manage_media_types"] is True
    assert user["can_manage_lists"] is False
    assert user["can_manage_schedules"] is False

    resp = await client.delete(f"/api/v1/users/{user['id']}", headers=auth_headers)
    assert resp.status_code == 204


async def test_non_admin_cannot_manage_users(client, auth_headers):
    user, headers = await _create_user_and_login(client, auth_headers, "plainuser")

    resp = await client.get("/api/v1/users", headers=headers)
    assert resp.status_code == 403

    resp = await client.post(
        "/api/v1/users", json={"username": "another", "email": "another@example.com"}, headers=headers
    )
    assert resp.status_code == 403

    resp = await client.delete(f"/api/v1/users/{user['id']}", headers=auth_headers)
    assert resp.status_code == 204


async def test_can_add_items_permission_enforced(client, auth_headers):
    cd_id = await _subtype_id(client, auth_headers, "CD")
    user, headers = await _create_user_and_login(client, auth_headers, "noadditemsuser", can_add_items=False)

    resp = await client.post(
        "/api/v1/media",
        json={"title": "Forbidden Item", "media_subtype_id": cd_id},
        headers=headers,
    )
    assert resp.status_code == 403

    # Read access is unaffected.
    resp = await client.get("/api/v1/media", headers=headers)
    assert resp.status_code == 200

    resp = await client.delete(f"/api/v1/users/{user['id']}", headers=auth_headers)
    assert resp.status_code == 204


async def test_is_read_only_overrides_all_permissions(client, auth_headers):
    cd_id = await _subtype_id(client, auth_headers, "CD")
    user, headers = await _create_user_and_login(client, auth_headers, "readonlyuser", is_read_only=True)

    resp = await client.post("/api/v1/locations", json={"name": "Read Only Shelf"}, headers=headers)
    assert resp.status_code == 403

    resp = await client.post(
        "/api/v1/media",
        json={"title": "Read Only Item", "media_subtype_id": cd_id},
        headers=headers,
    )
    assert resp.status_code == 403

    resp = await client.delete(f"/api/v1/users/{user['id']}", headers=auth_headers)
    assert resp.status_code == 204


async def test_can_manage_media_types_permission_enforced(client, auth_headers):
    # Default for new users is can_manage_media_types=False.
    user, headers = await _create_user_and_login(client, auth_headers, "subtypeuser")

    subtype_payload = {"name": "Vinyl", "category": "music", "supertype": "physical", "sort_order": 50}
    resp = await client.post("/api/v1/media-subtypes", json=subtype_payload, headers=headers)
    assert resp.status_code == 403

    resp = await client.put(
        f"/api/v1/users/{user['id']}", json={"can_manage_media_types": True}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["can_manage_media_types"] is True

    resp = await client.post("/api/v1/media-subtypes", json=subtype_payload, headers=headers)
    assert resp.status_code == 201, resp.text
    subtype_id = resp.json()["id"]

    resp = await client.delete(f"/api/v1/media-subtypes/{subtype_id}", headers=auth_headers)
    assert resp.status_code == 204
    resp = await client.delete(f"/api/v1/users/{user['id']}", headers=auth_headers)
    assert resp.status_code == 204


async def test_admin_bypasses_permission_checks(client, auth_headers):
    """An admin retains full access even with restrictive permission flags set."""
    resp = await client.post(
        "/api/v1/users",
        json={
            "username": "superadmin",
            "email": "superadmin@example.com",
            "is_admin": True,
            "is_read_only": True,
            "can_add_items": False,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    user = resp.json()
    await _set_password_directly("superadmin", "userpass123")

    resp = await client.post("/api/v1/auth/login", json={"username": "superadmin", "password": "userpass123"})
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    cd_id = await _subtype_id(client, auth_headers, "CD")
    resp = await client.post(
        "/api/v1/media",
        json={"title": "Admin Override Item", "media_subtype_id": cd_id},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    item_id = resp.json()["id"]

    resp = await client.delete(f"/api/v1/media/{item_id}", headers=auth_headers)
    assert resp.status_code == 204
    resp = await client.delete(f"/api/v1/users/{user['id']}", headers=auth_headers)
    assert resp.status_code == 204


async def test_cannot_demote_deactivate_or_delete_self(client, auth_headers):
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    me = resp.json()

    resp = await client.put(f"/api/v1/users/{me['id']}", json={"is_admin": False}, headers=auth_headers)
    assert resp.status_code == 400

    resp = await client.put(f"/api/v1/users/{me['id']}", json={"is_active": False}, headers=auth_headers)
    assert resp.status_code == 400

    resp = await client.delete(f"/api/v1/users/{me['id']}", headers=auth_headers)
    assert resp.status_code == 400


async def test_last_admin_cannot_be_demoted_by_others(client, auth_headers):
    """With two admins, one can be demoted; the resulting sole admin is protected."""
    resp = await client.post(
        "/api/v1/users",
        json={"username": "coadmin", "email": "coadmin@example.com", "is_admin": True},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    coadmin = resp.json()
    await _set_password_directly("coadmin", "userpass123")

    resp = await client.post("/api/v1/auth/login", json={"username": "coadmin", "password": "userpass123"})
    coadmin_headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    # Two admins exist — coadmin may demote the original admin... except that's
    # "admin"'s own account from coadmin's perspective it's not self, but
    # demoting the *only remaining* admin afterwards is blocked.
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    admin_id = resp.json()["id"]

    resp = await client.put(f"/api/v1/users/{admin_id}", json={"is_admin": False}, headers=coadmin_headers)
    assert resp.status_code == 200
    assert resp.json()["is_admin"] is False

    # Now "coadmin" is the sole admin — coadmin cannot demote themselves either.
    resp = await client.put(f"/api/v1/users/{coadmin['id']}", json={"is_admin": False}, headers=coadmin_headers)
    assert resp.status_code == 400

    # Restore "admin" to admin (using coadmin's credentials) for other tests, then clean up coadmin.
    resp = await client.put(f"/api/v1/users/{admin_id}", json={"is_admin": True}, headers=coadmin_headers)
    assert resp.status_code == 200

    resp = await client.delete(f"/api/v1/users/{coadmin['id']}", headers=auth_headers)
    assert resp.status_code == 204
