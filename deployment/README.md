# Deployment boundary

All runtime configuration belongs under this directory. The repository contains only safe templates and infrastructure definitions; real environment files, private keys, certificates, and tokens stay outside version control.

## Layout

```text
deployment/
  configs/       reverse proxy, observability, and platform configuration
  docker/        local/container composition
  env/           shape-only environment templates and ignored local values
  keys/          ignored private keys/certificates; README and placeholder remain tracked
  scripts/       deployment and operational command documentation/scripts
```

Copy `env/.env.example` to `env/.env` and replace every placeholder through the approved secret-management path before starting local containers. Do not paste real values into `.env.example`, commits, logs, or task output.

The compose file runs only the FastAPI service and its service-owned PostgreSQL dependency for
local development and integration tests. It does not authorize a deployment, expose secrets, or
replace production identity, TLS, backups, migrations, monitoring, and rollback runbooks.

The template also declares a disabled `booking_bot` and non-secret `BOOKING_*` tuning values.
Provision a tenant only after the database migration has run, and enable that bot only after its
token and distinct webhook secret have been supplied from the approved secret path. The booking
outbox worker is a separate process (`make worker-booking` from `backend`).
