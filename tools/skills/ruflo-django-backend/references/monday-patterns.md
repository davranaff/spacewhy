# monday-master: extracted engineering patterns

## Scope of the reference

Use `monday-master` only as an engineering-style reference. It is an older Django/DRF project and is not the source of truth for RuFlo product behavior, service boundaries, permissions, data model, or infrastructure.

Representative source files:

- `backend/apps/academy/views/student.py`
- `backend/apps/academy/serializers/student.py`
- `backend/apps/academy/queryset/student.py`
- `backend/apps/core/querysets/base_queryset.py`
- `backend/apps/academy/models.py`
- `backend/apps/academy/tests/test_student.py`

## Patterns to preserve

### Exact file-per-entity layout

Preserve the reference's real navigation pattern, not a generic Clean Architecture tree:

```text
apps/<domain>/
  models.py
  views/<entity>.py
  serializers/<entity>.py
  queryset/<entity>.py
  tests/test_<entity>.py
  urls.py
  admin.py
  migrations/
```

RuFlo standardizes the inconsistent reference spelling to `querysets/` and adds sibling `services/`, `policies/`, `events/`, `consumers/`, and `clients/` only when needed. Do not default to nested `api/application/domain/infrastructure` folders. A broad domain Django app contains related entities; an entity, screen, or endpoint is not automatically a new app.

### Domain-oriented modules

The project groups code around recognizable business domains instead of technical grab bags. Keep bounded-context vocabulary consistent across models, serializers, URLs, permissions, tests, and admin.

### Short, meaningful names

Classes and methods describe business intent. Prefer `EnrollStudent`, `ApprovePayment`, or `VisibleStudentsQuery` to generic `Manager`, `Helper`, or `ProcessData`.

### Thin HTTP views

Views focus on HTTP concerns, select the scoped query, validate request data, invoke a clear action, and return a serializer. Preserve this clarity, but move multi-step mutations to an application use case rather than a serializer or model hook.

### Serializer validation

DRF serializers provide a useful transport boundary and explicit validation errors. Keep field and cross-field validation close to the input schema. Repeat authorization and durable invariants in the application/domain layer so alternate transports cannot bypass them.

Use entity files such as `serializers/student.py`; do not collapse all serializers into one file and do not invent a separate validation framework when DRF serializer validation is the correct boundary. Pure reusable domain validation may live in a policy/value object, not in a view.

### Scoped QuerySets and selectors

Reusable QuerySets make visibility and common filtering readable. Preserve this pattern:

- start from a tenant-scoped base query;
- apply branch/assignment/self scope explicitly;
- centralize complex eager loading;
- name business filters;
- avoid returning an unscoped base manager from request code.

### Explicit permissions

The reference makes access rules visible near endpoints. Retain that visibility, but model exact grants plus resource scope; do not rely on a small global role list.

### Audit fields and deterministic defaults

Created/updated metadata and explicit default provisioning make state understandable. In the new system, include actor/correlation metadata and make default seeding idempotent and versioned.

### Endpoint-focused tests

The reference tests recognizable endpoint behavior. Keep this readability and add denial, scope, concurrency, idempotency, event, and migration cases.

## Patterns to modernize

### Dependency baseline

Do not reproduce the Django 3.1 / DRF 3.12-era stack. Use the project-approved supported baseline; for the initial RuFlo platform this means Python 3.13, Django 5.2 LTS, DRF 3.17, Celery 5.6, Supabase/PostgreSQL 17, RabbitMQ 4.3, and Redis 8.8 unless an ADR changes it. Pin the current security patch in dependency locks and images; do not silently jump runtime minors.

### Application layer

The reference sometimes lets serializers, views, or model methods coordinate multiple writes and side effects. Introduce an explicit application use case for every material command.

### Transactions and concurrency

An `atomic()` block alone is not a race strategy. Define uniqueness constraints, row locks or optimistic versions, idempotency records, and conflict errors. Keep remote calls out of the transaction.

### Service ownership

Foreign keys across apps can be appropriate in a monolith but are forbidden across RuFlo deployable services. A service keeps opaque external IDs and local event-fed projections.

### Async reliability

Replace direct after-save side effects and implicit signals with transactional outbox, versioned events, idempotent consumers, inbox deduplication, retry policy, DLQ, and reconciliation.

### Security

Never copy hardcoded Django secrets, custom perpetual tokens, credentials, permissive defaults, or in-process rate limits. Use central Auth/JWKS, KMS/secret manager, exact permissions, server-side scope, and shared rate limiting.

### Data types

Use `Decimal` plus currency for money, timezone-aware timestamps, enums for finite states, normalized grants, database constraints, and immutable ledgers where history matters.

### Query and response behavior

Replace manual/unbounded pagination and hidden N+1 loading with a standard pagination contract, selectors, `select_related`, `prefetch_related`, annotated aggregates, limits, and query-count tests for hot endpoints.

### Error behavior

Do not return successful responses after broad exception catches. Raise typed domain/application errors, map them once at the API boundary, and log unexpected failures with request/correlation IDs.

## Review lens

When reviewing code “in monday style”, ask:

1. Is the business language as clear and compact as the reference?
2. Is tenant/resource scope visible before data access?
3. Is transport validation explicit?
4. Has mutation orchestration moved into an application use case?
5. Are database and event invariants stronger than in the legacy project?
6. Are failure, retry, authorization, and concurrency paths tested?

Matching the senior's style means preserving clarity and intent while raising the reliability baseline, not reproducing old syntax.
