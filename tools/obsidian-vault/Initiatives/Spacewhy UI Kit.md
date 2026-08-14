---
type: initiative
tags: [project, frontend, design-system, liquid-glass]
updated: 2026-08-15
---

# Spacewhy UI Kit

## State

The complete Minimals-based Spacewhy UI kit is present and verified under `frontend/uikit/` on branch `codex/add-spacewhy-uikit`; implementation commit: `55283e6`.

## Scope

- Preserve the full Minimals route and component catalog.
- Provide dark and light themes with visible liquid-glass surfaces.
- Expose live material controls for optical intensity, transparency, and surface liquidity.
- Keep the UI kit isolated from the reserved `frontend/admin/` boundary.

## Verification

- `npm ci`
- `npm run lint`
- `npm run build` generated 121 routes.
