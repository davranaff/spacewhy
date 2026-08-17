"""Database-aggregated booking analytics with tenant and local-time boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import sqlalchemy as sa

from app.core.db.database import Database
from app.modules.booking.application.access import AccessPolicy
from app.modules.booking.application.context import BookingActor
from app.modules.booking.application.dto import AnalyticsQuery
from app.modules.booking.application.permissions import PermissionCode
from app.modules.booking.domain.enums import (
    AccessScope,
    AppointmentStatus,
    AvailabilityExceptionType,
)
from app.modules.booking.domain.errors import BookingDomainError, BookingErrorCode
from app.modules.booking.infrastructure.persistence.models import (
    Appointment,
    Customer,
    Payment,
    Product,
    Refund,
    StockBalance,
    Warehouse,
)

_MAX_ANALYTICS_DAYS = 93


@dataclass(frozen=True, slots=True)
class _AnalyticsScope:
    """One permission's organization/branch/self scope projected for aggregate queries."""

    permission: PermissionCode
    branch_ids: frozenset[UUID] | None
    self_specialist_id: UUID | None


@dataclass(frozen=True, slots=True)
class _AnalyticsAccess:
    """Resolved analytics domains, each retaining its own independently assigned scope."""

    booking: _AnalyticsScope | None
    finance: _AnalyticsScope | None
    staff: _AnalyticsScope | None
    inventory: _AnalyticsScope | None


