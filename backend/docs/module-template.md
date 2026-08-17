# Adding a business module

Create a module only after a product owner has supplied its bounded context, actor and tenant
scope, input and output contracts, durable invariants, authorization rules, error codes, and
persistence ownership.

Use this shape and omit folders that have no real implementation:

    src/app/modules/<module>/
      domain/
        entities.py
        value_objects.py
        events.py
        repositories.py
        errors.py
      application/
        commands/
        queries/
        dto.py
        ports.py
      infrastructure/
        persistence/
          models.py
          mappers.py
          repository.py
        integrations/
      presentation/
        http/
          router.py
          schemas.py
          dependencies.py
          presenters.py
      bootstrap.py
      public.py

## Boundary rules

- Domain code is pure and imports no FastAPI, Starlette, SQLAlchemy, environment variables, or
  container objects.
- Application handlers receive ports, a UnitOfWork, Clock, and ID generator through constructors.
  They must be callable outside HTTP.
- Infrastructure adapts application or domain ports. ORM models are module-private.
- FastAPI Depends belongs only in presentation/http/dependencies.py. It assembles a handler from
  explicit dependencies and never embeds Depends in a handler or service constructor.
- Module internals are private. Another module may import only public.py, never infrastructure or
  persistence models.
- Keep business schemas inside the module. Do not move business concepts into core merely because
  more than one module needs them.

## Optional bot presentation

When the approved product contract assigns a bot app to this module, declare it through the
module registry bootstrap. The declaration names one stable bot_app_id, translation domain, module
root, and handler factory. The factory receives only BotHandlerDependencies: an app-bound
ScopedBotGateway and ScopedLocalizer. It must not read settings, tokens, webhook secrets, global
registries, another module's catalogs, or provider SDK types.

Place shared module messages in locales/common/<locale>/messages.po and app-specific overrides in
locales/bots/<bot_app_id>/<locale>/messages.po. Do not create a bot presentation folder, handler,
or catalog until the owner, authorization, command contract, and localization requirements are
known. All bot apps owned by one module share that module's catalog root and translation domain.

## Commands and queries

A command validates transport shape in its HTTP schema, repeats authoritative authorization and
domain validation in the handler, runs a short transaction, and returns a DTO. Repositories never
commit. Remote I/O happens after the transaction or through a deliberate reliable workflow.

A query begins with tenant and resource scope, uses bounded pagination, has deterministic ordering,
and returns a DTO rather than an ORM object. Add cursor or offset contracts only when the actual
query needs them.

## Persistence and migrations

Each module logically owns its models and migration changes even though Alembic has one stream.
Import every owned model into the migration metadata discovery path only when it exists. Generate
a revision with make migration MESSAGE='describe change', inspect upgrade and downgrade manually,
then test upgrade, rollback where practical, and Alembic check against PostgreSQL.

## Tests

Add pure domain tests, application handler tests with ports substituted at their boundary, HTTP
tests for validation and stable errors, PostgreSQL tests for constraints and rollback, and
architecture checks for any new boundary. Add authorization, conflict, idempotency, and external
failure tests whenever the product contract requires them.
