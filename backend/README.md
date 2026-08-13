# Spacewhy backend

This directory is the initial Django service boundary. It is deliberately a small ASGI-first skeleton: the product bounded context and first domain app have not been specified yet.

## Runtime contract

- Python 3.13 and Django 5.2 LTS baseline.
- ASGI is the only HTTP deployment path (`config/asgi.py`); there is no `wsgi.py`.
- Container/runtime settings default to `config.settings.production`; local management commands use `config.settings.local` and tests use isolated test settings.
- New HTTP handlers are asynchronous. Use Django's async ORM methods where available and isolate unavoidable synchronous integrations behind an explicit `sync_to_async` bridge.
- Uvicorn is the local/container server. Celery, RabbitMQ, Redis, PostgreSQL, authentication, storage, and observability are integration boundaries rather than hidden application globals.
- `health/live` is process liveness. `health/ready` checks the service-owned database and returns `503` when it is unavailable.

## Intended domain layout

When the first bounded context is approved, add a broad domain app under `apps/<domain>/` and keep the RuFlo file-per-entity navigation:

```text
apps/<domain>/
  models.py
  views/<entity>.py
  serializers/<entity>.py
  querysets/<entity>.py
  services/<use_case>.py
  policies/<entity>.py       # only when needed
  events/<aggregate>.py      # only when needed
  consumers/<event>.py       # only when needed
  clients/<provider>.py      # only when needed
  tests/
```

Do not create empty architecture layers or a new app per endpoint/table/screen. Read `tools/skills/ruflo-django-backend/references/service-blueprint.md` before adding the first domain.

## Local commands

```bash
python -m pip install -e '.[dev]'
python manage.py check
pytest
ruff check .
ruff format --check .
```

Generate and review a lock file before a deployable image is promoted; this scaffold intentionally does not contain credentials or a generated lock.
