"""Provision one booking tenant and one-time owner bind code through an explicit ops command."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import re
import secrets
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from app.core.bots.ids import BotAppId
from app.core.config.settings import Settings
from app.core.db.database import Database
from app.modules.booking.application.access import RbacSynchronizer
from app.modules.booking.application.audit import append_audit_event
from app.modules.booking.domain.enums import AccessScope, ActorType, BuiltInRole
from app.modules.booking.infrastructure.persistence.models import (
    BookingMembership,
    BookingOrganization,
    BookingRole,
    BookingRoleAssignment,
    BookingSettings,
    BookingTelegramBotInstallation,
    Specialist,
    StaffBindCode,
)

_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
_CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")


class ProvisioningError(RuntimeError):
    """A safe operator-facing refusal that never includes database credentials or tokens."""


@dataclass(frozen=True, slots=True)
class ProvisionCommand:
    """Validated, intentionally small set of inputs needed for first tenant ownership."""

    organization_slug: str
    organization_name: str
    bot_app_id: BotAppId
    owner_display_name: str
    timezone: str
    currency: str
    bind_ttl_seconds: int


@dataclass(frozen=True, slots=True)
class ProvisionResult:
    """Non-secret identifiers plus the one-time owner bind code returned only to the operator."""

    organization_id: str
    organization_slug: str
    bot_app_id: str
    owner_specialist_id: str
    bind_code: str
    bind_code_expires_at: datetime


def _parse_command(arguments: Sequence[str] | None = None) -> ProvisionCommand:
    """Parse and locally validate operator input before opening a database connection."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--organization-slug", required=True)
    parser.add_argument("--organization-name", required=True)
    parser.add_argument("--owner-display-name", required=True)
    parser.add_argument("--bot-app-id", default="booking_bot")
    parser.add_argument("--timezone", default="UTC")
    parser.add_argument("--currency", default="UZS")
    parser.add_argument("--bind-ttl-seconds", type=int, default=900)
    parsed = parser.parse_args(arguments)

    slug = str(parsed.organization_slug).strip().lower()
    name = str(parsed.organization_name).strip()
    owner_display_name = str(parsed.owner_display_name).strip()
    timezone = str(parsed.timezone).strip()
    currency = str(parsed.currency).strip().upper()
    if not _SLUG_PATTERN.fullmatch(slug):
        parser.error("--organization-slug must use lowercase letters, digits, and hyphens.")
    if not name or len(name) > 200:
        parser.error("--organization-name must contain 1 to 200 characters.")
    if not owner_display_name or len(owner_display_name) > 200:
        parser.error("--owner-display-name must contain 1 to 200 characters.")
    if not _CURRENCY_PATTERN.fullmatch(currency):
        parser.error("--currency must be a three-letter uppercase ISO code.")
    if not 60 <= parsed.bind_ttl_seconds <= 86_400:
        parser.error("--bind-ttl-seconds must be between 60 and 86400.")
    try:
        ZoneInfo(timezone)
    except ZoneInfoNotFoundError:
        parser.error("--timezone must be a valid IANA timezone.")
    try:
        bot_app_id = BotAppId(str(parsed.bot_app_id))
    except ValueError as error:
        parser.error(str(error))
    return ProvisionCommand(
        organization_slug=slug,
        organization_name=name,
        bot_app_id=bot_app_id,
        owner_display_name=owner_display_name,
        timezone=timezone,
        currency=currency,
        bind_ttl_seconds=parsed.bind_ttl_seconds,
    )


