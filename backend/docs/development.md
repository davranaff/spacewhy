# Development

## Prerequisites

Install Python 3.13, Docker Desktop, and uv. The committed uv.lock is the authoritative
dependency resolution for local development, CI, and images.

## Local setup

From backend:

    cp ../deployment/env/.env.example ../deployment/env/.env
    uv sync --all-groups

The local environment template contains only a known-safe development database password. Replace
it with a secret-manager value for any shared environment. Do not commit deployment/env/.env.

## Run PostgreSQL and the API

From backend:

    make docker-up

The Docker image starts the API without reload. For a local host process, first start PostgreSQL
with Docker Compose, set DATABASE__URL to point at localhost, then run:

    make run

Check GET /health/live first. GET /health/ready returns 503 when PostgreSQL cannot be reached and
does not disclose driver details.

## Quality commands

From backend:

    make format
    make lint
    make typecheck
    make test-unit
    make test-architecture
    make test-smoke
    make test-bots
    make test-i18n
    TEST_DATABASE_URL=postgresql+asyncpg://spacewhy:spacewhy_local_password@127.0.0.1:5433/spacewhy make test-integration
    make test

Integration tests intentionally skip unless TEST_DATABASE_URL points to real PostgreSQL. SQLite is
not a PostgreSQL substitute for this suite.

## Bot platform and i18n

The tracked environment template contains only disabled bot examples and obvious placeholders.
Keep real Telegram tokens and webhook secrets in the ignored deployment environment or secret
manager path. Do not enable a placeholder configuration: startup validation rejects it.

Run the focused local checks from backend:

    make test-bots
    make test-i18n

The test suites use fake provider clients and temporary gettext catalogs. They do not call Telegram
or require a real bot token. Read docs/bot-platform.md and docs/i18n.md before adding an owned bot
module or production catalog.

## Booking module

The tracked environment template includes a disabled `BOTS__APPS__BOOKING_BOT` declaration and
`BOOKING_*` tuning values. Keep the bot disabled until a real, unique token and webhook secret are
available through the ignored deployment environment or secret manager. Once configured, apply
the migration and start the API and worker as separate processes:

    make migrate
    make sync-rbac
    make provision-booking ARGS='--organization-slug salon --organization-name "Salon" --owner-display-name "Owner"'
    make run
    make worker-booking

The worker expires holds, sends the durable notification outbox, retries transient provider
failures with bounded backoff, and creates deduplicated staff daily-agenda intents. It does not
run inside Uvicorn and must be deployed once per worker replica. Its `SKIP LOCKED` leases make
multiple worker replicas safe; delivery remains at-least-once, so downstream message effects must
be treated as potentially duplicated after a process crash.

Telegram WebApp authentication is exposed at `/api/v1/booking/auth/telegram/client` and
`/api/v1/booking/auth/telegram/staff`. It requires official signed `initData`; a raw Telegram user
ID or organization ID is never accepted from a client. See docs/booking.md for API scopes, data
rules, and the operational checklist.

`provision-booking` is a one-time, explicit operator command for this currently self-contained
tenant model. It refuses to merge existing tenants, creates the initial owner grant and prints a
single-use staff bind code once. Treat that code like a short-lived credential; do not redirect it
to a ticket or a log.

Booking role definitions are source-controlled. Run `make sync-rbac` after applying migrations and
after a deployment that changes `modules/booking/application/permissions.py`. It is idempotent and
does not delete tenant custom roles. Read `docs/rbac-deployment.md` before production rollout.

## Migrations

Migrations are an explicit operational action:

    make migration MESSAGE='describe schema change'
    make migrate
    make migration-check

Do not generate an empty placeholder revision. Review generated operations, naming, indexes,
upgrade, and downgrade manually. Never run migrations from the API lifespan or every replica.

## Docker and debugging readiness

Render the local composition from the repository root:

    docker compose -f deployment/docker/compose.yaml config

Build the backend image from backend:

    docker build .

The image deliberately starts one Uvicorn worker. Scale with separate replicas only after
calculating database pool size times replica count, and run Alembic as one separate operational
job rather than from every API replica.

If readiness fails, inspect the PostgreSQL container health, confirm DATABASE__URL uses the
postgresql+asyncpg scheme and the compose host name postgres, then check the application access
log using its request ID. Host-run integration tests reach the mapped PostgreSQL port 5433. Do not
paste connection strings into tickets or logs.
