"""Transaction contract independent of SQLAlchemy."""

from typing import Protocol


class UnitOfWork(Protocol):
    """Represent a short application transaction."""

    async def commit(self) -> None:
        """Persist work completed by a use case."""

    async def rollback(self) -> None:
        """Discard work after a failed use case."""