async def provision(*, database: Database, command: ProvisionCommand) -> ProvisionResult:
    """Create the minimum tenant graph atomically and refuse instead of merging existing data."""

    now = datetime.now(UTC)
    raw_bind_code = secrets.token_urlsafe(18)
    code_digest = hashlib.sha256(raw_bind_code.encode("utf-8")).hexdigest()
    try:
        async with database.session() as session, session.begin():
            await RbacSynchronizer(database=database).synchronize_session(session)
            existing_organization = await session.scalar(
                sa.select(BookingOrganization.id).where(
                    BookingOrganization.slug == command.organization_slug
                )
            )
            if existing_organization is not None:
                raise ProvisioningError("A booking organization with this slug already exists.")
            existing_installation = await session.scalar(
                sa.select(BookingTelegramBotInstallation.id).where(
                    BookingTelegramBotInstallation.bot_app_id == str(command.bot_app_id)
                )
            )
            if existing_installation is not None:
                raise ProvisioningError("This booking bot app is already assigned to a tenant.")

            organization = BookingOrganization(
                slug=command.organization_slug,
                name=command.organization_name,
                default_timezone=command.timezone,
            )
            session.add(organization)
            await session.flush()

            owner = Specialist(
                organization_id=organization.id,
                display_name=command.owner_display_name,
                accepts_bookings=False,
            )
            session.add_all(
                (
                    BookingSettings(
                        organization_id=organization.id,
                        currency=command.currency,
                    ),
                    BookingTelegramBotInstallation(
                        organization_id=organization.id,
                        bot_app_id=str(command.bot_app_id),
                    ),
                    owner,
                )
            )
            await session.flush()
            owner_membership = BookingMembership(
                organization_id=organization.id,
                subject_id=owner.id,
                specialist_id=owner.id,
                display_name=owner.display_name,
                is_active=True,
                access_version=1,
            )
            session.add(owner_membership)
            owner_role = await session.scalar(
                sa.select(BookingRole).where(
                    BookingRole.organization_id.is_(None),
                    BookingRole.code == BuiltInRole.OWNER.value,
                )
            )
            if owner_role is None:
                raise ProvisioningError("Booking RBAC roles were not initialized.")
            await session.flush()
            session.add(
                BookingRoleAssignment(
                    organization_id=organization.id,
                    membership_id=owner_membership.id,
                    role_id=owner_role.id,
                    scope=AccessScope.ORGANIZATION,
                    assigned_by=owner.id,
                )
            )
            bind_code = StaffBindCode(
                organization_id=organization.id,
                specialist_id=owner.id,
                membership_id=owner_membership.id,
                code_digest=code_digest,
                expires_at=now + timedelta(seconds=command.bind_ttl_seconds),
                created_by=owner.id,
            )
            session.add(bind_code)
            append_audit_event(
                session,
                organization_id=organization.id,
                action_code="tenant.provisioned",
                actor_type=ActorType.SYSTEM,
                target_type="organization",
                target_id=organization.id,
                metadata={"bot_app_id": str(command.bot_app_id)},
            )
            await session.flush()
            return ProvisionResult(
                organization_id=str(organization.id),
                organization_slug=organization.slug,
                bot_app_id=str(command.bot_app_id),
                owner_specialist_id=str(owner.id),
                bind_code=raw_bind_code,
                bind_code_expires_at=bind_code.expires_at,
            )
    except IntegrityError as error:
        raise ProvisioningError(
            "Tenant provisioning conflicted with existing booking data."
        ) from error


async def _run(command: ProvisionCommand) -> ProvisionResult:
    """Load configuration, require a declared app ID, and release the local engine afterwards."""

    settings = Settings()
    if command.bot_app_id not in settings.bots.apps:
        raise ProvisioningError("The requested booking bot app is not declared in configuration.")
    database = Database(settings.database)
    database.initialize()
    try:
        return await provision(database=database, command=command)
    finally:
        await database.dispose()


def main(arguments: Sequence[str] | None = None) -> None:
    """Run the explicit bootstrap operation and print the one-time bind code exactly once."""

    command = _parse_command(arguments)
    try:
        result = asyncio.run(_run(command))
    except ProvisioningError as error:
        raise SystemExit(f"Booking provisioning failed: {error}") from error
    print(f"Booking tenant '{result.organization_slug}' created ({result.organization_id}).")
    print(f"Booking bot app: {result.bot_app_id}")
    print(f"Initial owner specialist: {result.owner_specialist_id}")
    print(f"Owner bind code (show once; expires {result.bind_code_expires_at.isoformat()}):")
    print(result.bind_code)


if __name__ == "__main__":
    main()
