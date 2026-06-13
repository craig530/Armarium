from pydantic import BaseModel, Field
from typing import Optional


class PlexConfigResponse(BaseModel):
    configured: bool
    enabled: bool
    base_url: Optional[str] = None
    # Never includes the token.


class PlexConfigUpdate(BaseModel):
    base_url: str = Field(..., min_length=1, max_length=500)
    token: Optional[str] = Field(None, min_length=1, max_length=500)
    enabled: bool = True


class PlexTestRequest(BaseModel):
    base_url: str = Field(..., min_length=1, max_length=500)
    token: str = Field(..., min_length=1, max_length=500)
