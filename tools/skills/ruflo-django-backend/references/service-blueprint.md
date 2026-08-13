# Django service blueprint

## Deployable boundary

One deployable Django service owns one bounded context, one private database schema or physical database, one DB role, one migration history, and its own runtime configuration. A menu item or entity does not automatically deserve a service.

The service exposes:

- versioned REST/OpenAPI endpoints for synchronous commands and queries;
- versioned integration events for durable facts;
- idempotent event consumers and background tasks;
- health, readiness, metrics, traces, logs, admin, and reconciliation operations.

## Canonical RuFlo structure

For a new service, preserve the actual `monday-master` organization: `apps/<domain>/` and a file per entity in each layer folder. Modernize it by adding explicit `services/`, policies, clients, consumers, events, and reliable tests. Do not use nested `api/application/domain/infrastructure` folders as the default RuFlo layout.

```text
service/
  pyproject.toml
  Dockerfile
  config/
    settings/
    urls.py
    asgi.py
    celery.py
  apps/
    <domain>/
      models.py
      views/
        <entity>.py
      serializers/
        <entity>.py
      querysets/
        <entity>.py
      services/
        <use_case>.py
      policies/
        <entity>.py
      events/
        <aggregate>.py
      consumers/
        <event_or_projection>.py
      clients/
        <provider_or_service>.py
      dto.py
      exceptions.py
      tasks.py
      urls.py
      migrations/
      admin.py
      tests/
        test_<entity>.py
        test_<use_case>.py
        contract/
        integration/
```

Concrete navigation mirrors the reference:

```text
apps/education/views/student.py
apps/education/serializers/student.py
apps/education/querysets/student.py
apps/education/services/enroll_student.py
apps/education/tests/test_student.py
```

Rules:

- A deployable service owns one bounded context. Inside it, create one or a few broad domain Django apps; do not create an app per endpoint, table, or screen.
- Use exact plural layer folders. The reference mixed `queryset/` and `querysets/`; RuFlo standardizes on `querysets/`.
- Keep field and cross-field transport validation in `serializers/<entity>.py`. Put authoritative domain invariants in the use case/policy, even if the serializer already checks them.
- Keep views and serializers entity-oriented; keep services verb/use-case-oriented.
- `models.py` is acceptable while it remains coherent and under the file-size gate. Split to `models/<entity>.py` only when aggregate boundaries or file size justify it, preserving the same predictable naming.
- Optional folders are omitted when unused; never create empty architecture theater.
- Existing code with equivalent boundaries may keep its established layout, but all newly scaffolded RuFlo services use this house structure.

## Command path

```text
HTTP request
  → serializers/<entity>.py
  → services/<use_case>.py
  → authorization + invariant checks
  → short transaction
  → lock/version check
  → aggregate state + audit + outbox
  → commit
  → response DTO
  → outbox relay publishes event
```

The application command receives explicit dependencies through typed ports or narrow collaborators. It must be callable without HTTP.

## Query path

```text
HTTP request
  → validated filters
  → querysets/<entity>.py / scoped query service
  → bounded optimized query
  → immutable output DTO/page
```

Queries never bypass tenant and resource scope. Use read projections for data owned by another service.

## Event envelope

Use one organization-wide envelope:

```json
{
  "event_id": "uuid",
  "event_type": "education.student.enrolled",
  "event_version": 1,
  "occurred_at": "2026-07-29T10:00:00Z",
  "producer": "education",
  "organization_id": "uuid",
  "aggregate_type": "student",
  "aggregate_id": "uuid",
  "aggregate_version": 3,
  "correlation_id": "uuid",
  "causation_id": "uuid",
  "actor_principal_id": "uuid",
  "data": {}
}
```

Rules:

- `event_id` is globally unique and drives inbox deduplication.
- `event_type` names the fact; `event_version` is the major payload schema version. Consumer routing/contract checks use both.
- Payload contains the minimum durable fact, never secrets or an ORM serialization.
- Consumers ignore duplicates and stale aggregate versions.
- Breaking schema changes create a new event version and coexist during migration.

## Command idempotency

For externally retryable commands:

1. scope the idempotency key to organization, operation, and actor/client;
2. store a normalized request fingerprint;
3. reject reuse with a different payload;
4. return the original terminal response for an identical replay;
5. protect the record with a unique constraint;
6. define retention according to business risk.

Do not mark an operation complete before its state and outbox record commit.

## Cross-service workflows

Use a saga when a capability needs several owners:

- the initiating service persists its local `pending` state;
- it emits or sends the next command with correlation/causation IDs;
- each participant commits only local state;
- completion events advance the saga;
- timeout or rejection produces an explicit failed/compensating state;
- reconciliation can resume or repair the workflow.

Do not hold an HTTP request or database transaction open across the saga.

## Runtime responsibilities

- **RabbitMQ**: durable integration events and Celery broker.
- **Celery workers**: retryable jobs and consumers.
- **Celery Beat**: owner-service schedules; exactly one active scheduler instance per service that needs it.
- **Redis**: cache, distributed rate limits, Channels layer, and short leases only.
- **Supabase Auth**: central identity; services verify asymmetric JWTs through cached JWKS.
- **Supabase Storage**: private objects; owner service authorizes and returns short signed URLs.
- **Supabase Realtime**: safe browser-facing projections only, never the durable service bus.
- **PostgreSQL**: service-owned state, transactional outbox/inbox, audit, and ledgers.

Do not introduce a second queue for the same reliability domain without an ADR and an operational owner.

## Operational endpoints

Every service provides:

- liveness: process can answer;
- readiness: required database/broker dependencies are usable;
- metrics: latency, errors, saturation, queue lag, retry/DLQ counts;
- structured logs with request/correlation IDs and no sensitive payloads;
- traces across HTTP, tasks, and events;
- reconciliation commands safe to run more than once.

Per-service Django Admin is an operator surface, protected by SSO, exact staff permissions, audit, and network controls. A unified admin portal calls owner APIs/BFF; it never receives shared database access.

## Migration/cutover pattern

Migrate one capability at a time:

1. inventory legacy behavior and data quality;
2. define the target contract and owner;
3. create target schema and constraints;
4. backfill with a repeatable mapping;
5. reconcile counts, totals, hashes, and sampled records;
6. shadow-read or compare results where safe;
7. stop legacy writes for the capability;
8. run final delta import;
9. switch API/UI routing;
10. monitor and retain a time-bounded rollback path;
11. remove legacy write paths after the acceptance window.

Avoid permanent dual writes. If temporary dual write is unavoidable, name its owner, source of truth, repair job, metrics, and deletion date.
