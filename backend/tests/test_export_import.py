"""Tests for app.api.v1.export_import — library export/import and backups."""
from .conftest import _create_user_and_login, _subtype_id


async def test_export_json(client, auth_headers):
    resp = await client.get("/api/v1/library/export?format=json", headers=auth_headers)
    assert resp.status_code == 200
    assert "items" in resp.json()


async def test_export_csv(client, auth_headers):
    resp = await client.get("/api/v1/library/export?format=csv", headers=auth_headers)
    assert resp.status_code == 200
    assert b"title" in resp.content


async def test_import_csv_validates_foreign_keys(client, auth_headers):
    """Imported rows referencing locations/platforms/subtypes that don't
    exist must not create dangling foreign keys — invalid location/platform
    references are nulled, and rows with an unresolvable subtype are
    skipped."""
    import csv
    import io
    from app.api.v1.export_import import CSV_FIELDS

    cd_id = await _subtype_id(client, auth_headers, "CD")

    rows = [
        # Valid subtype, but location_id/platform_id point at rows that don't exist.
        {"title": "Imported Orphaned CD", "media_subtype_id": cd_id, "location_id": 999999, "platform_id": 999999},
        # media_subtype_id doesn't exist -> row is skipped entirely.
        {"title": "Imported Unknown Subtype", "media_subtype_id": 999999},
    ]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

    files = {"file": ("import.csv", output.getvalue().encode(), "text/csv")}
    resp = await client.post("/api/v1/library/import?format=csv", files=files, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == {"imported": 1, "skipped": 1}

    resp = await client.get("/api/v1/media?q=Imported+Orphaned+CD", headers=auth_headers)
    items = resp.json()["items"]
    assert len(items) == 1
    item = items[0]
    assert item["location_id"] is None
    assert item["platform_id"] is None

    resp = await client.delete(f"/api/v1/media/{item['id']}", headers=auth_headers)
    assert resp.status_code == 204


# ── Backups ───────────────────────────────────────────────────────────────────

async def test_backup_list_download_delete(client, auth_headers):
    from pathlib import Path
    from app.config import settings

    backup_dir = Path(settings.backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    name = "armarium_20260101_120000.db"
    (backup_dir / name).write_bytes(b"fake-db-contents")

    resp = await client.get("/api/v1/library/backup/list", headers=auth_headers)
    assert resp.status_code == 200
    assert any(b["name"] == name for b in resp.json()["backups"])

    resp = await client.get(f"/api/v1/library/backup/{name}/download", headers=auth_headers)
    assert resp.status_code == 200

    resp = await client.delete(f"/api/v1/library/backup/{name}", headers=auth_headers)
    assert resp.status_code == 204

    resp = await client.get("/api/v1/library/backup/list", headers=auth_headers)
    assert resp.status_code == 200
    assert not any(b["name"] == name for b in resp.json()["backups"])


async def test_backup_delete_unknown_or_invalid_name(client, auth_headers):
    resp = await client.delete("/api/v1/library/backup/does_not_exist.db", headers=auth_headers)
    assert resp.status_code == 400

    resp = await client.delete("/api/v1/library/backup/armarium_20260101_000000.db", headers=auth_headers)
    assert resp.status_code == 404


async def test_backup_delete_requires_admin(client, auth_headers):
    _, headers = await _create_user_and_login(client, auth_headers, "backupuser")

    resp = await client.delete("/api/v1/library/backup/armarium_20260101_000000.db", headers=headers)
    assert resp.status_code == 403
