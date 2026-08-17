# Spacewhy backend agent instructions

These rules apply to every change under `backend/`. They supplement the repository-wide rules in
`../AGENTS.md`; the root file's safety, security, project-memory, and verification requirements
remain mandatory.

## Required reading

Before editing backend code, configuration, schema, or operational scripts, read:

1. `docs/architecture.md`;
2. `docs/module-template.md`;
3. the relevant section of `docs/development.md`;
4. `pyproject.toml` and `Makefile` when changing dependencies, tooling, commands, or tests.
5. docs/bot-platform.md before changing bot registration, webhooks, providers, or bot settings.
6. docs/i18n.md before changing locales, catalogs, localizers, or translation validation.

## Architecture and boundaries

- Treat `backend/` as one deployable FastAPI modular monolith with service-owned PostgreSQL and
  one Alembic migration stream.
- The HTTP runtime is ASGI-only. Keep `src/app/main.py` minimal and use Uvicorn (or another ASGI
  server); do not introduce Django, WSGI, management commands, or synchronous ORM access.
- Assemble settings, long-lived resources, middleware, routes, exception handlers, and lifespan
  behavior in `src/app/bootstrap/`. Do not create global service locators.
- FastAPI and Starlette belong only at the presentation boundary. Vertical slices follow
  `presentation -> application -> domain`; infrastructure implements adapters and persistence
  concerns owned by its module.
- Domain code must not import FastAPI, Starlette, SQLAlchemy, HTTP exceptions, environment
  variables, or the application container. Application code must not import FastAPI, Starlette,
  HTTP exceptions, environment variables, or the application container. In the current
  service-owned transaction pattern, application use cases may depend on the typed `Database`,
  `AsyncSession`, and their own module's models; they must never reach into another module's ORM
  models or infrastructure internals.
- Use explicit constructor injection. FastAPI `Depends` belongs only in presentation HTTP
  dependencies, never in handlers or domain/application services.
- A module may expose cross-module behavior only through its `public.py` contract. Never import
  another module's ORM models or infrastructure internals.

## Bots and internationalization

- Treat every bot app as an isolated runtime. Its public bot_app_id, credentials, provider client,
  webhook secret, handler, and locale policy must never be shared with another app.
- Keep raw bot tokens and webhook secrets inside typed settings plus narrowly approved provider
  factory/verifier boundaries. Module handlers receive only their pre-bound ScopedBotGateway and
  ScopedLocalizer; they must not import the runtime registry or provider SDK.
- Register a bot app explicitly from its owning module bootstrap. Do not create a business handler,
  command, catalog, or bot configuration without an approved product contract.
- Core owns generic platform translations only. Module common catalogs and bot-app overrides must
  remain in the owning module; translation fallback must never cross module or bot-app scope.

## Database, configuration, and operations

- Use async SQLAlchemy 2.x and an `AsyncSession` scoped to one request, task, or use case.
  Transaction boundaries belong in application handlers or unit-of-work adapters, never routers or
  repositories.
- Build typed Pydantic settings at the composition root. Do not read environment variables directly
  from domain, application, or infrastructure code.
- Keep external I/O outside database transactions. Repositories never commit transactions.
- Run Alembic only through explicit operations such as `make migrate`; never from the API
  lifespan. Review every generated migration, including upgrade and downgrade, before committing it.
- Keep real secrets in ignored deployment environment or key locations. Never log, commit, print,
  or put them into errors, events, or task arguments.

## HTTP, errors, and observability

- Preserve the common RFC 9457-compatible `application/problem+json` error contract and request
  ID propagation.
- Use pure ASGI middleware that does not buffer request or response bodies. Do not log bodies,
  cookies, authorization headers, query strings, or unnecessary personal data.
- Keep structured logging and telemetry vendor-neutral. Production configuration must stay
  deny-by-default for debug mode, CORS, and trusted hosts.

## Modules and product scope

- Do not add a business module, schema, event, credential, or product behavior until its bounded
  context, owner, public contract, authorization scope, invariants, and persistence ownership are
  defined.
- Follow `docs/module-template.md` when a business module is authorized. Add only folders that
  have an actual responsibility; do not create speculative abstractions or generic CRUD bases.
- Use bounded queries, deterministic ordering, explicit authorization, idempotency where required,
  and behavior-focused tests.

## Tooling and verification

- Python 3.13 and the committed `uv.lock` are authoritative. Use `uv` and update the lockfile
  whenever dependencies change; do not introduce a second dependency manager.
- Use the commands in `Makefile` and `docs/development.md` for the affected scope. For code
  changes, run relevant format, lint, type-check, and tests. Integration tests require a real
  PostgreSQL `TEST_DATABASE_URL`; do not present skipped integration tests as passed.
- Run `make migration-check` for migration or metadata changes. Do not claim a check, migration,
  image build, or deployment gate passed unless it was actually run.
- Preserve unrelated user changes. Before reporting completion, inspect the diff and run
  `git diff --check`.
