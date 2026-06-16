"""APScheduler wrapper.

The in-memory scheduler is seeded from the `scheduled_jobs` table on startup
and kept in sync via `add_or_replace` / `remove` calls in the schedule CRUD
endpoints.  We deliberately avoid APScheduler's SQLAlchemy job-store (which
serialises jobs via pickle) in favour of our own table.
"""
import logging
import shutil
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger("armarium.scheduler")


class SchedulerService:
    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler()

    async def start(self, db) -> None:
        from ..repositories.scheduled_job import ScheduledJobRepository

        repo = ScheduledJobRepository(db)
        jobs = await repo.list_all()
        for job in jobs:
            self._register(job)
        self.scheduler.start()
        logger.info("Scheduler started with %d job(s)", len(jobs))

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def add_or_replace(self, job) -> None:
        self._register(job)

    def remove(self, db_id: int) -> None:
        if not self.scheduler.running:
            return
        aps_id = f"sj_{db_id}"
        if self.scheduler.get_job(aps_id):
            self.scheduler.remove_job(aps_id)

    def next_run_time(self, db_id: int) -> Optional[datetime]:
        if not self.scheduler.running:
            return None
        aps_job = self.scheduler.get_job(f"sj_{db_id}")
        return aps_job.next_run_time if aps_job else None

    def _register(self, job) -> None:
        if not self.scheduler.running:
            return
        self.scheduler.add_job(
            _dispatch,
            trigger=IntervalTrigger(hours=job.interval_hours),
            id=f"sj_{job.id}",
            args=[job.id],
            replace_existing=True,
            misfire_grace_time=300,
            coalesce=True,
        )


scheduler_service = SchedulerService()


# ── Dispatcher ────────────────────────────────────────────────────────────────

async def _dispatch(scheduled_job_id: int) -> None:
    """Entry point called by APScheduler for every scheduled job fire."""
    from ..database import AsyncSessionLocal
    from ..models.scheduled_job import ScheduledJob

    # Phase 1: read config (separate session so we don't hold it across the job)
    async with AsyncSessionLocal() as db:
        job = await db.get(ScheduledJob, scheduled_job_id)
        if job is None:
            return
        job_type = job.job_type
        target_id = job.target_id
        auto_remove_stale = job.auto_remove_stale
        export_base_dir = job.export_base_dir
        last_run_at = job.last_run_at

    # export_covers: enforce once-per-day limit
    if job_type == "export_covers" and last_run_at and last_run_at.date() == date.today():
        logger.info("Scheduled export_covers skipped — already ran today (job %d)", scheduled_job_id)
        return

    # Phase 2: run the job
    result: dict = {}
    try:
        if job_type == "plex_sync":
            result = await _run_plex_sync(target_id, bool(auto_remove_stale))
        elif job_type == "auto_link":
            result = await _run_auto_link()
        elif job_type == "redownload_covers":
            result = await _run_redownload_covers()
        elif job_type == "purge_covers":
            result = await _run_purge_covers()
        elif job_type == "export_covers":
            result = await _run_export_covers(export_base_dir)
        elif job_type == "backup":
            result = await _run_backup()
        else:
            result = {"status": "error", "error": f"Unknown job_type: {job_type}"}
        result.setdefault("status", "completed")
    except Exception as exc:
        logger.exception("Scheduled job %d (%s) failed", scheduled_job_id, job_type)
        result = {"status": "error", "error": str(exc)[:1000]}

    # Phase 3: persist result
    async with AsyncSessionLocal() as db:
        job = await db.get(ScheduledJob, scheduled_job_id)
        if job is not None:
            job.last_run_at = datetime.utcnow()
            job.last_run_status = result.get("status")
            job.last_run_created = result.get("created")
            job.last_run_updated = result.get("updated")
            job.last_run_removed = result.get("removed")
            job.last_run_error = result.get("error")
            await db.commit()


# ── Job handlers ──────────────────────────────────────────────────────────────