class BookingAnalyticsService:
    """Compute bounded operational metrics through grouped PostgreSQL queries, never ORM loops."""

    def __init__(self, *, database: Database) -> None:
        """Receive the application database resource through explicit composition."""

        self._database = database

    async def dashboard(
        self,
        *,
        actor: BookingActor,
        query: AnalyticsQuery,
    ) -> dict[str, Any]:
        """Return documented booking, cash, workload, customer, and inventory metrics."""

        access = resolve_analytics_access(actor)
        if query.date_to < query.date_from:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST)
        if (query.date_to - query.date_from).days > _MAX_ANALYTICS_DAYS:
            raise BookingDomainError(BookingErrorCode.BOOKING_TOO_FAR_IN_FUTURE)
        try:
            timezone = ZoneInfo(query.timezone)
        except ZoneInfoNotFoundError as error:
            raise BookingDomainError(BookingErrorCode.INVALID_REQUEST) from error
        lower_bound, upper_bound = _local_date_bounds(
            date_from=query.date_from,
            date_to=query.date_to,
            timezone=timezone,
        )
        async with self._database.session() as session:
            booking_conditions = _scoped_appointment_conditions(
                actor=actor,
                organization_id=actor.organization_id,
                query=query,
                scope=access.booking,
            )
            finance_conditions = _scoped_appointment_conditions(
                actor=actor,
                organization_id=actor.organization_id,
                query=query,
                scope=access.finance,
            )
            staff_conditions = _scoped_appointment_conditions(
                actor=actor,
                organization_id=actor.organization_id,
                query=query,
                scope=access.staff,
            )
            created = (
                await self._created_metrics(
                    session,
                    conditions=(
                        *booking_conditions,
                        Appointment.created_at >= lower_bound,
                        Appointment.created_at < upper_bound,
                    ),
                )
                if booking_conditions is not None
                else _empty_created_metrics()
            )
            completed = (
                await self._completed_metrics(
                    session,
                    conditions=(
                        *booking_conditions,
                        Appointment.completed_at >= lower_bound,
                        Appointment.completed_at < upper_bound,
                    ),
                    include_finance=False,
                )
                if booking_conditions is not None
                else _empty_completed_metrics()
            )
            finance_completed = (
                await self._completed_metrics(
                    session,
                    conditions=(
                        *finance_conditions,
                        Appointment.completed_at >= lower_bound,
                        Appointment.completed_at < upper_bound,
                    ),
                    include_finance=True,
                )
                if finance_conditions is not None
                else _empty_completed_metrics()
            )
            cash_flow = (
                await self._cash_flow(
                    session,
                    organization_id=actor.organization_id,
                    conditions=finance_conditions,
                    lower_bound=lower_bound,
                    upper_bound=upper_bound,
                )
                if finance_conditions is not None
                else {"payments": Decimal("0"), "refunds": Decimal("0")}
            )
            payment_state = (
                await self._payment_state(
                    session,
                    organization_id=actor.organization_id,
                    conditions=(
                        *finance_conditions,
                        Appointment.starts_at >= lower_bound,
                        Appointment.starts_at < upper_bound,
                    ),
                )
                if finance_conditions is not None
                else None
            )
            service_top = (
                await self._top_services(
                    session,
                    conditions=(
                        *booking_conditions,
                        Appointment.completed_at >= lower_bound,
                        Appointment.completed_at < upper_bound,
                    ),
                    include_finance=False,
                )
                if booking_conditions is not None
                else None
            )
            specialist_top = (
                await self._top_specialists(
                    session,
                    conditions=(
                        *staff_conditions,
                        Appointment.completed_at >= lower_bound,
                        Appointment.completed_at < upper_bound,
                    ),
                    include_finance=False,
                )
                if staff_conditions is not None
                else None
            )
            customer_metrics = (
                await self._customer_metrics(
                    session,
                    organization_id=actor.organization_id,
                    lower_bound=lower_bound,
                    upper_bound=upper_bound,
                    appointment_conditions=booking_conditions,
                    scope_predicate=AccessPolicy.appointment_predicate(
                        actor,
                        access.booking.permission,
                    ),
                )
                if booking_conditions is not None and access.booking is not None
                else None
            )
            busy_minutes = (
                await self._busy_minutes(
                    session,
                    conditions=(
                        *staff_conditions,
                        Appointment.starts_at >= lower_bound,
                        Appointment.starts_at < upper_bound,
                    ),
                )
                if staff_conditions is not None
                else None
            )
            available_minutes = (
                await self._available_minutes(
                    session,
                    organization_id=actor.organization_id,
                    query=query,
                    lower_bound=lower_bound,
                    upper_bound=upper_bound,
                    access=access.staff,
                )
                if access.staff is not None
                else None
            )
            low_stock = (
                await self._low_stock_products(
                    session,
                    organization_id=actor.organization_id,
                    branch_id=query.branch_id,
                    visible_branch_ids=access.inventory.branch_ids,
                )
                if access.inventory is not None
                else None
            )
            daily = (
                await self._daily_metrics(
                    session,
                    organization_id=actor.organization_id,
                    query=query,
                    lower_bound=lower_bound,
                    upper_bound=upper_bound,
                    appointment_conditions=booking_conditions,
                    include_finance=False,
                )
                if booking_conditions is not None
                else None
            )
        result: dict[str, Any] = {
            "range": {
                "date_from": query.date_from,
                "date_to": query.date_to,
                "timezone": query.timezone,
                "starts_at": lower_bound,
                "ends_at": upper_bound,
            }
        }
        if access.booking is not None:
            created_count = int(created["created_count"])
            cancelled_count = int(created["cancelled_count"])
            no_show_count = int(created["no_show_count"])
            completed_count = int(completed["completed_count"])
            resolved_visits = completed_count + no_show_count
            result["appointments"] = {
                "created": created_count,
                "confirmed": int(created["confirmed_count"]),
                "completed": completed_count,
                "cancelled": cancelled_count,
                "no_show": no_show_count,
                "cancellation_rate": _ratio(cancelled_count, created_count),
                "no_show_rate": _ratio(no_show_count, resolved_visits),
            }
            result["customers"] = customer_metrics
            result["top_services"] = service_top
            result["daily"] = daily
        if access.finance is not None:
            finance_completed_count = int(finance_completed["completed_count"])
            service_revenue = _decimal(finance_completed["service_revenue"])
            result["revenue"] = {
                "service_revenue": service_revenue,
                "average_check": (
                    (service_revenue / finance_completed_count).quantize(Decimal("0.01"))
                    if finance_completed_count
                    else Decimal("0")
                ),
                "cash_in": cash_flow["payments"],
                "cash_out": cash_flow["refunds"],
                "net_cash_flow": cash_flow["payments"] - cash_flow["refunds"],
            }
            result["payment_state"] = payment_state
        if access.staff is not None and busy_minutes is not None and available_minutes is not None:
            result["workload"] = {
                "available_minutes": available_minutes,
                "busy_minutes": busy_minutes,
                "occupancy_rate": _ratio(busy_minutes, available_minutes),
            }
            result["top_specialists"] = specialist_top
        if low_stock is not None:
            result["low_stock_products"] = low_stock
        return result

    async def _daily_metrics(
        self,
        session: Any,
        *,
        organization_id: UUID,
        query: AnalyticsQuery,
        lower_bound: datetime,
        upper_bound: datetime,
        appointment_conditions: tuple[Any, ...],
        include_finance: bool,
    ) -> list[dict[str, Any]]:
        """Return one bounded, local-date bucket per day through SQL aggregates.

        Appointment creation, completion, payments, and refunds deliberately use
        their own business timestamps.  The small merge below handles at most 94
        aggregate rows per query; it never materializes appointment or cash rows.
        """

        buckets: dict[date, dict[str, Any]] = {
            query.date_from + timedelta(days=offset): {
                "date": query.date_from + timedelta(days=offset),
                "created": 0,
                "confirmed": 0,
                "cancelled": 0,
                "no_show": 0,
                "completed": 0,
                **(
                    {
                        "service_revenue": Decimal("0"),
                        "payments": Decimal("0"),
                        "refunds": Decimal("0"),
                        "net_cash_flow": Decimal("0"),
                    }
                    if include_finance
                    else {}
                ),
            }
            for offset in range((query.date_to - query.date_from).days + 1)
        }

        created_day = _localized_date(Appointment.created_at, query.timezone).label("day")
        created_rows = (
            (
                await session.execute(
                    sa.select(
                        created_day,
                        sa.func.count(Appointment.id).label("created"),
                        sa.func.count(Appointment.id)
                        .filter(Appointment.status == AppointmentStatus.CONFIRMED)
                        .label("confirmed"),
                        sa.func.count(Appointment.id)
                        .filter(Appointment.status == AppointmentStatus.CANCELLED)
                        .label("cancelled"),
                        sa.func.count(Appointment.id)
                        .filter(Appointment.status == AppointmentStatus.NO_SHOW)
                        .label("no_show"),
                    )
                    .where(
                        *appointment_conditions,
                        Appointment.created_at >= lower_bound,
                        Appointment.created_at < upper_bound,
                    )
                    .group_by(created_day)
                    .order_by(created_day)
                )
            )
            .mappings()
            .all()
        )
        for row in created_rows:
            bucket = buckets.get(row["day"])
            if bucket is not None:
                bucket.update(
                    created=int(row["created"] or 0),
                    confirmed=int(row["confirmed"] or 0),
                    cancelled=int(row["cancelled"] or 0),
                    no_show=int(row["no_show"] or 0),
                )

        completed_day = _localized_date(Appointment.completed_at, query.timezone).label("day")
        completed_select = [
            completed_day,
            sa.func.count(Appointment.id).label("completed"),
        ]
        if include_finance:
            completed_select.append(
                sa.func.coalesce(sa.func.sum(Appointment.price_snapshot), 0).label(
                    "service_revenue"
                )
            )
        completed_rows = (
            (
                await session.execute(
                    sa.select(*completed_select)
                    .where(
                        *appointment_conditions,
                        Appointment.status == AppointmentStatus.COMPLETED,
                        Appointment.completed_at >= lower_bound,
                        Appointment.completed_at < upper_bound,
                    )
                    .group_by(completed_day)
                    .order_by(completed_day)
                )
            )
            .mappings()
            .all()
        )
        for row in completed_rows:
            bucket = buckets.get(row["day"])
            if bucket is not None:
                bucket["completed"] = int(row["completed"] or 0)
                if include_finance:
                    bucket["service_revenue"] = _decimal(row["service_revenue"])

        if include_finance:
            payment_day = _localized_date(Payment.created_at, query.timezone).label("day")
            payment_rows = (
                (
                    await session.execute(
                        sa.select(
                            payment_day,
                            sa.func.coalesce(sa.func.sum(Payment.amount), 0).label("payments"),
                        )
                        .join(Appointment, Appointment.id == Payment.appointment_id)
                        .where(
                            Payment.organization_id == organization_id,
                            Payment.created_at >= lower_bound,
                            Payment.created_at < upper_bound,
                            *appointment_conditions,
                        )
                        .group_by(payment_day)
                        .order_by(payment_day)
                    )
                )
                .mappings()
                .all()
            )
            for row in payment_rows:
                bucket = buckets.get(row["day"])
                if bucket is not None:
                    bucket["payments"] = _decimal(row["payments"])

            refund_day = _localized_date(Refund.created_at, query.timezone).label("day")
            refund_rows = (
                (
                    await session.execute(
                        sa.select(
                            refund_day,
                            sa.func.coalesce(sa.func.sum(Refund.amount), 0).label("refunds"),
                        )
                        .join(Payment, Payment.id == Refund.payment_id)
                        .join(Appointment, Appointment.id == Payment.appointment_id)
                        .where(
                            Refund.organization_id == organization_id,
                            Refund.created_at >= lower_bound,
                            Refund.created_at < upper_bound,
                            *appointment_conditions,
                        )
                        .group_by(refund_day)
                        .order_by(refund_day)
                    )
                )
                .mappings()
                .all()
            )
            for row in refund_rows:
                bucket = buckets.get(row["day"])
                if bucket is not None:
                    bucket["refunds"] = _decimal(row["refunds"])

            for bucket in buckets.values():
                bucket["net_cash_flow"] = bucket["payments"] - bucket["refunds"]
        return list(buckets.values())

    async def _created_metrics(
        self,
        session: Any,
        *,
        conditions: tuple[Any, ...],
    ) -> dict[str, Decimal | int]:
        """Aggregate creation-window lifecycle counts in one SQL query."""

        row = (
            (
                await session.execute(
                    sa.select(
                        sa.func.count(Appointment.id).label("created_count"),
                        sa.func.count(Appointment.id)
                        .filter(Appointment.status == AppointmentStatus.CONFIRMED)
                        .label("confirmed_count"),
                        sa.func.count(Appointment.id)
                        .filter(Appointment.status == AppointmentStatus.CANCELLED)
                        .label("cancelled_count"),
                        sa.func.count(Appointment.id)
                        .filter(Appointment.status == AppointmentStatus.NO_SHOW)
                        .label("no_show_count"),
                    ).where(*conditions)
                )
            )
            .mappings()
            .one()
        )
        return {
            "created_count": int(row["created_count"] or 0),
            "confirmed_count": int(row["confirmed_count"] or 0),
            "cancelled_count": int(row["cancelled_count"] or 0),
            "no_show_count": int(row["no_show_count"] or 0),
        }

    async def _completed_metrics(
        self,
        session: Any,
        *,
        conditions: tuple[Any, ...],
        include_finance: bool,
    ) -> dict[str, Decimal | int]:
        """Aggregate completed visit counts and snapshot service revenue in one SQL query."""

        columns: list[Any] = [sa.func.count(Appointment.id).label("completed_count")]
        if include_finance:
            columns.append(
                sa.func.coalesce(sa.func.sum(Appointment.price_snapshot), 0).label(
                    "service_revenue"
                )
            )
        row = (
            (
                await session.execute(
                    sa.select(*columns).where(
                        *conditions, Appointment.status == AppointmentStatus.COMPLETED
                    )
                )
            )
            .mappings()
            .one()
        )
        return {
            "completed_count": int(row["completed_count"] or 0),
            "service_revenue": _decimal(row.get("service_revenue")),
        }

    async def _cash_flow(
        self,
        session: Any,
        *,
        organization_id: UUID,
        conditions: tuple[Any, ...],
        lower_bound: datetime,
        upper_bound: datetime,
    ) -> dict[str, Decimal]:
        """Separate actual payment/refund cash dates from completed-service revenue dates."""

        payment_total = await session.scalar(
            sa.select(sa.func.coalesce(sa.func.sum(Payment.amount), 0))
            .join(Appointment, Appointment.id == Payment.appointment_id)
            .where(
                Payment.organization_id == organization_id,
                Payment.created_at >= lower_bound,
                Payment.created_at < upper_bound,
                *conditions,
            )
        )
        refund_total = await session.scalar(
            sa.select(sa.func.coalesce(sa.func.sum(Refund.amount), 0))
            .join(Payment, Payment.id == Refund.payment_id)
            .join(Appointment, Appointment.id == Payment.appointment_id)
            .where(
                Refund.organization_id == organization_id,
                Refund.created_at >= lower_bound,
                Refund.created_at < upper_bound,
                *conditions,
            )
        )
        return {"payments": _decimal(payment_total), "refunds": _decimal(refund_total)}

    async def _payment_state(
        self,
        session: Any,
        *,
        organization_id: UUID,
        conditions: tuple[Any, ...],
    ) -> dict[str, int]:
        """Count unpaid/partial appointments with grouped payment data, not per-row queries."""
        paid = (
            sa.select(
                Payment.appointment_id.label("appointment_id"),
                sa.func.coalesce(sa.func.sum(Payment.amount), 0).label("paid_amount"),
            )
            .where(Payment.organization_id == organization_id)
            .group_by(Payment.appointment_id)
            .subquery()
        )
        refunded = (
            sa.select(
                Payment.appointment_id.label("appointment_id"),
                sa.func.coalesce(sa.func.sum(Refund.amount), 0).label("refunded_amount"),
            )
            .join(Refund, Refund.payment_id == Payment.id)
            .where(Refund.organization_id == organization_id)
            .group_by(Payment.appointment_id)
            .subquery()
        )
        net_paid = sa.func.coalesce(paid.c.paid_amount, 0) - sa.func.coalesce(
            refunded.c.refunded_amount, 0
        )
        row = (
            (
                await session.execute(
                    sa.select(
                        sa.func.count(Appointment.id).filter(net_paid <= 0).label("unpaid"),
                        sa.func.count(Appointment.id)
                        .filter(sa.and_(net_paid > 0, net_paid < Appointment.price_snapshot))
                        .label("partial"),
                    )
                    .outerjoin(paid, paid.c.appointment_id == Appointment.id)
                    .outerjoin(refunded, refunded.c.appointment_id == Appointment.id)
                    .where(*conditions)
                )
            )
            .mappings()
            .one()
        )
        return {"unpaid": int(row["unpaid"] or 0), "partial": int(row["partial"] or 0)}

    async def _top_services(
        self,
        session: Any,
        *,
        conditions: tuple[Any, ...],
        include_finance: bool,
    ) -> list[dict[str, Any]]:
        """Return completed service leaders through one grouped, limited query."""

        columns: list[Any] = [
            Appointment.service_id,
            Appointment.service_name_snapshot,
            sa.func.count(Appointment.id).label("completed_count"),
        ]
        if include_finance:
            columns.append(
                sa.func.coalesce(sa.func.sum(Appointment.price_snapshot), 0).label("revenue")
            )
        order_by: list[Any] = [sa.desc("completed_count"), Appointment.service_id]
        if include_finance:
            order_by.insert(0, sa.desc("revenue"))
        rows = (
            (
                await session.execute(
                    sa.select(*columns)
                    .where(*conditions, Appointment.status == AppointmentStatus.COMPLETED)
                    .group_by(Appointment.service_id, Appointment.service_name_snapshot)
                    .order_by(*order_by)
                    .limit(10)
                )
            )
            .mappings()
            .all()
        )
        return [
            {
                "service_id": row["service_id"],
                "service_name": row["service_name_snapshot"],
                "completed_count": int(row["completed_count"]),
                **({"revenue": _decimal(row["revenue"])} if include_finance else {}),
            }
            for row in rows
        ]

    async def _top_specialists(
        self,
        session: Any,
        *,
        conditions: tuple[Any, ...],
        include_finance: bool,
    ) -> list[dict[str, Any]]:
        """Return completed specialist leaders through a grouped SQL query."""

        columns: list[Any] = [
            Appointment.specialist_id,
            Appointment.specialist_name_snapshot,
            sa.func.count(Appointment.id).label("completed_count"),
            sa.func.coalesce(
                sa.func.sum(
                    sa.extract("epoch", Appointment.busy_ends_at - Appointment.busy_starts_at) / 60
                ),
                0,
            ).label("busy_minutes"),
        ]
        if include_finance:
            columns.append(
                sa.func.coalesce(sa.func.sum(Appointment.price_snapshot), 0).label("revenue")
            )
        order_by: list[Any] = [sa.desc("completed_count"), Appointment.specialist_id]
        if include_finance:
            order_by.insert(0, sa.desc("revenue"))
        rows = (
            (
                await session.execute(
                    sa.select(*columns)
                    .where(*conditions, Appointment.status == AppointmentStatus.COMPLETED)
                    .group_by(Appointment.specialist_id, Appointment.specialist_name_snapshot)
                    .order_by(*order_by)
                    .limit(10)
                )
            )
            .mappings()
            .all()
        )
        return [
            {
                "specialist_id": row["specialist_id"],
                "specialist_name": row["specialist_name_snapshot"],
                "completed_count": int(row["completed_count"]),
                "busy_minutes": _decimal(row["busy_minutes"]),
                **({"revenue": _decimal(row["revenue"])} if include_finance else {}),
            }
            for row in rows
        ]

    async def _customer_metrics(
        self,
        session: Any,
        *,
        organization_id: UUID,
        lower_bound: datetime,
        upper_bound: datetime,
        appointment_conditions: tuple[Any, ...],
        scope_predicate: Any,
    ) -> dict[str, int]:
        """Count scoped customer activity without exposing unscoped tenant profiles."""

        new_customers = await session.scalar(
            sa.select(sa.func.count(sa.distinct(Customer.id)))
            .select_from(Customer)
            .join(Appointment, Appointment.customer_id == Customer.id)
            .where(
                *appointment_conditions,
                Customer.organization_id == organization_id,
                Customer.created_at >= lower_bound,
                Customer.created_at < upper_bound,
            )
        )
        prior_appointment = sa.exists(
            sa.select(Appointment.id).where(
                Appointment.organization_id == organization_id,
                Appointment.customer_id == Customer.id,
                Appointment.starts_at < lower_bound,
                Appointment.status.not_in((AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW)),
                scope_predicate,
            )
        )
        repeat_customers = await session.scalar(
            sa.select(sa.func.count(sa.distinct(Appointment.customer_id)))
            .select_from(Appointment)
            .join(Customer, Customer.id == Appointment.customer_id)
            .where(
                *appointment_conditions,
                Appointment.starts_at >= lower_bound,
                Appointment.starts_at < upper_bound,
                prior_appointment,
            )
        )
        return {
            "new": int(new_customers or 0),
            "repeat": int(repeat_customers or 0),
        }

    async def _busy_minutes(
        self,
        session: Any,
        *,
        conditions: tuple[Any, ...],
    ) -> Decimal:
        """Sum active appointment busy intervals rather than service duration alone."""

        value = await session.scalar(
            sa.select(
                sa.func.coalesce(
                    sa.func.sum(
                        sa.extract("epoch", Appointment.busy_ends_at - Appointment.busy_starts_at)
                        / 60
                    ),
                    0,
                )
            ).where(
                *conditions,
                Appointment.status.in_(
                    (
                        AppointmentStatus.PENDING,
                        AppointmentStatus.CONFIRMED,
                        AppointmentStatus.CHECKED_IN,
                        AppointmentStatus.COMPLETED,
                    )
                ),
            )
        )
        return _decimal(value)

    async def _available_minutes(
        self,
        session: Any,
        *,
        organization_id: UUID,
        query: AnalyticsQuery,
        lower_bound: datetime,
        upper_bound: datetime,
        access: _AnalyticsScope,
    ) -> Decimal:
        """Use PostgreSQL ranges to merge schedules/overrides and subtract unavailable time."""

        filters = ""
        parameters: dict[str, Any] = {
            "organization_id": organization_id,
            "timezone": query.timezone,
            "date_from": query.date_from,
            "date_to": query.date_to,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "unavailable": AvailabilityExceptionType.UNAVAILABLE.value,
            "override": AvailabilityExceptionType.AVAILABLE_OVERRIDE.value,
        }
        if query.branch_id is not None:
            filters += " AND ws.branch_id = :branch_id"
            parameters["branch_id"] = query.branch_id
        if query.specialist_id is not None:
            filters += " AND ws.specialist_id = :specialist_id"
            parameters["specialist_id"] = query.specialist_id
        if access.branch_ids is not None:
            if access.branch_ids:
                branch_scope = "ws.branch_id = ANY(CAST(:scope_branch_ids AS uuid[]))"
                parameters["scope_branch_ids"] = list(access.branch_ids)
            else:
                branch_scope = "FALSE"
            if access.self_specialist_id is not None:
                filters += f" AND ({branch_scope} OR ws.specialist_id = :scope_specialist_id)"
                parameters["scope_specialist_id"] = access.self_specialist_id
            else:
                filters += f" AND {branch_scope}"
        exception_filters = filters.replace("ws.", "ae.")
        statement = sa.text(
            f"""
            WITH working_ranges AS (
                SELECT
                    ws.specialist_id,
                    tstzrange(
                        ((day_value::date + ws.local_start_time) AT TIME ZONE :timezone),
                        ((day_value::date + ws.local_end_time) AT TIME ZONE :timezone),
                        '[)'
                    ) AS interval_value
                FROM booking_working_schedules AS ws
                CROSS JOIN generate_series(
                    CAST(:date_from AS date),
                    CAST(:date_to AS date),
                    INTERVAL '1 day'
                ) AS days(day_value)
                WHERE ws.organization_id = :organization_id
                  AND ws.is_active
                  AND ws.weekday = EXTRACT(ISODOW FROM day_value)::integer - 1
                  {filters}
            ),
            override_ranges AS (
                SELECT
                    ae.specialist_id,
                    tstzrange(
                        GREATEST(ae.starts_at, :lower_bound),
                        LEAST(ae.ends_at, :upper_bound),
                        '[)'
                    ) AS interval_value
                FROM booking_availability_exceptions AS ae
                WHERE ae.organization_id = :organization_id
                  AND ae.type = :override
                  AND ae.starts_at < :upper_bound
                  AND ae.ends_at > :lower_bound
                  {exception_filters}
            ),
            base_ranges AS (
                SELECT specialist_id, interval_value FROM working_ranges
                UNION ALL
                SELECT specialist_id, interval_value FROM override_ranges
            ),
            grouped_base AS (
                SELECT specialist_id, range_agg(interval_value) AS intervals
                FROM base_ranges
                GROUP BY specialist_id
            ),
            unavailable_ranges AS (
                SELECT
                    ae.specialist_id,
                    range_agg(
                        tstzrange(
                            GREATEST(ae.starts_at, :lower_bound),
                            LEAST(ae.ends_at, :upper_bound),
                            '[)'
                        )
                    ) AS intervals
                FROM booking_availability_exceptions AS ae
                WHERE ae.organization_id = :organization_id
                  AND ae.type = :unavailable
                  AND ae.starts_at < :upper_bound
                  AND ae.ends_at > :lower_bound
                  {exception_filters}
                GROUP BY ae.specialist_id
            ),
            actual_ranges AS (
                SELECT unnest(
                    base.intervals - COALESCE(unavailable.intervals, '{{}}'::tstzmultirange)
                ) AS interval_value
                FROM grouped_base AS base
                LEFT JOIN unavailable_ranges AS unavailable
                  ON unavailable.specialist_id = base.specialist_id
            )
            SELECT COALESCE(
                SUM(EXTRACT(EPOCH FROM (upper(interval_value) - lower(interval_value))) / 60),
                0
            ) AS available_minutes
            FROM actual_ranges
            """
        )
        value = await session.scalar(statement, parameters)
        return _decimal(value)

    async def _low_stock_products(
        self,
        session: Any,
        *,
        organization_id: UUID,
        branch_id: UUID | None,
        visible_branch_ids: frozenset[UUID] | None,
    ) -> list[dict[str, Any]]:
        """Aggregate balances in SQL and return products at or below their configured threshold."""

        conditions: list[Any] = [
            Product.organization_id == organization_id,
            Product.is_active.is_(True),
            Product.track_stock.is_(True),
            Product.low_stock_threshold.is_not(None),
        ]
        if branch_id is not None:
            conditions.append(Warehouse.branch_id == branch_id)
        if visible_branch_ids is not None:
            if not visible_branch_ids:
                return []
            conditions.append(Warehouse.branch_id.in_(visible_branch_ids))
        rows = (
            (
                await session.execute(
                    sa.select(
                        Product.id,
                        Product.name,
                        Product.unit,
                        Product.low_stock_threshold,
                        sa.func.coalesce(sa.func.sum(StockBalance.quantity), 0).label("quantity"),
                    )
                    .outerjoin(StockBalance, StockBalance.product_id == Product.id)
                    .outerjoin(Warehouse, Warehouse.id == StockBalance.warehouse_id)
                    .where(*conditions)
                    .group_by(Product.id, Product.name, Product.unit, Product.low_stock_threshold)
                    .having(
                        sa.func.coalesce(sa.func.sum(StockBalance.quantity), 0)
                        <= Product.low_stock_threshold
                    )
                    .order_by("quantity", Product.name)
                    .limit(100)
                )
            )
            .mappings()
            .all()
        )
        return [
            {
                "product_id": row["id"],
                "name": row["name"],
                "unit": row["unit"],
                "quantity": _decimal(row["quantity"]),
                "threshold": _decimal(row["low_stock_threshold"]),
            }
            for row in rows
        ]


