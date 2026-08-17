# Spacewhy backend

This is a production-oriented FastAPI modular monolith. Its first bounded context is `booking`:
tenant-scoped appointments through an isolated Telegram bot and future WebApps, staff workflows,
cash, inventory, analytics, and an at-least-once notification outbox worker.

- Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2.x async, PostgreSQL, and Alembic.
- The ASGI entry point is intentionally minimal; all assembly lives in bootstrap.
- Uvicorn is the only HTTP server. Database connections are created in the FastAPI lifespan,
  never at module import time.
- The liveness route checks only process liveness; readiness checks PostgreSQL safely.
- Booking owns the isolated `booking_bot` runtime and module Babel/gettext catalogs.
- `make worker-booking` runs the separate polling worker for hold expiry, reminders, and staff
  daily agendas.

Read [docs/booking.md](docs/booking.md) for domain and operational rules,
[docs/architecture.md](docs/architecture.md) for boundaries,
[docs/rbac-architecture.md](docs/rbac-architecture.md) for authorization design,
[docs/rbac-access-matrix.md](docs/rbac-access-matrix.md) for endpoint permissions, and
[docs/rbac-deployment.md](docs/rbac-deployment.md) for migration and rollout steps,
[docs/bot-platform.md](docs/bot-platform.md) before registering another bot,
[docs/i18n.md](docs/i18n.md) before adding catalogs, and
[docs/development.md](docs/development.md) for local commands.
