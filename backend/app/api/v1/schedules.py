"""Schedule CRUD for admin maintenance tasks.

Plex-sync schedules are managed via
  GET/POST/DELETE /admin/plex/mappings/{id}/schedule
and live in plex.py (they require the can_manage_schedules permission, not
full admin).  The endpoints here are admin-only and cover the four maintenance
tasks: auto_link, redownload_covers, purge_covers, export_covers, and backup.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from ...database import AsyncSessionLocal
from ...models.scheduled_job import ADMIN_JOB_TYPES, ScheduledJob
from ...repositories.scheduled_job import ScheduledJobRepository, get_scheduled_job_repository
from ...schemas.schedule import ScheduleCreate, ScheduleResponse, ScheduleUpdate, VALID_INTERVALS
from ...services.auth import get_current_admin
from ...services.scheduler import scheduler_service

router = APIRouter()


def _to_response(job: ScheduledJob) -> ScheduleResponse:
    resp = ScheduleResponse.model_validate(job)
    resp.next_run_at = scheduler_service.next_run_time(job.id)
    return resp


def _validate_job_type(job_type: str) -> None:
    if job_type not in ADMIN_JOB_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid job type. Must be one of: {', '.join(ADMIN_JOB_TYPES)}",
        )


def _validate_interval(interval_hours: int) -> None:
    if interval_hours not in VALID_INTERVALS:
        raise HTTPException(
            status_code=400,
            detail=f"interval_hours must be one of {VALID_INTERVALS}",
        )


@router.get("", response_model=List[ScheduleResponse])
async def list_schedules(
    _=Depends(get_current_admin),
    repo: ScheduledJobRepository = Depends(get_scheduled_job_repository),
):
    """List all scheduled jobs (admin only)."""
    jobs = await repo.list_all()
    return [_to_response(j) for j in jobs]


@router.get("/{job_type}", response_model=Optional[ScheduleResponse])
async def get_schedule(
    job_type: str,
    _=Depends(get_current_admin),
    repo: ScheduledJobRepository = Depends(get_scheduled_job_repository),
):
    """Get the current schedule for an admin maintenance job type (null if none)."""
    _validate_job_type(job_type)
    job = await repo.find_by_type(job_type)
    return _to_response(job) if job else None


@router.post("/{job_type}", response_model=ScheduleResponse, status_code=201)
async def upsert_schedule(
    job_type: str,
    payload: ScheduleCreate,
    _=Depends(get_current_admin),
    repo: ScheduledJobRepository = Depends(get_scheduled_job_repository),
):
    """Create or replace the schedule for an admin maintenance job type."""
    _validate_job_type(job_type)
    _validate_interval(payload.interval_hours)

    job = await repo.find_by_type(job_type)
    if job is None:
        job = ScheduledJob(job_type=job_type)
        repo.add(job)

    job.interval_hours = payload.interval_hours
    if payload.auto_remove_stale is not None:
        job.auto_remove_stale = payload.auto_remove_stale
    if payload.export_base_dir is not None:
        job.export_base_dir = payload.export_base_dir

    await repo.commit()
    await repo.refresh(job)
    scheduler_service.add_or_replace(job)
    return _to_response(job)


@router.delete("/{job_type}", status_code=204)
async def delete_schedule(
    job_type: str,
    _=Depends(get_current_admin),
    repo: ScheduledJobRepository = Depends(get_scheduled_job_repository),
):
    """Remove the schedule for an admin maintenance job type."""
    _validate_job_type(job_type)
    job = await repo.find_by_type(job_type)
    if job is None:
        raise HTTPException(status_code=404, detail="No schedule configured for this job type")
    scheduler_service.remove(job.id)
    await repo.delete(job)
    await repo.commit()


@router.post("/{job_type}/run-now", status_code=202)
async def run_now(
    job_type: str,
    _=Depends(get_current_admin),
    repo: ScheduledJobRepository = Depends(get_scheduled_job_repository),
):
    """Trigger an immediate run of a scheduled admin job (ignores once-per-day limits)."""
    _validate_job_type(job_type)
    job = await repo.find_by_type(job_type)
    if job is None:
        raise HTTPException(status_code=404, detail="No schedule configured for this job type")

    import asyncio
    from ...services.scheduler import _dispatch
    asyncio.create_task(_dispatch(job.id))
    return {"queued": True, "job_type": job_type}