def _scoped_appointment_conditions(
    *,
    organization_id: UUID,
    query: AnalyticsQuery,
    actor: BookingActor,
    scope: _AnalyticsScope | None,
) -> tuple[Any, ...] | None:
    """Build tenant-first appointment filters for one specific analytics permission scope."""

    if scope is None:
        return None

    conditions: list[Any] = [
        Appointment.organization_id == organization_id,
        AccessPolicy.appointment_predicate(actor, scope.permission),
    ]
    if query.branch_id is not None:
        conditions.append(Appointment.branch_id == query.branch_id)
    if query.specialist_id is not None:
        conditions.append(Appointment.specialist_id == query.specialist_id)
    if query.service_id is not None:
        conditions.append(Appointment.service_id == query.service_id)
    return tuple(conditions)


def _analytics_scope(
    actor: BookingActor,
    permission: PermissionCode,
) -> _AnalyticsScope:
    """Materialize one permission's scope while preserving combined branch and self grants."""

    grants = actor.grants_for(permission)
    self_specialist_id = (
        actor.specialist_id
        if actor.specialist_id is not None
        and any(grant.scope is AccessScope.SELF for grant in grants)
        else None
    )
    return _AnalyticsScope(
        permission=permission,
        branch_ids=AccessPolicy.branch_ids(actor, permission),
        self_specialist_id=self_specialist_id,
    )


