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

## Performance

- Client navigation has a single delegated listener with cleanup; it does not rescan the DOM or patch `history.pushState` repeatedly.
- Route loading uses a 3px progress indicator instead of a fullscreen animated splash.
- Framer Motion loads the smaller `domAnimation` feature set because the UI kit does not use motion drag/layout features.
- Static glass surfaces do not animate paint-heavy shadow, background and radius properties; interactive feedback remains within 160–180ms.
- Demo data is local-first through the Axios adapter, eliminating broken or slow requests to the retired Minimals demo API.
- Performance implementation commit: `fa08f4b`.
