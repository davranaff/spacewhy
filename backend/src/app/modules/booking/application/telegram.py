"""Provider-neutral booking bot flow backed by durable conversations and booking use cases."""

from __future__ import annotations

import secrets
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, cast
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from app.core.bots.contracts import BotUpdate
from app.core.clock import SystemClock
from app.core.contracts.clock import Clock
from app.core.db.database import Database
from app.modules.booking.application.access import BookingAccessService
from app.modules.booking.application.context import BookingActor
from app.modules.booking.application.dto import (
    AvailabilityQuery,
    CancelAppointmentCommand,
    ConfirmAppointmentCommand,
    HoldCommand,
    RescheduleCommitCommand,
    StatusTransitionCommand,
)
from app.modules.booking.application.management import BookingManagementService
from app.modules.booking.application.service import BookingService
from app.modules.booking.domain.enums import (
    AccessRole,
    ActorType,
    AppointmentSource,
    AppointmentStatus,
    AuditSource,
    ConversationState,
)
from app.modules.booking.domain.errors import BookingDomainError, BookingErrorCode
from app.modules.booking.domain.value_objects import require_aware
from app.modules.booking.infrastructure.persistence.models import (
    BookingBranch,
    BookingConversation,
    BookingOrganization,
    BookingSettings,
    BookingTelegramBotInstallation,
    Customer,
    CustomerIdentity,
    StaffTelegramBinding,
    TelegramUpdateReceipt,
)


@dataclass(frozen=True, slots=True)
class BotChoice:
    """One server-side callback choice; the callback data itself exposes only an opaque index."""

    label_key: str
    kind: str
    payload: Mapping[str, str | None]
    params: Mapping[str, object] | None = None


@dataclass(frozen=True, slots=True)
class BotResponse:
    """A localization-keyed outbound instruction for the thin Telegram presentation adapter."""

    locale: str
    message_key: str
    params: Mapping[str, object]
    choices: tuple[tuple[str, str, Mapping[str, object]], ...] = ()
    request_contact: bool = False


@dataclass(frozen=True, slots=True)
class _Participant:
    """Server-resolved bot customer/context; no tenant or role comes from callback payloads."""

    organization_id: UUID
    bot_app_id: str
    customer_id: UUID
    conversation_id: UUID
    telegram_user_id: str
    telegram_chat_id: str
    locale: str
    require_phone: bool

    def actor(self) -> BookingActor:
        """Build the least-privilege customer actor used by the application booking service."""

        return BookingActor(
            organization_id=self.organization_id,
            subject_id=self.customer_id,
            role=AccessRole.CUSTOMER,
            permissions=frozenset(),
            actor_type=ActorType.CUSTOMER,
            customer_id=self.customer_id,
            audit_source=AuditSource.TELEGRAM,
        )


@dataclass(frozen=True, slots=True)
class _CallbackDecision:
    """One validated opaque action pulled from a current conversation state and then invalidated."""

    kind: str
    payload: Mapping[str, str | None]
    data: Mapping[str, object]


