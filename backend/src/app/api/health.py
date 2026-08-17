"""Unauthenticated liveness and readiness system endpoints."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Request, status
from pydantic import BaseModel
from starlette.responses import JSONResponse

from app.bootstrap.container import get_container_from_app

router = APIRouter(tags=["system"])


class LivenessResponse(BaseModel):
    """Process-only liveness contract."""

    status: Literal["alive"]


class ReadinessChecks(BaseModel):
    """Dependency readiness statuses that do not expose internal details."""

    database: Literal["ok", "unavailable"]
    bot_platform: Literal["ok", "unavailable"]


class ReadinessResponse(BaseModel):
    """Readiness contract for traffic management."""

    status: Literal["ready", "not_ready"]
    checks: ReadinessChecks


@router.get("/health/live", response_model=LivenessResponse, summary="Application liveness")
async def live() -> LivenessResponse:
    """Confirm that this process can answer HTTP without checking dependencies."""

    return LivenessResponse(status="alive")


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse}},
    summary="Application readiness",
)
async def ready(request: Request) -> ReadinessResponse | JSONResponse:
    """Confirm PostgreSQL availability with the database adapter's strict timeout."""

    container = get_container_from_app(request.app)
    database_is_ready = await container.database.check_health()
    bot_platform_is_ready = container.bot_platform.is_ready
    if database_is_ready and bot_platform_is_ready:
        return ReadinessResponse(
            status="ready",
            checks=ReadinessChecks(database="ok", bot_platform="ok"),
        )
    unavailable = ReadinessResponse(
        status="not_ready",
        checks=ReadinessChecks(
            database="ok" if database_is_ready else "unavailable",
            bot_platform="ok" if bot_platform_is_ready else "unavailable",
        ),
    )
    return JSONResponse(
        content=unavailable.model_dump(mode="json"),
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    )
