# Bot platform

## Scope

The backend remains one FastAPI modular monolith. Bot applications are isolated runtimes inside
that process, not network microservices and not internal HTTP clients.

Each enabled bot application has exactly one public bot_app_id, owner module, provider adapter,
client, webhook secret, handler, and scoped translation domain. The `booking` bounded context owns
the `booking_bot` registration when that app is declared in settings; tests also use fake adapters
and temporary catalogs for platform-level isolation coverage.

## Runtime shape

    verified Telegram webhook
      -> public bot_app_id
      -> one immutable BotRuntimeRegistry entry
      -> one provider-bound client
      -> one owner handler

The registry is constructed in bootstrap, freezes after startup, and is never injected into module
handlers. A module handler receives only a ScopedBotGateway and ScopedLocalizer pre-bound to its
own app. It cannot select another app, enumerate apps, access a token, access a webhook secret, or
import another module's bot implementation.

The first provider is Telegram through one aiogram adapter. SDK types remain inside
infrastructure/bots/telegram. No global Telegram Bot, dispatcher, router, or mutable current-bot
state exists. Every incoming update resolves from the already-verified route app ID and dispatches
once to the exact runtime.

## Identity and configuration

BotAppId uses lowercase ASCII letters, digits, and underscores, begins with a letter, and is
limited to 63 characters. It is public and suitable for a log field and webhook path; it is never
derived from a token or username.

Each bot uses nested settings:

    BOTS__APPS__SUPPORT_BOT__PROVIDER=telegram
    BOTS__APPS__SUPPORT_BOT__ENABLED=true
    BOTS__APPS__SUPPORT_BOT__TOKEN=<secret-manager-value>
    BOTS__APPS__SUPPORT_BOT__WEBHOOK_SECRET=<different-secret-manager-value>
    BOTS__APPS__SUPPORT_BOT__DEFAULT_LOCALE=ru
    BOTS__APPS__SUPPORT_BOT__SUPPORTED_LOCALES=["ru","uz","en"]

The tracked deployment/env/.env.example contains two disabled examples only. An enabled bot fails
startup when it lacks a token, lacks a webhook secret, uses an obvious placeholder, uses duplicate
credentials, has invalid timeouts, or has a default locale outside its supported locales. Validation
reports bot_app_id but never a secret value. Disabled apps may intentionally be predeclared without
secrets and without a module owner; they cannot receive traffic.

Optional startup identity validation uses the provider identity endpoint separately for each enabled
app. Set VALIDATE_IDENTITY_ON_STARTUP=true and, when desired, EXPECTED_BOT_ID and
EXPECTED_USERNAME. Provider network availability is never part of liveness or ordinary readiness.

## Module ownership registration

A future authorized module exposes a bootstrap function:

    def register_bot_apps(registrar):
        registrar.register(
            owner_module="support",
            app_id=BotAppId("support_bot"),
            translation_domain="support",
            module_root=Path(__file__).parent,
            handler_factory=build_support_handler,
        )

The handler factory runs only after configuration, catalog validation, and client construction
succeed. It receives BotHandlerDependencies with a pre-bound gateway and localizer. It must not
accept raw settings or a token. The current booking module is wired explicitly by the composition
root because it also needs typed WebApp-verifier construction; another module should add only its
own bootstrap to the module registry/composition root, never modify booking internals.

At startup bootstrap validates all ownership invariants:

- a registration maps to a configured app;
- every enabled configured app has exactly one registration;
- one app has one owner and one handler factory;
- registered catalog roots exist and pass validation;
- duplicate client registrations are rejected;
- failed partial initialization closes every client already created.

## Webhooks

Telegram uses the non-secret route:

    POST /webhooks/telegram/{bot_app_id}

The token is never in a path, query string, request header, OpenAPI schema, metric, or log. The
route is excluded from public OpenAPI. It validates JSON content type, content length, streamed body
size, route app ID, enabled runtime, and the official Telegram secret-token header. The secret
comparison is constant time and happens before parsing an update or invoking a handler.

Unknown app IDs, disabled apps, missing secrets, and invalid secrets use the same non-revealing
response. Malformed payloads, timeouts, and provider failures return safe status-only responses.
No update body or private message text is logged.

## Lifecycle, readiness, and observability

During lifespan startup the service validates settings, loads core and registered module catalogs,
validates registrations, creates one client per enabled app, builds one handler per runtime,
optionally validates provider identity, and freezes the registry. A startup failure closes all
partially created clients.

Shutdown closes every provider client once, clears the immutable runtime registry, and releases
catalog state. Readiness includes only local bot-platform initialization; liveness remains process
only and never calls Telegram.

Structured logs may contain request_id, bot_app_id, owner_module, provider, locale, safe update ID,
duration, and result. They must never contain token values, webhook secrets, authorization headers,
payloads, private text, phone numbers, emails, chat IDs, or raw provider errors. The shared
redactor recognizes bot_token, telegram_token, webhook_secret, and provider_token.

Optional OpenTelemetry instrumentation records bounded-cardinality bot update, outbound message,
translation fallback, missing-translation, and booking-outbox-lag metrics. Metrics never use user
ID, chat ID, update ID, message text, token, or unbounded translation keys as labels.

## Adding or rotating a bot app

1. Obtain product owner approval for bounded context, owner, public contract, authorization, and
   persistence scope.
2. Choose a stable BotAppId.
3. Add separate environment settings and separate secret-manager token and webhook secret.
4. Create the module handler factory and registration in its own bootstrap.py.
5. Add module common and bot-app catalog files for en, ru, and uz.
6. Add the bootstrap function to app/modules/registry.py.
7. Deploy configuration with the app disabled first, validate startup and catalog checks, then
   enable it.
8. Register the provider webhook operationally using the public route and its secret header.
9. Optionally enable identity validation and compare expected bot identity.
10. Run bot settings, isolation, webhook, catalog, architecture, and full test suites.
11. Inspect structured logs to confirm no token or secret is present.

Rotate a token by issuing a new credential through the secret manager, deploying it only for that
one app, optionally validating identity, then revoking the old credential. Rotate the webhook
secret independently: deploy the new secret, update the provider webhook, verify safe delivery, and
retire the old secret. Never put either value into source control or a ticket.
