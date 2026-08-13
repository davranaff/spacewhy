# Backend quality gates

Use this checklist proportionally for every backend change. A gate marked not applicable needs a reason; it is not silently skipped.

## Contract and ownership

- [ ] One service owns every changed field and state transition.
- [ ] Command/query/event/task classification is explicit.
- [ ] Tenant, branch, self/assigned/resource scope is defined.
- [ ] Inputs, outputs, errors, and state transitions match the migration specification.
- [ ] No remote table, ORM model, cross-schema FK/JOIN/write/trigger, or distributed transaction was introduced.
- [ ] HTTP and event compatibility/versioning is deliberate.

## Validation and authorization

- [ ] Request shape and cross-field input are validated.
- [ ] Authoritative domain invariants are enforced inside the use case.
- [ ] Authentication, active membership, exact permission, resource scope, and domain state are all checked.
- [ ] Client-provided tenant, branch, ownership, price, total, role, identity, and status are not trusted.
- [ ] Denial, cross-tenant, cross-branch, self-versus-other, inactive-user, and stale-permission cases are tested.
- [ ] Sensitive actions record actor, reason, request/correlation ID, and before/after state.

## Data and transactions

- [ ] Money uses `Decimal` and explicit currency.
- [ ] Finite state uses an enum; impossible transitions fail.
- [ ] Database constraints and indexes enforce durable invariants and hot lookups.
- [ ] Transaction scope is short; no HTTP, broker, file, AI, or storage call occurs inside it.
- [ ] Race strategy is explicit: unique constraint, row lock, compare-and-swap version, or another justified mechanism.
- [ ] Approved/historical state uses correction, reversal, or append-only history instead of destructive mutation.
- [ ] Migration is reversible where practical and has a repeatable reconciliation check.

## Reliability

- [ ] Retryable create/effect commands have scoped idempotency keys and request fingerprints.
- [ ] State, audit, and outbox commit atomically.
- [ ] Consumers use inbox deduplication and tolerate replay, duplicates, and out-of-order versions.
- [ ] External calls have timeouts and typed retryable/non-retryable errors.
- [ ] Retries are bounded with backoff/jitter; terminal failure has DLQ or explicit operator-visible state.
- [ ] Tasks pass identifiers, not secrets or large mutable payloads.
- [ ] Saga timeout and compensation behavior exists for multi-service workflows.

## API and query behavior

- [ ] API returns a stable error envelope and never leaks tracebacks or sensitive internals.
- [ ] Lists are paginated/bounded with deterministic ordering.
- [ ] Query starts from tenant/resource scope.
- [ ] `select_related`, `prefetch_related`, annotations, and indexes are deliberate.
- [ ] Hot endpoints have query-count or performance regression coverage.
- [ ] DTOs/contracts do not expose mutable ORM objects or internal columns accidentally.

## Test coverage

- [ ] Domain policy/state transitions.
- [ ] Application use case success and every meaningful rejection.
- [ ] API authentication, authorization, validation, response, and error schema.
- [ ] Constraint, transaction rollback, and concurrency conflict.
- [ ] Idempotent replay and conflicting key reuse.
- [ ] Event contract, duplicate, stale, retry, and DLQ behavior.
- [ ] Legacy backfill/reconciliation and representative dirty data.
- [ ] At least one narrow end-to-end path for a new capability.

## Security and operations

- [ ] No secret, token, private URL, credential, or personal payload is committed or logged.
- [ ] JWT issuer, audience, expiry, and signature are verified through approved JWKS.
- [ ] Files use private storage; authorization precedes short-lived signed URL generation.
- [ ] Rate limits use shared infrastructure for horizontally scaled instances.
- [ ] Health/readiness, metrics, structured logs, trace/correlation IDs, alerts, and runbook impact are covered.
- [ ] Admin behavior uses exact permissions and audit; admin is not a bypass around domain rules.

## Mechanical verification

Discover the repository commands from its manifests and CI, then run the applicable set:

```bash
ruff check .
ruff format --check .
mypy .
python manage.py makemigrations --check --dry-run
python manage.py check --deploy
pytest
python manage.py spectacular --validate
```

Also run the project build/container check and focused security/dependency scan when applicable. Do not install or upgrade dependencies merely to make a gate available unless that is part of the task.

Review the final diff and migration plan manually. Tool success does not prove correct ownership, authorization, race handling, or product behavior.
