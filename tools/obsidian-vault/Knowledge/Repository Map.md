---
type: knowledge
tags: [project, repositories, operations]
updated: 2026-08-20
---

# Repository map

## Canonical repositories

| Responsibility | GitHub | Local path | Current state |
|---|---|---|---|
| Backend and shared platform | `davranaff/spacewhy` | `/Users/muxammadchariev/Documents/ChatGPT/spacewhy-repo` | FastAPI modular monolith; `booking` exists; Finance/Identity not yet implemented |
| Customer panel | `Muxammad1106/spacewhy-panel` | `/Users/muxammadchariev/Documents/ChatGPT/spacewhy-panel` | Clean Next.js 16 app in `frontend/`; UI kit reference in `uikit/`; product screen still scaffold |
| Reusable web UI kit | `Muxammad1106/ui-kit-spacewhy` | `/Users/muxammadchariev/Documents/ChatGPT/ui-kit-spacewhy` | Private template; full Next.js/MUI/Liquid Glass catalog, tests and docs |
| Public landing | deployed at `spacewhy.uz` | separate landing repository/worktree | Entry surface; deployment details are outside the current backend repository |
| Finance frontend | remote not assigned | to be created as `spacewhy-finance` | Must be exported from UI kit without source `.git`, renamed and initialized with a clean history |

`https://github.com/davranaff/spacewhy/backend` is a GitHub directory URL, not an
independent repository. Backend commits and pushes go to the `davranaff/spacewhy` repository.

## Backend navigation

```text
backend/
├── src/app/bootstrap/                 composition root and lifespan
├── src/app/core/                      technical primitives only
├── src/app/infrastructure/bots/       provider adapters and isolated runtimes
├── src/app/modules/booking/           existing booking bounded context
├── src/app/modules/identity/          planned shared identity/auth owner
├── src/app/modules/finance/           planned income/expense owner
├── migrations/                        one reviewed Alembic stream
├── tests/{unit,integration,smoke,architecture}/
└── docs/                              authoritative backend contracts
```

Read order before backend changes:

1. root `AGENTS.md`;
2. `backend/AGENTS.md`;
3. `backend/docs/architecture.md`;
4. `backend/docs/module-template.md`;
5. `backend/docs/bot-platform.md` for bot/auth changes;
6. relevant domain specification and `backend/docs/development.md`.

## Frontend navigation

- Panel feature code: `spacewhy-panel/frontend/src/`.
- Panel reference only: `spacewhy-panel/uikit/`.
- Template source: `ui-kit-spacewhy/frontend/`.
- New Finance app: a clean copy of the template repository, with package/product identifiers
  changed to `spacewhy-finance` and only Finance product routes retained or newly composed.
- Shared visual rules: semantic theme roles, `liquidGlass()` tokens, route constants, native
  buttons/links, keyboard access, reduced motion and responsive Telegram viewport behavior.

## Git and secrets

- Work happens on `codex/*` branches unless the user names another branch.
- Preserve dirty worktrees; stage only task-owned paths.
- Never commit `.env`, bot token, webhook secret, signing secret, OTP or private keys.
- The bot credential supplied on 2026-08-20 is considered exposed and must be rotated before
  any runtime enablement. Only the rotation requirement is recorded in Git.
