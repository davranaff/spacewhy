"""One async SQLAlchemy engine and session factory per application process."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config.settings import DatabaseSettings


class Database:
    """Own engine lifecycle, isolated sessions, and safe dependency health checks."""

    def __init__(self, settings: DatabaseSettings) -> None:
        self._settings = settings
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    @property
    def is_initialized(self) -> bool:
        """Return whether the lifespan has created this process's engine."""

        return self._engine is not None and self._session_factory is not None

    @property
    def engine(self) -> AsyncEngine:
        """Return the initialized engine or fail loudly outside a lifecycle."""

        if self._engine is None:
            raise RuntimeError("Database has not been initialized.")
        return self._engine

    def initialize(self) -> None:
        """Create the engine without opening a database connection."""

        if self.is_initialized:
            return
        engine = create_async_engine(
            self._settings.resolved_url,
            pool_pre_ping=True,
            pool_size=self._settings.pool_size,
            max_overflow=self._settings.max_overflow,
            pool_timeout=self._settings.pool_timeout_seconds,
            pool_recycle=self._settings.pool_recycle_seconds,
            connect_args={"command_timeout": self._settings.command_timeout_seconds},
        )
        self._engine = engine
        self._session_factory = async_sessionmaker(
            bind=engine,
            autoflush=False,
            expire_on_commit=False,
        )

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession]:
        """Yield one non-shared async session for a request, task, or use case."""

        session_factory = self._session_factory
        if session_factory is None:
            raise RuntimeError("Database has not been initialized.")
        session = session_factory()
        try:
            yield session
        finally:
            await session.close()

    async def check_health(self) -> bool:
        """Return database availability without exposing driver errors."""

        engine = self._engine
        if engine is None:
            return False

        async def check() -> None:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))

        try:
            await asyncio.wait_for(check(), timeout=self._settings.health_timeout_seconds)
        except (OSError, SQLAlchemyError, TimeoutError):
            return False
        return True

    async def dispose(self) -> None:
        """Dispose the engine and make this container's resources unavailable."""

        engine = self._engine
        self._engine = None
        self._session_factory = None
        if engine is not None:
            await engine.dispose()
