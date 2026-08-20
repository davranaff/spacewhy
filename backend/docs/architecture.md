# Architecture

## Shape and dependency direction

Spacewhy is a modular monolith: one deployable FastAPI process with one service-owned PostgreSQL
database and one Alembic migration stream. The owned modules are `booking`, shared `identity`, and
personal `finance`; future modules must preserve the same dependency and scope-isolation boundaries.

Dependencies point inward:

    presentation -> application -> domain
    infrastructure -> application and domain ports
    bootstrap -> presentation, infrastructure, core, and modules

Domain code must not import FastAPI, Starlette, SQLAlchemy ORM types, HTTP exceptions,
environment variables, or the application container. Application code must not import FastAPI,
Starlette, HTTP exceptions, environment variables, or the application container; it may use the
typed database/session and models of its own module to own a transaction. Core contains only
technical cross-cutting concerns, never shared business logic.

## Composition root

src/app/main.py only invokes create_app. The factory in bootstrap/app_factory.py constructs a
new FastAPI instance for each call, adds a typed AppContainer to application state, then
registers middleware, exception handlers, routes, and OpenAPI customization. The container holds
long-lived technical resources plus explicitly assembled module runtimes: Settings, Database,
Telemetry, LocalizationRuntime, BotPlatform, BookingModuleRuntime, IdentityModuleRuntime, and
FinanceModuleRuntime. It is not a global service
locator: a module receives its own scoped dependencies through composition.

## Configuration

Settings is constructed at the composition root from Pydantic Settings. Nested environment
variables use double underscores, such as APP__ENVIRONMENT, DATABASE__URL, and
SECURITY__TRUSTED_HOSTS. Local files may be backend/.env or deployment/env/.env; real files are
ignored by Git. The deployment environment template is deployment/env/.env.example.

Database URLs are SecretStr values and must use the postgresql+asyncpg scheme. Production rejects
debug mode, non-JSON logs, wildcard trusted hosts, and unsafe credentialed CORS settings.

## Database and transactions

Database creates an AsyncEngine and async_sessionmaker in the FastAPI lifespan. Engine creation
does not open a connection. Each request, task, or use case obtains its own AsyncSession through
Database.session; sessions are never global or shared concurrently.

Booking command handlers own their transaction directly through the async session boundary:

    handler
      -> async with unit of work
      -> repository operations
      -> automatic commit on success
      -> rollback on failure

Routers must not access sessions or coordinate transactions. Booking uses PostgreSQL exclusion
constraints for concurrent busy intervals, idempotency rows for retry-safe commands, and an
outbox intent in the same transaction as the corresponding business change.
SQLAlchemy metadata has deterministic names for primary keys, foreign keys, unique constraints,
checks, and indexes. Module models will inherit core.db.Base when a real owned schema exists.

## Booking authorization

Booking uses permission-based scoped RBAC rather than role checks in business code. The
source-controlled registry in `modules/booking/application/permissions.py` defines stable atomic
permission codes, permitted scopes, and ten immutable built-in role templates. The normalized
database representation consists of permission definitions, global system roles or tenant custom
roles, role permissions, tenant memberships, revocable role assignments, and branch lists for
branch-scoped assignments.

Every booking bearer token contains identity only. On each request the access adapter loads the
active membership, active time-valid role assignments, role permissions, and branch scopes. A
membership `access_version` makes issued staff tokens stale after a material assignment change;
the live lookup also makes role edits, expiry, and deactivation take effect immediately. Clients
are never memberships: their customer identity receives only the separate `CUSTOMER_OWN` scope.

`AccessPolicy` is the central authorization layer. It applies tenant predicates first, then branch
or appointment predicates at SQL level; object-level checks use the same semantics for
organization, branch, self/specialist, and customer-owned data. Presentation serializers apply
field filtering for client PII and financial appointment values. Platform administrators have a
separate resolver and cannot enter tenant bearer routes. Workers use explicit named, tenant- and
branch-bounded system contexts rather than an implicit global bypass. See `docs/rbac-architecture.md`.

## Lifespan and migrations

The lifespan validates already-constructed settings, configures application logging, initializes
the engine and optional telemetry provider, optionally checks critical dependencies, then disposes
telemetry and the engine on shutdown. It never runs migrations.

Alembic imports only typed settings and central metadata, never the FastAPI application. Run
migrations separately through make migrate or scripts/migrate.sh. Generated revisions are
starting points and must be manually reviewed before they are committed.

## HTTP behavior

Global system routes are:

- GET /health/live: process liveness only.
- GET /health/ready: PostgreSQL readiness with a strict timeout.

The `/api/v1/booking`, `/api/v1/identity`, and `/api/v1/finance` routers are mounted once from
their presentation boundaries. Booking client, staff, administrator, and Telegram WebApp-auth
subrouters remain thin transport adapters. Future
business presentation routes belong in their own modules, not app/api.

Middleware inbound order is request ID, optional trusted proxy headers, trusted host validation,
CORS, telemetry, access log, request timing, then the application. It uses pure ASGI middleware
and never buffers request or response bodies. Every HTTP response receives a validated or
generated UUID request ID. Access logs use route templates when available and do not log bodies,
cookies, authorization headers, or query strings.

## Errors and observability

Core application errors are ordinary typed exceptions with stable ErrorCode values. Bootstrap
maps them, framework validation failures, routing errors, and unknown errors to one
application/problem+json RFC 9457-compatible shape. Unknown errors are logged with a stack trace
and request ID but return only a generic detail.

Logging is owned by the spacewhy logger, writes to stdout, and is JSON in production. Its
formatter redacts sensitive keys recursively. Telemetry is an optional per-app OpenTelemetry
provider with no exporter or vendor coupling. When disabled it remains a no-op; when enabled,
request spans supply trace IDs to logs.

## Bot platform and i18n

Bot applications remain internal modular-monolith runtimes. Bootstrap collects explicit module
registrations, validates typed bot settings and gettext catalogs, creates one provider adapter per
enabled app, injects only an app-bound gateway and localizer into its handler, and freezes the
private runtime registry. Booking registers `booking_bot` and Identity registers
`spacewhy_auth_bot` only when each app is configured. Telegram is the first provider through the
infrastructure adapter; no domain or
application layer imports its SDK.

Each webhook uses POST /webhooks/telegram/{bot_app_id}. The public route ID selects one runtime,
then a constant-time Telegram webhook-secret comparison happens before provider parsing or module
dispatch. Liveness never calls a provider. Readiness reports only local runtime initialization.

Core i18n uses Babel and gettext PO catalogs. Core owns generic platform strings; module common
catalogs and bot-app overrides remain below their owning module. Bound localizers never fall back
to another module or bot app. HTTP locale is request-scoped; bot locale is immutable per update.
See docs/bot-platform.md and docs/i18n.md for operational workflows.

## Prohibited shortcuts

Do not add Django, WSGI, synchronous ORM calls, generic CRUD base classes, global sessions, HTTP
exceptions in domain/application code, automatic migrations at startup, cross-module ORM imports,
or unbounded raw-path/body logging. Booking's generic administration endpoint is intentionally a
whitelist over owned resource schemas, not a reusable unbounded CRUD framework.
