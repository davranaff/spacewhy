---
name: ruflo-django-backend
description: Implement, refactor, design, scaffold, or review RuFlo/LMS Django and Django REST Framework backend services with the monday-master file-per-entity house layout (`apps/domain/{views,serializers,querysets,services,tests}`), plus senior-grade boundaries, validation, transactions, concurrency control, event contracts, and tests. Use for new Django microservices/apps, API endpoints, models, QuerySets, application services, Celery tasks, RabbitMQ integrations, data migrations, backend architecture reviews, and code-quality reviews while modernizing unsafe or obsolete reference patterns.
---

# RuFlo Django Backend

Build backend capabilities as explicit, testable use cases. Preserve the actual `monday-master` navigation discipline—one broad domain app and one entity-named file in each layer folder—but never copy its product behavior, old dependencies, credentials, monolith coupling, or unreliable write patterns.

## Load the Right Context

Before changing code:

1. Read the repository instructions and inspect the current worktree.
2. Read the project's authoritative feature specification: migration-vault module and feature note when the repository provides them, otherwise the linked issue, ADR, API/event contract, or requirements document. Treat its target behavior, owner, invariants, contracts, and migration rules as the specification.
3. Read `references/quality-gates.md`.
4. For a new service, app, entity, or structural change, read both `references/service-blueprint.md` and `references/monday-patterns.md`.
5. For style matching, refactoring, or code review, also read `references/monday-patterns.md`.
6. Inspect existing local conventions before choosing names or directories. Do not force the blueprint onto an established codebase when its current structure already enforces the same boundaries.

If the migration specification is missing or contradicts the code, stop implementation at the contract boundary, document the conflict, and resolve the behavior before inventing it in code.

## Classify the Change

Classify every change before editing:

- **Command**: changes domain state. Requires an application use case, authorization, validation, transaction boundary, audit, and idempotency/concurrency analysis.
- **Query**: reads state. Requires tenant/scope enforcement, stable output schema, deliberate query loading, and pagination or bounded result size.
- **Domain event**: records an accepted fact. Requires a versioned schema, immutable identity, causation/correlation metadata, and transactional outbox.
- **Integration event**: exposes a domain fact to other services. Contains only the minimum contract; never leaks an ORM model.
- **Background task**: retries work. Requires an idempotency key, retry policy, timeout, observability, and terminal failure handling.
- **Projection consumer**: updates a local read model. Requires inbox deduplication, monotonic version handling, replay safety, and reconciliation.

A single capability can contain several types. Define each separately.

## Define the Contract Before Code

Write down, in the issue or working notes:

- owning bounded context and aggregate;
- actor, tenant, branch, and resource scope;
- preconditions and invariants;
- input/output DTOs;
- stable error codes and HTTP status mapping;
- state transition and audit record;
- idempotency and concurrency strategy;
- emitted/consumed event versions;
- timeout, retry, and compensation behavior for remote work;
- data migration and rollback/reconciliation plan.

Do not start with models or views when these facts are unknown.

## Implement Through Explicit Layers

Map responsibilities onto the RuFlo house folders. Do not replace them with nested `api/application/domain/infrastructure` packages in a new service:

1. **API adapter — `views/<entity>.py` + `serializers/<entity>.py`**
   - Authenticate and parse transport input.
   - Use serializers/schemas for shape and local field validation.
   - Call one application use case.
   - Map typed result or domain error to a stable response.
   - Never coordinate business side effects.

2. **Application use case — `services/<use_case>.py`**
   - Enforce tenant, branch, role, and resource authorization.
   - Load aggregates through service-local persistence.
   - Own the short `transaction.atomic()` boundary.
   - Lock rows or use optimistic versions where races matter.
   - Apply domain policy.
   - Persist state, audit entry, and outbox message in the same transaction.
   - Return a typed DTO, not a mutable ORM object.

3. **Domain policy — pure code in `policies/<entity>.py` or a narrowly named module**
   - Express invariants and state transitions in pure, deterministic code where practical.
   - Use domain-specific names and exceptions.
   - Do not import HTTP, Celery, RabbitMQ, Supabase, or another service client.

4. **Reads and adapters — `querysets/<entity>.py`, `clients/<provider>.py`, `consumers/<event>.py`, `tasks.py`**
   - Keep scoped, reusable ORM reads in named QuerySets and query services.
   - Keep message adapters, external clients, consumers, and Celery tasks in their explicit house folders/modules.
   - Add a repository abstraction only when it protects a real boundary, makes a complex aggregate coherent, or materially improves tests.
   - Do not add generic `infrastructure/` nesting merely to imitate Clean Architecture vocabulary.

