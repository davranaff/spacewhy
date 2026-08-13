# Spacewhy — shared agent template

This is the canonical working template for all agents in this project.

## Before changing anything

1. Read this file and the relevant repository files before editing.
2. For backend work, read `tools/skills/ruflo-django-backend/SKILL.md` and the referenced architecture/quality notes.
3. For project-memory work, read `tools/skills/obsidian-project-memory/SKILL.md` and `references/vault-conventions.md` in that skill.
4. At the beginning of a task, resolve the project vault with the bundled `project_memory.py` bootstrap utility and read `Home.md`, today's Daily note, `Knowledge/Open-Tails.md`, and relevant Architecture notes.
5. Never start the Obsidian desktop application. Filesystem vault operations are sufficient.

## Repository layout

```text
backend/                 ASGI-first Django service
deployment/              runtime configuration, compose files, and secret boundaries
frontend/admin/          reserved admin frontend; no framework scaffold yet
frontend/uikit/          reserved shared UI kit; no framework scaffold yet
tools/obsidian-vault/    project-scoped memory vault
tools/skills/            project-local reusable agent skills
```

## Backend rules

- Treat `backend/` as one deployable bounded context with service-owned persistence.
- HTTP runtime is ASGI-only: use `config/asgi.py`, Uvicorn/another ASGI server, and `async def` request handlers. Do not add `wsgi.py` or a WSGI deployment path.
- Prefer Django async ORM methods and async-compatible clients. If a required Django or third-party boundary is synchronous, isolate it explicitly through a narrow `sync_to_async` bridge and document why.
- Keep transport concerns in `views/<entity>.py` and `serializers/<entity>.py`; put material commands in `services/<use_case>.py`, domain rules in policies, and scoped reads in `querysets/<entity>.py`.
- Use the RuFlo house layout from the supplied skill: domain-oriented apps, plural layer folders, transactional outbox/inbox, idempotency, explicit authorization, bounded queries, and behavior-focused tests.
- Do not invent a domain app, schema, event, credential, or product behavior before the feature contract and owner are known.
- Keep external calls outside database transactions, never use signals for orchestration, and never put secrets or unnecessary personal data in logs, events, task arguments, or errors.

## Deployment and security rules

- Keep deployable configuration under `deployment/`; commit templates and non-secret infrastructure definitions only.
- Put real `.env` files, private keys, certificates, and tokens in the ignored `deployment/keys/` or `deployment/env/` locations as appropriate. Never commit or print their values.
- Use `.env.example` as a shape-only contract. Replace placeholders through a secret manager or an approved local mechanism before running services.
- Do not add production credentials, permissive defaults, cross-service database access, or frontend service-role credentials.

## Frontend rules

- Keep `frontend/admin/` and `frontend/uikit/` as reserved empty directories until the user explicitly asks to initialize a framework.
- Do not run a Next.js, React, Vite, or other frontend initializer as part of backend or deployment work.

## Memory and verification

- Record material decisions, actions, and verification in today's Daily note; update Architecture and Open Tails when appropriate.
- Keep notes in the user's conversation language while preserving code identifiers and commands verbatim.
- Before reporting completion, inspect the diff and run checks that are available for the changed scope. Never claim a test, migration, build, or deployment gate passed unless it was actually run.
- Preserve unrelated user changes and avoid destructive commands.
