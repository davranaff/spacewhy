"""Stable booking business enumerations."""

from enum import StrEnum


class AppointmentStatus(StrEnum):
    """Lifecycle status for one appointment."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class AppointmentSource(StrEnum):
    """Trusted channel that created an appointment."""

    TELEGRAM_BOT = "telegram_bot"
    CLIENT_API = "client_api"
    MINI_APP = "mini_app"
    ADMIN = "admin"
    STAFF = "staff"


class ReservationType(StrEnum):
    """A busy interval is either temporary or committed."""

    HOLD = "hold"
    APPOINTMENT = "appointment"


class ReservationStatus(StrEnum):
    """Persistence state for a temporary or committed busy interval."""

    ACTIVE = "active"
    RELEASED = "released"
    EXPIRED = "expired"


class AvailabilityExceptionType(StrEnum):
    """An exception removes or adds one availability interval."""

    UNAVAILABLE = "unavailable"
    AVAILABLE_OVERRIDE = "available_override"


class ActorType(StrEnum):
    """Auditable actor categories."""

    CUSTOMER = "customer"
    STAFF = "staff"
    ADMIN = "admin"
    SYSTEM = "system"
    TELEGRAM = "telegram"
    PLATFORM = "platform"


class PaymentMethod(StrEnum):
    """Supported internal payment methods."""

    CASH = "cash"
    CARD = "card"
    TRANSFER = "transfer"
    OTHER = "other"


class PaymentStatus(StrEnum):
    """Derived payment state exposed on appointment responses."""

    UNPAID = "unpaid"
    PARTIAL = "partial"
    PAID = "paid"
    PARTIALLY_REFUNDED = "partially_refunded"
    REFUNDED = "refunded"


class CashShiftStatus(StrEnum):
    """Cash shift lifecycle."""

    OPEN = "open"
    CLOSED = "closed"


class CashTransactionType(StrEnum):
    """Immutable cash ledger operation types."""

    SHIFT_OPENING = "shift_opening"
    APPOINTMENT_PAYMENT = "appointment_payment"
    REFUND = "refund"
    MANUAL_INCOME = "manual_income"
    MANUAL_EXPENSE = "manual_expense"
    ADJUSTMENT = "adjustment"
    REVERSAL = "reversal"


class StockMovementType(StrEnum):
    """Immutable inventory movement categories."""

    RECEIPT = "receipt"
    SERVICE_CONSUMPTION = "service_consumption"
    WRITE_OFF = "write_off"
    MANUAL_ADJUSTMENT = "manual_adjustment"
    REVERSAL = "reversal"


class OutboxStatus(StrEnum):
    """At-least-once notification delivery lifecycle."""

    PENDING = "pending"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AccessRole(StrEnum):
    """Legacy booking role labels retained only for backwards-compatible session display."""

    OWNER = "owner"
    ADMIN = "admin"
    BRANCH_MANAGER = "branch_manager"
    RECEPTIONIST = "receptionist"
    SPECIALIST = "specialist"
    CASHIER = "cashier"
    WAREHOUSE_MANAGER = "warehouse_manager"
    INVENTORY_MANAGER = "inventory_manager"
    ACCOUNTANT = "accountant"
    ANALYST = "analyst"
    AUDITOR = "auditor"
    CUSTOMER = "customer"


class AccessScope(StrEnum):
    """The durable scope carried by one role assignment, never a frontend capability."""

    ORGANIZATION = "organization"
    BRANCH = "branch"
    SELF = "self"
    CUSTOMER_OWN = "customer_own"


class BuiltInRole(StrEnum):
    """Stable system-role codes used by the permission seed and migration."""

    OWNER = "OWNER"
    ADMIN = "ADMIN"
    BRANCH_MANAGER = "BRANCH_MANAGER"
    RECEPTIONIST = "RECEPTIONIST"
    CASHIER = "CASHIER"
    SPECIALIST = "SPECIALIST"
    INVENTORY_MANAGER = "INVENTORY_MANAGER"
    ACCOUNTANT = "ACCOUNTANT"
    ANALYST = "ANALYST"
    AUDITOR = "AUDITOR"


class AuditSource(StrEnum):
    """Trusted origins written to the append-only booking audit trail."""

    API = "api"
    TELEGRAM = "telegram"
    WORKER = "worker"
    INTERNAL_ADMIN = "internal_admin"
    SYSTEM = "system"


class SessionPrincipal(StrEnum):
    """Signed-session identity category; scopes are always reloaded server-side."""

    CUSTOMER = "customer"
    STAFF = "staff"
    PLATFORM = "platform"


class ConversationState(StrEnum):
    """Booking-bot finite state namespace."""

    IDLE = "idle"
    LOCALE = "locale"
    CONTACT = "contact"
    BRANCH = "branch"
    CATEGORY = "category"
    SERVICE = "service"
    SPECIALIST = "specialist"
    DATE = "date"
    SLOT = "slot"
    CONFIRM = "confirm"
    RESCHEDULE_SLOT = "reschedule_slot"
    RESCHEDULE_CONFIRM = "reschedule_confirm"
    STAFF_CANCEL_REASON = "staff_cancel_reason"