Thin code is not the same as hidden code. Avoid generic base classes that conceal authorization, transitions, queries, or transaction behavior.

For new code, use plural folder names consistently: `views/`, `serializers/`, `querysets/`, `services/`, `tests/`. Name files by entity (`student.py`, `payment.py`) and services by business verb (`record_payment.py`, `grant_quiz_retake.py`). A capability does not become a separate Django app merely because it has a screen or table.

## Persistence and Service Boundaries

- A service accesses only its own schema/database through its own DB role.
- Store external identities as opaque typed UUIDs without cross-schema foreign keys.
- Maintain local projections from versioned events when a remote name/status is needed.
- Never use cross-service ORM imports, SQL joins, views, triggers, cascades, or shared writable tables.
- Use `Decimal` for money, explicit currency, timezone-aware datetimes, `TextChoices`/enums for finite states, and database constraints for invariants the database can enforce.
- Prefer explicit audit/history tables or append-oriented ledgers for money, approvals, permissions, and irreversible actions.
- Never delete approved financial or historical records to “undo” them; create a reversal/refund/correction.
- Keep external calls outside database transactions.
- Do not use Django signals for business orchestration.

## APIs, Events, and Tasks

- Expose synchronous operations through versioned REST/OpenAPI contracts.
- Use stable machine-readable errors such as `{"error": {"code": "...", "message": "...", "details": {...}, "request_id": "..."}}`.
- Validate at the transport boundary and repeat authoritative domain checks inside the use case.
- Require an idempotency key for retryable commands that can create money, messages, enrollments, jobs, or external effects.
- Publish integration events with transactional outbox; consume with inbox deduplication. Keep a stable `event_type` and an explicit major `event_version`.
- Assume RabbitMQ/Celery delivery is at least once.
- Configure bounded retries with exponential backoff and jitter only for retryable failures.
- Set I/O timeouts. Route terminal failures to a DLQ or explicit failed state with an operator action.
- Never put secrets or unnecessary personal data in events, logs, task arguments, or error details.

## Authorization Rules

Authorization is a conjunction, not one boolean:

`authenticated principal + active tenant membership + exact permission + branch/resource scope + domain-state permission`

- Deny by default.
- Resolve scope server-side; never trust tenant, branch, owner, role, price, approval status, or identity claims merely because the client sent them.
- Distinguish “self”, assigned resources, branch-wide, and organization-wide access.
- Re-check authorization at approval/execution time for long-running workflows.
- Record actor, effective principal, request/correlation ID, reason, and before/after state for sensitive changes.

## Testing Workflow

Implement tests with the behavior, not after it:

1. pure policy/state-transition tests;
2. application-use-case tests with ports mocked at service boundaries;
3. API tests for success, validation, authentication, permissions, scope, and stable errors;
4. database tests for constraints, locking/version conflicts, and transaction rollback;
5. idempotency, duplicate event, retry, replay, and out-of-order event tests;
6. consumer/provider contract tests for HTTP and events;
7. migration and reconciliation tests for legacy data;
8. a narrow end-to-end happy path for the capability.

Mock external services, clock, UUID generation, and message publication. Do not mock the behavior under test or replace every ORM call with meaningless mocks.

## Finish the Change

1. Run the repository's formatter, lint, type checks, tests, migration checks, and build/container validation that apply.
2. Review the diff for accidental scope, secrets, unsafe logging, missing indexes, unbounded queries, N+1 access, and remote calls inside transactions.
3. Verify OpenAPI/event contracts and migration compatibility.
4. Update the project memory or documentation required by the repository instructions. When the project uses an Obsidian vault, update its Daily entry, relevant Architecture/Initiative note, and Open Tails for any discovered unresolved defect.
5. Report what changed, what was verified, and any remaining risk. Never claim a gate passed without running it.

## Non-Negotiable Rejections

Reject or rewrite:

- business logic in serializers, views, `Model.save()`, admin hooks, or signals;
- hardcoded secrets, custom perpetual bearer tokens, or frontend service-role credentials;
- float money or client-computed authoritative totals;
- comma-separated/array roles in place of normalized grants;
- cross-service database access or distributed transactions;
- silent fallback tenant/branch IDs;
- catch-all exceptions that convert defects into successful responses;
- fire-and-forget side effects without state, idempotency, retries, and observability;
- mutable published event schemas without versioning;
- “temporary” dual writes without an owner, reconciliation, and removal gate;
- tests that cover only the happy path.
