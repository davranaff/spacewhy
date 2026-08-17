UV ?= python3 -m uv
COMPOSE ?= docker compose -f ../deployment/docker/compose.yaml

.PHONY: install format lint typecheck test test-unit test-integration test-architecture test-smoke test-bots test-i18n test-coverage migrate migration migration-check sync-rbac run worker-booking provision-booking docker-up docker-down

install:
	$(UV) sync --all-groups

format:
	$(UV) run ruff format .

lint:
	$(UV) run ruff check .

typecheck:
	$(UV) run pyright

test:
	$(UV) run pytest

test-unit:
	$(UV) run pytest tests/unit

test-integration:
	$(UV) run pytest tests/integration

test-architecture:
	$(UV) run pytest tests/architecture

test-smoke:
	$(UV) run pytest tests/smoke

test-bots:
	$(UV) run pytest tests/unit/bots tests/smoke/test_bot_webhooks.py

test-i18n:
	$(UV) run pytest tests/unit/core/test_i18n.py tests/smoke/test_http_i18n.py

test-coverage:
	$(UV) run coverage run -m pytest
	$(UV) run coverage report

migrate:
	$(UV) run alembic upgrade head

migration:
	@test -n "$(MESSAGE)" || (echo "MESSAGE is required, for example: make migration MESSAGE='add table'"; exit 2)
	$(UV) run alembic revision --autogenerate -m "$(MESSAGE)"

migration-check:
	$(UV) run python scripts/check_migrations.py

sync-rbac:
	$(UV) run python scripts/sync_booking_rbac.py

run:
	$(UV) run uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-proxy-headers

worker-booking:
	$(UV) run python scripts/run_booking_worker.py

provision-booking:
	$(UV) run python scripts/provision_booking_tenant.py $(ARGS)

docker-up:
	$(COMPOSE) up --build

docker-down:
	$(COMPOSE) down
