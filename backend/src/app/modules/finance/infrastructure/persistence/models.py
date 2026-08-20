"""Append-oriented Finance persistence models."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base
from app.modules.finance.domain.enums import EntryDirection, EntryKind, WorkspaceRole

_UUID = sa.Uuid(as_uuid=True)
_UTC_DATETIME = sa.DateTime(timezone=True)
_MONEY = sa.Numeric(18, 2)


def _uuid() -> UUID:
    return uuid4()


def _enum_values(members: type[StrEnum]) -> list[str]:
    return [member.value for member in members]


def _enum(enum_type: type[StrEnum], *, length: int) -> sa.Enum:
    return sa.Enum(
        enum_type,
        native_enum=False,
        length=length,
        values_callable=_enum_values,
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        _UTC_DATETIME, server_default=sa.func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        _UTC_DATETIME, server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False
    )


class FinanceWorkspace(TimestampMixin, Base):
    __tablename__ = "finance_workspaces"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(sa.String(160), nullable=False)
    default_currency: Mapped[str] = mapped_column(sa.String(3), nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)


class FinanceMembership(TimestampMixin, Base):
    __tablename__ = "finance_memberships"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    workspace_id: Mapped[UUID] = mapped_column(
        _UUID, sa.ForeignKey("finance_workspaces.id", ondelete="CASCADE"), nullable=False
    )
    principal_id: Mapped[UUID] = mapped_column(_UUID, nullable=False)
    role: Mapped[WorkspaceRole] = mapped_column(_enum(WorkspaceRole, length=16), nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)

    __table_args__ = (
        sa.UniqueConstraint(
            "workspace_id", "principal_id", name="finance_memberships_workspace_principal"
        ),
        sa.Index(
            "uq_finance_memberships_active_personal",
            "principal_id",
            unique=True,
            postgresql_where=sa.text("is_active"),
        ),
    )


class FinanceAccount(TimestampMixin, Base):
    __tablename__ = "finance_accounts"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    workspace_id: Mapped[UUID] = mapped_column(
        _UUID, sa.ForeignKey("finance_workspaces.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(sa.String(120), nullable=False)
    currency: Mapped[str] = mapped_column(sa.String(3), nullable=False)
    color: Mapped[str | None] = mapped_column(sa.String(16), nullable=True)
    is_archived: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)

    __table_args__ = (
        sa.UniqueConstraint("workspace_id", "name", name="finance_accounts_workspace_name"),
        sa.Index("ix_finance_accounts_workspace_archived", "workspace_id", "is_archived"),
    )


class FinanceCategory(TimestampMixin, Base):
    __tablename__ = "finance_categories"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    workspace_id: Mapped[UUID] = mapped_column(
        _UUID, sa.ForeignKey("finance_workspaces.id", ondelete="CASCADE"), nullable=False
    )
    direction: Mapped[EntryDirection] = mapped_column(
        _enum(EntryDirection, length=16), nullable=False
    )
    name: Mapped[str] = mapped_column(sa.String(120), nullable=False)
    icon: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    is_system: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    is_archived: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)

    __table_args__ = (
        sa.UniqueConstraint(
            "workspace_id", "direction", "name", name="finance_categories_workspace_direction_name"
        ),
        sa.Index("ix_finance_categories_workspace_archived", "workspace_id", "is_archived"),
    )


class FinanceEntry(Base):
    __tablename__ = "finance_entries"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    workspace_id: Mapped[UUID] = mapped_column(
        _UUID, sa.ForeignKey("finance_workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    account_id: Mapped[UUID] = mapped_column(
        _UUID, sa.ForeignKey("finance_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    category_id: Mapped[UUID | None] = mapped_column(
        _UUID, sa.ForeignKey("finance_categories.id", ondelete="RESTRICT"), nullable=True
    )
    direction: Mapped[EntryDirection] = mapped_column(
        _enum(EntryDirection, length=16), nullable=False
    )
    kind: Mapped[EntryKind] = mapped_column(_enum(EntryKind, length=24), nullable=False)
    amount: Mapped[Decimal] = mapped_column(_MONEY, nullable=False)
    currency: Mapped[str] = mapped_column(sa.String(3), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(_UTC_DATETIME, nullable=False)
    note: Mapped[str | None] = mapped_column(sa.String(500), nullable=True)
    created_by_principal_id: Mapped[UUID] = mapped_column(_UUID, nullable=False)
    reversal_of_id: Mapped[UUID | None] = mapped_column(
        _UUID, sa.ForeignKey("finance_entries.id", ondelete="RESTRICT"), nullable=True
    )
    transfer_id: Mapped[UUID | None] = mapped_column(_UUID, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        _UTC_DATETIME, server_default=sa.func.now(), nullable=False
    )

    __table_args__ = (
        sa.CheckConstraint("amount > 0", name="finance_entries_amount_positive"),
        sa.Index(
            "ix_finance_entries_workspace_occurred",
            "workspace_id",
            "occurred_at",
            "id",
        ),
        sa.Index("ix_finance_entries_account_occurred", "account_id", "occurred_at"),
        sa.Index(
            "uq_finance_entries_reversal_once",
            "reversal_of_id",
            unique=True,
            postgresql_where=sa.text("reversal_of_id IS NOT NULL"),
        ),
    )


class FinanceIdempotency(Base):
    __tablename__ = "finance_idempotency"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    workspace_id: Mapped[UUID] = mapped_column(_UUID, nullable=False)
    principal_id: Mapped[UUID] = mapped_column(_UUID, nullable=False)
    operation: Mapped[str] = mapped_column(sa.String(80), nullable=False)
    key: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    response_entry_id: Mapped[UUID] = mapped_column(
        _UUID, sa.ForeignKey("finance_entries.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        _UTC_DATETIME, server_default=sa.func.now(), nullable=False
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "workspace_id",
            "principal_id",
            "operation",
            "key",
            name="finance_idempotency_scope",
        ),
    )


class FinanceAudit(Base):
    __tablename__ = "finance_audit_log"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    workspace_id: Mapped[UUID] = mapped_column(_UUID, nullable=False)
    principal_id: Mapped[UUID] = mapped_column(_UUID, nullable=False)
    action: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    resource_id: Mapped[UUID | None] = mapped_column(_UUID, nullable=True)
    request_id: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        _UTC_DATETIME, server_default=sa.func.now(), nullable=False
    )

    __table_args__ = (sa.Index("ix_finance_audit_workspace_created", "workspace_id", "created_at"),)


class FinanceOutbox(Base):
    __tablename__ = "finance_outbox"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    workspace_id: Mapped[UUID] = mapped_column(_UUID, nullable=False)
    event_type: Mapped[str] = mapped_column(sa.String(120), nullable=False)
    event_version: Mapped[int] = mapped_column(sa.SmallInteger, nullable=False, default=1)
    aggregate_id: Mapped[UUID] = mapped_column(_UUID, nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(_UTC_DATETIME, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(_UTC_DATETIME, nullable=True)

    __table_args__ = (
        sa.CheckConstraint("event_version > 0", name="finance_outbox_version_positive"),
        sa.Index("ix_finance_outbox_unpublished", "published_at", "occurred_at"),
    )
