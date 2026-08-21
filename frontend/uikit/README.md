# Spacewhy Web UI Kit

Next.js App Router, React, TypeScript and MUI web UI kit with Spacewhy Liquid
Glass, public pages, auth variants, dashboard templates and a complete component
catalog.

The agent-facing documentation starts at [docs/README.md](docs/README.md).
Cross-platform rules shared with the React Native kit are documented in
[../docs/README.md](../docs/README.md).

## Run locally

```sh
npm install
npm run dev
```

The development server uses `http://localhost:8081`.

## Required checks

```sh
npm test
npm run lint -- --no-cache
npx tsc --noEmit --incremental false
npm run build
```

Do not remove routes or component variants during visual refactors. The web kit
is the source of truth for shared component anatomy and parity inventory.
