# Booking RBAC architecture

## Security model

Booking authorization is deny-by-default and permission-based. Roles are reusable templates;
services ask for a stable `PermissionCode`, while `AccessPolicy` resolves the scope for that
specific code. A grant from one role never broadens a different permission.

Every data query starts with `organization_id`. Branch filtering is added to SQL for branch-bearing
entities; appointment filtering additionally understands `SELF` (the linked specialist) and
`CUSTOMER_OWN` (the linked customer). A guessed ID outside the tenant is not loaded and returns a
not-found response. A same-tenant object outside the actor's scope is denied.

## Persisted model

| Entity | Responsibility |
| --- | --- |
| `booking_permission_definitions` | Stable code, category, allowed scopes, sensitivity flag. |
| `booking_roles` | Global immutable built-ins and tenant-owned custom role templates. |
| `booking_role_permissions` | Atomic permission membership of a role. |
| `booking_memberships` | Active staff identity in one tenant; clients do not have memberships. |
| `booking_role_assignments` | Revocable, time-bounded role assignment with one explicit scope. |
| `booking_role_assignment_branches` | Many branches for a `BRANCH` assignment. |
| `booking_platform_administrators` | Platform-only identities; never a tenant role. |
| `booking_audit_log` | Append-only security and business audit events. |

Built-in roles have `organization_id = NULL`, are source-controlled, and cannot be edited or
deleted through tenant APIs. Custom roles belong to exactly one organization and cannot contain an
unknown or platform permission. One membership may have any number of active assignments; their
grants are unioned while each individual permission retains all of its scopes.

## Scopes

| Scope | Meaning |
| --- | --- |
| `ORGANIZATION` | All allowed objects in the signed tenant, never another tenant. |
| `BRANCH` | Only branches explicitly linked to the assignment. |
| `SELF` | Only the actor's linked specialist objects, primarily appointments and personal analytics. |
| `CUSTOMER_OWN` | Only the authenticated client's customer record and appointments. |

`AccessPolicy.branch_predicate()` and `AccessPolicy.appointment_predicate()` are the canonical
SQL policy builders. `require_branch()` and `require_appointment()` use identical semantics after
an object is loaded. Do not introduce `if role == ...` checks in new use cases.

## Request and session flow

1. Telegram WebApp authentication verifies signed `initData` and resolves the tenant from the
   server-owned bot installation.
2. The issued JWT contains only subject, tenant, principal type, customer/membership identity,
   access version, and expiry. It contains no role or permission snapshot.
3. `get_booking_actor` verifies the signature and calls `BookingAccessService` to hydrate current
   authority on every request.
4. The router passes the actor to an application service; the service repeats authoritative
   permission and scope checks before reading or mutating data.
5. Audit metadata from the HTTP request is attached to sensitive writes in the same transaction.

A revoked assignment, deactivated membership, expired assignment, changed role permission, or
stale membership access version therefore stops working at the next request. There is no long-TTL
permission cache. The version remains available for a future cache key if one is introduced.

## Client, staff, platform, and worker boundaries

Clients are represented by `ActorType.CUSTOMER` and fixed client permissions under
`CUSTOMER_OWN`. They cannot receive tenant staff roles. Staff are active memberships and derive
authority from active assignments only. `BookingSessionCodec` refuses to issue a public tenant
bearer token for a system or platform identity.

`BookingPlatformAccessService` resolves a row from `booking_platform_administrators` and returns a
separate platform access value, not a `BookingActor`. No public Booking route accepts it. A future
internal platform boundary must authenticate it independently and audit every cross-tenant action.

Workers provide organization, task ID, source, and named operation to `system_actor`. The current
hold-expiry and daily-agenda operations receive only their narrow operation permissions and a
concrete branch scope where available. Before notification delivery the worker re-checks the
recipient's active binding, membership, role permission, time window, and scope.

## Custom-role and delegation safeguards

Creating, cloning, updating, assigning, or changing a custom role requires a role-management
permission. The assigning actor must already possess every delegated permission. Assignment scope
must be supported by every permission in the role, every branch must belong to the tenant, and a
branch-scoped actor must hold access to every requested branch. Branch managers can assign only
safe built-in branch roles or custom roles whose permissions and branch scope do not exceed their
current access.

System roles cannot be updated, deactivated, or deleted. Deactivation of a custom role increments
the access version of all active assignees. Deletion is allowed only when no assignment history
references the role. Updates to role assignment scope both authorize the old scope and validate
the requested replacement scope.

The `OWNER` role must always be organization-scoped and non-expiring. Revoking an owner assignment
or deactivating an owner membership locks current owners and refuses the operation if it would
remove the last effective owner. Ownership transfer atomically grants the target active membership
the global `OWNER` assignment and revokes prior owner assignments with an audit event.

## Field and output restrictions

The generic management serializer is an explicit field whitelist. Customer phone and notes are
omitted unless `clients.view_sensitive` is present. Appointment responses expose payment state,
amounts, and refund flags only to clients or actors with a financial read permission. Analytics
returns scoped aggregates by domain; finance, booking, staff, and inventory scopes are resolved
independently so one wider grant cannot expand another domain's query.

New read models must follow the same approach: start with a safe DTO, add fields only when the
relevant permission requires them, and never rely on a frontend to hide data.

## Audit

`append_audit_event()` writes immutable `booking_audit_log` rows in the same transaction as a
sensitive mutation. Rows include tenant and optional branch, actor type/subject/membership, action
code, target, reason, safe before/after values, request/correlation/task IDs, source, IP, user
agent, and timestamp. PostgreSQL rejects updates and deletes from the table. Do not place tokens,
credentials, full payment data, or unnecessary sensitive PII in audit payloads.

## Using the policy layer

```python
statement = sa.select(Appointment).where(
    Appointment.organization_id == actor.organization_id,
    AccessPolicy.appointment_predicate(actor, PermissionCode.BOOKINGS_VIEW),
)

AccessPolicy.require_appointment(
    actor,
    PermissionCode.BOOKINGS_COMPLETE,
    branch_id=appointment.branch_id,
    specialist_id=appointment.specialist_id,
    customer_id=appointment.customer_id,
)
```

For a branch-bound create operation, load the referenced object under the signed tenant first,
then call `AccessPolicy.require_branch()` with the server-verified branch ID. Never authorize a
caller from an `organization_id`, role, permission, or branch ID supplied in the request body.
