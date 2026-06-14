from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PlexSyncJob:
    """Tracks the progress of one in-flight (or just-finished) background
    sync for a `PlexLibraryMapping`. Held in memory only — if the process
    restarts mid-sync, the job is gone and the status endpoint reports
    "idle" again, which is fine since per-item progress is already committed."""

    status: str = "running"  # running | completed | cancelled | error
    total: Optional[int] = None
    processed: int = 0
    created: int = 0
    updated: int = 0
    stale_items: list = field(default_factory=list)
    error: Optional[str] = None
    cancel_requested: bool = False


# One job per mapping at a time, keyed by mapping id.
_jobs: dict[int, PlexSyncJob] = {}


def get_job(mapping_id: int) -> Optional[PlexSyncJob]:
    return _jobs.get(mapping_id)


def set_job(mapping_id: int, job: PlexSyncJob) -> None:
    _jobs[mapping_id] = job
