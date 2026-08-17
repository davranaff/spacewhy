"""Real PostgreSQL integration tests for async sessions and transaction behavior."""

from __future__ import annotations

import pytest
from pydantic import SecretStr
from sqlalchemy import text

from app.core.config.settings import DatabaseSettings
from app.core.db.database import Database
from app.core.db.transaction import SqlAlchemyUnitOfWork

_PROBE_TABLE = "integration_transaction_probe"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_async_database_sessions_commit_rollback_and_health(test_database_url: str) -> None:
    """Verify actual asyncpg lifecycle behavior rather than substituting SQLite."""

    database = Database(DatabaseSettings(url=SecretStr(test_database_url)))
    database.initialize()
    assert await database.check_health()

    try:
        async with database.engine.begin() as connection:
            await connection.execute(
                text(
                    f"CREATE TABLE IF NOT EXISTS {_PROBE_TABLE} "
                    "(id integer PRIMARY KEY, value text NOT NULL)"
                )
            )
            await connection.execute(text(f"TRUNCATE TABLE {_PROBE_TABLE}"))

        async with SqlAlchemyUnitOfWork(database) as unit_of_work:
            await unit_of_work.session.execute(
                text(f"INSERT INTO {_PROBE_TABLE} (id, value) VALUES (1, 'committed')")
            )

        async with database.session() as session:
            committed = await session.scalar(text(f"SELECT value FROM {_PROBE_TABLE} WHERE id = 1"))
        assert committed == "committed"

        with pytest.raises(RuntimeError, match="rollback probe"):
            async with SqlAlchemyUnitOfWork(database) as unit_of_work:
                await unit_of_work.session.execute(
                    text(f"INSERT INTO {_PROBE_TABLE} (id, value) VALUES (2, 'rolled back')")
                )
                raise RuntimeError("rollback probe")

        async with database.session() as session:
            rolled_back = await session.scalar(
                text(f"SELECT value FROM {_PROBE_TABLE} WHERE id = 2")
            )
        assert rolled_back is None
    finally:
        async with database.engine.begin() as connection:
            await connection.execute(text(f"DROP TABLE IF EXISTS {_PROBE_TABLE}"))
        await database.dispose()
