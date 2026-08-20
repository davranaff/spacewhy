# Identity and Finance

## Ownership

`identity` is the shared authentication owner for Spacewhy panel and SpaceDrop applications. It
owns principals, verified Telegram contacts, phone challenges and identity-only access tokens.
`finance` owns personal workspaces, memberships, accounts, categories, ledger entries,
idempotency, audit and Finance outbox facts. Finance references only the public Identity
`principal_id`; it has no cross-module foreign key or ORM import.

## Telegram phone authentication

A Telegram bot cannot initiate a conversation from an arbitrary phone number. Enrollment must
start in `spacewhy_auth_bot`: the user opens the bot and shares a native Telegram contact. The
handler accepts it only when the contact user ID matches the update sender. Phone input is
normalized to E.164 and bound to that Telegram user/chat.

The browser requests `POST /api/v1/identity/auth/telegram/challenges`. The response is deliberately
identical for known and unknown numbers. For a verified binding the API sends a six-digit,
five-minute code through the pre-bound bot runtime after the challenge transaction commits. The
database stores only keyed digests, expiry and remaining attempts. The bot token is never passed
to module code or stored in Git.

Telegram Mini Apps use `POST /api/v1/identity/auth/telegram/webapp`; the verifier checks the exact
configured bot signature and age before resolving a pre-enrolled principal.

## Finance vertical slice

1. `POST /api/v1/finance/bootstrap` creates one personal workspace, owner membership, first
   account and default categories. Repeated calls return the current workspace.
2. `GET/POST /api/v1/finance/accounts` reads or creates scoped accounts.
3. `GET /api/v1/finance/categories` returns scoped income/expense categories.
4. `POST /api/v1/finance/transactions` requires `Idempotency-Key` and appends an immutable entry,
   audit row and `finance.entry.created` outbox fact in one transaction.
5. `GET /api/v1/finance/transactions` uses deterministic `(occurred_at, id)` cursor pagination.
6. `GET /api/v1/finance/dashboard/summary` groups balances, income and expenses by currency so
   unrelated currencies are never silently added together.

Amounts use `Decimal`/`NUMERIC(18, 2)`, currencies use explicit three-letter codes, and account,
category and workspace scope is always loaded from the active principal membership. Future
reversal, correction and transfer commands must append linked ledger rows; they must not mutate or
delete posted history.

## Configuration

Shape-only settings are in `deployment/env/.env.example`. Keep `spacewhy_auth_bot` disabled until
the exposed credential has been rotated, a distinct webhook secret is provisioned and HTTPS
webhook registration is complete. Production must also replace the shared session signing secret.

## Verification

Run `ruff format --check .`, `ruff check .`, `pyright`, `pytest`, and `alembic check` against a real
PostgreSQL database. Integration tests skip without an explicit `TEST_DATABASE_URL`; skipped tests
must not be reported as passed database verification.
