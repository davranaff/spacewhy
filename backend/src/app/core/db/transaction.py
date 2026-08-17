"""SQLAlchemy adapter for the technology-independent transaction contract."""

from __future__ import annotations

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.database import Database


class SqlAlchemyUnitOfWork:
    """Commit on successful use-case completion and rollback on any failure."""

    def __init__(self, database: Database) -> None:
        self._database = database
        self._session_context = database.session()
        self._session: AsyncSession | None = None

    @property
    def session(self) -> AsyncSession:
        """Expose the scoped session to a repository adapter during this use case."""

        if self._session is None:
            raise RuntimeError("Unit of work has not been entered.")
        return self._session

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        """Open the scoped session."""

        self._session = await self._session_context.__aenter__()
        return self

    async def commit(self) -> None:
        """Commit the transaction explicitly when a handler needs that boundary."""

        await self.session.commit()

    async def rollback(self) -> None:
        """Rollback the current transaction safely."""

        await self.session.rollback()

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Commit success and rollback failures before closing the session."""

        try:
            if exception_type is not None:
                await self.rollback()
            else:
                try:
                    await self.commit()
                except BaseException:
                    await self.rollback()
                    raise
        finally:
            await self._session_context.__aexit__(exception_type, exception, traceback)
            self._session = None