class BookingTelegramService:
    """Run client/staff flows without a Telegram SDK or bot credentials."""

    def __init__(
        self,
        *,
        database: Database,
        access: BookingAccessService,
        booking: BookingService,
        management: BookingManagementService,
        callback_ttl_seconds: int,
        clock: Clock | None = None,
    ) -> None:
        """Inject only durable application services and module-owned timing policy."""

        self._database = database
        self._access = access
        self._booking = booking
        self._management = management
        self._callback_ttl_seconds = callback_ttl_seconds
        self._clock = clock or SystemClock()

    async def handle_update(self, *, bot_app_id: str, update: BotUpdate) -> BotResponse | None:
        """Process one verified update and record completion for duplicate-delivery safety."""

        if update.provider_user_id is None or update.provider_chat_id is None:
            return None
        if await self._already_processed(
            bot_app_id=bot_app_id, update_id=update.provider_update_id
        ):
            return None
        response = await self._dispatch(bot_app_id=bot_app_id, update=update)
        await self._record_processed(bot_app_id=bot_app_id, update_id=update.provider_update_id)
        return response

    async def _dispatch(self, *, bot_app_id: str, update: BotUpdate) -> BotResponse | None:
        """Route only normalized provider-neutral text, contacts, and opaque callback actions."""

        message_text = (update.message_text or "").strip()
        if message_text.lower().startswith("/bind"):
            return await self._bind_staff(bot_app_id=bot_app_id, update=update, text=message_text)
        participant = await self._participant(bot_app_id=bot_app_id, update=update)
        if update.contact_phone_number is not None:
            return await self._accept_contact(participant=participant, update=update)
        if update.callback_data is not None:
            return await self._handle_callback(participant=participant, update=update)
        if message_text.lower() in {"/start", "/menu"}:
            return await self._start(participant=participant)
        if message_text.lower() in {"/appointments", "/my"}:
            return await self._show_appointments(participant=participant)
        if message_text.lower() == "/history":
            return await self._show_appointments(participant=participant, history=True)
        if message_text.lower() == "/contacts":
            return await self._show_contacts(participant=participant)
        if message_text.lower() == "/help":
            return await self._show_help(participant=participant)
        if message_text.lower() in {"/agenda", "/agenda today"}:
            return await self._show_staff_agenda(participant=participant)
        if message_text.lower() == "/agenda tomorrow":
            return await self._show_staff_agenda(participant=participant, day_offset=1)
        if message_text and await self._is_waiting_for_staff_cancel_reason(participant):
            return await self._cancel_staff_appointment_from_reason(
                participant=participant,
                reason=message_text,
                update_id=update.provider_update_id,
            )
        return await self._show_main(participant=participant)

    async def _start(self, *, participant: _Participant) -> BotResponse:
        """Start after durable identity resolution and required contact policy checks."""

        if participant.require_phone and not await self._customer_has_phone(participant):
            return await self._show_contact_request(participant=participant)
        return await self._show_main(participant=participant, message_key="bot.welcome")

    async def _bind_staff(
        self,
        *,
        bot_app_id: str,
        update: BotUpdate,
        text: str,
    ) -> BotResponse:
        """Consume a one-time admin code, never a username, to bind a staff Telegram user."""

        parts = text.split(maxsplit=1)
        if len(parts) != 2 or not parts[1].strip():
            return BotResponse(
                locale=_preferred_locale(update.provider_language_code),
                message_key="staff.bind.usage",
                params={},
            )
        await self._management.consume_staff_bind_code(
            bot_app_id=bot_app_id,
            telegram_user_id=update.provider_user_id or "",
            telegram_chat_id=update.provider_chat_id or "",
            raw_code=parts[1],
        )
        return BotResponse(
            locale=_preferred_locale(update.provider_language_code),
            message_key="staff.bind.success",
            params={},
        )

    async def _handle_callback(
        self,
        *,
        participant: _Participant,
        update: BotUpdate,
    ) -> BotResponse:
        """Validate a compact callback against the current server-side nonce and choice map."""

        decision = await self._consume_callback(
            participant=participant,
            callback_data=update.callback_data or "",
        )
        if decision is None:
            return BotResponse(
                locale=participant.locale,
                message_key="errors.callback_expired",
                params={},
            )
        if decision.kind == "language":
            locale = decision.payload.get("locale")
            if locale not in {"ru", "uz", "en"}:
                raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
            participant = await self._set_customer_locale(participant=participant, locale=locale)
            if participant.require_phone and not await self._customer_has_phone(participant):
                return await self._show_contact_request(participant=participant)
            return await self._show_main(participant=participant, message_key="language.changed")
        if decision.kind == "menu_book":
            await self._reset_booking_data(participant)
            return await self._choose_branch(participant=participant)
        if decision.kind == "menu_appointments":
            return await self._show_appointments(participant=participant)
        if decision.kind == "appointments_history_page":
            offset = _non_negative_offset(decision.payload.get("offset"))
            return await self._show_appointments(
                participant=participant,
                history=True,
                offset=offset,
            )
        if decision.kind == "menu_language":
            return await self._choose_language(participant=participant)
        if decision.kind == "menu_contacts":
            return await self._show_contacts(participant=participant)
        if decision.kind == "menu_help":
            return await self._show_help(participant=participant)
        if decision.kind == "branch":
            branch_id = _uuid_payload(decision.payload, "branch_id")
            await self._update_conversation_data(participant, {"branch_id": str(branch_id)})
            return await self._choose_category_or_service(participant=participant)
        if decision.kind == "category":
            category_id = _uuid_payload(decision.payload, "category_id")
            await self._update_conversation_data(participant, {"category_id": str(category_id)})
            return await self._choose_service(participant=participant)
        if decision.kind == "service":
            service_id = _uuid_payload(decision.payload, "service_id")
            await self._update_conversation_data(participant, {"service_id": str(service_id)})
            return await self._choose_specialist(participant=participant)
        if decision.kind == "specialist":
            specialist_id = decision.payload.get("specialist_id")
            await self._update_conversation_data(
                participant,
                {"specialist_id": specialist_id}
                if specialist_id is not None
                else {"specialist_id": None},
            )
            return await self._choose_date(participant=participant, data=decision.data)
        if decision.kind == "date":
            selected_date = decision.payload.get("date")
            if selected_date is None:
                raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
            try:
                parsed_date = date.fromisoformat(selected_date)
            except ValueError as error:
                raise BookingDomainError(BookingErrorCode.INVALID_REQUEST) from error
            return await self._choose_slot(
                participant=participant,
                selected_date=parsed_date,
                data=decision.data,
            )
        if decision.kind == "slot":
            return await self._create_hold(
                participant=participant,
                decision=decision,
                update_id=update.provider_update_id,
            )
        if decision.kind == "confirm":
            return await self._confirm_hold(
                participant=participant,
                decision=decision,
                update_id=update.provider_update_id,
            )
        if decision.kind == "appointment":
            return await self._show_appointment_actions(participant=participant, decision=decision)
        if decision.kind == "cancel":
            return await self._cancel_appointment(
                participant=participant,
                decision=decision,
                update_id=update.provider_update_id,
            )
        if decision.kind == "reschedule":
            appointment_id = _uuid_payload(decision.payload, "appointment_id")
            appointment = await self._booking.get_appointment(
                actor=participant.actor(), appointment_id=appointment_id
            )
            await self._update_conversation_data(
                participant,
                {
                    "branch_id": str(appointment.branch_id),
                    "service_id": str(appointment.service_id),
                    "reschedule_appointment_id": str(appointment.id),
                },
            )
            return await self._choose_date(
                participant=participant, data=decision.data, reschedule=True
            )
        if decision.kind == "confirm_reschedule":
            return await self._commit_reschedule(
                participant=participant,
                decision=decision,
                update_id=update.provider_update_id,
            )
        if decision.kind == "staff_appointment":
            return await self._show_staff_appointment_actions(
                participant=participant,
                decision=decision,
            )
        if decision.kind == "staff_transition":
            return await self._transition_staff_appointment(
                participant=participant,
                decision=decision,
                update_id=update.provider_update_id,
            )
        if decision.kind == "staff_cancel_request":
            return await self._request_staff_cancel_reason(
                participant=participant,
                decision=decision,
            )
        return BotResponse(
            locale=participant.locale, message_key="errors.callback_expired", params={}
        )

    async def _choose_language(self, *, participant: _Participant) -> BotResponse:
        """Offer only the module-supported locale set through opaque callback entries."""

        return await self._present(
            participant=participant,
            state=ConversationState.LOCALE,
            message_key="language.choose",
            choices=(
                BotChoice("language.ru", "language", {"locale": "ru"}),
                BotChoice("language.uz", "language", {"locale": "uz"}),
                BotChoice("language.en", "language", {"locale": "en"}),
            ),
        )

    async def _show_contact_request(self, *, participant: _Participant) -> BotResponse:
        """Request a Telegram native contact only when tenant policy requires a phone number."""

        return await self._present(
            participant=participant,
            state=ConversationState.CONTACT,
            message_key="contact.request",
            choices=(),
            request_contact=True,
        )

    async def _show_main(
        self,
        *,
        participant: _Participant,
        message_key: str = "menu.main",
        params: Mapping[str, object] | None = None,
    ) -> BotResponse:
        """Display a compact entry menu without assuming a branch or customer selection."""

        return await self._present(
            participant=participant,
            state=ConversationState.IDLE,
            message_key=message_key,
            params=params or {},
            choices=(
                BotChoice("menu.book", "menu_book", {}),
                BotChoice("menu.appointments", "menu_appointments", {}),
                BotChoice("menu.language", "menu_language", {}),
                BotChoice("menu.contacts", "menu_contacts", {}),
                BotChoice("menu.help", "menu_help", {}),
            ),
        )

    async def _show_contacts(self, *, participant: _Participant) -> BotResponse:
        """Show only active tenant branch contacts sourced from server-side records."""

        branches = await self._booking.list_branches(actor=participant.actor())
        lines = "\n".join(
            " — ".join(
                value
                for value in (
                    str(branch["name"]),
                    str(branch["address"]) if branch["address"] else "",
                    str(branch["phone"]) if branch["phone"] else "",
                )
                if value
            )
            for branch in branches
        )
        return await self._present(
            participant=participant,
            state=ConversationState.IDLE,
            message_key="contacts.list" if lines else "contacts.empty",
            params={"contacts": lines},
            choices=(),
        )

    async def _show_help(self, *, participant: _Participant) -> BotResponse:
        """Render the module-owned help copy without embedding user-facing text in a handler."""

        return await self._present(
            participant=participant,
            state=ConversationState.IDLE,
            message_key="help.text",
            choices=(),
        )

    async def _reset_booking_data(self, participant: _Participant) -> None:
        """Clear stale booking and staff-action selections before a new client flow begins."""

        keys = (
            "branch_id",
            "category_id",
            "service_id",
            "specialist_id",
            "reschedule_appointment_id",
            "staff_cancel_appointment_id",
        )
        async with self._database.session() as session, session.begin():
            conversation = await self._conversation(session, participant, lock=True)
            data = dict(conversation.data)
            data.pop("callbacks", None)
            for key in keys:
                data.pop(key, None)
            conversation.data = data
            conversation.version += 1

    async def _choose_branch(self, *, participant: _Participant) -> BotResponse:
        """Skip the branch selection screen when exactly one active branch exists."""

        async with self._database.session() as session:
            branches = (
                await session.scalars(
                    sa.select(BookingBranch)
                    .where(
                        BookingBranch.organization_id == participant.organization_id,
                        BookingBranch.is_active.is_(True),
                    )
                    .order_by(BookingBranch.name, BookingBranch.id)
                )
            ).all()
        if len(branches) == 1:
            await self._update_conversation_data(participant, {"branch_id": str(branches[0].id)})
            return await self._choose_category_or_service(participant=participant)
        return await self._present(
            participant=participant,
            state=ConversationState.BRANCH,
            message_key="branch.choose",
            choices=tuple(
                BotChoice(
                    "branch.option",
                    "branch",
                    {"branch_id": str(branch.id)},
                    {"name": branch.name},
                )
                for branch in branches[:20]
            ),
        )

    async def _choose_category_or_service(self, *, participant: _Participant) -> BotResponse:
        """Show categories only when the tenant uses them, otherwise show services directly."""

        categories = await self._booking.list_categories(actor=participant.actor())
        if not categories:
            await self._update_conversation_data(participant, {"category_id": None})
            return await self._choose_service(participant=participant)
        return await self._present(
            participant=participant,
            state=ConversationState.CATEGORY,
            message_key="category.choose",
            choices=tuple(
                BotChoice(
                    "category.option",
                    "category",
                    {"category_id": str(category["id"])},
                    {"name": str(category["name"])},
                )
                for category in categories[:20]
            ),
        )

    async def _choose_service(self, *, participant: _Participant) -> BotResponse:
        """List only currently bookable services for the stored branch selection."""

        data = await self._conversation_data(participant)
        branch_id = _uuid_data(data, "branch_id")
        category_value = data.get("category_id")
        category_id = UUID(str(category_value)) if category_value else None
        services = await self._booking.list_services(
            actor=participant.actor(),
            branch_id=branch_id,
            category_id=category_id,
        )
        return await self._present(
            participant=participant,
            state=ConversationState.SERVICE,
            message_key="service.choose",
            choices=tuple(
                BotChoice(
                    "service.option",
                    "service",
                    {"service_id": str(service["id"])},
                    {"name": str(service["name"]), "price": service["price"]},
                )
                for service in services[:20]
            ),
        )

    async def _choose_specialist(self, *, participant: _Participant) -> BotResponse:
        """Allow an explicit specialist or server-selected deterministic any-specialist choice."""

        data = await self._conversation_data(participant)
        branch_id = _uuid_data(data, "branch_id")
        service_id = _uuid_data(data, "service_id")
        specialists = await self._booking.list_specialists(
            actor=participant.actor(),
            branch_id=branch_id,
            service_id=service_id,
        )
        choices: list[BotChoice] = [
            BotChoice("specialist.any", "specialist", {"specialist_id": None})
        ]
        choices.extend(
            BotChoice(
                "specialist.option",
                "specialist",
                {"specialist_id": str(specialist["id"])},
                {"name": str(specialist["display_name"])},
            )
            for specialist in specialists[:19]
        )
        return await self._present(
            participant=participant,
            state=ConversationState.SPECIALIST,
            message_key="specialist.choose",
            choices=tuple(choices),
        )

    async def _choose_date(
        self,
        *,
        participant: _Participant,
        data: Mapping[str, object],
        reschedule: bool = False,
    ) -> BotResponse:
        """Offer the next seven local dates bounded by tenant policy and branch timezone."""

        branch_id = _uuid_data(await self._conversation_data(participant), "branch_id")
        timezone = await self._branch_timezone(participant.organization_id, branch_id)
        today = require_aware(self._clock.now(), field_name="now").astimezone(timezone).date()
        choices = tuple(
            BotChoice(
                "date.option",
                "date",
                {"date": (today + timedelta(days=offset)).isoformat()},
                {"date": (today + timedelta(days=offset)).isoformat()},
            )
            for offset in range(7)
        )
        state = ConversationState.RESCHEDULE_SLOT if reschedule else ConversationState.DATE
        return await self._present(
            participant=participant,
            state=state,
            message_key="date.choose",
            choices=choices,
        )

    async def _choose_slot(
        self,
        *,
        participant: _Participant,
        selected_date: date,
        data: Mapping[str, object],
    ) -> BotResponse:
        """Compute live slots only after all booking selections are server-side."""

        current_data = await self._conversation_data(participant)
        branch_id = _uuid_data(current_data, "branch_id")
        service_id = _uuid_data(current_data, "service_id")
        specialist_value = current_data.get("specialist_id")
        specialist_id = UUID(str(specialist_value)) if specialist_value else None
        slots = await self._booking.availability(
            actor=participant.actor(),
            query=AvailabilityQuery(
                branch_id=branch_id,
                service_id=service_id,
                specialist_id=specialist_id,
                customer_id=participant.customer_id,
                date_from=selected_date,
                date_to=selected_date,
            ),
        )
        reschedule_id = current_data.get("reschedule_appointment_id")
        state = ConversationState.RESCHEDULE_SLOT if reschedule_id else ConversationState.SLOT
        return await self._present(
            participant=participant,
            state=state,
            message_key="slot.choose",
            choices=tuple(
                BotChoice(
                    "slot.option",
                    "slot",
                    {
                        "starts_at": slot.starts_at.isoformat(),
                        "specialist_id": str(slot.specialist_id),
                        "reschedule_appointment_id": str(reschedule_id)
                        if reschedule_id is not None
                        else None,
                    },
                    {"starts_at": slot.starts_at.isoformat()},
                )
                for slot in slots[:12]
            ),
        )

    async def _create_hold(
        self,
        *,
        participant: _Participant,
        decision: _CallbackDecision,
        update_id: str | None,
    ) -> BotResponse:
        """Create an ordinary or replacement hold with an update-derived durable idempotency key."""

        starts_at_text = decision.payload.get("starts_at")
        specialist_text = decision.payload.get("specialist_id")
        if starts_at_text is None or specialist_text is None or update_id is None:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        try:
            starts_at = require_aware(
                datetime.fromisoformat(starts_at_text), field_name="starts_at"
            )
            specialist_id = UUID(specialist_text)
        except ValueError as error:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST) from error
        data = await self._conversation_data(participant)
        command = HoldCommand(
            branch_id=_uuid_data(data, "branch_id"),
            service_id=_uuid_data(data, "service_id"),
            specialist_id=specialist_id,
            starts_at=starts_at,
            idempotency_key=f"telegram:hold:{participant.conversation_id}:{update_id}",
        )
        reschedule_text = decision.payload.get("reschedule_appointment_id")
        if reschedule_text is None:
            hold = await self._booking.create_hold(actor=participant.actor(), command=command)
            kind = "confirm"
            state = ConversationState.CONFIRM
        else:
            try:
                appointment_id = UUID(reschedule_text)
            except ValueError as error:
                raise BookingDomainError(BookingErrorCode.INVALID_REQUEST) from error
            hold = await self._booking.create_reschedule_hold(
                actor=participant.actor(),
                appointment_id=appointment_id,
                command=command,
            )
            kind = "confirm_reschedule"
            state = ConversationState.RESCHEDULE_CONFIRM
        return await self._present(
            participant=participant,
            state=state,
            message_key="booking.review",
            params={
                "starts_at": hold.starts_at.isoformat(),
                "service_name": hold.service_name,
                "specialist_name": hold.specialist_name,
                "duration_minutes": hold.duration_minutes,
                "price": hold.price,
                "currency": hold.currency,
            },
            choices=(
                BotChoice(
                    "booking.confirm",
                    kind,
                    {
                        "hold_id": str(hold.id),
                        "appointment_id": reschedule_text,
                    },
                ),
            ),
        )

    async def _confirm_hold(
        self,
        *,
        participant: _Participant,
        decision: _CallbackDecision,
        update_id: str | None,
    ) -> BotResponse:
        """Promote one owned hold into an appointment after its callback nonce has been consumed."""

        if update_id is None:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        hold_id = _uuid_payload(decision.payload, "hold_id")
        appointment = await self._booking.confirm_appointment(
            actor=participant.actor(),
            command=ConfirmAppointmentCommand(
                hold_id=hold_id,
                customer_note=None,
                idempotency_key=f"telegram:confirm:{participant.conversation_id}:{update_id}",
                source=AppointmentSource.TELEGRAM_BOT,
            ),
        )
        return await self._show_main(
            participant=participant,
            message_key="booking.created",
            params={
                "number": appointment.public_number,
                "starts_at": appointment.starts_at.isoformat(),
            },
        )

    async def _show_appointments(
        self,
        *,
        participant: _Participant,
        history: bool = False,
        offset: int = 0,
    ) -> BotResponse:
        """Show own upcoming or paginated historical appointments with opaque actions."""

        limit = 8
        appointments = await self._booking.list_appointments(
            actor=participant.actor(),
            upcoming=not history,
            history=history,
            limit=limit,
            offset=offset,
        )
        lines = "\n".join(
            f"{appointment.public_number} — {appointment.starts_at.isoformat()}"
            for appointment in appointments
        )
        choices: list[BotChoice] = [
            BotChoice(
                "appointment.option",
                "appointment",
                {"appointment_id": str(appointment.id)},
                {"number": appointment.public_number},
            )
            for appointment in appointments
        ]
        if history:
            if offset > 0:
                choices.append(
                    BotChoice(
                        "appointments.history.previous",
                        "appointments_history_page",
                        {"offset": str(max(offset - limit, 0))},
                    )
                )
            if len(appointments) == limit:
                choices.append(
                    BotChoice(
                        "appointments.history.next",
                        "appointments_history_page",
                        {"offset": str(offset + limit)},
                    )
                )
        else:
            choices.append(
                BotChoice(
                    "appointments.history.show",
                    "appointments_history_page",
                    {"offset": "0"},
                )
            )
        return await self._present(
            participant=participant,
            state=ConversationState.IDLE,
            message_key=(
                "appointments.history"
                if history and appointments
                else "appointments.list"
                if appointments
                else "appointments.history.empty"
                if history
                else "appointments.empty"
            ),
            params={"appointments": lines},
            choices=tuple(choices),
        )

    async def _show_appointment_actions(
        self,
        *,
        participant: _Participant,
        decision: _CallbackDecision,
    ) -> BotResponse:
        """Offer cancellation or rescheduling for one verified own appointment only."""

        appointment_id = _uuid_payload(decision.payload, "appointment_id")
        appointment = await self._booking.get_appointment(
            actor=participant.actor(), appointment_id=appointment_id
        )
        choices: tuple[BotChoice, ...] = ()
        if appointment.status in {AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED}:
            choices = (
                BotChoice(
                    "appointment.cancel",
                    "cancel",
                    {"appointment_id": str(appointment.id)},
                ),
                BotChoice(
                    "appointment.reschedule",
                    "reschedule",
                    {"appointment_id": str(appointment.id)},
                ),
            )
        return await self._present(
            participant=participant,
            state=ConversationState.IDLE,
            message_key="appointment.actions",
            params={
                "number": appointment.public_number,
                "starts_at": appointment.starts_at.isoformat(),
            },
            choices=choices,
        )

    async def _cancel_appointment(
        self,
        *,
        participant: _Participant,
        decision: _CallbackDecision,
        update_id: str | None,
    ) -> BotResponse:
        """Cancel one own booking through the same policy and idempotency rules as HTTP."""

        if update_id is None:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        appointment = await self._booking.cancel_appointment(
            actor=participant.actor(),
            command=CancelAppointmentCommand(
                appointment_id=_uuid_payload(decision.payload, "appointment_id"),
                reason=None,
                idempotency_key=f"telegram:cancel:{participant.conversation_id}:{update_id}",
            ),
        )
        return await self._show_main(
            participant=participant,
            message_key="appointment.cancelled",
            params={"number": appointment.public_number},
        )

    async def _commit_reschedule(
        self,
        *,
        participant: _Participant,
        decision: _CallbackDecision,
        update_id: str | None,
    ) -> BotResponse:
        """Commit an owned old/new reservation swap only after a valid replacement hold exists."""

        if update_id is None:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        appointment = await self._booking.commit_reschedule(
            actor=participant.actor(),
            command=RescheduleCommitCommand(
                appointment_id=_uuid_payload(decision.payload, "appointment_id"),
                hold_id=_uuid_payload(decision.payload, "hold_id"),
                idempotency_key=f"telegram:reschedule:{participant.conversation_id}:{update_id}",
            ),
        )
        return await self._show_main(
            participant=participant,
            message_key="appointment.rescheduled",
            params={
                "number": appointment.public_number,
                "starts_at": appointment.starts_at.isoformat(),
            },
        )

    async def _accept_contact(
        self,
        *,
        participant: _Participant,
        update: BotUpdate,
    ) -> BotResponse:
        """Accept a contact only when Telegram declares it belongs to the current user."""

        # Telegram may omit ``user_id`` for some contact payloads.  When it is
        # present it is authoritative; otherwise accept the explicit user action
        # without inventing an ownership claim from the phone number itself.
        if (
            update.contact_user_id is not None
            and update.contact_user_id != participant.telegram_user_id
        ):
            return BotResponse(
                locale=participant.locale,
                message_key="errors.contact_owner_mismatch",
                params={},
            )
        phone = _normalize_phone(update.contact_phone_number or "")
        if phone is None:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        async with self._database.session() as session, session.begin():
            customer = await session.scalar(
                sa.select(Customer)
                .where(
                    Customer.id == participant.customer_id,
                    Customer.organization_id == participant.organization_id,
                )
                .with_for_update()
            )
            if customer is None:
                raise BookingDomainError(BookingErrorCode.FORBIDDEN)
            customer.normalized_phone = phone
        return await self._show_main(participant=participant, message_key="contact.saved")

    async def _show_staff_agenda(
        self,
        *,
        participant: _Participant,
        day_offset: int = 0,
    ) -> BotResponse:
        """Provide a bound specialist their own local agenda and action-safe appointment choices."""

        actor, timezone = await self._staff_actor_and_timezone(participant)
        local_day = require_aware(self._clock.now(), field_name="now").astimezone(
            timezone
        ).date() + timedelta(days=day_offset)
        agenda = await self._booking.staff_agenda(actor=actor, local_day=local_day)
        lines = "\n".join(
            f"{item.starts_at.astimezone(timezone):%H:%M} — {item.service_name}" for item in agenda
        )
        return await self._present(
            participant=participant,
            state=ConversationState.IDLE,
            message_key="staff.agenda" if agenda else "staff.agenda.empty",
            params={"appointments": lines},
            choices=tuple(
                BotChoice(
                    "staff.appointment.option",
                    "staff_appointment",
                    {"appointment_id": str(appointment.id)},
                    {"number": appointment.public_number},
                )
                for appointment in agenda
            ),
        )

    async def _show_staff_appointment_actions(
        self,
        *,
        participant: _Participant,
        decision: _CallbackDecision,
    ) -> BotResponse:
        """Expose only lifecycle actions that match the current own-appointment status."""

        actor, _ = await self._staff_actor_and_timezone(participant)
        appointment_id = _uuid_payload(decision.payload, "appointment_id")
        appointment = await self._booking.get_appointment(
            actor=actor, appointment_id=appointment_id
        )
        choices: list[BotChoice] = []
        if appointment.status is AppointmentStatus.PENDING:
            choices.append(
                BotChoice(
                    "staff.action.confirm",
                    "staff_transition",
                    {
                        "appointment_id": str(appointment.id),
                        "target_status": AppointmentStatus.CONFIRMED.value,
                    },
                )
            )
        if appointment.status is AppointmentStatus.CONFIRMED:
            choices.extend(
                (
                    BotChoice(
                        "staff.action.check_in",
                        "staff_transition",
                        {
                            "appointment_id": str(appointment.id),
                            "target_status": AppointmentStatus.CHECKED_IN.value,
                        },
                    ),
                    BotChoice(
                        "staff.action.complete",
                        "staff_transition",
                        {
                            "appointment_id": str(appointment.id),
                            "target_status": AppointmentStatus.COMPLETED.value,
                        },
                    ),
                    BotChoice(
                        "staff.action.no_show",
                        "staff_transition",
                        {
                            "appointment_id": str(appointment.id),
                            "target_status": AppointmentStatus.NO_SHOW.value,
                        },
                    ),
                )
            )
        if appointment.status is AppointmentStatus.CHECKED_IN:
            choices.append(
                BotChoice(
                    "staff.action.complete",
                    "staff_transition",
                    {
                        "appointment_id": str(appointment.id),
                        "target_status": AppointmentStatus.COMPLETED.value,
                    },
                )
            )
        if appointment.status in {
            AppointmentStatus.PENDING,
            AppointmentStatus.CONFIRMED,
            AppointmentStatus.CHECKED_IN,
        }:
            choices.append(
                BotChoice(
                    "staff.action.cancel",
                    "staff_cancel_request",
                    {"appointment_id": str(appointment.id)},
                )
            )
        return await self._present(
            participant=participant,
            state=ConversationState.IDLE,
            message_key="staff.appointment.actions",
            params={
                "number": appointment.public_number,
                "starts_at": appointment.starts_at.isoformat(),
                "service_name": appointment.service_name,
            },
            choices=tuple(choices),
        )

    async def _transition_staff_appointment(
        self,
        *,
        participant: _Participant,
        decision: _CallbackDecision,
        update_id: str | None,
    ) -> BotResponse:
        """Apply one permission-checked transition through the same service used by HTTP."""

        if update_id is None:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        target_value = decision.payload.get("target_status")
        try:
            target_status = AppointmentStatus(target_value or "")
        except ValueError as error:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST) from error
        actor, _ = await self._staff_actor_and_timezone(participant)
        await self._booking.transition_appointment(
            actor=actor,
            command=StatusTransitionCommand(
                appointment_id=_uuid_payload(decision.payload, "appointment_id"),
                target_status=target_status,
                idempotency_key=(
                    f"telegram:staff_transition:{participant.conversation_id}:{update_id}:"
                    f"{target_status.value}"
                ),
            ),
        )
        return await self._show_staff_agenda(participant=participant)

    async def _request_staff_cancel_reason(
        self,
        *,
        participant: _Participant,
        decision: _CallbackDecision,
    ) -> BotResponse:
        """Store only the verified appointment ID before waiting for a mandatory staff reason."""

        appointment_id = _uuid_payload(decision.payload, "appointment_id")
        await self._update_conversation_data(
            participant,
            {"staff_cancel_appointment_id": str(appointment_id)},
        )
        return await self._present(
            participant=participant,
            state=ConversationState.STAFF_CANCEL_REASON,
            message_key="staff.cancel.reason.request",
            choices=(),
        )

    async def _is_waiting_for_staff_cancel_reason(self, participant: _Participant) -> bool:
        """Treat arbitrary text as a cancellation reason only in the durable dedicated state."""

        async with self._database.session() as session:
            conversation = await self._conversation(session, participant, lock=False)
            return conversation.state is ConversationState.STAFF_CANCEL_REASON

    async def _cancel_staff_appointment_from_reason(
        self,
        *,
        participant: _Participant,
        reason: str,
        update_id: str | None,
    ) -> BotResponse:
        """Cancel one staff-scoped appointment only after collecting a non-empty audit reason."""

        normalized_reason = reason.strip()
        if not normalized_reason or update_id is None:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        data = await self._conversation_data(participant)
        appointment_id = _uuid_data(data, "staff_cancel_appointment_id")
        actor, _ = await self._staff_actor_and_timezone(participant)
        await self._booking.cancel_appointment(
            actor=actor,
            command=CancelAppointmentCommand(
                appointment_id=appointment_id,
                reason=normalized_reason,
                idempotency_key=(
                    f"telegram:staff_cancel:{participant.conversation_id}:{update_id}"
                ),
            ),
        )
        await self._update_conversation_data(participant, {"staff_cancel_appointment_id": None})
        return await self._show_staff_agenda(participant=participant)

    async def _staff_actor_and_timezone(
        self,
        participant: _Participant,
    ) -> tuple[BookingActor, ZoneInfo]:
        """Rehydrate one active binding's live membership before every staff bot operation."""

        async with self._database.session() as session:
            binding = await session.scalar(
                sa.select(StaffTelegramBinding).where(
                    StaffTelegramBinding.organization_id == participant.organization_id,
                    StaffTelegramBinding.bot_app_id == participant.bot_app_id,
                    StaffTelegramBinding.telegram_user_id == participant.telegram_user_id,
                    StaffTelegramBinding.is_active.is_(True),
                )
            )
            if binding is None:
                raise BookingDomainError(BookingErrorCode.STAFF_NOT_BOUND)
            organization = await session.get(BookingOrganization, participant.organization_id)
            if organization is None:
                raise BookingDomainError(BookingErrorCode.STAFF_NOT_BOUND)
        try:
            timezone = ZoneInfo(organization.default_timezone)
        except ZoneInfoNotFoundError as error:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST) from error
        actor = await self._access.actor_for_staff_binding(
            organization_id=participant.organization_id,
            subject_id=binding.specialist_id if binding.membership_id is None else None,
            membership_id=binding.membership_id,
            specialist_id=binding.specialist_id,
        )
        return actor, timezone

    async def _participant(self, *, bot_app_id: str, update: BotUpdate) -> _Participant:
        """Resolve tenant, identity, customer, and conversation under an advisory lock."""

        user_id = update.provider_user_id
        chat_id = update.provider_chat_id
        if user_id is None or chat_id is None:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        now = require_aware(self._clock.now(), field_name="now")
        async with self._database.session() as session, session.begin():
            installation = await session.scalar(
                sa.select(BookingTelegramBotInstallation).where(
                    BookingTelegramBotInstallation.bot_app_id == bot_app_id,
                    BookingTelegramBotInstallation.is_active.is_(True),
                )
            )
            if installation is None:
                raise BookingDomainError(BookingErrorCode.FORBIDDEN)
            lock_key = f"booking:bot_identity:{installation.organization_id}:{bot_app_id}:{user_id}"
            await session.execute(
                sa.select(sa.func.pg_advisory_xact_lock(sa.func.hashtext(lock_key)))
            )
            identity = await session.scalar(
                sa.select(CustomerIdentity)
                .where(
                    CustomerIdentity.organization_id == installation.organization_id,
                    CustomerIdentity.provider == "telegram",
                    CustomerIdentity.bot_app_id == bot_app_id,
                    CustomerIdentity.external_user_id == user_id,
                )
                .with_for_update()
            )
            if identity is None:
                customer = Customer(
                    organization_id=installation.organization_id,
                    first_name=(update.provider_first_name or "Telegram")[:160],
                    last_name=(update.provider_last_name or None),
                    locale=_preferred_locale(update.provider_language_code),
                )
                session.add(customer)
                await session.flush()
                identity = CustomerIdentity(
                    organization_id=installation.organization_id,
                    customer_id=customer.id,
                    provider="telegram",
                    bot_app_id=bot_app_id,
                    external_user_id=user_id,
                    external_chat_id=chat_id,
                    username=update.provider_username,
                    metadata_json={},
                )
                session.add(identity)
            else:
                customer = await session.scalar(
                    sa.select(Customer)
                    .where(
                        Customer.id == identity.customer_id,
                        Customer.organization_id == installation.organization_id,
                    )
                    .with_for_update()
                )
                if customer is None:
                    raise BookingDomainError(BookingErrorCode.FORBIDDEN)
                identity.external_chat_id = chat_id
                identity.username = update.provider_username
            if customer.is_blocked:
                raise BookingDomainError(BookingErrorCode.CUSTOMER_BLOCKED)
            settings = await session.get(BookingSettings, installation.organization_id)
            if settings is None:
                raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
            conversation = await session.scalar(
                sa.select(BookingConversation)
                .where(
                    BookingConversation.organization_id == installation.organization_id,
                    BookingConversation.bot_app_id == bot_app_id,
                    BookingConversation.telegram_user_id == user_id,
                    BookingConversation.telegram_chat_id == chat_id,
                )
                .with_for_update()
            )
            if conversation is None:
                conversation = BookingConversation(
                    organization_id=installation.organization_id,
                    bot_app_id=bot_app_id,
                    telegram_user_id=user_id,
                    telegram_chat_id=chat_id,
                    customer_id=customer.id,
                    state=ConversationState.IDLE,
                    data={},
                    callback_nonce="",
                    expires_at=now + timedelta(seconds=self._callback_ttl_seconds),
                )
                session.add(conversation)
                await session.flush()
            return _Participant(
                organization_id=installation.organization_id,
                bot_app_id=bot_app_id,
                customer_id=customer.id,
                conversation_id=conversation.id,
                telegram_user_id=user_id,
                telegram_chat_id=chat_id,
                locale=customer.locale,
                require_phone=settings.require_client_phone,
            )

    async def _present(
        self,
        *,
        participant: _Participant,
        state: ConversationState,
        message_key: str,
        choices: Sequence[BotChoice],
        params: Mapping[str, object] | None = None,
        request_contact: bool = False,
    ) -> BotResponse:
        """Replace callback map/nonce atomically so stale messages cannot affect new state."""

        now = require_aware(self._clock.now(), field_name="now")
        async with self._database.session() as session, session.begin():
            conversation = await self._conversation(session, participant, lock=True)
            data = dict(conversation.data)
            data.pop("callbacks", None)
            nonce = secrets.token_hex(8) if choices else ""
            callback_map: dict[str, dict[str, str | None]] = {}
            rendered_choices: list[tuple[str, str, Mapping[str, object]]] = []
            for index, choice in enumerate(choices, start=1):
                callback_key = str(index)
                callback_map[callback_key] = {"kind": choice.kind, **dict(choice.payload)}
                rendered_choices.append(
                    (
                        choice.label_key,
                        f"b:{nonce}:{callback_key}",
                        dict(choice.params or {}),
                    )
                )
            if callback_map:
                data["callbacks"] = callback_map
            conversation.state = state
            conversation.data = data
            conversation.callback_nonce = nonce
            conversation.expires_at = now + timedelta(seconds=self._callback_ttl_seconds)
            conversation.version += 1
            return BotResponse(
                locale=participant.locale,
                message_key=message_key,
                params=dict(params or {}),
                choices=tuple(rendered_choices),
                request_contact=request_contact,
            )

    async def _consume_callback(
        self,
        *,
        participant: _Participant,
        callback_data: str,
    ) -> _CallbackDecision | None:
        """Read and invalidate exactly one opaque callback map entry before side effects begin."""

        parts = callback_data.split(":")
        if len(parts) != 3 or parts[0] != "b":
            return None
        nonce, callback_key = parts[1], parts[2]
        now = require_aware(self._clock.now(), field_name="now")
        async with self._database.session() as session, session.begin():
            conversation = await self._conversation(session, participant, lock=True)
            if (
                not conversation.callback_nonce
                or conversation.callback_nonce != nonce
                or conversation.expires_at is None
                or conversation.expires_at <= now
            ):
                return None
            raw_callbacks = conversation.data.get("callbacks")
            if not isinstance(raw_callbacks, Mapping):
                return None
            callbacks = cast(Mapping[object, object], raw_callbacks)
            raw_choice_value = callbacks.get(callback_key)
            if not isinstance(raw_choice_value, Mapping):
                return None
            raw_choice = cast(Mapping[object, object], raw_choice_value)
            kind = raw_choice.get("kind")
            if not isinstance(kind, str):
                return None
            payload: dict[str, str | None] = {}
            for raw_key, raw_value in raw_choice.items():
                if raw_key == "kind":
                    continue
                payload[str(raw_key)] = (
                    raw_value if isinstance(raw_value, str) or raw_value is None else None
                )
            data = dict(conversation.data)
            data.pop("callbacks", None)
            conversation.data = data
            conversation.callback_nonce = ""
            conversation.expires_at = now + timedelta(seconds=self._callback_ttl_seconds)
            conversation.version += 1
            return _CallbackDecision(kind=kind, payload=payload, data=data)

    async def _conversation_data(self, participant: _Participant) -> Mapping[str, object]:
        """Return current server-side conversation data without callback map internals."""

        async with self._database.session() as session:
            conversation = await self._conversation(session, participant, lock=False)
            data = dict(conversation.data)
            data.pop("callbacks", None)
            return data

    async def _update_conversation_data(
        self,
        participant: _Participant,
        values: Mapping[str, str | None],
    ) -> None:
        """Persist selections in the tenant-scoped conversation rather than callback payloads."""

        async with self._database.session() as session, session.begin():
            conversation = await self._conversation(session, participant, lock=True)
            data = dict(conversation.data)
            data.pop("callbacks", None)
            data.update(values)
            conversation.data = data
            conversation.version += 1

    async def _set_customer_locale(self, *, participant: _Participant, locale: str) -> _Participant:
        """Persist a supported locale and return a matching immutable participant context."""

        async with self._database.session() as session, session.begin():
            customer = await session.scalar(
                sa.select(Customer)
                .where(
                    Customer.id == participant.customer_id,
                    Customer.organization_id == participant.organization_id,
                )
                .with_for_update()
            )
            if customer is None:
                raise BookingDomainError(BookingErrorCode.FORBIDDEN)
            customer.locale = locale
        return _Participant(
            organization_id=participant.organization_id,
            bot_app_id=participant.bot_app_id,
            customer_id=participant.customer_id,
            conversation_id=participant.conversation_id,
            telegram_user_id=participant.telegram_user_id,
            telegram_chat_id=participant.telegram_chat_id,
            locale=locale,
            require_phone=participant.require_phone,
        )

    async def _customer_has_phone(self, participant: _Participant) -> bool:
        """Check current durable customer state instead of retaining stale session profile data."""

        async with self._database.session() as session:
            phone = await session.scalar(
                sa.select(Customer.normalized_phone).where(
                    Customer.id == participant.customer_id,
                    Customer.organization_id == participant.organization_id,
                )
            )
            return phone is not None

    async def _branch_timezone(self, organization_id: UUID, branch_id: UUID) -> ZoneInfo:
        """Resolve the selected tenant branch timezone before generating local date options."""

        async with self._database.session() as session:
            branch = await session.scalar(
                sa.select(BookingBranch).where(
                    BookingBranch.id == branch_id,
                    BookingBranch.organization_id == organization_id,
                )
            )
            if branch is None:
                raise BookingDomainError(BookingErrorCode.BRANCH_INACTIVE)
            if branch.timezone:
                timezone_name = branch.timezone
            else:
                organization = await session.get(BookingOrganization, organization_id)
                if organization is None:
                    raise BookingDomainError(BookingErrorCode.FORBIDDEN)
                timezone_name = organization.default_timezone
        try:
            return ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as error:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST) from error

    async def _conversation(
        self,
        session: Any,
        participant: _Participant,
        *,
        lock: bool,
    ) -> BookingConversation:
        """Load the exact app/chat/user conversation through all tenant scope predicates."""

        statement = sa.select(BookingConversation).where(
            BookingConversation.id == participant.conversation_id,
            BookingConversation.organization_id == participant.organization_id,
            BookingConversation.bot_app_id == participant.bot_app_id,
            BookingConversation.telegram_user_id == participant.telegram_user_id,
            BookingConversation.telegram_chat_id == participant.telegram_chat_id,
        )
        if lock:
            statement = statement.with_for_update()
        conversation = await session.scalar(statement)
        if conversation is None:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        return conversation

    async def _already_processed(self, *, bot_app_id: str, update_id: str | None) -> bool:
        """Check a durable receipt before handling an at-least-once webhook delivery."""

        if update_id is None:
            return False
        async with self._database.session() as session:
            installation = await session.scalar(
                sa.select(BookingTelegramBotInstallation).where(
                    BookingTelegramBotInstallation.bot_app_id == bot_app_id,
                    BookingTelegramBotInstallation.is_active.is_(True),
                )
            )
            if installation is None:
                raise BookingDomainError(BookingErrorCode.FORBIDDEN)
            receipt = await session.scalar(
                sa.select(TelegramUpdateReceipt.id).where(
                    TelegramUpdateReceipt.organization_id == installation.organization_id,
                    TelegramUpdateReceipt.bot_app_id == bot_app_id,
                    TelegramUpdateReceipt.provider_update_id == update_id,
                )
            )
            return receipt is not None

    async def _record_processed(self, *, bot_app_id: str, update_id: str | None) -> None:
        """Write a receipt after processing; mutation keys guard concurrent duplicate effects."""

        if update_id is None:
            return
        async with self._database.session() as session, session.begin():
            installation = await session.scalar(
                sa.select(BookingTelegramBotInstallation).where(
                    BookingTelegramBotInstallation.bot_app_id == bot_app_id,
                    BookingTelegramBotInstallation.is_active.is_(True),
                )
            )
            if installation is None:
                raise BookingDomainError(BookingErrorCode.FORBIDDEN)
            try:
                async with session.begin_nested():
                    session.add(
                        TelegramUpdateReceipt(
                            organization_id=installation.organization_id,
                            bot_app_id=bot_app_id,
                            provider_update_id=update_id,
                        )
                    )
                    await session.flush()
            except IntegrityError:
                return


