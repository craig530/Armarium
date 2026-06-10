from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional
import csv
import io
import json
from datetime import datetime
from pathlib import Path
import shutil

from ...database import get_db
from ...models.media import MediaItem
from ...schemas.media import MediaItemCreate
from ...services.auth import get_current_user, get_current_admin
from ...config import settings

router = APIRouter()

CSV_FIELDS = [
    "title", "media_type", "year", "genres", "edition", "barcode",
    "artist", "label", "track_count",
    "director", "studio", "runtime_minutes", "rating",
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
        for int_field in ("year", "track_count", "runtime_minutes", "page_count", "tmdb_id"):
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
    db: AsyncSession = Depends(get_db),
):
    """Export the full library as JSON or CSV."""
    stmt = select(MediaItem).order_by(MediaItem.title)
    items = (await db.execute(stmt)).scalars().all()

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


@router.post("/import")
async def import_library(
    file: UploadFile = File(...),
    format: str = Query("csv", pattern="^(json|csv)$"),
    _=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
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

    created, skipped = 0, 0
    for row in rows:
        item_create = _row_to_create(dict(row))
        if item_create is None:
            skipped += 1
            continue
        db.add(MediaItem(**item_create.model_dump()))
        created += 1

    await db.commit()
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
    backup_dir = Path(settings.backup_dir)
    if not backup_dir.exists():
        return {"backups": []}

    backups = sorted(backup_dir.glob("armarium_*.db"), reverse=True)
    return {
        "backups": [
            {"name": b.name, "size_bytes": b.stat().st_size, "created": datetime.fromtimestamp(b.stat().st_mtime).isoformat()}
            for b in backups
        ]
    }
