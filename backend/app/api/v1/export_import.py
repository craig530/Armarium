from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse, FileResponse
from typing import Optional
import csv
import io
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
import shutil

from ...models.media import MediaItem
from ...models.enums import Supertype
from ...repositories.location import LocationRepository, get_location_repository
from ...repositories.media_item import MediaItemRepository, get_media_item_repository
from ...repositories.media_subtype import MediaSubtypeRepository, get_media_subtype_repository
from ...repositories.platform import PlatformRepository, get_platform_repository
from ...schemas.media import MediaItemCreate
from ...services.auth import get_current_user, get_current_admin
from ...config import settings

router = APIRouter()

BACKUP_NAME_PATTERN = re.compile(r"^armarium_\d{8}_\d{6}\.db$")

CSV_FIELDS = [
    "title", "media_subtype_id", "year", "genres", "edition", "barcode",
    "location_id", "platform_id",
    "artist", "label", "track_count",
    "director", "studio", "runtime_minutes", "rating", "cast_list",
    "seasons_owned", "episode_count",
    "author", "publisher", "page_count", "isbn", "language",
    "description", "notes",
    "musicbrainz_id", "tmdb_id", "openlibrary_id",
    "cover_image_url", "created_at",
]


def _item_to_row(item: MediaItem) -> dict:
    return {f: getattr(item, f, None) for f in CSV_FIELDS}


def _row_to_create(row: dict) -> Optional[MediaItemCreate]:
    try:
        # Type coerce numeric strings
        for int_field in ("year", "track_count", "runtime_minutes", "page_count", "tmdb_id", "media_subtype_id", "episode_count", "location_id", "platform_id"):
            if row.get(int_field):
                row[int_field] = int(row[int_field]) if str(row[int_field]).strip() else None
            else:
                row[int_field] = None
        # Strip created_at — it's export-only
        row.pop("created_at", None)
        return MediaItemCreate(**{k: v or None for k, v in row.items()})
    except Exception:
        return None


@router.get("/export")
async def export_library(
    format: str = Query("json", pattern="^(json|csv)$"),
    _=Depends(get_current_user),
    repo: MediaItemRepository = Depends(get_media_item_repository),
):
    """Export the full library as JSON or CSV."""
    items = await repo.list(MediaItem.title)

    if format == "json":
        data = [
            {f: getattr(it, f, None) for f in CSV_FIELDS + ["id"]}
            for it in items
        ]
        content = json.dumps(
            {"exported_at": datetime.utcnow().isoformat(), "count": len(data), "items": data},
            indent=2,
            default=str,
        )
        return StreamingResponse(
            io.BytesIO(content.encode()),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=armarium-export.json"},
        )

    # CSV
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for item in items:
        writer.writerow(_item_to_row(item))

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=armarium-export.csv"},
    )


@router.get("/export/covers")
async def export_covers(_=Depends(get_current_admin)):
    """Export all user-downloaded/uploaded cover images as a zip (admin only)."""
    covers_dir = Path(settings.covers_dir)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        if covers_dir.exists():
            for file in covers_dir.rglob("*"):
                if file.is_file():
                    zf.write(file, file.relative_to(covers_dir))
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=armarium-covers.zip"},
    )


@router.post("/import")
async def import_library(
    file: UploadFile = File(...),
    format: str = Query("csv", pattern="^(json|csv)$"),
    _=Depends(get_current_admin),
    media_repo: MediaItemRepository = Depends(get_media_item_repository),
    subtype_repo: MediaSubtypeRepository = Depends(get_media_subtype_repository),
    location_repo: LocationRepository = Depends(get_location_repository),
    platform_repo: PlatformRepository = Depends(get_platform_repository),
):
    """
    Bulk import media items from a CSV or JSON file.
    Admin only. CSV must match the export format (header row required).
    """
    content = await file.read()

    if format == "json":
        try:
            payload = json.loads(content)
            rows = payload if isinstance(payload, list) else payload.get("items", [])
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    else:
        reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
        rows = list(reader)

    # Validate foreign keys against what actually exists, rather than letting
    # stale/foreign ids from an old export create dangling references.
    subtype_supertypes = await subtype_repo.supertype_map()
    valid_locations = await location_repo.existing_ids()
    valid_platforms = await platform_repo.existing_ids()

    created, skipped = 0, 0
    for row in rows:
        item_create = _row_to_create(dict(row))
        if item_create is None:
            skipped += 1
            continue

        supertype = subtype_supertypes.get(item_create.media_subtype_id)
        if supertype is None:
            skipped += 1
            continue

        if supertype != Supertype.PHYSICAL or item_create.location_id not in valid_locations:
            item_create.location_id = None
        if supertype != Supertype.DIGITAL or item_create.platform_id not in valid_platforms:
            item_create.platform_id = None

        media_repo.add(MediaItem(**item_create.model_dump()))
        created += 1

    await media_repo.commit()
    return {"imported": created, "skipped": skipped}


@router.post("/backup")
async def trigger_backup(_=Depends(get_current_admin)):
    """Create a timestamped backup of the SQLite database (admin only)."""
    if "sqlite" not in settings.database_url:
        raise HTTPException(status_code=400, detail="Backup only supported for SQLite databases")

    db_path = Path(settings.database_url.replace("sqlite+aiosqlite:///", ""))
    if not db_path.exists():
        raise HTTPException(status_code=404, detail="Database file not found")

    backup_dir = Path(settings.backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = backup_dir / f"armarium_{timestamp}.db"
    shutil.copy2(db_path, dest)

    # Retain only the 30 most recent backups
    backups = sorted(backup_dir.glob("armarium_*.db"))
    for old in backups[:-30]:
        old.unlink(missing_ok=True)

    return {"backup": dest.name, "size_bytes": dest.stat().st_size}


@router.get("/backup/list")
async def list_backups(_=Depends(get_current_admin)):
    """List available database backups (admin only)."""
    backup_supported = "sqlite" in settings.database_url
    backup_dir = Path(settings.backup_dir)
    if not backup_dir.exists():
        return {"backups": [], "backup_supported": backup_supported}

    backups = sorted(backup_dir.glob("armarium_*.db"), reverse=True)
    return {
        "backups": [
            {"name": b.name, "size_bytes": b.stat().st_size, "created": datetime.fromtimestamp(b.stat().st_mtime).isoformat()}
            for b in backups
        ],
        "backup_supported": backup_supported,
    }


@router.get("/backup/{name}/download")
async def download_backup(name: str, _=Depends(get_current_admin)):
    """Download a previously-created database backup (admin only)."""
    if not BACKUP_NAME_PATTERN.match(name):
        raise HTTPException(status_code=400, detail="Invalid backup name")

    path = Path(settings.backup_dir) / name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Backup not found")

    return FileResponse(path, media_type="application/octet-stream", filename=name)


@router.delete("/backup/{name}", status_code=204)
async def delete_backup(name: str, _=Depends(get_current_admin)):
    """Delete a database backup (admin only)."""
    if not BACKUP_NAME_PATTERN.match(name):
        raise HTTPException(status_code=400, detail="Invalid backup name")

    path = Path(settings.backup_dir) / name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Backup not found")

    path.unlink()