def _preferred_locale(value: str | None) -> str:
    """Normalize provider language hints to the product's three currently shipped bot locales."""

    normalized = value.lower().split("-", maxsplit=1)[0] if value else "ru"
    return normalized if normalized in {"ru", "uz", "en"} else "ru"


def _uuid_payload(payload: Mapping[str, str | None], field: str) -> UUID:
    """Decode one opaque server-generated UUID payload and reject callback tampering."""

    value = payload.get(field)
    if value is None:
        raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
    try:
        return UUID(value)
    except ValueError as error:
        raise BookingDomainError(BookingErrorCode.INVALID_REQUEST) from error


def _non_negative_offset(value: str | None) -> int:
    """Decode a bounded page cursor that was issued by this server-side callback map."""

    try:
        offset = int(value or "")
    except ValueError as error:
        raise BookingDomainError(BookingErrorCode.INVALID_REQUEST) from error
    if offset < 0 or offset > 10_000:
        raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
    return offset


def _uuid_data(data: Mapping[str, object], field: str) -> UUID:
    """Decode a UUID stored in server-side conversation state."""

    value = data.get(field)
    if not isinstance(value, str):
        raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
    try:
        return UUID(value)
    except ValueError as error:
        raise BookingDomainError(BookingErrorCode.INVALID_REQUEST) from error


def _normalize_phone(value: str) -> str | None:
    """Keep a compact phone-like value without treating it as a globally unique identity."""

    digits = "".join(character for character in value if character.isdigit())
    if not 7 <= len(digits) <= 20:
        return None
    return ("+" if value.strip().startswith("+") else "") + digits
