import json
from typing import List, Literal, Optional

from pydantic import BaseModel, field_validator

_VALID_CATEGORIES = {"music", "films_tv", "books", "games"}


class AppConfigResponse(BaseModel):
    ownership_mode: Literal["shared", "by_login"]
    disabled_categories: List[str] = []

    model_config = {"from_attributes": True}

    @field_validator("disabled_categories", mode="before")
    @classmethod
    def parse_json(cls, v):
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else []
            except (json.JSONDecodeError, ValueError):
                return []
        return v or []


class AppConfigUpdate(BaseModel):
    ownership_mode: Optional[Literal["shared", "by_login"]] = None
    disabled_categories: Optional[List[str]] = None


class OwnershipMigrateRequest(BaseModel):
    """Admin request to migrate all existing items/lists/mappings from the
    shared system user to a real user login before switching to 'by_login' mode."""
    target_user_id: int
