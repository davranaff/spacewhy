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

The compose file is a local infrastructure contract only. It does not authorize a deployment, expose secrets, or replace production identity, TLS, backups, migrations, monitoring, and rollback runbooks.
