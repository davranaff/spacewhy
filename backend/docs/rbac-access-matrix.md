# Booking RBAC access matrix

All entries are tenant-scoped first. `O` means organization, `B` means assigned branch(es), `S`
means the linked specialist's own objects, and `C` means the authenticated customer's own objects.
`Audit` means an append-only event is written in the same transaction. `Reason` means a non-empty
reason is required for staff action.

## Built-in roles

| Role | Default scope | Primary capability |
| --- | --- | --- |
| OWNER | O | All tenant permissions including ownership transfer; never platform access. |
| ADMIN | O | All daily tenant operations except ownership transfer. |
| BRANCH_MANAGER | B | Operational branch management and safe staff delegation. |
| RECEPTIONIST | B | Booking desk and non-sensitive client workflow. |
| CASHIER | B | Own cash-shift, payment, and refund workflow. |
| SPECIALIST | S | Own agenda and assigned service delivery. |
| INVENTORY_MANAGER | B | Stock, products, and consumption workflow. |
| ACCOUNTANT | O/B | Finance, reconciliation, and finance audit data. |
| ANALYST | O/B | Read-only aggregate analytics. |
| AUDITOR | O/B | Read-only operations, finance, inventory, and audit history. |

## Permission registry

| Domain | Codes |
| --- | --- |
| Organization | `organization.settings.view`, `organization.settings.manage`, `organization.billing.view`, `organization.billing.manage`, `organization.ownership.transfer` |
| Access | `access.members.view`, `access.members.invite`, `access.members.manage`, `access.members.deactivate`, `access.roles.view`, `access.roles.manage`, `access.roles.assign`, `access.bind_codes.view`, `access.bind_codes.create`, `access.bind_codes.revoke`, `audit.view` |
| Branches | `branches.view`, `branches.create`, `branches.update`, `branches.delete` |
| Catalog | `categories.view`, `categories.manage`, `services.view`, `services.manage`, `services.prices.manage` |
| Staff and availability | `staff.view`, `staff.manage`, `availability.view`, `availability.manage`, `availability.exceptions.manage`, `availability.override` |
| Bookings | `bookings.view`, `bookings.create`, `bookings.update`, `bookings.confirm`, `bookings.reschedule`, `bookings.cancel`, `bookings.check_in`, `bookings.complete`, `bookings.no_show`, `bookings.override`, `bookings.notes.view`, `bookings.notes.manage` |
| Clients | `clients.view`, `clients.create`, `clients.update`, `clients.view_sensitive`, `clients.export`, `clients.anonymize` |
| Cash | `cash.shifts.view`, `cash.shifts.open`, `cash.shifts.close`, `cash.shifts.manage_others`, `cash.payments.view`, `cash.payments.create`, `cash.refunds.create`, `cash.refunds.approve`, `cash.ledger.view`, `cash.ledger.manual_entry` |
| Inventory | `inventory.products.view`, `inventory.products.manage`, `inventory.stock.view`, `inventory.stock.adjust`, `inventory.movements.view`, `inventory.movements.create`, `inventory.consumption.view`, `inventory.consumption.override` |
| Analytics | `analytics.bookings.view`, `analytics.finance.view`, `analytics.staff.view`, `analytics.inventory.view`, `analytics.personal.view`, `analytics.export` |

## HTTP and service actions

