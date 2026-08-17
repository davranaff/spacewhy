"""Application factory smoke tests."""

import pytest

from app.bootstrap.app_factory import create_app
from app.core.config.settings import Settings


@pytest.mark.smoke
def test_application_factory_builds_isolated_app_instances(test_settings: Settings) -> None:
    """Repeated factory calls have distinct containers and no database connections."""

    first = create_app(test_settings)
    second = create_app(test_settings)

    assert first is not second
    assert first.state.container is not second.state.container
    assert not first.state.container.database.is_initialized
    assert first.openapi_url == "/openapi.json"


@pytest.mark.smoke
@pytest.mark.asyncio
async def test_lifespan_disposes_database_resources(test_settings: Settings) -> None:
    """The application lifespan releases its process-scoped engine on shutdown."""

    app = create_app(test_settings)
    database = app.state.container.database

    async with app.router.lifespan_context(app):
        assert database.is_initialized

    assert not database.is_initialized
