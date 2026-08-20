"""Add one-time Identity session handoffs.

Revision ID: 20260820_04
Revises: 20260820_03
Create Date: 2026-08-20
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260820_04"
down_revision = "20260820_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "identity_session_handoffs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("principal_id", sa.Uuid(), nullable=False),
        sa.Column("target", sa.String(length=32), nullable=False),
        sa.Column("token_digest", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["principal_id"],
            ["identity_principals.id"],
            name="fk_identity_session_handoffs_principal_id_identity_principals",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_identity_session_handoffs"),
        sa.UniqueConstraint("token_digest", name="uq_identity_session_handoffs_token_digest"),
    )
    op.create_index(
        "ix_identity_session_handoffs_expiry",
        "identity_session_handoffs",
        ["expires_at", "consumed_at"],
    )
    op.create_index(
        "ix_identity_session_handoffs_principal",
        "identity_session_handoffs",
        ["principal_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_identity_session_handoffs_principal",
        table_name="identity_session_handoffs",
    )
    op.drop_index(
        "ix_identity_session_handoffs_expiry",
        table_name="identity_session_handoffs",
    )
    op.drop_table("identity_session_handoffs")
