from pydantic import BaseModel
from typing import Literal


class AppConfigResponse(BaseModel):
    ownership_mode: Literal["shared", "by_login"]

    model_config = {"from_attributes": True}


class AppConfigUpdate(BaseModel):
    ownership_mode: Literal["shared", "by_login"]


class OwnershipMigrateRequest(BaseModel):
    """Admin request to migrate all existing items/lists/mappings from the
    shared system user to a real user login before switching to 'by_login' mode."""
    target_user_id: int
