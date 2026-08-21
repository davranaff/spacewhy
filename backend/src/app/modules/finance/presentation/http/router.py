"""Thin Finance HTTP routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, status

from app.bootstrap.container import get_container_from_app
from app.core.http.context import request_context_from_scope
from app.modules.finance.domain.errors import FinanceDomainError, FinanceErrorCode
from app.modules.finance.presentation.http.dependencies import require_finance_principal
from app.modules.finance.presentation.http.schemas import (
    AccountResponse,
    BootstrapRequest,
    CategoryResponse,
    CreateAccountRequest,
    CreateEntryRequest,
    CreateTransferRequest,
    CurrencySummaryResponse,
    EntryPageResponse,
    EntryResponse,
    SummaryResponse,
    TransferResponse,
    WorkspaceResponse,
)
from app.modules.identity.public import IdentityPrincipal

router = APIRouter(prefix="/finance", tags=["finance"])


def _request_id(request: Request) -> str | None:
    context = request_context_from_scope(request.scope)
    return context.request_id if context is not None else None


def require_idempotency_key(
    value: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> str:
    if value is None or not value.strip() or len(value) > 128:
        raise FinanceDomainError(FinanceErrorCode.INVALID_REQUEST)
    return value.strip()


@router.post(
    "/bootstrap",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or return the principal's personal Finance workspace",
)
async def bootstrap_workspace(
    payload: BootstrapRequest,
    request: Request,
    principal: Annotated[IdentityPrincipal, Depends(require_finance_principal)],
) -> WorkspaceResponse:
    result = await get_container_from_app(request.app).finance.service.bootstrap_workspace(
        principal_id=principal.id,
        workspace_name=payload.workspace_name,
        default_currency=payload.default_currency,
        account_name=payload.account_name,
        initial_balance=payload.initial_balance,
        request_id=_request_id(request),
    )
    return WorkspaceResponse.from_result(result)


@router.get("/accounts", response_model=list[AccountResponse], summary="List scoped accounts")
async def list_accounts(
    request: Request,
    principal: Annotated[IdentityPrincipal, Depends(require_finance_principal)],
) -> list[AccountResponse]:
    results = await get_container_from_app(request.app).finance.service.list_accounts(
        principal_id=principal.id
    )
    return [AccountResponse.from_result(result) for result in results]


@router.post(
    "/accounts",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a scoped Finance account",
)
async def create_account(
    payload: CreateAccountRequest,
    request: Request,
    principal: Annotated[IdentityPrincipal, Depends(require_finance_principal)],
) -> AccountResponse:
    result = await get_container_from_app(request.app).finance.service.create_account(
        principal_id=principal.id,
        name=payload.name,
        currency=payload.currency,
        color=payload.color,
        request_id=_request_id(request),
    )
    return AccountResponse.from_result(result)


@router.get("/categories", response_model=list[CategoryResponse], summary="List scoped categories")
async def list_categories(
    request: Request,
    principal: Annotated[IdentityPrincipal, Depends(require_finance_principal)],
) -> list[CategoryResponse]:
    results = await get_container_from_app(request.app).finance.service.list_categories(
        principal_id=principal.id
    )
    return [CategoryResponse.from_result(result) for result in results]


@router.post(
    "/transactions",
    response_model=EntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Append an idempotent income or expense ledger entry",
)
async def create_transaction(
    payload: CreateEntryRequest,
    request: Request,
    principal: Annotated[IdentityPrincipal, Depends(require_finance_principal)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> EntryResponse:
    result = await get_container_from_app(request.app).finance.service.create_entry(
        principal_id=principal.id,
        account_id=payload.account_id,
        category_id=payload.category_id,
        direction=payload.direction,
        amount=payload.amount,
        currency=payload.currency,
        occurred_at=payload.occurred_at,
        note=payload.note,
        idempotency_key=idempotency_key,
        request_id=_request_id(request),
    )
    return EntryResponse.from_result(result)


@router.post(
    "/transactions/{entry_id}/reversal",
    response_model=EntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Append an idempotent reversal for a standard ledger entry",
)
async def reverse_transaction(
    entry_id: UUID,
    request: Request,
    principal: Annotated[IdentityPrincipal, Depends(require_finance_principal)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> EntryResponse:
    result = await get_container_from_app(request.app).finance.service.reverse_entry(
        principal_id=principal.id,
        entry_id=entry_id,
        idempotency_key=idempotency_key,
        request_id=_request_id(request),
    )
    return EntryResponse.from_result(result)


@router.post(
    "/transfers",
    response_model=TransferResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Append an idempotent transfer between two scoped accounts",
)
async def create_transfer(
    payload: CreateTransferRequest,
    request: Request,
    principal: Annotated[IdentityPrincipal, Depends(require_finance_principal)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> TransferResponse:
    result = await get_container_from_app(request.app).finance.service.create_transfer(
        principal_id=principal.id,
        source_account_id=payload.source_account_id,
        destination_account_id=payload.destination_account_id,
        amount=payload.amount,
        currency=payload.currency,
        occurred_at=payload.occurred_at,
        note=payload.note,
        idempotency_key=idempotency_key,
        request_id=_request_id(request),
    )
    return TransferResponse.from_result(result)


@router.get(
    "/transactions",
    response_model=EntryPageResponse,
    summary="List scoped ledger entries with a stable cursor",
)
async def list_transactions(
    request: Request,
    principal: Annotated[IdentityPrincipal, Depends(require_finance_principal)],
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
) -> EntryPageResponse:
    result = await get_container_from_app(request.app).finance.service.list_entries(
        principal_id=principal.id,
        limit=limit,
        cursor=cursor,
    )
    return EntryPageResponse.from_result(result)


@router.get(
    "/dashboard/summary",
    response_model=SummaryResponse,
    summary="Return balances and income/expense totals grouped by currency",
)
async def get_summary(
    request: Request,
    principal: Annotated[IdentityPrincipal, Depends(require_finance_principal)],
) -> SummaryResponse:
    results = await get_container_from_app(request.app).finance.service.summary(
        principal_id=principal.id
    )
    return SummaryResponse(
        currencies=[CurrencySummaryResponse.from_result(result) for result in results]
    )
