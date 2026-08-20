---
type: knowledge
tags: [project, open-tails]
updated: 2026-08-20
---

# Open tails

| Priority | Status | Item | Owner | Evidence |
|---|---|---|---|---|
| P0 | open | Rotate the Telegram bot token exposed in conversation before enabling any bot runtime. | Project owner | Credential was shared on 2026-08-20; value is intentionally absent from Git. |
| P0 | open | Run `alembic upgrade head` and all 4 skipped integration tests against real PostgreSQL. | Backend | `b5e63e5`: 100 passed, 4 skipped without Docker/`TEST_DATABASE_URL`. |
| P0 | open | Implement a short-lived one-time panel → Finance SSO handoff; never place bearer tokens in URLs. | Identity + Frontend | Panel card and both session entry points exist, but browser origins are not bridged. |
| P0 | open | Bind the authenticated Finance UI to live accounts/categories/transactions/summary instead of preview data. | Finance frontend | Local `spacewhy-finance` commit `3fdd171`. |
| P1 | open | Add refresh/revocation, durable OTP delivery outbox worker, edge rate limits and enrollment-link HTTP flow. | Identity | `b5e63e5` implements the first auth slice only. |
| P1 | open | Add transfers, reversal/correction, account/category mutation and cashflow query with concurrency/integration coverage. | Finance backend | `b5e63e5` implements income/expense append and summary. |
| P1 | done | Implement phone/OTP session flow and Finance SpaceDrop entry in the customer panel. | Frontend | `spacewhy-panel` commit `ea83ca2`; lint/type/build passed. |
| P1 | partial | Create standalone `spacewhy-finance` from the UI kit; assign and push its Git remote. | Frontend + repository owner | Local commit `3fdd171`; no remote specified. |
| P1 | done | Reconcile the source of truth with the current FastAPI backend. | Backend | Architecture and README updates in `7a92a1f`/`b5e63e5`. |
| P-medium | open | Select production secret manager and generate a reviewed dependency/image lock before deployment. | Deployment owner | Only `.env.example` and local compose templates exist. |
| P-medium | open | Upgrade the legacy Minimals dependency tree without breaking the 121-route UI kit; `npm audit` reports 73 advisories. | Frontend owner | `npm ci` verification on 2026-08-15. |
