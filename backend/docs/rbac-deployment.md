# Deploying Booking RBAC

## Migration order

Deploy the application code and migration together, then run migrations as one explicit
operational job before rolling out API and worker replicas:

```bash
cd backend
make migrate
make sync-rbac
```

`20260817_02_scoped_rbac` creates the normalized RBAC tables, extends binding and audit records,
seeds the registry and built-in roles, preserves legacy `booking_access_grants`, and migrates
recognized legacy staff grants into memberships and assignments. The data copy deliberately runs
only against a live database. `alembic upgrade head --sql` remains available to inspect schema and
static seed SQL; it does not execute a data-dependent legacy copy.

`make sync-rbac` is idempotent and is safe to run after every deployment. It creates missing
permission definitions and built-in roles, updates their source-controlled metadata and role
permissions, and never deletes tenant custom roles.

## First tenant owner and bootstrap

Use the explicit provisioning command only for a new booking tenant:

```bash
make provision-booking ARGS='--organization-slug salon --organization-name "Salon" --owner-display-name "Owner"'
```

It synchronizes RBAC and creates an active owner membership with the global `OWNER` role. It can
print a one-time staff bind code; handle it as a short-lived credential and do not put it into
source control, tickets, or logs. Existing tenants are migrated from active legacy staff grants.
Review migration logs for any legacy grant whose role or explicit permission cannot be recognized.

## Post-deployment verification

Run these from `backend` after configuring an actual PostgreSQL URL:

```bash
make migration-check
make lint
make typecheck
make test
python3 -m uv run alembic upgrade head --sql
```

Check that every organization has at least one active, effective global `OWNER` assignment. Verify
`GET /api/v1/access/me` using a staff bearer token, then confirm that a revoked assignment or a
deactivated membership is rejected on its next request. Test a branch-scoped actor against both an
allowed and a sibling branch.

## Operational troubleshooting

| Symptom | Check |
| --- | --- |
| Staff bearer rejected after a role change | The access version intentionally invalidates it; authenticate again and inspect membership/activity. |
| Staff Telegram callback stops working | Verify active binding, membership, role assignment, time window, specialist link, and branch scope. |
| Permission missing from `/access/me` | Run `make sync-rbac`, then verify the active role assignment and its allowed scope. |
| Branch manager cannot reach another branch | Expected: inspect assignment-branch rows instead of widening a request parameter. |
| Audit query appears incomplete | Branch-scoped auditors see only audit rows with an allowed branch; organization scope is required for tenant-wide events. |

Never repair RBAC by editing a JWT, hard-coding a role condition, or directly inserting a broad
assignment in production. Use the access-management API or a reviewed, tenant-scoped SQL repair
with an accompanying audit event.

## Rollback considerations

The downgrade removes normalized RBAC structures and newly added audit/binding columns, and drops
the audit append-only trigger. It deliberately leaves the pre-existing legacy access-grant table
unchanged, but it cannot recreate role/assignment changes made after the migration. Take a backup
and assess tenant access changes before rollback. Prefer a forward fix plus `make sync-rbac` for
registry metadata issues.
