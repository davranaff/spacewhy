"""Identity-owned SQLAlchemy models."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import conv

from app.core.db.base import Base

_UUID = sa.Uuid(as_uuid=True)
_UTC_DATETIME = sa.DateTime(timezone=True)


def _uuid() -> UUID:
    return uuid4()


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        _UTC_DATETIME, server_default=sa.func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        _UTC_DATETIME, server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False
    )


class Principal(TimestampMixin, Base):
    """One shared Spacewhy person identity."""

    __tablename__ = "identity_principals"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    display_name: Mapped[str | None] = mapped_column(sa.String(200), nullable=True)
    locale: Mapped[str] = mapped_column(sa.String(16), nullable=False, default="ru")
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)


class TelegramBinding(TimestampMixin, Base):
    """Verified current-user Telegram contact binding."""

    __tablename__ = "identity_telegram_bindings"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    principal_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("identity_principals.id", ondelete="CASCADE"),
        nullable=False,
    )
    bot_app_id: Mapped[str] = mapped_column(sa.String(63), nullable=False)
    telegram_user_id: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    telegram_chat_id: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    normalized_phone: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    verified_at: Mapped[datetime] = mapped_column(_UTC_DATETIME, nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)

    __table_args__ = (
        sa.UniqueConstraint(
            "bot_app_id", "telegram_user_id", name="identity_telegram_bindings_bot_user"
        ),
        sa.Index(
            "uq_identity_telegram_bindings_active_phone",
            "normalized_phone",
            unique=True,
            postgresql_where=sa.text("is_active"),
        ),
        sa.Index("ix_identity_telegram_bindings_principal", "principal_id", "is_active"),
    )


class AuthChallenge(Base):
    """One-time phone challenge with no stored raw OTP."""

    __tablename__ = "identity_auth_challenges"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    binding_id: Mapped[UUID | None] = mapped_column(
        _UUID,
        sa.ForeignKey("identity_telegram_bindings.id", ondelete="SET NULL"),
        nullable=True,
    )
    phone_digest: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    code_digest: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    attempts_remaining: Mapped[int] = mapped_column(sa.SmallInteger, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(_UTC_DATETIME, nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(_UTC_DATETIME, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        _UTC_DATETIME, server_default=sa.func.now(), nullable=False
    )

    __table_args__ = (
        sa.CheckConstraint(
            "attempts_remaining >= 0",
            name=conv("ck_identity_auth_challenges_identity_auth_challenges_attempts_n"),
        ),
        sa.Index("ix_identity_auth_challenges_expiry", "expires_at", "consumed_at"),
    )


class SessionHandoff(Base):
    """Short-lived one-time bridge into an independently deployed SpaceDrop."""

    __tablename__ = "identity_session_handoffs"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    principal_id: Mapped[UUID] = mapped_column(
        _UUID,
        sa.ForeignKey("identity_principals.id", ondelete="CASCADE"),
        nullable=False,
    )
    target: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    token_digest: Mapped[str] = mapped_column(sa.String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(_UTC_DATETIME, nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(_UTC_DATETIME, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        _UTC_DATETIME, server_default=sa.func.now(), nullable=False
    )

    __table_args__ = (
        sa.Index("ix_identity_session_handoffs_expiry", "expires_at", "consumed_at"),
        sa.Index("ix_identity_session_handoffs_principal", "principal_id", "created_at"),
    )


class IdentityAudit(Base):
    """Append-only identity security audit without secrets."""

    __tablename__ = "identity_audit_log"

    id: Mapped[UUID] = mapped_column(_UUID, primary_key=True, default=_uuid)
    principal_id: Mapped[UUID | None] = mapped_column(_UUID, nullable=True)
    action: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    request_id: Mapped[str | None] = mapped_column(sa.String(128), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        _UTC_DATETIME, server_default=sa.func.now(), nullable=False
    )

    __table_args__ = (
        sa.Index("ix_identity_audit_principal_created", "principal_id", "created_at"),
    )
