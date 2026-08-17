"""Thin FastAPI adapters for tenant-scoped booking client and staff use cases."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.modules.booking.application.auth import BookingAuthResult
from app.modules.booking.application.context import BookingActor
from app.modules.booking.application.dto import (
    AnalyticsQuery,
    AvailabilityQuery,
    CancelAppointmentCommand,
    CashShiftCommand,
    CashTransactionCommand,
    ConfirmAppointmentCommand,
    HoldCommand,
    PaymentCommand,
    PriceOverrideCommand,
    RefundCommand,
    RescheduleCommitCommand,
    StatusTransitionCommand,
    StockMovementCommand,
    StockMovementLine,
)
from app.modules.booking.bootstrap import BookingModuleRuntime
from app.modules.booking.domain.enums import AppointmentSource, AppointmentStatus
from app.modules.booking.presentation.http.dependencies import (
    get_backoffice_actor,
    get_booking_runtime,
    get_client_actor,
    get_staff_actor,
    require_idempotency_key,
)
from app.modules.booking.presentation.http.schemas import (
    AdminArchiveRequest,
    AdminHoldRequest,
    AdminResourceListResponse,
    AdminResourcePayload,
    AdminResourceResponse,
    AnalyticsResponse,
    AppointmentListResponse,
    AppointmentResponse,
    AvailabilityResponse,
    BranchResponse,
    CancelAppointmentRequest,
    CashShiftRequest,
    CashShiftResponse,
    CashTransactionRequest,
    CategoryResponse,
    ClientBootstrapResponse,
    CreateAppointmentRequest,
    HoldRequest,
    HoldResponse,
    PaymentRequest,
    PaymentResponse,
    PriceOverrideRequest,
    RefundRequest,
    RescheduleCommitRequest,
    ServiceResponse,
    SessionActorResponse,
    SessionResponse,
    SpecialistResponse,
    StaffBindCodeRequest,
    StaffBindCodeResponse,
    StatusTransitionRequest,
    StockMovementRequest,
    StockMovementResponse,
    TelegramAuthRequest,
)

router = APIRouter(prefix="/booking", tags=["booking"])
auth_router = APIRouter(prefix="/auth", tags=["booking-auth"])
client_router = APIRouter(prefix="/client", tags=["booking-client"])
staff_router = APIRouter(prefix="/staff/me", tags=["booking-staff"])
admin_router = APIRouter(prefix="/admin", tags=["booking-admin"])

AdminResourceName = Literal[
    "branches",
    "categories",
    "services",
    "specialists",
    "specialist-services",
    "schedules",
    "availability-exceptions",
    "customers",
    "cashboxes",
    "products",
    "warehouses",
    "service-materials",
]


def _rate_limit_key(request: Request, bot_app_id: str) -> str:
    """Use the socket peer address only as a coarse, non-authoritative auth limit key."""

    client_host = request.client.host if request.client is not None else "unknown"
    return f"{bot_app_id}:{client_host}"


def _session_response(result: BookingAuthResult) -> SessionResponse:
    """Build the documented session response without exposing auth-service internals."""

    return SessionResponse(
        access_token=result.access_token,
        expires_at=result.expires_at,
        actor=SessionActorResponse.from_actor(result.actor),
    )


@auth_router.post(
    "/telegram/client",
    response_model=SessionResponse,
    summary="Authenticate a booking client from signed Telegram WebApp initData",
)
async def authenticate_client(
    payload: TelegramAuthRequest,
    request: Request,
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
) -> SessionResponse:
    """Validate official Telegram data and issue only a server-scoped client session."""

    result = await runtime.auth.authenticate_client(
        bot_app_id=payload.bot_app_id,
        init_data=payload.init_data,
        rate_limit_key=_rate_limit_key(request, payload.bot_app_id),
    )
    return _session_response(result)


@auth_router.post(
    "/telegram/staff",
    response_model=SessionResponse,
    summary="Authenticate bound booking staff from signed Telegram WebApp initData",
)
async def authenticate_staff(
    payload: TelegramAuthRequest,
    request: Request,
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
) -> SessionResponse:
    """Issue a staff session only after the server finds an active binding and grant."""

    result = await runtime.auth.authenticate_staff(
        bot_app_id=payload.bot_app_id,
        init_data=payload.init_data,
        rate_limit_key=_rate_limit_key(request, payload.bot_app_id),
    )
    return _session_response(result)


@client_router.get(
    "/bootstrap",
    response_model=ClientBootstrapResponse,
    summary="Get client profile and booking display configuration",
)
async def client_bootstrap(
    actor: Annotated[BookingActor, Depends(get_client_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
) -> ClientBootstrapResponse:
    """Provide one signed customer's initial client payload."""

    return ClientBootstrapResponse.model_validate(
        await runtime.service.client_bootstrap(actor=actor)
    )


