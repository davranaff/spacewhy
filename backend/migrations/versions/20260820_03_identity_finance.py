"""Add shared Telegram identity and the first Finance ledger vertical slice.

Revision ID: 20260820_03
Revises: 20260817_02
Create Date: 2026-08-20
"""

from __future__ import annotations

from alembic import op

revision = "20260820_03"
down_revision = "20260817_02"
branch_labels = None
depends_on = None

_UPGRADE_SQL = """
CREATE TABLE identity_principals (
    id UUID NOT NULL,
    display_name VARCHAR(200),
    locale VARCHAR(16) NOT NULL,
    is_active BOOLEAN NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_identity_principals PRIMARY KEY (id)
);

CREATE TABLE identity_telegram_bindings (
    id UUID NOT NULL,
    principal_id UUID NOT NULL,
    bot_app_id VARCHAR(63) NOT NULL,
    telegram_user_id VARCHAR(128) NOT NULL,
    telegram_chat_id VARCHAR(128) NOT NULL,
    normalized_phone VARCHAR(16) NOT NULL,
    verified_at TIMESTAMP WITH TIME ZONE NOT NULL,
    is_active BOOLEAN NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_identity_telegram_bindings PRIMARY KEY (id),
    CONSTRAINT fk_identity_telegram_bindings_principal_id_identity_principals
        FOREIGN KEY(principal_id) REFERENCES identity_principals (id) ON DELETE CASCADE,
    CONSTRAINT identity_telegram_bindings_bot_user UNIQUE (bot_app_id, telegram_user_id)
);
CREATE UNIQUE INDEX uq_identity_telegram_bindings_active_phone
    ON identity_telegram_bindings (normalized_phone) WHERE is_active;
CREATE INDEX ix_identity_telegram_bindings_principal
    ON identity_telegram_bindings (principal_id, is_active);

CREATE TABLE identity_auth_challenges (
    id UUID NOT NULL,
    binding_id UUID,
    phone_digest VARCHAR(64) NOT NULL,
    code_digest VARCHAR(64) NOT NULL,
    attempts_remaining SMALLINT NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    consumed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_identity_auth_challenges PRIMARY KEY (id),
    CONSTRAINT fk_identity_auth_challenges_binding_id_identity_telegram_bindings
        FOREIGN KEY(binding_id) REFERENCES identity_telegram_bindings (id) ON DELETE SET NULL,
    CONSTRAINT ck_identity_auth_challenges_identity_auth_challenges_attempts_non_negative
        CHECK (attempts_remaining >= 0)
);
CREATE INDEX ix_identity_auth_challenges_expiry
    ON identity_auth_challenges (expires_at, consumed_at);

CREATE TABLE identity_audit_log (
    id UUID NOT NULL,
    principal_id UUID,
    action VARCHAR(100) NOT NULL,
    request_id VARCHAR(128),
    metadata_json JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_identity_audit_log PRIMARY KEY (id)
);
CREATE INDEX ix_identity_audit_principal_created
    ON identity_audit_log (principal_id, created_at);

CREATE TABLE finance_workspaces (
    id UUID NOT NULL,
    name VARCHAR(160) NOT NULL,
    default_currency VARCHAR(3) NOT NULL,
    is_active BOOLEAN NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_finance_workspaces PRIMARY KEY (id)
);

CREATE TABLE finance_memberships (
    id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    principal_id UUID NOT NULL,
    role VARCHAR(16) NOT NULL,
    is_active BOOLEAN NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_finance_memberships PRIMARY KEY (id),
    CONSTRAINT fk_finance_memberships_workspace_id_finance_workspaces
        FOREIGN KEY(workspace_id) REFERENCES finance_workspaces (id) ON DELETE CASCADE,
    CONSTRAINT finance_memberships_workspace_principal UNIQUE (workspace_id, principal_id)
);
CREATE UNIQUE INDEX uq_finance_memberships_active_personal
    ON finance_memberships (principal_id) WHERE is_active;

CREATE TABLE finance_accounts (
    id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    name VARCHAR(120) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    color VARCHAR(16),
    is_archived BOOLEAN NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_finance_accounts PRIMARY KEY (id),
    CONSTRAINT fk_finance_accounts_workspace_id_finance_workspaces
        FOREIGN KEY(workspace_id) REFERENCES finance_workspaces (id) ON DELETE CASCADE,
    CONSTRAINT finance_accounts_workspace_name UNIQUE (workspace_id, name)
);
CREATE INDEX ix_finance_accounts_workspace_archived
    ON finance_accounts (workspace_id, is_archived);

CREATE TABLE finance_categories (
    id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    direction VARCHAR(16) NOT NULL,
    name VARCHAR(120) NOT NULL,
    icon VARCHAR(64),
    is_system BOOLEAN NOT NULL,
    is_archived BOOLEAN NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_finance_categories PRIMARY KEY (id),
    CONSTRAINT fk_finance_categories_workspace_id_finance_workspaces
        FOREIGN KEY(workspace_id) REFERENCES finance_workspaces (id) ON DELETE CASCADE,
    CONSTRAINT finance_categories_workspace_direction_name UNIQUE (workspace_id, direction, name)
);
CREATE INDEX ix_finance_categories_workspace_archived
    ON finance_categories (workspace_id, is_archived);

CREATE TABLE finance_entries (
    id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    account_id UUID NOT NULL,
    category_id UUID,
    direction VARCHAR(16) NOT NULL,
    kind VARCHAR(24) NOT NULL,
    amount NUMERIC(18, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
    note VARCHAR(500),
    created_by_principal_id UUID NOT NULL,
    reversal_of_id UUID,
    transfer_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_finance_entries PRIMARY KEY (id),
    CONSTRAINT fk_finance_entries_workspace_id_finance_workspaces
        FOREIGN KEY(workspace_id) REFERENCES finance_workspaces (id) ON DELETE RESTRICT,
    CONSTRAINT fk_finance_entries_account_id_finance_accounts
        FOREIGN KEY(account_id) REFERENCES finance_accounts (id) ON DELETE RESTRICT,
    CONSTRAINT fk_finance_entries_category_id_finance_categories
        FOREIGN KEY(category_id) REFERENCES finance_categories (id) ON DELETE RESTRICT,
    CONSTRAINT fk_finance_entries_reversal_of_id_finance_entries
        FOREIGN KEY(reversal_of_id) REFERENCES finance_entries (id) ON DELETE RESTRICT,
    CONSTRAINT ck_finance_entries_finance_entries_amount_positive CHECK (amount > 0)
);
CREATE INDEX ix_finance_entries_workspace_occurred
    ON finance_entries (workspace_id, occurred_at, id);
CREATE INDEX ix_finance_entries_account_occurred
    ON finance_entries (account_id, occurred_at);
CREATE UNIQUE INDEX uq_finance_entries_reversal_once
    ON finance_entries (reversal_of_id) WHERE reversal_of_id IS NOT NULL;

CREATE TABLE finance_idempotency (
    id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    principal_id UUID NOT NULL,
    operation VARCHAR(80) NOT NULL,
    key VARCHAR(128) NOT NULL,
    request_fingerprint VARCHAR(64) NOT NULL,
    response_entry_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_finance_idempotency PRIMARY KEY (id),
    CONSTRAINT fk_finance_idempotency_response_entry_id_finance_entries
        FOREIGN KEY(response_entry_id) REFERENCES finance_entries (id) ON DELETE RESTRICT,
    CONSTRAINT finance_idempotency_scope UNIQUE (workspace_id, principal_id, operation, key)
);

CREATE TABLE finance_audit_log (
    id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    principal_id UUID NOT NULL,
    action VARCHAR(100) NOT NULL,
    resource_id UUID,
    request_id VARCHAR(128),
    metadata_json JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_finance_audit_log PRIMARY KEY (id)
);
CREATE INDEX ix_finance_audit_workspace_created
    ON finance_audit_log (workspace_id, created_at);

CREATE TABLE finance_outbox (
    id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    event_type VARCHAR(120) NOT NULL,
    event_version SMALLINT NOT NULL,
    aggregate_id UUID NOT NULL,
    payload JSONB NOT NULL,
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT pk_finance_outbox PRIMARY KEY (id),
    CONSTRAINT ck_finance_outbox_finance_outbox_version_positive CHECK (event_version > 0)
);
CREATE INDEX ix_finance_outbox_unpublished
    ON finance_outbox (published_at, occurred_at);
"""

_DOWNGRADE_SQL = """
DROP TABLE finance_outbox;
DROP TABLE finance_audit_log;
DROP TABLE finance_idempotency;
DROP TABLE finance_entries;
DROP TABLE finance_categories;
DROP TABLE finance_accounts;
DROP TABLE finance_memberships;
DROP TABLE finance_workspaces;
DROP TABLE identity_audit_log;
DROP TABLE identity_auth_challenges;
DROP TABLE identity_telegram_bindings;
DROP TABLE identity_principals;
"""


def upgrade() -> None:
    op.execute(_UPGRADE_SQL)


def downgrade() -> None:
    op.execute(_DOWNGRADE_SQL)
