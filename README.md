# spacewhy

Spacewhy is a production-oriented FastAPI modular monolith. It includes the `booking` bounded
context: tenant-scoped booking, Telegram bot/WebApp authentication, staff operations, internal
cash and inventory accounting, analytics, and a durable notification outbox worker.

The backend uses async SQLAlchemy, PostgreSQL, Alembic, typed configuration, RFC
9457-compatible errors, structured logging, explicit composition, isolated multi-bot runtimes,
and gettext i18n. Start with [the backend guide](backend/README.md) and the
[booking module guide](backend/docs/booking.md).
