---
type: knowledge
tags: [project, open-tails]
updated: 2026-08-15
---

# Open tails

| Priority | Status | Item | Owner | Evidence |
|---|---|---|---|---|
| P-high | open | Define the first product bounded context, owner, contracts, authorization scope, and persistence model before adding a Django domain app. | Product + backend | Initial scaffold intentionally contains no domain app. |
| P-medium | open | Select production secret manager and generate a reviewed dependency/image lock before deployment. | Deployment owner | Only `.env.example` and local compose templates exist. |
| P-medium | open | Upgrade the legacy Minimals dependency tree without breaking the 121-route UI kit; `npm audit` reports 73 advisories. | Frontend owner | `npm ci` verification on 2026-08-15. |