def resolve_analytics_access(actor: BookingActor) -> _AnalyticsAccess:
    """Resolve independent analytics domains without borrowing another permission's scope."""

    booking_permission = (
        PermissionCode.ANALYTICS_BOOKINGS_VIEW
        if actor.has(PermissionCode.ANALYTICS_BOOKINGS_VIEW)
        else (
            PermissionCode.ANALYTICS_PERSONAL_VIEW
            if actor.has(PermissionCode.ANALYTICS_PERSONAL_VIEW)
            else None
        )
    )
    finance = (
        _analytics_scope(actor, PermissionCode.ANALYTICS_FINANCE_VIEW)
        if actor.has(PermissionCode.ANALYTICS_FINANCE_VIEW)
        else None
    )
    staff = (
        _analytics_scope(actor, PermissionCode.ANALYTICS_STAFF_VIEW)
        if actor.has(PermissionCode.ANALYTICS_STAFF_VIEW)
        else None
    )
    inventory = (
        _analytics_scope(actor, PermissionCode.ANALYTICS_INVENTORY_VIEW)
        if actor.has(PermissionCode.ANALYTICS_INVENTORY_VIEW)
        else None
    )
    if booking_permission is None and finance is None and staff is None and inventory is None:
        actor.require(PermissionCode.ANALYTICS_BOOKINGS_VIEW)
        raise AssertionError("actor.require always raises for a missing permission")
    return _AnalyticsAccess(
        booking=_analytics_scope(actor, booking_permission)
        if booking_permission is not None
        else None,
        finance=finance,
        staff=staff,
        inventory=inventory,
    )


