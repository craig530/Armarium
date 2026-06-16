from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String, func
from ..database import Base

# Valid job_type values
ADMIN_JOB_TYPES = ("auto_link", "redownload_covers", "purge_covers", "export_covers", "backup")
PLEX_JOB_TYPE = "plex_sync"
ALL_JOB_TYPES = (PLEX_JOB_TYPE,) + ADMIN_JOB_TYPES


class ScheduledJob(Base):
    """Persistent schedule configuration for a recurring background task.
    APScheduler's in-memory scheduler is seeded from this table on startup
    and kept in sync on create/update/delete — no APScheduler job store needed."""

    __tablename__ = "scheduled_jobs"

    id = Column(Integer, primary_key=True)
    job_type = Column(String(50), nullable=False, index=True)
    # mapping_id for plex_sync; NULL for singleton admin jobs
    target_id = Column(Integer, nullable=True, index=True)
    # Repeat every N hours (1=hourly, 6, 12, 24=daily, 168=weekly)
    interval_hours = Column(Integer, nullable=False)

    # plex_sync option: auto-remove stale items after each scheduled sync
    auto_remove_stale = Column(Boolean, nullable=True)
    # export_covers option: parent directory for date-stamped export folders
    export_base_dir = Column(String(500), nullable=True)

    # Last-run result — written by the scheduler after each run
    last_run_at = Column(DateTime, nullable=True)
    last_run_status = Column(String(20), nullable=True)   # completed | error
    last_run_created = Column(Integer, nullable=True)
    last_run_updated = Column(Integer, nullable=True)
    last_run_removed = Column(Integer, nullable=True)
    last_run_error = Column(String(1000), nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())