@client_router.get(
    "/branches",
    response_model=list[BranchResponse],
    summary="List active booking branches",
)
async def list_client_branches(
    actor: Annotated[BookingActor, Depends(get_client_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
) -> list[BranchResponse]:
    """Return active branches in deterministic display order."""

    return [
        BranchResponse.model_validate(item)
        for item in await runtime.service.list_branches(actor=actor)
    ]


@client_router.get(
    "/categories",
    response_model=list[CategoryResponse],
    summary="List active service categories",
)
async def list_client_categories(
    actor: Annotated[BookingActor, Depends(get_client_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
) -> list[CategoryResponse]:
    """Return categories needed by a service-first client flow."""

    return [
        CategoryResponse.model_validate(item)
        for item in await runtime.service.list_categories(actor=actor)
    ]


@client_router.get(
    "/services",
    response_model=list[ServiceResponse],
    summary="List client-bookable services",
)
async def list_client_services(
    actor: Annotated[BookingActor, Depends(get_client_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
    branch_id: UUID | None = None,
    category_id: UUID | None = None,
    specialist_id: UUID | None = None,
) -> list[ServiceResponse]:
    """Filter services through tenant-owned service and assignment eligibility."""

    return [
        ServiceResponse.model_validate(item)
        for item in await runtime.service.list_services(
            actor=actor,
            branch_id=branch_id,
            category_id=category_id,
            specialist_id=specialist_id,
        )
    ]


@client_router.get(
    "/specialists",
    response_model=list[SpecialistResponse],
    summary="List bookable specialists",
)
async def list_client_specialists(
    actor: Annotated[BookingActor, Depends(get_client_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
    branch_id: UUID | None = None,
    service_id: UUID | None = None,
) -> list[SpecialistResponse]:
    """Return active specialists eligible for optional branch/service filters."""

    return [
        SpecialistResponse.model_validate(item)
        for item in await runtime.service.list_specialists(
            actor=actor,
            branch_id=branch_id,
            service_id=service_id,
        )
    ]


@client_router.get(
    "/availability",
    response_model=list[AvailabilityResponse],
    summary="Calculate currently available booking slots",
)
async def client_availability(
    actor: Annotated[BookingActor, Depends(get_client_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
    branch_id: UUID,
    service_id: UUID,
    date_from: date,
    date_to: date,
    specialist_id: UUID | None = None,
) -> list[AvailabilityResponse]:
    """Calculate choices from live schedules, exceptions, reservations, and policy."""

    slots = await runtime.service.availability(
        actor=actor,
        query=AvailabilityQuery(
            branch_id=branch_id,
            service_id=service_id,
            specialist_id=specialist_id,
            customer_id=actor.customer_id,
            date_from=date_from,
            date_to=date_to,
        ),
    )
    return [AvailabilityResponse.from_result(slot) for slot in slots]


@client_router.post(
    "/holds",
    response_model=HoldResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a short-lived exclusive slot hold",
)
async def create_client_hold(
    payload: HoldRequest,
    actor: Annotated[BookingActor, Depends(get_client_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> HoldResponse:
    """Reserve the selected time under a durable tenant-scoped idempotency key."""

    hold = await runtime.service.create_hold(
        actor=actor,
        command=HoldCommand(
            branch_id=payload.branch_id,
            service_id=payload.service_id,
            specialist_id=payload.specialist_id,
            starts_at=payload.starts_at,
            idempotency_key=idempotency_key,
        ),
    )
    return HoldResponse.from_result(hold)


@client_router.post(
    "/appointments",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Confirm an owned active hold into an appointment",
)
async def create_client_appointment(
    payload: CreateAppointmentRequest,
    actor: Annotated[BookingActor, Depends(get_client_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> AppointmentResponse:
    """Promote only the authenticated customer's live hold into an appointment."""

    appointment = await runtime.service.confirm_appointment(
        actor=actor,
        command=ConfirmAppointmentCommand(
            hold_id=payload.hold_id,
            customer_note=payload.customer_note,
            idempotency_key=idempotency_key,
            source=AppointmentSource.CLIENT_API,
        ),
    )
    return AppointmentResponse.from_result(appointment, actor=actor)


@client_router.get(
    "/appointments",
    response_model=AppointmentListResponse,
    summary="List only the authenticated customer's appointments",
)
async def list_client_appointments(
    actor: Annotated[BookingActor, Depends(get_client_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
    upcoming: bool | None = None,
    history: bool | None = None,
    status_filter: Annotated[AppointmentStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AppointmentListResponse:
    """Return a bounded customer-only timeline with an explicit continuation cursor."""

    items = await runtime.service.list_appointments(
        actor=actor,
        upcoming=upcoming,
        history=history,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    rendered = [AppointmentResponse.from_result(item, actor=actor) for item in items]
    return AppointmentListResponse(
        items=rendered,
        limit=limit,
        offset=offset,
        next_offset=offset + len(rendered) if len(rendered) == limit else None,
    )


@client_router.get(
    "/appointments/{appointment_id}",
    response_model=AppointmentResponse,
    summary="Get one owned appointment",
)
async def get_client_appointment(
    appointment_id: UUID,
    actor: Annotated[BookingActor, Depends(get_client_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
) -> AppointmentResponse:
    """Use server-side customer scope so UUID guessing cannot cause an IDOR leak."""

    return AppointmentResponse.from_result(
        await runtime.service.get_appointment(actor=actor, appointment_id=appointment_id),
        actor=actor,
    )


@client_router.post(
    "/appointments/{appointment_id}/cancel",
    response_model=AppointmentResponse,
    summary="Cancel an owned appointment within its tenant policy cutoff",
)
async def cancel_client_appointment(
    appointment_id: UUID,
    payload: CancelAppointmentRequest,
    actor: Annotated[BookingActor, Depends(get_client_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> AppointmentResponse:
    """Release the reservation and schedule durable notifications after the transaction commits."""

    appointment = await runtime.service.cancel_appointment(
        actor=actor,
        command=CancelAppointmentCommand(
            appointment_id=appointment_id,
            reason=payload.reason,
            idempotency_key=idempotency_key,
        ),
    )
    return AppointmentResponse.from_result(appointment, actor=actor)


@client_router.post(
    "/appointments/{appointment_id}/reschedule/holds",
    response_model=HoldResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a replacement hold while preserving the current appointment",
)
async def create_client_reschedule_hold(
    appointment_id: UUID,
    payload: HoldRequest,
    actor: Annotated[BookingActor, Depends(get_client_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> HoldResponse:
    """Create the prospective reservation without modifying the old appointment yet."""

    hold = await runtime.service.create_reschedule_hold(
        actor=actor,
        appointment_id=appointment_id,
        command=HoldCommand(
            branch_id=payload.branch_id,
            service_id=payload.service_id,
            specialist_id=payload.specialist_id,
            starts_at=payload.starts_at,
            idempotency_key=idempotency_key,
        ),
    )
    return HoldResponse.from_result(hold)


@client_router.post(
    "/appointments/{appointment_id}/reschedule/commit",
    response_model=AppointmentResponse,
    summary="Atomically replace an owned appointment's reservation with a live hold",
)
async def commit_client_reschedule(
    appointment_id: UUID,
    payload: RescheduleCommitRequest,
    actor: Annotated[BookingActor, Depends(get_client_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> AppointmentResponse:
    """Keep the original appointment intact if replacement hold validation fails."""

    appointment = await runtime.service.commit_reschedule(
        actor=actor,
        command=RescheduleCommitCommand(
            appointment_id=appointment_id,
            hold_id=payload.hold_id,
            idempotency_key=idempotency_key,
        ),
    )
    return AppointmentResponse.from_result(appointment, actor=actor)


@staff_router.get(
    "/agenda",
    response_model=list[AppointmentResponse],
    summary="Get the bound specialist's local-day agenda",
)
async def staff_agenda(
    actor: Annotated[BookingActor, Depends(get_staff_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
    local_day: Annotated[date, Query(alias="date")],
    branch_id: UUID | None = None,
) -> list[AppointmentResponse]:
    """Restrict staff to their specialist identifier unless an explicit broad grant exists."""

    appointments = await runtime.service.staff_agenda(
        actor=actor,
        local_day=local_day,
        branch_id=branch_id,
    )
    return [AppointmentResponse.from_result(item, actor=actor) for item in appointments]


@staff_router.get(
    "/appointments/{appointment_id}",
    response_model=AppointmentResponse,
    summary="Get one permitted staff appointment",
)
async def get_staff_appointment(
    appointment_id: UUID,
    actor: Annotated[BookingActor, Depends(get_staff_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
) -> AppointmentResponse:
    """Fetch a staff-scoped appointment with the same IDOR defenses as the client API."""

    return AppointmentResponse.from_result(
        await runtime.service.get_appointment(actor=actor, appointment_id=appointment_id),
        actor=actor,
    )


async def _staff_transition(
    *,
    actor: BookingActor,
    runtime: BookingModuleRuntime,
    appointment_id: UUID,
    target_status: AppointmentStatus,
    idempotency_key: str,
) -> AppointmentResponse:
    """Run one server-selected lifecycle transition for the staff API endpoints."""

    appointment = await runtime.service.transition_appointment(
        actor=actor,
        command=StatusTransitionCommand(
            appointment_id=appointment_id,
            target_status=target_status,
            idempotency_key=idempotency_key,
        ),
    )
    return AppointmentResponse.from_result(appointment, actor=actor)


@staff_router.post(
    "/appointments/{appointment_id}/confirm",
    response_model=AppointmentResponse,
    summary="Confirm a permitted pending appointment",
)
async def confirm_staff_appointment(
    appointment_id: UUID,
    actor: Annotated[BookingActor, Depends(get_staff_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> AppointmentResponse:
    """Confirm only the target selected by the URL, never a client-provided status."""

    return await _staff_transition(
        actor=actor,
        runtime=runtime,
        appointment_id=appointment_id,
        target_status=AppointmentStatus.CONFIRMED,
        idempotency_key=idempotency_key,
    )


@staff_router.post(
    "/appointments/{appointment_id}/check-in",
    response_model=AppointmentResponse,
    summary="Mark a permitted appointment as checked in",
)
async def check_in_staff_appointment(
    appointment_id: UUID,
    actor: Annotated[BookingActor, Depends(get_staff_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> AppointmentResponse:
    """Apply the checked-in transition under the appointment row lock."""

    return await _staff_transition(
        actor=actor,
        runtime=runtime,
        appointment_id=appointment_id,
        target_status=AppointmentStatus.CHECKED_IN,
        idempotency_key=idempotency_key,
    )


@staff_router.post(
    "/appointments/{appointment_id}/complete",
    response_model=AppointmentResponse,
    summary="Complete an appointment and atomically consume its material snapshot",
)
async def complete_staff_appointment(
    appointment_id: UUID,
    actor: Annotated[BookingActor, Depends(get_staff_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> AppointmentResponse:
    """Complete the booking only after inventory constraints succeed in the same transaction."""

    return await _staff_transition(
        actor=actor,
        runtime=runtime,
        appointment_id=appointment_id,
        target_status=AppointmentStatus.COMPLETED,
        idempotency_key=idempotency_key,
    )


@staff_router.post(
    "/appointments/{appointment_id}/no-show",
    response_model=AppointmentResponse,
    summary="Mark a permitted appointment as a no-show",
)
async def no_show_staff_appointment(
    appointment_id: UUID,
    actor: Annotated[BookingActor, Depends(get_staff_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> AppointmentResponse:
    """Release the slot and cancel future reminders after marking no-show."""

    return await _staff_transition(
        actor=actor,
        runtime=runtime,
        appointment_id=appointment_id,
        target_status=AppointmentStatus.NO_SHOW,
        idempotency_key=idempotency_key,
    )


@staff_router.post(
    "/appointments/{appointment_id}/cancel",
    response_model=AppointmentResponse,
    summary="Cancel a permitted appointment with a staff reason when required",
)
async def cancel_staff_appointment(
    appointment_id: UUID,
    payload: CancelAppointmentRequest,
    actor: Annotated[BookingActor, Depends(get_staff_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> AppointmentResponse:
    """Apply the same cutoff/override policy as other booking cancellation channels."""

    appointment = await runtime.service.cancel_appointment(
        actor=actor,
        command=CancelAppointmentCommand(
            appointment_id=appointment_id,
            reason=payload.reason,
            idempotency_key=idempotency_key,
        ),
    )
    return AppointmentResponse.from_result(appointment, actor=actor)


@admin_router.get(
    "/settings",
    response_model=AdminResourceResponse,
    summary="Get tenant-owned booking policy settings",
)
async def get_admin_settings(
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
) -> AdminResourceResponse:
    """Return settings only after the settings-specific permission check in the use case."""

    return AdminResourceResponse(data=await runtime.management.get_settings(actor=actor))


@admin_router.patch(
    "/settings",
    response_model=AdminResourceResponse,
    summary="Update tenant-owned booking policy settings",
)
async def update_admin_settings(
    payload: AdminResourcePayload,
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
) -> AdminResourceResponse:
    """Persist policy changes through a strict settings whitelist and audit event."""

    return AdminResourceResponse(
        data=await runtime.management.update_settings(actor=actor, values=payload.values)
    )


@admin_router.post(
    "/staff-bind-codes",
    response_model=StaffBindCodeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a one-time staff Telegram bind code",
)
async def generate_staff_bind_code(
    payload: StaffBindCodeRequest,
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
) -> StaffBindCodeResponse:
    """Return a raw code once while the database keeps only its one-time hash."""

    return StaffBindCodeResponse.model_validate(
        await runtime.management.generate_staff_bind_code(
            actor=actor,
            specialist_id=payload.specialist_id,
            ttl_seconds=payload.ttl_seconds,
        )
    )


@admin_router.post(
    "/appointments/holds",
    response_model=HoldResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an appointment hold on behalf of an existing tenant customer",
)
async def create_admin_hold(
    payload: AdminHoldRequest,
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> HoldResponse:
    """Keep customer, price, duration, and tenant authority server-derived for admin bookings."""

    hold = await runtime.service.create_hold(
        actor=actor,
        command=HoldCommand(
            branch_id=payload.branch_id,
            service_id=payload.service_id,
            specialist_id=payload.specialist_id,
            starts_at=payload.starts_at,
            customer_id=payload.customer_id,
            idempotency_key=idempotency_key,
        ),
    )
    return HoldResponse.from_result(hold)


@admin_router.post(
    "/appointments",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Confirm an admin-created hold into an appointment",
)
async def create_admin_appointment(
    payload: CreateAppointmentRequest,
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> AppointmentResponse:
    """Confirm a scoped live hold using the same transactional invariants as client flow."""

    appointment = await runtime.service.confirm_appointment(
        actor=actor,
        command=ConfirmAppointmentCommand(
            hold_id=payload.hold_id,
            customer_note=payload.customer_note,
            idempotency_key=idempotency_key,
            source=AppointmentSource.ADMIN,
        ),
    )
    return AppointmentResponse.from_result(appointment, actor=actor)


@admin_router.get(
    "/appointments",
    response_model=AppointmentListResponse,
    summary="List tenant appointments with back-office filters",
)
async def list_admin_appointments(
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
    branch_id: UUID | None = None,
    specialist_id: UUID | None = None,
    customer_id: UUID | None = None,
    status_filter: Annotated[AppointmentStatus | None, Query(alias="status")] = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AppointmentListResponse:
    """Use tenant-scoped, bounded filtering for a staff/admin agenda or search screen."""

    items = await runtime.service.list_appointments(
        actor=actor,
        branch_id=branch_id,
        specialist_id=specialist_id,
        customer_id=customer_id,
        status=status_filter,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    rendered = [AppointmentResponse.from_result(item, actor=actor) for item in items]
    return AppointmentListResponse(
        items=rendered,
        limit=limit,
        offset=offset,
        next_offset=offset + len(rendered) if len(rendered) == limit else None,
    )


@admin_router.get(
    "/appointments/{appointment_id}",
    response_model=AppointmentResponse,
    summary="Get one tenant appointment for an authorized back-office actor",
)
async def get_admin_appointment(
    appointment_id: UUID,
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
) -> AppointmentResponse:
    """Return one appointment using server-derived broad staff scope where granted."""

    return AppointmentResponse.from_result(
        await runtime.service.get_appointment(actor=actor, appointment_id=appointment_id),
        actor=actor,
    )


@admin_router.post(
    "/appointments/{appointment_id}/status",
    response_model=AppointmentResponse,
    summary="Apply a permitted admin appointment status transition",
)
async def transition_admin_appointment(
    appointment_id: UUID,
    payload: StatusTransitionRequest,
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> AppointmentResponse:
    """Let the application state machine and exact permission determine transition validity."""

    appointment = await runtime.service.transition_appointment(
        actor=actor,
        command=StatusTransitionCommand(
            appointment_id=appointment_id,
            target_status=payload.target_status,
            reason=payload.reason,
            idempotency_key=idempotency_key,
        ),
    )
    return AppointmentResponse.from_result(appointment, actor=actor)


@admin_router.post(
    "/appointments/{appointment_id}/price-override",
    response_model=AppointmentResponse,
    summary="Manually override an appointment snapshot price with an audit reason",
)
async def override_admin_appointment_price(
    appointment_id: UUID,
    payload: PriceOverrideRequest,
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> AppointmentResponse:
    """Preserve immutable payment records while recording the old/new price in history and audit."""

    appointment = await runtime.service.override_appointment_price(
        actor=actor,
        command=PriceOverrideCommand(
            appointment_id=appointment_id,
            price=payload.price,
            reason=payload.reason,
            idempotency_key=idempotency_key,
        ),
    )
    return AppointmentResponse.from_result(appointment, actor=actor)


@admin_router.post(
    "/appointments/{appointment_id}/cancel",
    response_model=AppointmentResponse,
    summary="Cancel a tenant appointment with the staff override policy",
)
async def cancel_admin_appointment(
    appointment_id: UUID,
    payload: CancelAppointmentRequest,
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> AppointmentResponse:
    """Evaluate cancellation reason and cutoff rules in the same transactional use case."""

    appointment = await runtime.service.cancel_appointment(
        actor=actor,
        command=CancelAppointmentCommand(
            appointment_id=appointment_id,
            reason=payload.reason,
            idempotency_key=idempotency_key,
        ),
    )
    return AppointmentResponse.from_result(appointment, actor=actor)


@admin_router.post(
    "/appointments/{appointment_id}/reschedule/holds",
    response_model=HoldResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a replacement hold for a tenant appointment",
)
async def create_admin_reschedule_hold(
    appointment_id: UUID,
    payload: HoldRequest,
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> HoldResponse:
    """Hold the replacement first so a failing reschedule cannot lose the old booking."""

    hold = await runtime.service.create_reschedule_hold(
        actor=actor,
        appointment_id=appointment_id,
        command=HoldCommand(
            branch_id=payload.branch_id,
            service_id=payload.service_id,
            specialist_id=payload.specialist_id,
            starts_at=payload.starts_at,
            idempotency_key=idempotency_key,
        ),
    )
    return HoldResponse.from_result(hold)


@admin_router.post(
    "/appointments/{appointment_id}/reschedule/commit",
    response_model=AppointmentResponse,
    summary="Atomically commit an admin replacement hold",
)
async def commit_admin_reschedule(
    appointment_id: UUID,
    payload: RescheduleCommitRequest,
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> AppointmentResponse:
    """Commit the two-reservation swap under locks and keep history/audit evidence."""

    appointment = await runtime.service.commit_reschedule(
        actor=actor,
        command=RescheduleCommitCommand(
            appointment_id=appointment_id,
            hold_id=payload.hold_id,
            idempotency_key=idempotency_key,
        ),
    )
    return AppointmentResponse.from_result(appointment, actor=actor)


@admin_router.post(
    "/cash/shifts/open",
    response_model=CashShiftResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Open a cashbox shift",
)
async def open_admin_cash_shift(
    payload: CashShiftRequest,
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> CashShiftResponse:
    """Create the opening ledger transaction under a unique open-shift invariant."""

    result = await runtime.service.open_cash_shift(
        actor=actor,
        command=CashShiftCommand(
            cashbox_id=payload.cashbox_id,
            amount=payload.amount,
            notes=payload.notes,
            idempotency_key=idempotency_key,
        ),
    )
    return CashShiftResponse.from_result(result)


@admin_router.post(
    "/cash/shifts/close",
    response_model=CashShiftResponse,
    summary="Close a cashbox shift with an actual counted amount",
)
async def close_admin_cash_shift(
    payload: CashShiftRequest,
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> CashShiftResponse:
    """Calculate expected cash from immutable ledger rows before persisting the close difference."""

    result = await runtime.service.close_cash_shift(
        actor=actor,
        command=CashShiftCommand(
            cashbox_id=payload.cashbox_id,
            amount=payload.amount,
            notes=payload.notes,
            idempotency_key=idempotency_key,
        ),
    )
    return CashShiftResponse.from_result(result)


@admin_router.post(
    "/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record an immutable appointment payment",
)
async def create_admin_payment(
    payload: PaymentRequest,
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> PaymentResponse:
    """Lock the appointment balance and optional cash shift before accepting a payment."""

    result = await runtime.service.record_payment(
        actor=actor,
        command=PaymentCommand(
            appointment_id=payload.appointment_id,
            amount=payload.amount,
            currency=payload.currency,
            method=payload.method,
            cashbox_id=payload.cashbox_id,
            external_reference=payload.external_reference,
            note=payload.note,
            idempotency_key=idempotency_key,
        ),
    )
    return PaymentResponse.from_result(result)


@admin_router.post(
    "/refunds",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record an immutable manual payment refund",
)
async def create_admin_refund(
    payload: RefundRequest,
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> PaymentResponse:
    """Limit cumulative refunds under payment locks and create a matching cash ledger row."""

    result = await runtime.service.refund_payment(
        actor=actor,
        command=RefundCommand(
            payment_id=payload.payment_id,
            amount=payload.amount,
            currency=payload.currency,
            reason=payload.reason,
            cashbox_id=payload.cashbox_id,
            idempotency_key=idempotency_key,
        ),
    )
    return PaymentResponse.from_result(result)


@admin_router.post(
    "/cash/transactions",
    response_model=AdminResourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record an audited manual cash ledger transaction",
)
async def create_admin_cash_transaction(
    payload: CashTransactionRequest,
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> AdminResourceResponse:
    """Permit only explicit manual transaction types on a currently open cash shift."""

    transaction_id = await runtime.service.record_manual_cash_transaction(
        actor=actor,
        command=CashTransactionCommand(
            cashbox_id=payload.cashbox_id,
            type=payload.type,
            amount_delta=payload.amount_delta,
            currency=payload.currency,
            reason=payload.reason,
            idempotency_key=idempotency_key,
        ),
    )
    return AdminResourceResponse(data={"id": transaction_id})


@admin_router.post(
    "/inventory/movements",
    response_model=StockMovementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record an immutable tenant-scoped stock movement",
)
async def create_admin_stock_movement(
    payload: StockMovementRequest,
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
    idempotency_key: Annotated[str, Depends(require_idempotency_key)],
) -> StockMovementResponse:
    """Apply each stock balance delta under ordered locks with one durable idempotency key."""

    result = await runtime.service.record_stock_movement(
        actor=actor,
        command=StockMovementCommand(
            warehouse_id=payload.warehouse_id,
            type=payload.type,
            lines=tuple(
                StockMovementLine(
                    product_id=line.product_id,
                    quantity_delta=line.quantity_delta,
                    unit_cost=line.unit_cost,
                )
                for line in payload.lines
            ),
            reason=payload.reason,
            reference_type=payload.reference_type,
            reference_id=payload.reference_id,
            idempotency_key=idempotency_key,
        ),
    )
    return StockMovementResponse.from_result(result)


@admin_router.get(
    "/analytics",
    response_model=AnalyticsResponse,
    summary="Get bounded tenant booking analytics grouped by a requested IANA timezone",
)
async def get_admin_analytics(
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
    date_from: date,
    date_to: date,
    timezone: Annotated[str, Query(min_length=1, max_length=64)],
    branch_id: UUID | None = None,
    specialist_id: UUID | None = None,
    service_id: UUID | None = None,
) -> AnalyticsResponse:
    """Keep every aggregate in PostgreSQL and use half-open local-day bounds for the time window."""

    return AnalyticsResponse(
        data=await runtime.analytics.dashboard(
            actor=actor,
            query=AnalyticsQuery(
                date_from=date_from,
                date_to=date_to,
                timezone=timezone,
                branch_id=branch_id,
                specialist_id=specialist_id,
                service_id=service_id,
            ),
        )
    )


@admin_router.get(
    "/resources/{resource}",
    response_model=AdminResourceListResponse,
    summary="List a supported tenant booking resource",
)
async def list_admin_resource(
    resource: AdminResourceName,
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
    include_inactive: bool = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AdminResourceListResponse:
    """Expose only the enumerated resources and fields supported by the management service."""

    items = await runtime.management.list_resources(
        actor=actor,
        resource=resource,
        include_inactive=include_inactive,
        limit=limit,
        offset=offset,
    )
    rendered = list(items)
    return AdminResourceListResponse(
        items=rendered,
        limit=limit,
        offset=offset,
        next_offset=offset + len(rendered) if len(rendered) == limit else None,
    )


@admin_router.post(
    "/resources/{resource}",
    response_model=AdminResourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a supported tenant booking resource",
)
async def create_admin_resource(
    resource: AdminResourceName,
    payload: AdminResourcePayload,
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
) -> AdminResourceResponse:
    """Reject arbitrary columns and derive organization ownership exclusively from the session."""

    return AdminResourceResponse(
        data=await runtime.management.create_resource(
            actor=actor,
            resource=resource,
            values=payload.values,
        )
    )


@admin_router.get(
    "/resources/{resource}/{resource_id}",
    response_model=AdminResourceResponse,
    summary="Get one supported tenant booking resource",
)
async def get_admin_resource(
    resource: AdminResourceName,
    resource_id: UUID,
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
) -> AdminResourceResponse:
    """Load through the same tenant predicate used by every mutation and list endpoint."""

    return AdminResourceResponse(
        data=await runtime.management.get_resource(
            actor=actor,
            resource=resource,
            resource_id=resource_id,
        )
    )


@admin_router.patch(
    "/resources/{resource}/{resource_id}",
    response_model=AdminResourceResponse,
    summary="Update allowed fields of a supported tenant booking resource",
)
async def update_admin_resource(
    resource: AdminResourceName,
    resource_id: UUID,
    payload: AdminResourcePayload,
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
) -> AdminResourceResponse:
    """Retain entity identity/history and audit exactly which whitelisted fields changed."""

    return AdminResourceResponse(
        data=await runtime.management.update_resource(
            actor=actor,
            resource=resource,
            resource_id=resource_id,
            values=payload.values,
        )
    )


@admin_router.post(
    "/resources/{resource}/{resource_id}/archive",
    response_model=AdminResourceResponse,
    summary="Archive or deactivate a supported booking resource",
)
async def archive_admin_resource(
    resource: AdminResourceName,
    resource_id: UUID,
    payload: AdminArchiveRequest,
    actor: Annotated[BookingActor, Depends(get_backoffice_actor)],
    runtime: Annotated[BookingModuleRuntime, Depends(get_booking_runtime)],
) -> AdminResourceResponse:
    """Avoid hard deletion of entities that may be referenced by historical booking records."""

    return AdminResourceResponse(
        data=await runtime.management.archive_resource(
            actor=actor,
            resource=resource,
            resource_id=resource_id,
            reason=payload.reason,
        )
    )


router.include_router(auth_router)
router.include_router(client_router)
router.include_router(staff_router)
router.include_router(admin_router)