async def _run_plex_sync(mapping_id: Optional[int], auto_remove_stale: bool) -> dict:
    if mapping_id is None:
        return {"status": "error", "error": "No mapping_id configured for plex_sync job"}

    from ..services.plex_sync_jobs import PlexSyncJob, set_job
    from ..api.v1.plex import _run_sync

    plex_job = PlexSyncJob()
    set_job(mapping_id, plex_job)
    await _run_sync(mapping_id, plex_job, auto_remove_stale=auto_remove_stale)

    return {
        "status": plex_job.status,
        "created": plex_job.created,
        "updated": plex_job.updated,
        "removed": plex_job.removed,
        "error": plex_job.error,
    }


async def _run_auto_link() -> dict:
    from ..database import AsyncSessionLocal
    from ..repositories.media_item import AUTO_LINK_FIELD, MediaItemRepository

    async with AsyncSessionLocal() as db:
        repo = MediaItemRepository(db)
        items = await repo.list()
        linked = 0
        for item in items:
            subtype = item.media_subtype
            if subtype is None or subtype.category not in AUTO_LINK_FIELD:
                continue
            linked += await repo.auto_link_item(item, subtype)
        await db.commit()

    return {"updated": linked}


async def _run_redownload_covers() -> dict:
    from ..database import AsyncSessionLocal
    from ..repositories.media_item import MediaItemRepository
    from ..services.cover_art import download_cover

    async with AsyncSessionLocal() as db:
        repo = MediaItemRepository(db)
        item_ids = list(await repo.ids_with_cover_url())

    updated = 0
    for item_id in item_ids:
        async with AsyncSessionLocal() as db:
            repo = MediaItemRepository(db)
            item = await repo.get(item_id)
            if item is None or not item.cover_image_url:
                continue
            local_path = await download_cover(item.cover_image_url, item_id, force=True)
            if local_path:
                item.cover_image_path = local_path
                await db.commit()
                updated += 1

    return {"updated": updated}


async def _run_purge_covers() -> dict:
    from ..database import AsyncSessionLocal
    from ..config import settings
    from ..repositories.media_item import MediaItemRepository

    covers_dir = Path(settings.covers_dir)
    deleted = 0

    if covers_dir.exists():
        async with AsyncSessionLocal() as db:
            repo = MediaItemRepository(db)
            cover_paths = await repo.cover_paths()

        referenced: set[str] = set()
        for cover_path in cover_paths:
            rel = cover_path.removeprefix("/covers/")
            referenced.add(rel)
            p = Path(rel)
            referenced.add(str(p.with_name(f"{p.stem}_thumb{p.suffix}")))

        for file in covers_dir.rglob("*"):
            if not file.is_file():
                continue
            if str(file.relative_to(covers_dir)) not in referenced:
                file.unlink()
                deleted += 1

    return {"removed": deleted}


async def _run_export_covers(export_base_dir: Optional[str]) -> dict:
    from ..config import settings

    base_dir = export_base_dir or settings.backup_dir
    export_dir = Path(base_dir) / date.today().isoformat()
    export_dir.mkdir(parents=True, exist_ok=True)

    covers_dir = Path(settings.covers_dir)
    zip_path = export_dir / "armarium-covers.zip"

    file_count = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if covers_dir.exists():
            for file in covers_dir.rglob("*"):
                if file.is_file():
                    zf.write(file, file.relative_to(covers_dir))
                    file_count += 1

    return {"updated": file_count}


async def _run_backup() -> dict:
    from ..config import settings

    if "sqlite" not in settings.database_url:
        return {"status": "error", "error": "Backup only supported for SQLite databases"}

    db_path = Path(settings.database_url.replace("sqlite+aiosqlite:///", ""))
    if not db_path.exists():
        return {"status": "error", "error": "Database file not found"}

    backup_dir = Path(settings.backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = backup_dir / f"armarium_{timestamp}.db"
    shutil.copy2(db_path, dest)

    backups = sorted(backup_dir.glob("armarium_*.db"))
    for old in backups[:-30]:
        old.unlink(missing_ok=True)

    return {}
