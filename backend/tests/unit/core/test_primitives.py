"""Clock, ID, and database lifecycle unit tests."""

import pytest

from app.core.clock import SystemClock
from app.core.config.settings import DatabaseSettings
from app.core.db.database import Database
from app.core.ids import UUID4Generator


def test_system_clock_returns_aware_utc_timestamp() -> None:
    """The production clock follows the UTC-aware timestamp convention."""

    assert SystemClock().now().tzinfo is not None


def test_uuid4_generator_returns_distinct_identifiers() -> None:
    """Generated IDs are opaque UUIDs rather than predictable counters."""

    generator = UUID4Generator()
    assert generator.new() != generator.new()


@pytest.mark.asyncio
async def test_database_initialization_does_not_connect_until_used() -> None:
    """Constructing an engine remains safe without a reachable PostgreSQL server."""

    database = Database(DatabaseSettings())

    assert not database.is_initialized
    database.initialize()
    assert database.is_initialized

    await database.dispose()
    assert not database.is_initialized
