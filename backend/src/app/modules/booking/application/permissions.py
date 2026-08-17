"""Central booking permission registry and stable built-in role definitions.

Persistence seed code, access resolution, services, HTTP, and tests all import these stable codes
instead of inventing permission strings at call sites.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from app.modules.booking.domain.enums import AccessRole, AccessScope, BuiltInRole
from app.modules.booking.domain.errors import BookingDomainError, BookingErrorCode


class PermissionCode(StrEnum):
    """Stable tenant permission codes. Platform authority is intentionally absent."""

    ORGANIZATION_SETTINGS_VIEW = "organization.settings.view"
    ORGANIZATION_SETTINGS_MANAGE = "organization.settings.manage"
    ORGANIZATION_BILLING_VIEW = "organization.billing.view"
    ORGANIZATION_BILLING_MANAGE = "organization.billing.manage"
    ORGANIZATION_OWNERSHIP_TRANSFER = "organization.ownership.transfer"

    ACCESS_MEMBERS_VIEW = "access.members.view"
    ACCESS_MEMBERS_INVITE = "access.members.invite"
    ACCESS_MEMBERS_MANAGE = "access.members.manage"
    ACCESS_MEMBERS_DEACTIVATE = "access.members.deactivate"
    ACCESS_ROLES_VIEW = "access.roles.view"
    ACCESS_ROLES_MANAGE = "access.roles.manage"
    ACCESS_ROLES_ASSIGN = "access.roles.assign"
    ACCESS_BIND_CODES_VIEW = "access.bind_codes.view"
    ACCESS_BIND_CODES_CREATE = "access.bind_codes.create"
    ACCESS_BIND_CODES_REVOKE = "access.bind_codes.revoke"
    AUDIT_VIEW = "audit.view"

    BRANCHES_VIEW = "branches.view"
    BRANCHES_CREATE = "branches.create"
    BRANCHES_UPDATE = "branches.update"
    BRANCHES_DELETE = "branches.delete"

    CATEGORIES_VIEW = "categories.view"
    CATEGORIES_MANAGE = "categories.manage"
    SERVICES_VIEW = "services.view"
    SERVICES_MANAGE = "services.manage"
    SERVICES_PRICES_MANAGE = "services.prices.manage"

    STAFF_VIEW = "staff.view"
    STAFF_MANAGE = "staff.manage"
    AVAILABILITY_VIEW = "availability.view"
    AVAILABILITY_MANAGE = "availability.manage"
    AVAILABILITY_EXCEPTIONS_MANAGE = "availability.exceptions.manage"
    AVAILABILITY_OVERRIDE = "availability.override"

    BOOKINGS_VIEW = "bookings.view"
    BOOKINGS_CREATE = "bookings.create"
    BOOKINGS_UPDATE = "bookings.update"
    BOOKINGS_CONFIRM = "bookings.confirm"
    BOOKINGS_RESCHEDULE = "bookings.reschedule"
    BOOKINGS_CANCEL = "bookings.cancel"
    BOOKINGS_CHECK_IN = "bookings.check_in"
    BOOKINGS_COMPLETE = "bookings.complete"
    BOOKINGS_NO_SHOW = "bookings.no_show"
    BOOKINGS_OVERRIDE = "bookings.override"
    BOOKINGS_NOTES_VIEW = "bookings.notes.view"
    BOOKINGS_NOTES_MANAGE = "bookings.notes.manage"

    CLIENTS_VIEW = "clients.view"
    CLIENTS_CREATE = "clients.create"
    CLIENTS_UPDATE = "clients.update"
    CLIENTS_VIEW_SENSITIVE = "clients.view_sensitive"
    CLIENTS_EXPORT = "clients.export"
    CLIENTS_ANONYMIZE = "clients.anonymize"

    CASH_SHIFTS_VIEW = "cash.shifts.view"
    CASH_SHIFTS_OPEN = "cash.shifts.open"
    CASH_SHIFTS_CLOSE = "cash.shifts.close"
    CASH_SHIFTS_MANAGE_OTHERS = "cash.shifts.manage_others"
    CASH_PAYMENTS_VIEW = "cash.payments.view"
    CASH_PAYMENTS_CREATE = "cash.payments.create"
    CASH_REFUNDS_CREATE = "cash.refunds.create"
    CASH_REFUNDS_APPROVE = "cash.refunds.approve"
    CASH_LEDGER_VIEW = "cash.ledger.view"
    CASH_LEDGER_MANUAL_ENTRY = "cash.ledger.manual_entry"

    INVENTORY_PRODUCTS_VIEW = "inventory.products.view"
    INVENTORY_PRODUCTS_MANAGE = "inventory.products.manage"
    INVENTORY_STOCK_VIEW = "inventory.stock.view"
    INVENTORY_STOCK_ADJUST = "inventory.stock.adjust"
    INVENTORY_MOVEMENTS_VIEW = "inventory.movements.view"
    INVENTORY_MOVEMENTS_CREATE = "inventory.movements.create"
    INVENTORY_CONSUMPTION_VIEW = "inventory.consumption.view"
    INVENTORY_CONSUMPTION_OVERRIDE = "inventory.consumption.override"

    ANALYTICS_BOOKINGS_VIEW = "analytics.bookings.view"
    ANALYTICS_FINANCE_VIEW = "analytics.finance.view"
    ANALYTICS_STAFF_VIEW = "analytics.staff.view"
    ANALYTICS_INVENTORY_VIEW = "analytics.inventory.view"
    ANALYTICS_PERSONAL_VIEW = "analytics.personal.view"
    ANALYTICS_EXPORT = "analytics.export"


class BookingPermission(StrEnum):
    """Compatibility names for current service call sites during the RBAC migration."""

    SETTINGS_MANAGE = PermissionCode.ORGANIZATION_SETTINGS_MANAGE.value
    BRANCHES_MANAGE = PermissionCode.BRANCHES_UPDATE.value
    SERVICES_MANAGE = PermissionCode.SERVICES_MANAGE.value
    SPECIALISTS_MANAGE = PermissionCode.STAFF_MANAGE.value
    SCHEDULES_MANAGE = PermissionCode.AVAILABILITY_MANAGE.value
    APPOINTMENTS_CREATE = PermissionCode.BOOKINGS_CREATE.value
    APPOINTMENTS_VIEW_ALL = PermissionCode.BOOKINGS_VIEW.value
    APPOINTMENTS_VIEW_OWN = PermissionCode.BOOKINGS_VIEW.value
    APPOINTMENTS_RESCHEDULE = PermissionCode.BOOKINGS_RESCHEDULE.value
    APPOINTMENTS_CANCEL = PermissionCode.BOOKINGS_CANCEL.value
    APPOINTMENTS_OVERRIDE_RULES = PermissionCode.BOOKINGS_OVERRIDE.value
    APPOINTMENTS_CONFIRM = PermissionCode.BOOKINGS_CONFIRM.value
    APPOINTMENTS_CHECK_IN = PermissionCode.BOOKINGS_CHECK_IN.value
    APPOINTMENTS_COMPLETE = PermissionCode.BOOKINGS_COMPLETE.value
    APPOINTMENTS_NO_SHOW = PermissionCode.BOOKINGS_NO_SHOW.value
    CUSTOMERS_VIEW = PermissionCode.CLIENTS_VIEW.value
    CUSTOMERS_MANAGE = PermissionCode.CLIENTS_UPDATE.value
    CASH_VIEW = PermissionCode.CASH_PAYMENTS_VIEW.value
    CASH_MANAGE = PermissionCode.CASH_PAYMENTS_CREATE.value
    INVENTORY_VIEW = PermissionCode.INVENTORY_STOCK_VIEW.value
    INVENTORY_MANAGE = PermissionCode.INVENTORY_MOVEMENTS_CREATE.value
    ANALYTICS_VIEW = PermissionCode.ANALYTICS_BOOKINGS_VIEW.value
    STAFF_BIND = PermissionCode.ACCESS_BIND_CODES_CREATE.value


@dataclass(frozen=True, slots=True)
class PermissionDefinitionSpec:
    """Metadata persisted into the central permission registry."""

    code: PermissionCode
    name: str
    description: str
    category: str
    allowed_scopes: frozenset[AccessScope]
    is_sensitive: bool = False


_ORG: Final = frozenset({AccessScope.ORGANIZATION})
_ORG_BRANCH: Final = frozenset({AccessScope.ORGANIZATION, AccessScope.BRANCH})
_ORG_BRANCH_SELF: Final = frozenset(
    {AccessScope.ORGANIZATION, AccessScope.BRANCH, AccessScope.SELF}
)


def _definition(
    code: PermissionCode,
    *,
    category: str,
    scopes: frozenset[AccessScope],
    sensitive: bool = False,
) -> PermissionDefinitionSpec:
    """Build one terse, centrally owned registry definition."""

    return PermissionDefinitionSpec(
        code=code,
        name=code.value,
        description=f"Allows {code.value}.",
        category=category,
        allowed_scopes=scopes,
        is_sensitive=sensitive,
    )


PERMISSION_DEFINITIONS: Final[tuple[PermissionDefinitionSpec, ...]] = (
    _definition(PermissionCode.ORGANIZATION_SETTINGS_VIEW, category="organization", scopes=_ORG),
    _definition(
        PermissionCode.ORGANIZATION_SETTINGS_MANAGE,
        category="organization",
        scopes=_ORG,
        sensitive=True,
    ),
    _definition(PermissionCode.ORGANIZATION_BILLING_VIEW, category="organization", scopes=_ORG),
    _definition(
        PermissionCode.ORGANIZATION_BILLING_MANAGE,
        category="organization",
        scopes=_ORG,
        sensitive=True,
    ),
    _definition(
        PermissionCode.ORGANIZATION_OWNERSHIP_TRANSFER,
        category="organization",
        scopes=_ORG,
        sensitive=True,
    ),
    _definition(PermissionCode.ACCESS_MEMBERS_VIEW, category="access", scopes=_ORG_BRANCH),
    _definition(PermissionCode.ACCESS_MEMBERS_INVITE, category="access", scopes=_ORG_BRANCH),
    _definition(
        PermissionCode.ACCESS_MEMBERS_MANAGE, category="access", scopes=_ORG, sensitive=True
    ),
    _definition(
        PermissionCode.ACCESS_MEMBERS_DEACTIVATE, category="access", scopes=_ORG, sensitive=True
    ),
    _definition(PermissionCode.ACCESS_ROLES_VIEW, category="access", scopes=_ORG_BRANCH),
    _definition(PermissionCode.ACCESS_ROLES_MANAGE, category="access", scopes=_ORG, sensitive=True),
    _definition(
        PermissionCode.ACCESS_ROLES_ASSIGN, category="access", scopes=_ORG_BRANCH, sensitive=True
    ),
    _definition(PermissionCode.ACCESS_BIND_CODES_VIEW, category="access", scopes=_ORG_BRANCH),
    _definition(
        PermissionCode.ACCESS_BIND_CODES_CREATE,
        category="access",
        scopes=_ORG_BRANCH,
        sensitive=True,
    ),
    _definition(
        PermissionCode.ACCESS_BIND_CODES_REVOKE,
        category="access",
        scopes=_ORG_BRANCH,
        sensitive=True,
    ),
    _definition(PermissionCode.AUDIT_VIEW, category="audit", scopes=_ORG_BRANCH, sensitive=True),
    _definition(PermissionCode.BRANCHES_VIEW, category="branches", scopes=_ORG_BRANCH),
    _definition(PermissionCode.BRANCHES_CREATE, category="branches", scopes=_ORG),
    _definition(PermissionCode.BRANCHES_UPDATE, category="branches", scopes=_ORG_BRANCH),
    _definition(
        PermissionCode.BRANCHES_DELETE, category="branches", scopes=_ORG_BRANCH, sensitive=True
    ),
    _definition(PermissionCode.CATEGORIES_VIEW, category="catalog", scopes=_ORG),
    _definition(PermissionCode.CATEGORIES_MANAGE, category="catalog", scopes=_ORG),
    _definition(PermissionCode.SERVICES_VIEW, category="catalog", scopes=_ORG_BRANCH),
    _definition(PermissionCode.SERVICES_MANAGE, category="catalog", scopes=_ORG),
    _definition(
        PermissionCode.SERVICES_PRICES_MANAGE, category="catalog", scopes=_ORG, sensitive=True
    ),
    _definition(PermissionCode.STAFF_VIEW, category="staff", scopes=_ORG_BRANCH_SELF),
    _definition(PermissionCode.STAFF_MANAGE, category="staff", scopes=_ORG_BRANCH),
    _definition(PermissionCode.AVAILABILITY_VIEW, category="availability", scopes=_ORG_BRANCH_SELF),
    _definition(PermissionCode.AVAILABILITY_MANAGE, category="availability", scopes=_ORG_BRANCH),
    _definition(
        PermissionCode.AVAILABILITY_EXCEPTIONS_MANAGE, category="availability", scopes=_ORG_BRANCH
    ),
    _definition(
        PermissionCode.AVAILABILITY_OVERRIDE,
        category="availability",
        scopes=_ORG_BRANCH,
        sensitive=True,
    ),
    _definition(PermissionCode.BOOKINGS_VIEW, category="bookings", scopes=_ORG_BRANCH_SELF),
    _definition(PermissionCode.BOOKINGS_CREATE, category="bookings", scopes=_ORG_BRANCH),
    _definition(PermissionCode.BOOKINGS_UPDATE, category="bookings", scopes=_ORG_BRANCH_SELF),
    _definition(PermissionCode.BOOKINGS_CONFIRM, category="bookings", scopes=_ORG_BRANCH_SELF),
    _definition(PermissionCode.BOOKINGS_RESCHEDULE, category="bookings", scopes=_ORG_BRANCH_SELF),
    _definition(PermissionCode.BOOKINGS_CANCEL, category="bookings", scopes=_ORG_BRANCH_SELF),
    _definition(PermissionCode.BOOKINGS_CHECK_IN, category="bookings", scopes=_ORG_BRANCH_SELF),
    _definition(PermissionCode.BOOKINGS_COMPLETE, category="bookings", scopes=_ORG_BRANCH_SELF),
    _definition(PermissionCode.BOOKINGS_NO_SHOW, category="bookings", scopes=_ORG_BRANCH_SELF),
    _definition(
        PermissionCode.BOOKINGS_OVERRIDE, category="bookings", scopes=_ORG_BRANCH, sensitive=True
    ),
    _definition(PermissionCode.BOOKINGS_NOTES_VIEW, category="bookings", scopes=_ORG_BRANCH_SELF),
    _definition(PermissionCode.BOOKINGS_NOTES_MANAGE, category="bookings", scopes=_ORG_BRANCH_SELF),
    _definition(PermissionCode.CLIENTS_VIEW, category="clients", scopes=_ORG_BRANCH_SELF),
    _definition(PermissionCode.CLIENTS_CREATE, category="clients", scopes=_ORG_BRANCH),
    _definition(PermissionCode.CLIENTS_UPDATE, category="clients", scopes=_ORG_BRANCH),
    _definition(
        PermissionCode.CLIENTS_VIEW_SENSITIVE,
        category="clients",
        scopes=_ORG_BRANCH_SELF,
        sensitive=True,
    ),
    _definition(PermissionCode.CLIENTS_EXPORT, category="clients", scopes=_ORG, sensitive=True),
    _definition(PermissionCode.CLIENTS_ANONYMIZE, category="clients", scopes=_ORG, sensitive=True),
    _definition(PermissionCode.CASH_SHIFTS_VIEW, category="cash", scopes=_ORG_BRANCH_SELF),
    _definition(PermissionCode.CASH_SHIFTS_OPEN, category="cash", scopes=_ORG_BRANCH),
    _definition(PermissionCode.CASH_SHIFTS_CLOSE, category="cash", scopes=_ORG_BRANCH_SELF),
    _definition(
        PermissionCode.CASH_SHIFTS_MANAGE_OTHERS,
        category="cash",
        scopes=_ORG_BRANCH,
        sensitive=True,
    ),
    _definition(PermissionCode.CASH_PAYMENTS_VIEW, category="cash", scopes=_ORG_BRANCH),
    _definition(PermissionCode.CASH_PAYMENTS_CREATE, category="cash", scopes=_ORG_BRANCH),
    _definition(
        PermissionCode.CASH_REFUNDS_CREATE, category="cash", scopes=_ORG_BRANCH, sensitive=True
    ),
    _definition(
        PermissionCode.CASH_REFUNDS_APPROVE, category="cash", scopes=_ORG_BRANCH, sensitive=True
    ),
    _definition(PermissionCode.CASH_LEDGER_VIEW, category="cash", scopes=_ORG_BRANCH),
    _definition(
        PermissionCode.CASH_LEDGER_MANUAL_ENTRY, category="cash", scopes=_ORG_BRANCH, sensitive=True
    ),
    _definition(PermissionCode.INVENTORY_PRODUCTS_VIEW, category="inventory", scopes=_ORG_BRANCH),
    _definition(PermissionCode.INVENTORY_PRODUCTS_MANAGE, category="inventory", scopes=_ORG_BRANCH),
    _definition(PermissionCode.INVENTORY_STOCK_VIEW, category="inventory", scopes=_ORG_BRANCH),
    _definition(
        PermissionCode.INVENTORY_STOCK_ADJUST,
        category="inventory",
        scopes=_ORG_BRANCH,
        sensitive=True,
    ),
    _definition(PermissionCode.INVENTORY_MOVEMENTS_VIEW, category="inventory", scopes=_ORG_BRANCH),
    _definition(
        PermissionCode.INVENTORY_MOVEMENTS_CREATE, category="inventory", scopes=_ORG_BRANCH
    ),
    _definition(
        PermissionCode.INVENTORY_CONSUMPTION_VIEW, category="inventory", scopes=_ORG_BRANCH
    ),
    _definition(
        PermissionCode.INVENTORY_CONSUMPTION_OVERRIDE,
        category="inventory",
        scopes=_ORG_BRANCH,
        sensitive=True,
    ),
    _definition(PermissionCode.ANALYTICS_BOOKINGS_VIEW, category="analytics", scopes=_ORG_BRANCH),
    _definition(PermissionCode.ANALYTICS_FINANCE_VIEW, category="analytics", scopes=_ORG_BRANCH),
    _definition(PermissionCode.ANALYTICS_STAFF_VIEW, category="analytics", scopes=_ORG_BRANCH_SELF),
    _definition(PermissionCode.ANALYTICS_INVENTORY_VIEW, category="analytics", scopes=_ORG_BRANCH),
    _definition(
        PermissionCode.ANALYTICS_PERSONAL_VIEW, category="analytics", scopes=_ORG_BRANCH_SELF
    ),
    _definition(
        PermissionCode.ANALYTICS_EXPORT, category="analytics", scopes=_ORG_BRANCH, sensitive=True
    ),
)

PERMISSION_BY_CODE: Final[dict[PermissionCode, PermissionDefinitionSpec]] = {
    definition.code: definition for definition in PERMISSION_DEFINITIONS
}


@dataclass(frozen=True, slots=True)
class BuiltInRoleDefinition:
    """A non-editable role template applied by the idempotent RBAC synchronizer."""

    code: BuiltInRole
    name: str
    description: str
    permissions: frozenset[PermissionCode]
    default_scope: AccessScope


_ALL_PERMISSIONS: Final[frozenset[PermissionCode]] = frozenset(PERMISSION_BY_CODE)

_BRANCH_MANAGER_PERMISSIONS: Final[frozenset[PermissionCode]] = frozenset(
    {
        PermissionCode.BRANCHES_VIEW,
        PermissionCode.BRANCHES_UPDATE,
        PermissionCode.SERVICES_VIEW,
        PermissionCode.STAFF_VIEW,
        PermissionCode.STAFF_MANAGE,
        PermissionCode.AVAILABILITY_VIEW,
        PermissionCode.AVAILABILITY_MANAGE,
        PermissionCode.AVAILABILITY_EXCEPTIONS_MANAGE,
        PermissionCode.BOOKINGS_VIEW,
        PermissionCode.BOOKINGS_CREATE,
        PermissionCode.BOOKINGS_UPDATE,
        PermissionCode.BOOKINGS_CONFIRM,
        PermissionCode.BOOKINGS_RESCHEDULE,
        PermissionCode.BOOKINGS_CANCEL,
        PermissionCode.BOOKINGS_CHECK_IN,
        PermissionCode.BOOKINGS_COMPLETE,
        PermissionCode.BOOKINGS_NO_SHOW,
        PermissionCode.CLIENTS_VIEW,
        PermissionCode.CLIENTS_CREATE,
        PermissionCode.CLIENTS_UPDATE,
        PermissionCode.CASH_SHIFTS_VIEW,
        PermissionCode.CASH_SHIFTS_OPEN,
        PermissionCode.CASH_SHIFTS_CLOSE,
        PermissionCode.CASH_SHIFTS_MANAGE_OTHERS,
        PermissionCode.CASH_PAYMENTS_VIEW,
        PermissionCode.CASH_PAYMENTS_CREATE,
        PermissionCode.CASH_REFUNDS_CREATE,
        PermissionCode.CASH_LEDGER_VIEW,
        PermissionCode.CASH_LEDGER_MANUAL_ENTRY,
        PermissionCode.INVENTORY_PRODUCTS_VIEW,
        PermissionCode.INVENTORY_STOCK_VIEW,
        PermissionCode.INVENTORY_STOCK_ADJUST,
        PermissionCode.INVENTORY_MOVEMENTS_VIEW,
        PermissionCode.INVENTORY_MOVEMENTS_CREATE,
        PermissionCode.INVENTORY_CONSUMPTION_VIEW,
        PermissionCode.ANALYTICS_BOOKINGS_VIEW,
        PermissionCode.ANALYTICS_STAFF_VIEW,
        PermissionCode.ANALYTICS_INVENTORY_VIEW,
        PermissionCode.ACCESS_MEMBERS_VIEW,
        PermissionCode.ACCESS_MEMBERS_INVITE,
        PermissionCode.ACCESS_ROLES_VIEW,
        PermissionCode.ACCESS_ROLES_ASSIGN,
        PermissionCode.ACCESS_BIND_CODES_VIEW,
        PermissionCode.ACCESS_BIND_CODES_CREATE,
        PermissionCode.ACCESS_BIND_CODES_REVOKE,
        PermissionCode.AUDIT_VIEW,
    }
)

_RECEPTIONIST_PERMISSIONS: Final[frozenset[PermissionCode]] = frozenset(
    {
        PermissionCode.BRANCHES_VIEW,
        PermissionCode.CATEGORIES_VIEW,
        PermissionCode.SERVICES_VIEW,
        PermissionCode.STAFF_VIEW,
        PermissionCode.AVAILABILITY_VIEW,
        PermissionCode.BOOKINGS_VIEW,
        PermissionCode.BOOKINGS_CREATE,
        PermissionCode.BOOKINGS_CONFIRM,
        PermissionCode.BOOKINGS_RESCHEDULE,
        PermissionCode.BOOKINGS_CANCEL,
        PermissionCode.BOOKINGS_CHECK_IN,
        PermissionCode.BOOKINGS_NO_SHOW,
        PermissionCode.CLIENTS_VIEW,
        PermissionCode.CLIENTS_CREATE,
        PermissionCode.CLIENTS_UPDATE,
        PermissionCode.CASH_PAYMENTS_VIEW,
    }
)

_CASHIER_PERMISSIONS: Final[frozenset[PermissionCode]] = frozenset(
    {
        PermissionCode.BOOKINGS_VIEW,
        PermissionCode.CASH_SHIFTS_VIEW,
        PermissionCode.CASH_SHIFTS_OPEN,
        PermissionCode.CASH_SHIFTS_CLOSE,
        PermissionCode.CASH_PAYMENTS_VIEW,
        PermissionCode.CASH_PAYMENTS_CREATE,
        PermissionCode.CASH_REFUNDS_CREATE,
        PermissionCode.CASH_LEDGER_VIEW,
    }
)

_SPECIALIST_PERMISSIONS: Final[frozenset[PermissionCode]] = frozenset(
    {
        PermissionCode.STAFF_VIEW,
        PermissionCode.AVAILABILITY_VIEW,
        PermissionCode.BOOKINGS_VIEW,
        PermissionCode.BOOKINGS_CONFIRM,
        PermissionCode.BOOKINGS_CHECK_IN,
        PermissionCode.BOOKINGS_COMPLETE,
        PermissionCode.BOOKINGS_NO_SHOW,
        PermissionCode.BOOKINGS_CANCEL,
        PermissionCode.BOOKINGS_NOTES_VIEW,
        PermissionCode.BOOKINGS_NOTES_MANAGE,
        PermissionCode.CLIENTS_VIEW,
        PermissionCode.INVENTORY_CONSUMPTION_VIEW,
        PermissionCode.ANALYTICS_PERSONAL_VIEW,
    }
)

_INVENTORY_MANAGER_PERMISSIONS: Final[frozenset[PermissionCode]] = frozenset(
    {
        PermissionCode.INVENTORY_PRODUCTS_VIEW,
        PermissionCode.INVENTORY_PRODUCTS_MANAGE,
        PermissionCode.INVENTORY_STOCK_VIEW,
        PermissionCode.INVENTORY_STOCK_ADJUST,
        PermissionCode.INVENTORY_MOVEMENTS_VIEW,
        PermissionCode.INVENTORY_MOVEMENTS_CREATE,
        PermissionCode.INVENTORY_CONSUMPTION_VIEW,
        PermissionCode.INVENTORY_CONSUMPTION_OVERRIDE,
        PermissionCode.ANALYTICS_INVENTORY_VIEW,
    }
)

_ACCOUNTANT_PERMISSIONS: Final[frozenset[PermissionCode]] = frozenset(
    {
        PermissionCode.BOOKINGS_VIEW,
        PermissionCode.CASH_SHIFTS_VIEW,
        PermissionCode.CASH_SHIFTS_MANAGE_OTHERS,
        PermissionCode.CASH_PAYMENTS_VIEW,
        PermissionCode.CASH_REFUNDS_CREATE,
        PermissionCode.CASH_REFUNDS_APPROVE,
        PermissionCode.CASH_LEDGER_VIEW,
        PermissionCode.CASH_LEDGER_MANUAL_ENTRY,
        PermissionCode.ANALYTICS_BOOKINGS_VIEW,
        PermissionCode.ANALYTICS_FINANCE_VIEW,
        PermissionCode.ANALYTICS_EXPORT,
        PermissionCode.AUDIT_VIEW,
    }
)

_ANALYST_PERMISSIONS: Final[frozenset[PermissionCode]] = frozenset(
    {
        PermissionCode.ANALYTICS_BOOKINGS_VIEW,
        PermissionCode.ANALYTICS_STAFF_VIEW,
        PermissionCode.ANALYTICS_INVENTORY_VIEW,
    }
)

_AUDITOR_PERMISSIONS: Final[frozenset[PermissionCode]] = frozenset(
    {
        PermissionCode.BOOKINGS_VIEW,
        PermissionCode.CASH_SHIFTS_VIEW,
        PermissionCode.CASH_PAYMENTS_VIEW,
        PermissionCode.CASH_LEDGER_VIEW,
        PermissionCode.INVENTORY_PRODUCTS_VIEW,
        PermissionCode.INVENTORY_STOCK_VIEW,
        PermissionCode.INVENTORY_MOVEMENTS_VIEW,
        PermissionCode.INVENTORY_CONSUMPTION_VIEW,
        PermissionCode.AUDIT_VIEW,
    }
)

BUILTIN_ROLE_DEFINITIONS: Final[tuple[BuiltInRoleDefinition, ...]] = (
    BuiltInRoleDefinition(
        BuiltInRole.OWNER,
        "Owner",
        "All tenant permissions, never platform authority.",
        _ALL_PERMISSIONS,
        AccessScope.ORGANIZATION,
    ),
    BuiltInRoleDefinition(
        BuiltInRole.ADMIN,
        "Administrator",
        "Daily tenant administrator without ownership transfer.",
        _ALL_PERMISSIONS - {PermissionCode.ORGANIZATION_OWNERSHIP_TRANSFER},
        AccessScope.ORGANIZATION,
    ),
    BuiltInRoleDefinition(
        BuiltInRole.BRANCH_MANAGER,
        "Branch manager",
        "Operational manager restricted to assigned branches.",
        _BRANCH_MANAGER_PERMISSIONS,
        AccessScope.BRANCH,
    ),
    BuiltInRoleDefinition(
        BuiltInRole.RECEPTIONIST,
        "Receptionist",
        "Booking desk operator restricted to assigned branches.",
        _RECEPTIONIST_PERMISSIONS,
        AccessScope.BRANCH,
    ),
    BuiltInRoleDefinition(
        BuiltInRole.CASHIER,
        "Cashier",
        "Payment operator restricted to assigned branches and own shifts.",
        _CASHIER_PERMISSIONS,
        AccessScope.BRANCH,
    ),
    BuiltInRoleDefinition(
        BuiltInRole.SPECIALIST,
        "Specialist",
        "Service provider restricted to their own appointments.",
        _SPECIALIST_PERMISSIONS,
        AccessScope.SELF,
    ),
    BuiltInRoleDefinition(
        BuiltInRole.INVENTORY_MANAGER,
        "Inventory manager",
        "Stock operator restricted to assigned branches.",
        _INVENTORY_MANAGER_PERMISSIONS,
        AccessScope.BRANCH,
    ),
    BuiltInRoleDefinition(
        BuiltInRole.ACCOUNTANT,
        "Accountant",
        "Finance reader/operator limited by assignment scope.",
        _ACCOUNTANT_PERMISSIONS,
        AccessScope.ORGANIZATION,
    ),
    BuiltInRoleDefinition(
        BuiltInRole.ANALYST,
        "Analyst",
        "Read-only aggregate analytics role.",
        _ANALYST_PERMISSIONS,
        AccessScope.ORGANIZATION,
    ),
    BuiltInRoleDefinition(
        BuiltInRole.AUDITOR,
        "Auditor",
        "Read-only operational and audit-trail role.",
        _AUDITOR_PERMISSIONS,
        AccessScope.ORGANIZATION,
    ),
)

BUILTIN_ROLE_BY_CODE: Final[dict[BuiltInRole, BuiltInRoleDefinition]] = {
    definition.code: definition for definition in BUILTIN_ROLE_DEFINITIONS
}

SAFE_BRANCH_MANAGER_ROLE_CODES: Final[frozenset[BuiltInRole]] = frozenset(
    {
        BuiltInRole.RECEPTIONIST,
        BuiltInRole.CASHIER,
        BuiltInRole.SPECIALIST,
        BuiltInRole.INVENTORY_MANAGER,
        BuiltInRole.ANALYST,
    }
)

LEGACY_ROLE_TO_BUILTIN_ROLE: Final[dict[AccessRole, BuiltInRole]] = {
    AccessRole.OWNER: BuiltInRole.OWNER,
    AccessRole.ADMIN: BuiltInRole.ADMIN,
    AccessRole.BRANCH_MANAGER: BuiltInRole.BRANCH_MANAGER,
    AccessRole.RECEPTIONIST: BuiltInRole.RECEPTIONIST,
    AccessRole.SPECIALIST: BuiltInRole.SPECIALIST,
    AccessRole.CASHIER: BuiltInRole.CASHIER,
    AccessRole.WAREHOUSE_MANAGER: BuiltInRole.INVENTORY_MANAGER,
    AccessRole.INVENTORY_MANAGER: BuiltInRole.INVENTORY_MANAGER,
    AccessRole.ACCOUNTANT: BuiltInRole.ACCOUNTANT,
    AccessRole.ANALYST: BuiltInRole.ANALYST,
    AccessRole.AUDITOR: BuiltInRole.AUDITOR,
}


def normalize_permission(code: PermissionCode | BookingPermission | str) -> PermissionCode:
    """Normalize only registry codes and compatibility enum values into a stable code."""

    raw = code.value if isinstance(code, StrEnum) else code
    try:
        return PermissionCode(raw)
    except ValueError as error:
        raise BookingDomainError(BookingErrorCode.FORBIDDEN) from error


def permission_definition(
    code: PermissionCode | BookingPermission | str,
) -> PermissionDefinitionSpec:
    """Resolve a canonical registry permission and reject arbitrary strings."""

    return PERMISSION_BY_CODE[normalize_permission(code)]


def effective_permissions(
    *,
    role: AccessRole,
    explicit_permissions: frozenset[str],
) -> frozenset[BookingPermission]:
    """Read legacy grant rows during migration; new authorization does not call this helper."""

    defaults: set[BookingPermission]
    if role is AccessRole.CUSTOMER:
        defaults = {
            BookingPermission.APPOINTMENTS_CREATE,
            BookingPermission.APPOINTMENTS_VIEW_OWN,
            BookingPermission.APPOINTMENTS_RESCHEDULE,
            BookingPermission.APPOINTMENTS_CANCEL,
        }
    else:
        built_in = LEGACY_ROLE_TO_BUILTIN_ROLE.get(role)
        legacy_values = {permission.value for permission in BookingPermission}
        defaults = (
            {
                BookingPermission(permission.value)
                for permission in BUILTIN_ROLE_BY_CODE[built_in].permissions
                if permission.value in legacy_values
            }
            if built_in is not None
            else set[BookingPermission]()
        )
    defaults.update(
        permission for permission in BookingPermission if permission.value in explicit_permissions
    )
    return frozenset(defaults)


def require_permission(
    granted: frozenset[PermissionCode | BookingPermission | str],
    permission: PermissionCode | BookingPermission | str,
) -> None:
    """Compatibility guard for callers with already-materialized canonical grants."""

    canonical = normalize_permission(permission)
    if canonical not in {normalize_permission(value) for value in granted}:
        raise BookingDomainError(BookingErrorCode.FORBIDDEN)
