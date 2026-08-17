"""Add live scoped RBAC, platform separation, and append-only audit metadata.

Revision ID: 20260817_02
Revises: 20260815_01
Create Date: 2026-08-17
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from uuid import UUID, uuid4

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

from app.modules.booking.application.permissions import (
    BUILTIN_ROLE_BY_CODE,
    BUILTIN_ROLE_DEFINITIONS,
    LEGACY_ROLE_TO_BUILTIN_ROLE,
    PERMISSION_DEFINITIONS,
)
from app.modules.booking.domain.enums import AccessRole

revision = "20260817_02"
down_revision = "20260815_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create normalized RBAC tables and migrate legacy staff grants without data loss."""

    op.create_table(
        "booking_permission_definitions",
        sa.Column("code", sa.String(length=120), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("allowed_scopes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_booking_permission_definitions_category",
        "booking_permission_definitions",
        ["category", "is_active"],
    )
    op.create_table(
        "booking_roles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(is_system AND organization_id IS NULL) OR NOT is_system",
            name="booking_roles_system_global",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["booking_organizations.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "code",
            name="booking_roles_organization_code",
            postgresql_nulls_not_distinct=True,
        ),
    )
    op.create_index(
        "ix_booking_roles_organization_active",
        "booking_roles",
        ["organization_id", "is_active"],
    )
    op.create_table(
        "booking_role_permissions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("permission_code", sa.String(length=120), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["role_id"], ["booking_roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["permission_code"],
            ["booking_permission_definitions.code"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("role_id", "permission_code", name="booking_role_permissions_scope"),
    )
    op.create_index(
        "ix_booking_role_permissions_permission",
        "booking_role_permissions",
        ["permission_code", "role_id"],
    )
    op.create_table(
        "booking_memberships",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("specialist_id", sa.Uuid(), nullable=True),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("access_version", sa.Integer(), nullable=False),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deactivated_by", sa.Uuid(), nullable=True),
        sa.Column("deactivation_reason", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "access_version > 0", name="booking_memberships_access_version_positive"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["booking_organizations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["specialist_id"],
            ["booking_specialists.id"],
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "subject_id",
            name="booking_memberships_organization_subject",
        ),
    )
    op.create_index(
        "ix_booking_memberships_organization_active",
        "booking_memberships",
        ["organization_id", "is_active"],
    )
    op.create_index(
        "ix_booking_memberships_specialist",
        "booking_memberships",
        ["organization_id", "specialist_id"],
    )
    op.create_table(
        "booking_role_assignments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("membership_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("scope", sa.String(length=24), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_by", sa.Uuid(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by", sa.Uuid(), nullable=True),
        sa.Column("revoke_reason", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "ends_at IS NULL OR starts_at IS NULL OR ends_at > starts_at",
            name="booking_role_assignments_window",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["booking_organizations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["membership_id"],
            ["booking_memberships.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["role_id"], ["booking_roles.id"], ondelete="RESTRICT"),
    )
    op.create_index(
        "uq_booking_role_assignments_active_scope",
        "booking_role_assignments",
        ["membership_id", "role_id", "scope"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )
    op.create_index(
        "ix_booking_role_assignments_membership_active",
        "booking_role_assignments",
        ["organization_id", "membership_id", "is_active"],
    )
    op.create_table(
        "booking_role_assignment_branches",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("assignment_id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["assignment_id"],
            ["booking_role_assignments.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["branch_id"], ["booking_branches.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "assignment_id",
            "branch_id",
            name="booking_role_assignment_branches_scope",
        ),
    )
    op.create_index(
        "ix_booking_role_assignment_branches_branch",
        "booking_role_assignment_branches",
        ["branch_id", "assignment_id"],
    )
    op.create_table(
        "booking_platform_administrators",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("subject_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("access_version", sa.Integer(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "access_version > 0",
            name="booking_platform_administrators_access_version_positive",
        ),
    )

    op.add_column(
        "booking_staff_telegram_bindings", sa.Column("membership_id", sa.Uuid(), nullable=True)
    )
    op.create_foreign_key(
        "fk_booking_staff_bindings_membership",
        "booking_staff_telegram_bindings",
        "booking_memberships",
        ["membership_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_booking_staff_bindings_membership_active",
        "booking_staff_telegram_bindings",
        ["organization_id", "membership_id", "is_active"],
    )
    op.add_column("booking_staff_bind_codes", sa.Column("membership_id", sa.Uuid(), nullable=True))
    op.add_column(
        "booking_staff_bind_codes",
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("booking_staff_bind_codes", sa.Column("revoked_by", sa.Uuid(), nullable=True))
    op.add_column(
        "booking_staff_bind_codes", sa.Column("revoke_reason", sa.String(length=500), nullable=True)
    )
    op.create_foreign_key(
        "fk_booking_staff_bind_codes_membership",
        "booking_staff_bind_codes",
        "booking_memberships",
        ["membership_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("booking_audit_log", sa.Column("branch_id", sa.Uuid(), nullable=True))
    op.add_column(
        "booking_audit_log", sa.Column("action_code", sa.String(length=120), nullable=True)
    )
    op.add_column("booking_audit_log", sa.Column("actor_membership_id", sa.Uuid(), nullable=True))
    op.add_column("booking_audit_log", sa.Column("source", sa.String(length=24), nullable=True))
    op.add_column(
        "booking_audit_log",
        sa.Column("before_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "booking_audit_log",
        sa.Column("after_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "booking_audit_log", sa.Column("request_id", sa.String(length=128), nullable=True)
    )
    op.add_column(
        "booking_audit_log", sa.Column("correlation_id", sa.String(length=128), nullable=True)
    )
    op.add_column("booking_audit_log", sa.Column("task_id", sa.String(length=128), nullable=True))
    op.add_column("booking_audit_log", sa.Column("ip_address", sa.String(length=64), nullable=True))
    op.add_column(
        "booking_audit_log", sa.Column("user_agent", sa.String(length=500), nullable=True)
    )
    op.execute("UPDATE booking_audit_log SET action_code = event_type, source = 'system'")
    op.alter_column("booking_audit_log", "action_code", nullable=False)
    op.alter_column("booking_audit_log", "source", nullable=False)
    op.create_foreign_key(
        "fk_booking_audit_log_branch",
        "booking_audit_log",
        "booking_branches",
        ["branch_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_booking_audit_log_membership",
        "booking_audit_log",
        "booking_memberships",
        ["actor_membership_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_booking_audit_log_action_created",
        "booking_audit_log",
        ["organization_id", "action_code", "created_at"],
    )

    _seed_registry()
    # The legacy-data copy needs a live database query.  Schema and static seed SQL remain
    # inspectable through ``alembic upgrade --sql``; deployment always runs this revision online.
    if not context.is_offline_mode():
        _backfill_legacy_staff_grants()
    op.execute(
        """
        CREATE OR REPLACE FUNCTION booking_audit_log_append_only() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'booking_audit_log is append-only' USING ERRCODE = '55000';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER booking_audit_log_no_mutation
            BEFORE UPDATE OR DELETE ON booking_audit_log
            FOR EACH ROW EXECUTE FUNCTION booking_audit_log_append_only()
        """
    )


def downgrade() -> None:
    """Remove RBAC structures while preserving original legacy access grants unchanged."""

    op.execute("DROP TRIGGER IF EXISTS booking_audit_log_no_mutation ON booking_audit_log")
    op.execute("DROP FUNCTION IF EXISTS booking_audit_log_append_only()")
    op.drop_index("ix_booking_audit_log_action_created", table_name="booking_audit_log")
    op.drop_constraint("fk_booking_audit_log_membership", "booking_audit_log", type_="foreignkey")
    op.drop_constraint("fk_booking_audit_log_branch", "booking_audit_log", type_="foreignkey")
    for column in (
        "user_agent",
        "ip_address",
        "task_id",
        "correlation_id",
        "request_id",
        "after_json",
        "before_json",
        "source",
        "actor_membership_id",
        "action_code",
        "branch_id",
    ):
        op.drop_column("booking_audit_log", column)

    op.drop_constraint(
        "fk_booking_staff_bind_codes_membership",
        "booking_staff_bind_codes",
        type_="foreignkey",
    )
    for column in ("revoke_reason", "revoked_by", "revoked_at", "membership_id"):
        op.drop_column("booking_staff_bind_codes", column)
    op.drop_index(
        "ix_booking_staff_bindings_membership_active",
        table_name="booking_staff_telegram_bindings",
    )
    op.drop_constraint(
        "fk_booking_staff_bindings_membership",
        "booking_staff_telegram_bindings",
        type_="foreignkey",
    )
    op.drop_column("booking_staff_telegram_bindings", "membership_id")

    op.drop_table("booking_platform_administrators")
    op.drop_index(
        "ix_booking_role_assignment_branches_branch",
        table_name="booking_role_assignment_branches",
    )
    op.drop_table("booking_role_assignment_branches")
    op.drop_index(
        "ix_booking_role_assignments_membership_active",
        table_name="booking_role_assignments",
    )
    op.drop_index(
        "uq_booking_role_assignments_active_scope",
        table_name="booking_role_assignments",
    )
    op.drop_table("booking_role_assignments")
    op.drop_index("ix_booking_memberships_specialist", table_name="booking_memberships")
    op.drop_index(
        "ix_booking_memberships_organization_active",
        table_name="booking_memberships",
    )
    op.drop_table("booking_memberships")
    op.drop_index(
        "ix_booking_role_permissions_permission",
        table_name="booking_role_permissions",
    )
    op.drop_table("booking_role_permissions")
    op.drop_index("ix_booking_roles_organization_active", table_name="booking_roles")
    op.drop_table("booking_roles")
    op.drop_index(
        "ix_booking_permission_definitions_category",
        table_name="booking_permission_definitions",
    )
    op.drop_table("booking_permission_definitions")


def _seed_registry() -> None:
    """Insert stable permission and built-in role definitions from the one central registry."""

    # SQLAlchemy cannot render JSONB literals for Alembic's offline SQL mode. The registry is
    # source-controlled static data, so generate properly escaped SQL literals deliberately.
    for definition in PERMISSION_DEFINITIONS:
        allowed_scopes = json.dumps(
            sorted(scope.value for scope in definition.allowed_scopes),
            separators=(",", ":"),
        )
        op.execute(
            "INSERT INTO booking_permission_definitions "
            "(code, name, description, category, allowed_scopes, is_sensitive, is_active) VALUES "
            f"({_sql_literal(definition.code.value)}, {_sql_literal(definition.name)}, "
            f"{_sql_literal(definition.description)}, {_sql_literal(definition.category)}, "
            f"{_sql_literal(allowed_scopes)}::jsonb, {_sql_bool(definition.is_sensitive)}, TRUE)"
        )
    role_ids = {definition.code: uuid4() for definition in BUILTIN_ROLE_DEFINITIONS}
    role_table = sa.table(
        "booking_roles",
        sa.column("id", sa.Uuid()),
        sa.column("organization_id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("is_system", sa.Boolean()),
        sa.column("is_active", sa.Boolean()),
    )
    op.bulk_insert(
        role_table,
        [
            {
                "id": role_ids[definition.code],
                "organization_id": None,
                "code": definition.code.value,
                "name": definition.name,
                "description": definition.description,
                "is_system": True,
                "is_active": True,
            }
            for definition in BUILTIN_ROLE_DEFINITIONS
        ],
    )
    role_permission_table = sa.table(
        "booking_role_permissions",
        sa.column("id", sa.Uuid()),
        sa.column("role_id", sa.Uuid()),
        sa.column("permission_code", sa.String()),
    )
    op.bulk_insert(
        role_permission_table,
        [
            {
                "id": uuid4(),
                "role_id": role_ids[definition.code],
                "permission_code": permission.value,
            }
            for definition in BUILTIN_ROLE_DEFINITIONS
            for permission in definition.permissions
        ],
    )


def _backfill_legacy_staff_grants() -> None:
    """Copy pre-existing staff grants into memberships and role assignments transactionally."""

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT id, organization_id, subject_id, role, permissions, specialist_id, is_active
            FROM booking_access_grants
            WHERE role <> 'customer'
            """
        )
    ).mappings()
    system_role_ids = {
        row["code"]: row["id"]
        for row in bind.execute(
            sa.text("SELECT id, code FROM booking_roles WHERE organization_id IS NULL")
        ).mappings()
    }
    memberships: list[dict[str, object]] = []
    assignments: list[dict[str, object]] = []
    custom_roles: list[dict[str, object]] = []
    role_permissions: list[dict[str, object]] = []
    linked_memberships: list[tuple[UUID, UUID, UUID]] = []
    for row in rows:
        try:
            legacy_role = AccessRole(row["role"])
        except ValueError:
            continue
        built_in = LEGACY_ROLE_TO_BUILTIN_ROLE.get(legacy_role)
        if built_in is None:
            continue
        membership_id = uuid4()
        grant_id = row["id"]
        organization_id = row["organization_id"]
        specialist_id = row["specialist_id"]
        memberships.append(
            {
                "id": membership_id,
                "organization_id": organization_id,
                "subject_id": row["subject_id"],
                "specialist_id": specialist_id,
                "display_name": None,
                "is_active": row["is_active"],
                "access_version": 1,
                "deactivated_at": None,
                "deactivated_by": None,
                "deactivation_reason": None,
            }
        )
        explicit = _recognized_permissions(row["permissions"])
        built_in_permissions = {
            permission.value for permission in BUILTIN_ROLE_BY_CODE[built_in].permissions
        }
        extra_permissions = explicit.difference(built_in_permissions)
        role_id = system_role_ids[built_in.value]
        if extra_permissions:
            role_id = uuid4()
            custom_roles.append(
                {
                    "id": role_id,
                    "organization_id": organization_id,
                    "code": f"MIGRATED_{grant_id.hex}",
                    "name": f"Migrated {legacy_role.value}",
                    "description": "Legacy booking grant preserved during scoped RBAC migration.",
                    "is_system": False,
                    "is_active": True,
                    "created_by": row["subject_id"],
                    "updated_by": row["subject_id"],
                }
            )
            role_permissions.extend(
                {
                    "id": uuid4(),
                    "role_id": role_id,
                    "permission_code": permission,
                }
                for permission in sorted(built_in_permissions | extra_permissions)
            )
        assignments.append(
            {
                "id": uuid4(),
                "organization_id": organization_id,
                "membership_id": membership_id,
                "role_id": role_id,
                "scope": "organization",
                "is_active": row["is_active"],
                "starts_at": None,
                "ends_at": None,
                "assigned_by": row["subject_id"],
                "revoked_at": None,
                "revoked_by": None,
                "revoke_reason": None,
            }
        )
        if specialist_id is not None:
            linked_memberships.append((membership_id, organization_id, specialist_id))
    _bulk_insert("booking_memberships", memberships)
    _bulk_insert("booking_roles", custom_roles)
    _bulk_insert("booking_role_permissions", role_permissions)
    _bulk_insert("booking_role_assignments", assignments)
    for membership_id, organization_id, specialist_id in linked_memberships:
        bind.execute(
            sa.text(
                """
                UPDATE booking_staff_telegram_bindings
                SET membership_id = :membership_id
                WHERE organization_id = :organization_id AND specialist_id = :specialist_id
                """
            ),
            {
                "membership_id": membership_id,
                "organization_id": organization_id,
                "specialist_id": specialist_id,
            },
        )
        bind.execute(
            sa.text(
                """
                UPDATE booking_staff_bind_codes
                SET membership_id = :membership_id
                WHERE organization_id = :organization_id AND specialist_id = :specialist_id
                """
            ),
            {
                "membership_id": membership_id,
                "organization_id": organization_id,
                "specialist_id": specialist_id,
            },
        )


def _recognized_permissions(value: object) -> set[str]:
    """Keep only registry-known legacy explicit permissions; unknown strings never grant access."""

    if not isinstance(value, list):
        return set()
    known = {definition.code.value for definition in PERMISSION_DEFINITIONS}
    return {item for item in value if isinstance(item, str) and item in known}


def _sql_literal(value: str) -> str:
    """Render source-controlled text as a PostgreSQL string literal."""

    return f"'{value.replace("'", "''")}'"


def _sql_bool(value: bool) -> str:
    """Render a PostgreSQL boolean literal without relying on dialect-bound parameters."""

    return "TRUE" if value else "FALSE"


def _bulk_insert(table_name: str, rows: Iterable[dict[str, object]]) -> None:
    """Avoid issuing an empty bulk insert while retaining readable migration data setup."""

    materialized = list(rows)
    if materialized:
        column_types: dict[str, sa.types.TypeEngine[object]] = {
            "id": sa.Uuid(),
            "organization_id": sa.Uuid(),
            "subject_id": sa.Uuid(),
            "specialist_id": sa.Uuid(),
            "display_name": sa.String(),
            "is_active": sa.Boolean(),
            "access_version": sa.Integer(),
            "deactivated_at": sa.DateTime(timezone=True),
            "deactivated_by": sa.Uuid(),
            "deactivation_reason": sa.String(),
            "code": sa.String(),
            "name": sa.String(),
            "description": sa.Text(),
            "is_system": sa.Boolean(),
            "created_by": sa.Uuid(),
            "updated_by": sa.Uuid(),
            "role_id": sa.Uuid(),
            "permission_code": sa.String(),
            "membership_id": sa.Uuid(),
            "scope": sa.String(),
            "starts_at": sa.DateTime(timezone=True),
            "ends_at": sa.DateTime(timezone=True),
            "assigned_by": sa.Uuid(),
            "revoked_at": sa.DateTime(timezone=True),
            "revoked_by": sa.Uuid(),
            "revoke_reason": sa.String(),
        }
        op.bulk_insert(
            sa.table(
                table_name,
                *(sa.column(name, column_types[name]) for name in materialized[0]),
            ),
            materialized,
        )
