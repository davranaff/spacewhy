# Spacewhy — project agent instructions

These instructions apply throughout the repository. A nested `AGENTS.md` adds rules for its
directory; read all applicable instruction files before making a change. Repository-wide safety,
security, memory, and verification rules remain mandatory in every scope.

## Before changing anything

1. Read this file, the nearest nested `AGENTS.md`, and relevant repository files before editing.
2. For work in `backend/`, read `backend/AGENTS.md` and the documentation it requires before
   editing.
3. For project-memory work, read tools/skills/obsidian-project-memory/SKILL.md and its vault conventions reference.
4. At the beginning of a task, resolve the project vault with the bundled project_memory.py bootstrap utility and read Home.md, today's Daily note, Knowledge/Open-Tails.md, and relevant Architecture notes.
5. Never start the Obsidian desktop application. Filesystem vault operations are sufficient.

## Repository layout

backend/                 ASGI-first FastAPI modular monolith
deployment/              runtime configuration, compose files, and secret boundaries
frontend/admin/          reserved admin frontend; no framework scaffold yet
frontend/uikit/          established Next.js shared UI kit, owned by frontend work
tools/obsidian-vault/    archived scaffold vault, not the active vault by default
tools/skills/            project-local reusable agent skills

## Scoped instructions

- `backend/AGENTS.md` is the authoritative implementation guide for the FastAPI service. It
  defines backend architecture, database, migration, and quality-gate rules.
- The root file continues to govern deployment, security, frontend boundaries, project memory, and
  verification for all work, including backend changes.

## Deployment and security rules

- Keep deployable configuration under deployment; commit templates and non-secret infrastructure definitions only.
- Put real .env files, private keys, certificates, and tokens in the ignored deployment/keys or deployment/env locations as appropriate. Never commit or print their values.
- Use .env.example as a shape-only contract. Replace placeholders through a secret manager or an approved local mechanism before running services.
- Do not add production credentials, permissive defaults, cross-service database access, or frontend service-role credentials.

## Frontend rules

- Keep frontend/admin as a reserved empty directory until the user explicitly asks to initialize it.
- Do not initialize, reinitialize, or modify frontend/uikit as part of backend or deployment work.
- Do not run a Next.js, React, Vite, or other frontend initializer as part of backend or deployment work.

## Memory and verification

- Record material decisions, actions, and verification in today's Daily note; update Architecture and Open Tails when appropriate.
- Keep notes in the user's conversation language while preserving code identifiers and commands verbatim.
- Before reporting completion, inspect the diff and run checks that are available for the changed scope. Never claim a test, migration, build, or deployment gate passed unless it was actually run.
- Preserve unrelated user changes and avoid destructive commands.
