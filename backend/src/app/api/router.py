"""One root versioned router reserved for future module presentation adapters."""

from fastapi import APIRouter

from app.core.constants import API_V1_PREFIX
from app.modules.booking.presentation.http.access_router import router as booking_access_router
from app.modules.booking.presentation.http.router import router as booking_router

router = APIRouter(prefix=API_V1_PREFIX)
router.include_router(booking_access_router)
router.include_router(booking_router)
