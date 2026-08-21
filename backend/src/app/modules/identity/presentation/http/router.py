"""Versioned Identity HTTP endpoints."""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status

from app.bootstrap.container import get_container_from_app
from app.core.bots.errors import BotRuntimeError
from app.core.http.context import request_context_from_scope
from app.modules.identity.presentation.http.dependencies import require_identity_principal
from app.modules.identity.presentation.http.schemas import (
    CreateHandoffRequest,
    ExchangeHandoffRequest,
    HandoffResponse,
    PhoneChallengeRequest,
    PhoneChallengeResponse,
    PrincipalResponse,
    SessionResponse,
    TelegramWebAppRequest,
    VerifyChallengeRequest,
)
from app.modules.identity.public import IdentityPrincipal

logger = logging.getLogger("spacewhy")

router = APIRouter(prefix="/identity", tags=["identity"])


def _request_id(request: Request) -> str | None:
    context = request_context_from_scope(request.scope)
    return context.request_id if context is not None else None


@router.post(
    "/auth/telegram/challenges",
    response_model=PhoneChallengeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request an enumeration-safe Telegram phone challenge",
)
async def create_phone_challenge(
    payload: PhoneChallengeRequest,
    request: Request,
    response: Response,
) -> PhoneChallengeResponse:
    container = get_container_from_app(request.app)
    result = await container.identity.service.create_phone_challenge(
        bot_app_id=container.identity.settings.bot_app_id,
        phone=payload.phone,
        request_id=_request_id(request),
    )
    if result.delivery is not None:
        try:
            await container.bot_platform.send_message(
                app_id=container.identity_bot_app_id,
                recipient_id=result.delivery.telegram_chat_id,
                text=f"Код для входа в Space Drop: {result.delivery.code}",
            )
        except BotRuntimeError:
            logger.warning(
                "identity_otp_delivery_unavailable",
                extra={"request_id": _request_id(request), "result": "unavailable"},
            )
    response.headers["Cache-Control"] = "no-store"
    return PhoneChallengeResponse(
        challenge_id=result.id,
        expires_at=result.expires_at,
        telegram_start_parameter=result.start_parameter,
    )


@router.post(
    "/auth/telegram/challenges/{challenge_id}/verify",
    response_model=SessionResponse,
    summary="Verify one Telegram-delivered phone challenge",
)
async def verify_phone_challenge(
    challenge_id: UUID,
    payload: VerifyChallengeRequest,
    request: Request,
    response: Response,
) -> SessionResponse:
    container = get_container_from_app(request.app)
    session = await container.identity.service.verify_phone_challenge(
        challenge_id=challenge_id,
        code=payload.code,
        request_id=_request_id(request),
    )
    response.headers["Cache-Control"] = "no-store"
    return SessionResponse.from_session(session)


@router.post(
    "/auth/telegram/webapp",
    response_model=SessionResponse,
    summary="Exchange verified Telegram Mini App initData for a Spacewhy session",
)
async def authenticate_webapp(
    payload: TelegramWebAppRequest,
    request: Request,
    response: Response,
) -> SessionResponse:
    container = get_container_from_app(request.app)
    session = await container.identity.service.authenticate_webapp(
        bot_app_id=container.identity.settings.bot_app_id,
        init_data=payload.init_data,
    )
    response.headers["Cache-Control"] = "no-store"
    return SessionResponse.from_session(session)


@router.post(
    "/session-handoffs",
    response_model=HandoffResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a one-time authenticated handoff to an independent SpaceDrop",
)
async def create_session_handoff(
    payload: CreateHandoffRequest,
    request: Request,
    response: Response,
    principal: Annotated[IdentityPrincipal, Depends(require_identity_principal)],
) -> HandoffResponse:
    result = await get_container_from_app(request.app).identity.service.create_session_handoff(
        principal=principal,
        target=payload.target,
        request_id=_request_id(request),
    )
    response.headers["Cache-Control"] = "no-store"
    return HandoffResponse(handoff_token=result.token, expires_at=result.expires_at)


@router.post(
    "/session-handoffs/exchange",
    response_model=SessionResponse,
    summary="Consume a one-time SpaceDrop handoff",
)
async def exchange_session_handoff(
    payload: ExchangeHandoffRequest,
    request: Request,
    response: Response,
) -> SessionResponse:
    session = await get_container_from_app(request.app).identity.service.exchange_session_handoff(
        token=payload.handoff_token,
        target=payload.target,
        request_id=_request_id(request),
    )
    response.headers["Cache-Control"] = "no-store"
    return SessionResponse.from_session(session)


@router.get("/me", response_model=PrincipalResponse, summary="Get the active Spacewhy principal")
async def get_me(
    principal: Annotated[IdentityPrincipal, Depends(require_identity_principal)],
) -> PrincipalResponse:
    return PrincipalResponse.from_principal(principal)
