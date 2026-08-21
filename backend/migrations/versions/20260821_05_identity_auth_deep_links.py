"""Link phone challenges to Telegram deep-link sessions.

Revision ID: 20260821_05
Revises: 20260820_04
Create Date: 2026-08-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260821_05"
down_revision = "20260820_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "identity_auth_challenges",
        sa.Column(
            "bot_app_id",
            sa.String(length=63),
            server_default="spacewhy_auth_bot",
            nullable=False,
        ),
    )
    op.alter_column("identity_auth_challenges", "bot_app_id", server_default=None)
    op.add_column(
        "identity_auth_challenges",
        sa.Column("claimed_telegram_user_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "identity_auth_challenges",
        sa.Column("claimed_telegram_chat_id", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "ix_identity_auth_challenges_telegram_claim",
        "identity_auth_challenges",
        ["bot_app_id", "claimed_telegram_user_id", "expires_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_identity_auth_challenges_telegram_claim",
        table_name="identity_auth_challenges",
    )
    op.drop_column("identity_auth_challenges", "claimed_telegram_chat_id")
    op.drop_column("identity_auth_challenges", "claimed_telegram_user_id")
    op.drop_column("identity_auth_challenges", "bot_app_id")
