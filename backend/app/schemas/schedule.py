from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

VALID_INTERVALS = (1, 6, 12, 24, 168)   # hours: hourly / 6h / 12h / daily / weekly


class ScheduleCreate(BaseModel):
    interval_hours: int = Field(..., description=f"One of {VALID_INTERVALS}")
    # plex_sync only
    auto_remove_stale: Optional[bool] = None
    # export_covers only
    export_base_dir: Optional[str] = Field(None, max_length=500)


class ScheduleUpdate(BaseModel):
    interval_hours: Optional[int] = None
    auto_remove_stale: Optional[bool] = None
    export_base_dir: Optional[str] = Field(None, max_length=500)


class ScheduleResponse(BaseModel):
    id: int
    job_type: str
    target_id: Optional[int] = None
    interval_hours: int
    auto_remove_stale: Optional[bool] = None
    export_base_dir: Optional[str] = None
    last_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None
    last_run_created: Optional[int] = None
    last_run_updated: Optional[int] = None
    last_run_removed: Optional[int] = None
    last_run_error: Optional[str] = None
    next_run_at: Optional[datetime] = None   # injected from APScheduler
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
