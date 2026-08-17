"""Deterministic FastAPI application assembly."""

from __future__ import annotations

from collections.abc import Sequence

from fastapi import FastAPI

from app.api.openapi import configure_openapi, generate_operation_id
from app.bootstrap.container import create_container
from app.bootstrap.exception_handlers import register_exception_handlers
from app.bootstrap.lifespan import lifespan
from app.bootstrap.middleware import register_middleware
from app.bootstrap.routes import register_routes
from app.core.config.settings import Settings
from app.infrastructure.bots.factory import BotProviderFactory
from app.modules.registry import ModuleBotBootstrap


def create_app(
    settings: Settings | None = None,
    *,
    module_bot_bootstraps: Sequence[ModuleBotBootstrap] | None = None,
    bot_provider_factory: BotProviderFactory | None = None,
) -> FastAPI:
    """Build an isolated FastAPI app without connecting to PostgreSQL at import time."""

    effective_settings = settings or Settings()
    app = FastAPI(
        title=effective_settings.api.title,
        description=effective_settings.api.description,
        version=effective_settings.app.version,
        debug=effective_settings.app.debug,
        docs_url="/docs" if effective_settings.api.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if effective_settings.api.openapi_enabled else None,
        generate_unique_id_function=generate_operation_id,
        lifespan=lifespan,
    )
    container = create_container(
        effective_settings,
        module_bot_bootstraps=module_bot_bootstraps,
        bot_provider_factory=bot_provider_factory,
    )
    app.state.container = container
    register_middleware(app, container)
    register_exception_handlers(app)
    register_routes(app)
    configure_openapi(app, effective_settings)
    return app
