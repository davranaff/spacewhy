"""Synchronize the source-controlled booking permission registry and built-in roles."""

from __future__ import annotations

import asyncio

from app.core.config.settings import Settings
from app.core.db.database import Database
from app.modules.booking.application.access import RbacSynchronizer


async def _run() -> None:
    """Open the configured database, run one atomic idempotent sync, then release resources."""

    settings = Settings()
    database = Database(settings.database)
    database.initialize()
    try:
        await RbacSynchronizer(database=database).synchronize()
    finally:
        await database.dispose()


def main() -> None:
    """Run the registry synchronization command as a standalone operator action."""

    asyncio.run(_run())


if __name__ == "__main__":
    main()
