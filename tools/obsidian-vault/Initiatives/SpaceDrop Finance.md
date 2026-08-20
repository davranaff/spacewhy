---
type: initiative
tags: [project, finance, telegram, panel]
updated: 2026-08-20
---

# SpaceDrop Finance

## Implementation state — 2026-08-20

- Architecture/specification: complete and pushed in `7a92a1f`.
- Backend vertical slice: pushed in `b5e63e5`. Implemented verified-contact enrollment, phone OTP, Mini App `initData`, bearer principal, Finance bootstrap/accounts/categories/income-expense transactions/cursor list/summary, migration, audit, idempotency and outbox persistence.
- Correct panel vertical slice: actual ready `Spacewhy/space-drop` UI, pushed to `Muxammad1106/spacewhy-panel` branch `codex/space-drop-auth-finance` as `254e716`. Earlier scaffold commit `ea83ca2` is obsolete.
- Finance client: independent local repository commit `3fdd171`; remote not assigned.
- The API tables below remain the target contract. Refresh/revoke, enrollment-link HTTP, handoff, transfers, reversals/corrections, category mutation, live frontend binding and cashflow endpoint are not yet implemented.

`identity` is only the internal technical name of the auth module. It must not appear as a separate Spacewhy ID product. The bot authenticates entry into the existing Space Drop panel; Finance and every other SpaceDrop remain separate product/domain entities.

## Goal

Запустить первый сквозной SpaceDrop для личного финансового учёта: пользователь приходит с
landing в panel, входит по телефону через Telegram bot, открывает Finance и записывает доходы,
расходы и переводы в web/Mini App.

Официальное написание в коде и интерфейсе: **Finance** и `spacewhy-finance`. Опечатки
`finace`/`SpaceDorp` из исходного сообщения не становятся публичными identifiers.

## Bounded contexts

### Identity owns

- Spacewhy principal;
- normalized phone and verification status;
- Telegram user/chat binding for one isolated auth bot;
- enrollment nonce, OTP challenge, attempt/rate-limit state;
- access/refresh sessions and revocation;
- identity audit and auth notification outbox.

### Finance owns

- personal/shared-ready workspace and membership projection;
- accounts and explicit currency;
- income/expense categories;
- append-only ledger entries;
- linked transfer legs;
- reversals/corrections;
- idempotency, audit, outbox and dashboard projections.

Finance stores an opaque `principal_id`. It does not read Identity tables or Booking customers.

## MVP API contract

### Identity

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/identity/enrollments` | Create short-lived signed bot enrollment link |
| `POST` | `/api/v1/identity/auth/telegram/challenges` | Request generic phone login challenge |
| `POST` | `/api/v1/identity/auth/telegram/challenges/{id}/verify` | Verify OTP and issue session |
| `POST` | `/api/v1/identity/auth/telegram/webapp` | Exchange verified Telegram `initData` for session |
| `POST` | `/api/v1/identity/sessions/refresh` | Rotate refresh session |
| `DELETE` | `/api/v1/identity/sessions/current` | Revoke current session |
| `GET` | `/api/v1/identity/me` | Return display-safe principal DTO |

### Finance

| Method | Path | Purpose |
|---|---|---|
| `GET/POST` | `/api/v1/finance/accounts` | List/create accounts |
| `PATCH` | `/api/v1/finance/accounts/{id}` | Rename/archive account; never rewrite history |
| `GET/POST` | `/api/v1/finance/categories` | List/create custom categories |
| `PATCH` | `/api/v1/finance/categories/{id}` | Rename/archive custom category |
| `GET/POST` | `/api/v1/finance/transactions` | Cursor list/create ledger entry |
| `GET` | `/api/v1/finance/transactions/{id}` | Entry and correction chain |
| `POST` | `/api/v1/finance/transactions/{id}/reverse` | One idempotent reversal |
| `POST` | `/api/v1/finance/transactions/{id}/correct` | Reversal + replacement |
| `POST` | `/api/v1/finance/transfers` | Atomic linked debit/credit legs |
| `GET` | `/api/v1/finance/dashboard/summary` | Balances, totals and comparison |
| `GET` | `/api/v1/finance/dashboard/cashflow` | Bounded time-series cashflow |

## Core data invariants

- All IDs are UUIDs and all timestamps timezone-aware UTC.
- Amount is positive `Decimal`; direction is an enum, never encoded by an ambiguous signed input.
- Account currency is ISO 4217 and immutable after the first ledger entry.
- Category direction must match the transaction direction.
- Every record belongs to exactly one workspace; scope is resolved from authenticated membership.
- Initial balance, correction, reversal and transfer are explicit entry kinds.
- A posted entry is immutable. Reversal is unique per original entry.
- Transfer legs share `transfer_id`, occur atomically and cannot reference the same account.
- Idempotency scope is workspace + actor + operation + key, with normalized request fingerprint.
- State, audit and outbox commit together. Provider calls happen after commit.
- Lists are cursor-paginated, bounded and ordered by `(occurred_at DESC, id DESC)`.

## Stable error codes

- `identity_enrollment_required`
- `identity_challenge_invalid_or_expired`
- `identity_challenge_attempts_exhausted`
- `identity_session_invalid`
- `finance_membership_required`
- `finance_permission_denied`
- `finance_account_archived`
- `finance_currency_mismatch`
- `finance_category_direction_mismatch`
- `finance_transaction_already_reversed`
- `finance_idempotency_conflict`
- `finance_cursor_invalid`

All map to the repository-wide RFC 9457 response with `request_id`.

## Frontend scope

### Panel

- phone input and OTP confirmation flow;
- enrollment deep link when phone is not bound, without account enumeration;
- authenticated shell and session refresh/logout;
- SpaceDrops catalog with Finance card/status/action;
- open Finance while preserving common session through approved redirect/code exchange, not URL bearer token.

### `spacewhy-finance`

- responsive Telegram-safe shell, light/dark Liquid Glass theme;
- onboarding: default currency, first account and initial balance;
- dashboard: total balance, income, expenses, cashflow and recent entries;
- fast add income/expense form;
- accounts and category management;
- transaction list/filter/detail, reversal and correction;
- transfers;
- loading, empty, validation, offline/retry and reduced-motion states;
- Russian first, with Uzbek and English message keys ready.

## Test and delivery gates

Backend: Ruff format/lint, strict Pyright, unit, smoke, architecture, migration check and real
PostgreSQL integration tests for constraints/idempotency/rollback. Frontend: unit tests, ESLint,
TypeScript, production build, responsive browser QA and `git diff --check`. Secret scanning is
mandatory before every push.

Actual verification on 2026-08-20: Ruff, strict Pyright and 100 backend tests passed; 4 database integration tests were skipped because no PostgreSQL test runtime was available. Panel lint/type/build passed. Finance client 16 tests/lint/type/build passed. Production migration and deployment gates remain open.

## Out of MVP

Budgets, recurring transactions, bank integrations, CSV import/export, shared family workspaces,
receipt OCR, multi-organization billing and advanced analytics are separate increments after the
first secure end-to-end path works.
