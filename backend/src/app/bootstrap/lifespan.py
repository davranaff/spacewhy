"""FastAPI lifespan ownership for resource startup and graceful shutdown."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.bootstrap.container import get_container_from_app
from app.core.observability.logging import configure_logging

logger = logging.getLogger("spacewhy")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Initialize process resources once and dispose them on shutdown."""

    container = get_container_from_app(app)
    configure_logging(container.settings)
    container.database.initialize()
    container.telemetry.initialize()
    try:
        if container.settings.app.verify_dependencies_on_startup:
            is_ready = await container.database.check_health()
            if not is_ready:
                raise RuntimeError("Required database dependency is unavailable.")
        await container.bot_platform.initialize()
        yield
    finally:
        await container.bot_platform.shutdown()
        await container.telemetry.shutdown()
        await container.database.dispose()
        logger.info("application_resources_disposed")
