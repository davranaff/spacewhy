"""System router registration; module routers will be registered explicitly later."""

from fastapi import FastAPI

from app.api.bot_webhooks import router as bot_webhook_router
from app.api.health import router as health_router
from app.api.router import router as api_v1_router


def register_routes(app: FastAPI) -> None:
    """Mount global system routes and the single versioned API root."""

    app.include_router(health_router)
    app.include_router(api_v1_router)
    app.include_router(bot_webhook_router)
