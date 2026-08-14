---
type: architecture
tags: [project, architecture]
updated: 2026-08-15
---

# Architecture overview

## Current boundaries

- `backend/` is one deployable Django service boundary with an ASGI-only HTTP runtime.
- `deployment/` owns infrastructure composition and configuration templates; real secret values are outside version control.
- `frontend/admin/` remains a reserved empty frontend boundary.
- `frontend/uikit/` now contains the complete Spacewhy liquid-glass UI kit, implemented as a standalone Next.js/TypeScript application derived from the Minimals component demo.
- The UI kit uses an in-memory Axios demo adapter by default so catalog, blog, mail, chat, kanban and calendar surfaces do not depend on a remote demo backend. A real/remote demo API is explicit opt-in through `NEXT_PUBLIC_USE_REMOTE_DEMO_API=true`.
- `tools/obsidian-vault/` is the explicitly requested project-scoped filesystem memory vault. Obsidian is not required or started.
- `tools/skills/` contains the supplied RuFlo backend and project-memory instructions.

## Backend runtime

The initial service is Python 3.13 / Django 5.2 baseline, served through `config/asgi.py` by Uvicorn. New HTTP handlers are asynchronous. The only current endpoints are `health/live` and `health/ready`; the latter uses a narrow `sync_to_async` bridge for Django's database connection check. There is intentionally no `wsgi.py`.

When a bounded context is approved, add a broad domain app under `backend/apps/<domain>/` and use the RuFlo file-per-entity layout: `views/`, `serializers/`, `querysets/`, `services/`, and only the additional policy/event/consumer/client layers that are actually needed. Commands must own authorization, invariants, short transactions, audit, outbox, idempotency, and concurrency behavior; reads must begin from explicit tenant/resource scope.

## Runtime dependencies

The deployment composition reserves service-owned PostgreSQL 17, RabbitMQ 4.3, and Redis 8.8 boundaries. Authentication, storage, observability, migrations, backups, and production secret management remain explicit decisions rather than hidden defaults.

## Initial architecture decisions

1. No product domain or schema was invented before a feature contract and owner were supplied.
2. The shared UI kit boundary was initialized only after the user's explicit request; the admin frontend remains deferred.
3. The project memory vault is kept inside the repository because that location was explicitly requested; its secret notes must still never contain values in the repository.
4. Client navigation uses one delegated progress listener and lightweight route feedback; DOM-wide mutation observers are prohibited for link instrumentation.
5. App pages import their concrete view module instead of multi-view barrel indexes so unrelated editors, PDF renderers and detail screens do not enter the route graph.
6. Internal links disable viewport-wide automatic prefetch and warm only on explicit pointer or keyboard intent; this prevents the dense component catalog and dashboard sidebar from saturating the preview with concurrent route downloads.
7. Syntax highlighting uses `highlight.js/lib/core` with an explicit language set, while optional editors and calendar dialogs remain lazy boundaries.
