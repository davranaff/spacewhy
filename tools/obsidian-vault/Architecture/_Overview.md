---
type: architecture
tags: [project, architecture]
updated: 2026-08-20
---

# Architecture overview

## Текущее состояние

- `backend/` — один deployable FastAPI modular monolith на Python 3.13, ASGI/Uvicorn,
  Pydantic v2, async SQLAlchemy 2, PostgreSQL и Alembic. Актуальная архитектура
  определяется `backend/AGENTS.md` и `backend/docs/`, а не устаревшими Django-заметками.
- `backend/src/app/modules/booking/` — первый bounded context. Он владеет своей схемой,
  tenant-scoped RBAC, Telegram bot/WebApp auth, booking, cash/inventory и outbox worker.
- `backend/src/app/core/` — только общие технические primitives: configuration, database,
  bot platform, i18n, errors, observability. Бизнес-сущности туда не переносятся.
- `backend/src/app/modules/finance/` — новый владелец учёта доходов и расходов. Модуль
  добавляется по шаблону `domain -> application -> infrastructure -> presentation`.
- `backend/src/app/modules/identity/` — планируемый владелец общей идентичности Spacewhy,
  Telegram phone binding и сессий. Finance хранит только opaque `principal_id` и не
  импортирует ORM-модели Identity или Booking.
- `deployment/` — compose и shape-only environment templates. Реальные `.env`, bot token,
  signing keys и webhook secrets остаются вне Git.
- `frontend/` в этом репозитории — UI-kit/reference boundary, не customer panel.
- `tools/obsidian-vault/` — намеренно версионируемая проектная память без значений секретов.

## Продуктовые поверхности

- `https://spacewhy.uz/` — публичный landing и вход в экосистему.
- `Muxammad1106/spacewhy-panel` — центральная customer panel. Product code находится в
  `frontend/`, рядом лежит независимый `uikit/` reference package.
- `Muxammad1106/ui-kit-spacewhy` — GitHub Template Repository с полным Next.js/MUI
  Liquid Glass UI kit. Из него создаётся отдельный `spacewhy-finance` web application.
- `spacewhy-finance` — standalone responsive web app и Telegram Mini App. Он использует
  общую авторизацию, Finance API и открывается как из panel, так и из Telegram bot.

## Dependency and ownership rules

- FastAPI/Starlette существует только в presentation boundary.
- Domain не импортирует FastAPI, SQLAlchemy, settings или container.
- Application-use-cases владеют авторизацией, invariant checks и короткой транзакцией.
- Infrastructure реализует persistence/integration adapters; repository не делает commit.
- Другой модуль доступен только через `public.py` или versioned event contract.
- Money всегда `Decimal` + ISO 4217 currency. Никаких `float`.
- Финансовая история не удаляется: ошибка исправляется reversal/correction.
- Повторяемые commands требуют idempotency key и request fingerprint.
- State, audit и transactional outbox фиксируются атомарно.
- Telegram/API вызовы выполняются вне database transaction.
- Errors сохраняют общий RFC 9457 `application/problem+json` contract.

## Identity boundary

Telegram не позволяет боту первым найти пользователя только по номеру телефона. Поэтому
phone auth работает лишь после явной привязки:

1. Пользователь сам открывает Spacewhy auth bot.
2. Бот просит native Telegram contact button.
3. Backend принимает контакт только когда `contact.user_id == message.from.id`, нормализует
   телефон в E.164 и создаёт verified binding.
4. В обычной panel пользователь вводит телефон; backend отвечает одинаково для существующего
   и неизвестного номера и, если binding существует, ставит отправку OTP в outbox.
5. OTP короткоживущий, хранится только как keyed hash, имеет лимит попыток и rate limit.
6. Telegram Mini App использует подписанный `initData` и не просит OTP повторно.
7. После проверки Identity выдаёт короткую access-session и rotating refresh-session;
   frontend не хранит refresh token в `localStorage`.

## Runtime dependencies

PostgreSQL — durable state, audit, idempotency, inbox/outbox и ledger. Существующая bot
platform изолирует bot apps и credentials. Redis допускается для распределённых rate limits,
но authoritative challenge state остаётся в PostgreSQL. Отдельная очередь вводится только
после ADR; до этого outbox обрабатывается bounded worker-процессом по существующему паттерну.

## Architecture decisions

1. Актуальный backend остаётся FastAPI modular monolith; Django в проект не добавляется.
2. Общая panel-авторизация не принадлежит Finance или Booking: owner — `identity`.
3. Finance — отдельный bounded context с opaque external principal identifiers.
4. Первый release — personal finance workspace. Organization/shared workspace закладывается
   в модель membership, но shared access UI не входит в MVP.
5. Суммы и валюты не конвертируются неявно; transfer между разными валютами требует явных
   source amount, destination amount и rate metadata.
6. UI kit копируется как clean template с новой Git-историей; исходный `.git` не переносится.
7. В Git-памяти никогда не хранятся реальные bot tokens, OTP, signing keys или `.env`.
