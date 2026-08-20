---
type: flow
tags: [project, finance, identity, telegram, e2e]
updated: 2026-08-20
---

# SpaceDrop Finance end-to-end

## Entry surfaces

```text
spacewhy.uz
  -> spacewhy-panel
       -> Telegram phone login
       -> SpaceDrop catalog
       -> Finance card
       -> spacewhy-finance web app

Telegram auth bot
  -> verified phone binding
  -> OTP for browser panel
  -> Finance Mini App launch
```

Panel and Finance do not invent separate user accounts. Both trust the same Identity session.
Finance receives only a verified `principal_id`; Telegram identifiers and phone numbers remain
owned by Identity.

## First-time enrollment

1. User opens the exact Spacewhy auth bot from panel deep link.
2. Bot handles `/start <signed_nonce>` and displays a Telegram native `request_contact` button.
3. User shares the contact. Handler rejects forwarded/foreign contacts and accepts only
   `contact.user_id == message.from.id`.
4. Identity normalizes the phone to E.164, confirms uniqueness policy, stores the verified
   Telegram user/chat binding, consumes the nonce and writes audit/outbox records atomically.
5. Bot confirms enrollment without echoing the full phone number.

## Browser panel login by phone

1. User enters an E.164-compatible phone number.
2. `POST /api/v1/identity/auth/telegram/challenges` returns `202` and the same generic body for
   known and unknown numbers.
3. For a verified binding, Identity creates a challenge with a keyed OTP hash, five-minute TTL,
   maximum attempts and rate-limit counters. A notification intent is written to outbox in the
   same transaction.
4. Worker sends the one-time code to the already-bound Telegram chat. Provider I/O is outside
   the database transaction; retries are bounded and terminal failure is operator-visible.
5. `POST /api/v1/identity/auth/telegram/challenges/{id}/verify` atomically checks expiry,
   attempts and one-time consumption.
6. Successful verification creates an access session plus rotating refresh session. Replay,
   expired code, excessive attempts and conflicting challenge state return stable problem codes.
7. Panel uses a secure HTTP-only refresh cookie or BFF session. It never persists a long-lived
   bearer token in `localStorage`.

## Telegram Mini App login

1. Mini App receives Telegram `initData`.
2. Identity validates the Telegram signature against the bot credential, `auth_date`, replay
   window and exact bot app binding.
3. Backend resolves the verified Telegram subject to one principal and issues the same Spacewhy
   session contract. Tenant, workspace and permissions always come from server-side state.

## Record income or expense

1. Authenticated principal selects a Finance workspace and account.
2. Client submits direction, Decimal amount, account currency, category, occurred timestamp,
   optional note/tags and an `Idempotency-Key`.
3. Finance verifies active membership and `finance.transaction.create`, validates category
   direction, account state, currency and timestamp.
4. One short transaction locks the idempotency scope, appends the ledger entry, updates no
   client-authoritative balance, writes audit and outbox, and commits.
5. API returns an immutable DTO. Identical replay returns the original response; reuse of the key
   with different input returns a conflict.
6. Dashboard balance and cashflow are calculated from scoped ledger queries/projections.

## Correction and reversal

- Posted financial entries are never hard-deleted or amount-edited.
- Reversal creates a linked opposite ledger entry once.
- Correction atomically creates a reversal and replacement entry, preserving the complete audit
  chain and correlation ID.
- Archived account/category remains readable in history but unavailable for new transactions.

## Transfer

One use case creates two linked legs in one Finance transaction: debit from source and credit to
destination. Same-currency transfer requires equal absolute amounts. Cross-currency transfer
requires both explicit amounts and rate metadata; Finance never silently fetches or applies a rate.

## Read model

- `GET /api/v1/finance/accounts`
- `GET /api/v1/finance/categories`
- `GET /api/v1/finance/transactions` with cursor, date/account/category/direction filters
- `GET /api/v1/finance/dashboard/summary`
- `GET /api/v1/finance/dashboard/cashflow`

Every query begins from membership/workspace scope, uses deterministic ordering and bounded
pagination. Responses never include phone, Telegram chat ID, credential data or internal hashes.
