---
type: knowledge
tags: [project, open-tails]
updated: 2026-08-20
---

# Open tails

| Priority | Status | Item | Owner | Evidence |
|---|---|---|---|---|
| P0 | open | Rotate the Telegram bot token exposed in conversation before enabling any bot runtime. | Project owner | Credential was shared on 2026-08-20; value is intentionally absent from Git. |
| P1 | open | Implement the approved Identity + Finance vertical slice and prove it with real PostgreSQL integration tests. | Backend | [[Initiatives/SpaceDrop Finance]] and [[End-to-End Flows/SpaceDrop Finance]] |
| P1 | open | Implement phone/OTP session flow and Finance SpaceDrop entry in the customer panel. | Frontend | `spacewhy-panel/frontend` is still a clean scaffold. |
| P1 | open | Create the standalone `spacewhy-finance` frontend from the UI kit and assign its Git remote. | Frontend + repository owner | UI kit template is ready; Finance remote was not specified. |
| P1 | open | Reconcile stale repository-level Django instructions/memory with the current FastAPI backend so future agents follow one source of truth. | Backend | `backend/AGENTS.md` and current code are FastAPI; parts of root memory/instructions were stale. |
| P-medium | open | Select production secret manager and generate a reviewed dependency/image lock before deployment. | Deployment owner | Only `.env.example` and local compose templates exist. |
| P-medium | open | Upgrade the legacy Minimals dependency tree without breaking the 121-route UI kit; `npm audit` reports 73 advisories. | Frontend owner | `npm ci` verification on 2026-08-15. |