def _empty_created_metrics() -> dict[str, Decimal | int]:
    """Keep optional domain calculations type-stable without issuing an unneeded query."""

    return {
        "created_count": 0,
        "confirmed_count": 0,
        "cancelled_count": 0,
        "no_show_count": 0,
    }


def _empty_completed_metrics() -> dict[str, Decimal | int]:
    """Keep optional domain calculations type-stable without issuing an unneeded query."""

    return {"completed_count": 0, "service_revenue": Decimal("0")}


def _local_date_bounds(
    *,
    date_from: date,
    date_to: date,
    timezone: ZoneInfo,
) -> tuple[datetime, datetime]:
    """Convert inclusive local dates into half-open UTC query bounds."""

    lower = datetime.combine(date_from, time.min, tzinfo=timezone).astimezone(UTC)
    upper = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=timezone).astimezone(UTC)
    return lower, upper


def _localized_date(column: Any, timezone: str) -> Any:
    """Make PostgreSQL group a ``timestamptz`` column by an IANA local date."""

    return sa.cast(sa.func.timezone(timezone, column), sa.Date)


def _decimal(value: Any) -> Decimal:
    """Normalize PostgreSQL numeric aggregates without a binary float conversion."""

    return Decimal(str(value or 0))


def _ratio(numerator: Decimal | int, denominator: Decimal | int) -> Decimal:
    """Return a stable percentage ratio rounded for dashboard display."""

    if not denominator:
        return Decimal("0")
    return (Decimal(numerator) / Decimal(denominator)).quantize(Decimal("0.0001"))