| Endpoint/action | Method | Permission | Scope | Field / policy | Reason | Audit |
| --- | --- | --- | --- | --- | --- | --- |
| Client catalog, availability | GET | Client booking read/create capability | C/public | Public active catalog only | — | — |
| Client hold and appointment confirm | POST | `bookings.create` | C | Customer identity is derived from bearer | — | Creation is durable/outbox-backed |
| Client appointment list/get | GET | `bookings.view` | C | SQL customer predicate | — | — |
| Client cancel/reschedule | POST | `bookings.cancel`, `bookings.reschedule` | C | Own appointment and policy cutoff | Client policy | Yes |
| Staff agenda/list/get | GET | `bookings.view` | O/B/S | SQL appointment predicate | — | — |
| Staff confirm/check-in/complete/no-show | POST | Exact `bookings.*` transition code | O/B/S | State machine and object scope | Transition policy | Status audit; completion inventory is idempotent |
| Staff/admin cancel/reschedule | POST | `bookings.cancel`, `bookings.reschedule` | O/B/S | State and object scope | Yes for staff cancel | Yes |
| Admin price override | POST | `bookings.override` | O/B | Snapshot only, no raw price from client hold | Yes | Yes |
| Settings | GET/PATCH | `organization.settings.view/manage` | O | Strict settings whitelist | — | Settings audit |
| Branch/category/service/admin resources | GET/POST/PATCH/DELETE | Read code plus narrow create/manage/delete code | O/B | Tenant SQL filter and explicit field whitelist | Sensitive changes as policy requires | Resource audit |
| Customers | GET/POST/PATCH | `clients.view/create/update` | O/B/S where applicable | Phone and notes need `clients.view_sensitive` | — | Resource audit |
| Staff bind code | POST/revoke/list | `access.bind_codes.create/revoke/view` | O/B | Hash stored; raw code returned once only | Revoke reason optional | Yes |
| Cash shifts | POST | `cash.shifts.open/close` | O/B/S | Cashbox and shift branch verified | Close notes as policy | Yes |
| Payment | POST | `cash.payments.create` | O/B | Appointment and cashbox share tenant/branch | — | Yes |
| Refund | POST | `cash.refunds.create` | O/B | Locks source payment; amount is bounded/idempotent | Yes | Yes |
| Manual ledger entry | POST | `cash.ledger.manual_entry` | O/B | Open shift and cashbox branch verified | Yes | Yes |
| Inventory movement/adjustment | POST | `inventory.movements.create` / `inventory.stock.adjust` | O/B | Warehouse and product tenant/branch verified | Adjustment reason | Yes |
| Analytics dashboard | GET | Per-domain `analytics.*.view` | O/B/S | Separate SQL scope per analytics domain; aggregates only | — | — |
| Effective access | GET `/access/me`, `/access/members/{id}/access` | Active membership / `access.members.view` | O/B/S | Live roles, grants, capabilities; never trusted client flags | — | — |
| Registry / roles | GET/POST/PATCH | `access.roles.view/manage` | O | System roles immutable; delegated permissions cannot exceed actor | — | Yes |
| Role clone/deactivate/delete | POST/DELETE | `access.roles.manage` | O | Custom roles only; delete requires no assignment history | Optional | Yes |
| Assign/change/revoke role | POST/PATCH | `access.roles.assign` | O/B | Every target branch and old/new scope checked | Revoke optional | Yes |
| Create/deactivate member | POST | `access.members.invite/deactivate` | O/B or O | Last OWNER cannot be removed | Optional | Yes |
| Ownership transfer | POST | `organization.ownership.transfer` | O | Atomic replacement of OWNER assignment | Optional | Yes |
| Access audit history | GET | `audit.view` | O/B | SQL tenant/branch filtering; append-only store | — | — |

## Role-by-action summary

| Action family | OWNER | ADMIN | BRANCH_MANAGER | RECEPTIONIST | CASHIER | SPECIALIST | INVENTORY | ACCOUNTANT | ANALYST | AUDITOR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Booking lifecycle | yes | yes | B | B, no complete | read/payment context | S | no | read | no | read |
| Cash / refunds | yes | yes | B | no | B/own shift | no | no | O/B | no | read |
| Inventory | yes | yes | B | no | no | consumption read | B | no | aggregate | read |
| Client PII | sensitive | sensitive | B as granted | operational contacts | minimal booking data | minimal service data | none | safe finance reference | aggregates | no sensitive fields |
| Role/access management | yes | yes | safe B assignments | no | no | no | no | no | no | read audit |
| Analytics | all | all | B | no | no | personal | inventory | finance | aggregates | read-only data/audit |

`yes` always means only the permission set and scope actually assigned. A role name never bypasses
the central policy layer.
