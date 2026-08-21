# Spacewhy UI Kit Mobile

Bare React Native UI kit and native template catalog for Spacewhy. The package
uses React Native `0.84`, React `19`, Hermes and the New Architecture. Expo is
not installed.

The agent-facing documentation starts at [docs/README.md](docs/README.md). It
defines the architecture, public component contracts, glass rules, navigation,
catalog parity workflow and required quality gates.

## Run locally

Use Node.js `22.11` or newer.

```sh
npm install
npm start
```

Metro uses port `8082`. In a second terminal run one platform:

```sh
npm run ios
npm run android
```

For iOS, install pods after the first clone and whenever native dependencies
change:

```sh
cd ios
pod install
cd ..
```

## Required checks

```sh
npm run typecheck
npm run lint
npm test -- --runInBand
```

Do not import native glass, blur or audio packages directly from feature and
screen code. Use the boundaries documented in [docs/components.md](docs/components.md).
