"""Tests for app.api.v1.schedules — admin maintenance schedule CRUD."""
import pytest

from .conftest import _create_user_and_login


# ── helpers ───────────────────────────────────────────────────────────────────

_VALID_JOB_TYPES = ["auto_link", "redownload_covers", "purge_covers", "export_covers", "backup"]


# ── GET /admin/schedules ──────────────────────────────────────────────────────

async def test_list_schedules_empty(client, auth_headers):
    resp = await client.get("/api/v1/admin/schedules", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_schedules_requires_admin(client, auth_headers):
    _, headers = await _create_user_and_login(client, auth_headers, "schedlistuser")
    resp = await client.get("/api/v1/admin/schedules", headers=headers)
    assert resp.status_code == 403


# ── GET /admin/schedules/{job_type} ──────────────────────────────────────────

async def test_get_schedule_none_returns_null(client, auth_headers):
    for job_type in _VALID_JOB_TYPES:
        resp = await client.get(f"/api/v1/admin/schedules/{job_type}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() is None


async def test_get_schedule_invalid_type_returns_400(client, auth_headers):
    resp = await client.get("/api/v1/admin/schedules/nonexistent_type", headers=auth_headers)
    assert resp.status_code == 400


# ── POST /admin/schedules/{job_type} ─────────────────────────────────────────

async def test_upsert_schedule_creates_and_reads_back(client, auth_headers):
    resp = await client.post(
        "/api/v1/admin/schedules/auto_link",
        json={"interval_hours": 24},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["job_type"] == "auto_link"
    assert body["interval_hours"] == 24
    assert body["id"] is not None

    # Verify GET returns it now.
    resp = await client.get("/api/v1/admin/schedules/auto_link", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["job_type"] == "auto_link"
    assert resp.json()["interval_hours"] == 24


async def test_upsert_schedule_updates_existing(client, auth_headers):
    await client.post(
        "/api/v1/admin/schedules/purge_covers",
        json={"interval_hours": 24},
        headers=auth_headers,
    )
    resp = await client.post(
        "/api/v1/admin/schedules/purge_covers",
        json={"interval_hours": 168},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["interval_hours"] == 168

    # List should still contain only one entry for purge_covers.
    resp = await client.get("/api/v1/admin/schedules", headers=auth_headers)
    purge_entries = [s for s in resp.json() if s["job_type"] == "purge_covers"]
    assert len(purge_entries) == 1


async def test_upsert_schedule_export_covers_with_base_dir(client, auth_headers):
    resp = await client.post(
        "/api/v1/admin/schedules/export_covers",
        json={"interval_hours": 24, "export_base_dir": "/mnt/covers"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["export_base_dir"] == "/mnt/covers"


@pytest.mark.parametrize("hours", [2, 0, -1, 999])
async def test_upsert_schedule_invalid_interval_rejected(client, auth_headers, hours):
    resp = await client.post(
        "/api/v1/admin/schedules/auto_link",
        json={"interval_hours": hours},
        headers=auth_headers,
    )
    assert resp.status_code == 400


async def test_upsert_schedule_invalid_job_type_rejected(client, auth_headers):
    resp = await client.post(
        "/api/v1/admin/schedules/plex_sync",  # plex_sync is not an admin job type
        json={"interval_hours": 24},
        headers=auth_headers,
    )
    assert resp.status_code == 400


async def test_upsert_schedule_requires_admin(client, auth_headers):
    _, headers = await _create_user_and_login(client, auth_headers, "schedcreateuser")
    resp = await client.post(
        "/api/v1/admin/schedules/auto_link",
        json={"interval_hours": 24},
        headers=headers,
    )
    assert resp.status_code == 403


# ── DELETE /admin/schedules/{job_type} ───────────────────────────────────────

async def test_delete_schedule(client, auth_headers):
    await client.post(
        "/api/v1/admin/schedules/redownload_covers",
        json={"interval_hours": 12},
        headers=auth_headers,
    )

    resp = await client.delete("/api/v1/admin/schedules/redownload_covers", headers=auth_headers)
    assert resp.status_code == 204

    resp = await client.get("/api/v1/admin/schedules/redownload_covers", headers=auth_headers)
    assert resp.json() is None


async def test_delete_schedule_not_found_returns_404(client, auth_headers):
    resp = await client.delete("/api/v1/admin/schedules/backup", headers=auth_headers)
    assert resp.status_code == 404


async def test_delete_schedule_requires_admin(client, auth_headers):
    _, headers = await _create_user_and_login(client, auth_headers, "scheddeluser")
    resp = await client.delete("/api/v1/admin/schedules/auto_link", headers=headers)
    assert resp.status_code == 403


# ── List of schedules includes all configured types ───────────────────────────

async def test_list_schedules_after_multiple_creates(client, auth_headers):
    for job_type in ["auto_link", "backup"]:
        await client.post(
            f"/api/v1/admin/schedules/{job_type}",
            json={"interval_hours": 24},
            headers=auth_headers,
        )

    resp = await client.get("/api/v1/admin/schedules", headers=auth_headers)
    assert resp.status_code == 200
    job_types = {s["job_type"] for s in resp.json()}
    assert {"auto_link", "backup"}.issubset(job_types)
