# ADR 0002: Use async SQLAlchemy with PostgreSQL

Status: accepted

The service uses SQLAlchemy 2.x AsyncEngine, async_sessionmaker, asyncpg, PostgreSQL, and
Alembic. The engine is created once in the FastAPI lifespan, sessions are scoped to a request,
task, or use case, and sessions do not cross concurrent tasks.

This gives ASGI handlers a native async data path while retaining explicit database transaction
semantics and a reviewed migration stream. SQLite does not substitute for PostgreSQL integration
verification.
