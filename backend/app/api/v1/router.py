from fastapi import APIRouter
from .media import router as media_router
from .locations import router as locations_router
from .lookup import router as lookup_router
from .auth import router as auth_router
from .users import router as users_router
from .export_import import router as export_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(users_router, prefix="/users", tags=["users"])
router.include_router(media_router, prefix="/media", tags=["media"])
router.include_router(locations_router, prefix="/locations", tags=["locations"])
router.include_router(lookup_router, prefix="/lookup", tags=["lookup"])
router.include_router(export_router, prefix="/library", tags=["library"])
