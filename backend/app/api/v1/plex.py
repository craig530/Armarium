from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...models.plex_config import PlexConfig
from ...schemas.plex import PlexConfigResponse, PlexConfigUpdate, PlexTestRequest
from ...services import plex as plex_service
from ...services.auth import get_current_admin

router = APIRouter()


async def _get_config(db: AsyncSession) -> PlexConfig | None:
    return (await db.execute(select(PlexConfig))).scalars().first()


@router.get("/config", response_model=PlexConfigResponse)
async def get_config(_=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    config = await _get_config(db)
    if config is None:
        return PlexConfigResponse(configured=False, enabled=False, base_url=None)
    return PlexConfigResponse(configured=True, enabled=config.enabled, base_url=config.base_url)


@router.put("/config", response_model=PlexConfigResponse)
async def update_config(
    payload: PlexConfigUpdate,
    _=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    config = await _get_config(db)
    if config is None:
        if not payload.token:
            raise HTTPException(status_code=400, detail="Token is required for initial setup")
        config = PlexConfig(base_url=payload.base_url, token=payload.token, enabled=payload.enabled)
        db.add(config)
    else:
        config.base_url = payload.base_url
        config.enabled = payload.enabled
        if payload.token:
            config.token = payload.token

    await db.commit()
    return PlexConfigResponse(configured=True, enabled=config.enabled, base_url=config.base_url)


@router.delete("/config", status_code=204)
async def delete_config(_=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    config = await _get_config(db)
    if config is not None:
        await db.delete(config)
        await db.commit()


@router.post("/test")
async def test_connection(payload: PlexTestRequest, _=Depends(get_current_admin)):
    try:
        return await plex_service.test_connection(payload.base_url, payload.token)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not connect to Plex: {e}")
