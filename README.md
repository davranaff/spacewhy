# spacewhy

Spacewhy is a production-oriented FastAPI modular monolith. It includes three explicit bounded
contexts: `booking`, shared Telegram-based `identity`, and personal `finance`. Identity owns
verified phone binding and short-lived Spacewhy sessions; Finance owns personal workspaces,
accounts, categories, an append-only income/expense ledger, idempotency, audit, and outbox facts.

The backend uses async SQLAlchemy, PostgreSQL, Alembic, typed configuration, RFC
9457-compatible errors, structured logging, explicit composition, isolated multi-bot runtimes,
and gettext i18n. Start with [the backend guide](backend/README.md) and the
[booking](backend/docs/booking.md) or [Finance](backend/docs/finance.md) module guide.
