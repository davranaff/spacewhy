# ruff: noqa: E501
"""Create the first tenant-isolated booking persistence schema.

Revision ID: 20260815_01
Revises:
Create Date: 2026-08-15
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260815_01"
down_revision = None
branch_labels = None
depends_on = None

_UPGRADE_SQL = """
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE booking_organizations (
	id UUID NOT NULL,
	slug VARCHAR(63) NOT NULL,
	name VARCHAR(200) NOT NULL,
	default_timezone VARCHAR(64) NOT NULL,
	is_active BOOLEAN NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_booking_organizations PRIMARY KEY (id),
	CONSTRAINT uq_booking_organizations_slug UNIQUE (slug)
)

;

CREATE TABLE booking_telegram_bot_installations (
    id UUID NOT NULL,
    organization_id UUID NOT NULL,
    bot_app_id VARCHAR(63) NOT NULL,
    is_active BOOLEAN NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_booking_telegram_bot_installations PRIMARY KEY (id),
    CONSTRAINT uq_booking_telegram_bot_installations_bot_app_id UNIQUE (bot_app_id),
    CONSTRAINT fk_booking_telegram_bot_installations_organization_id_booking_organizations
        FOREIGN KEY(organization_id) REFERENCES booking_organizations (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_booking_telegram_bot_installations_organization_active
    ON booking_telegram_bot_installations (organization_id, is_active);

CREATE TABLE booking_rate_limit_buckets (
    id UUID NOT NULL,
    scope VARCHAR(64) NOT NULL,
    key_digest VARCHAR(64) NOT NULL,
    window_started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    request_count INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_booking_rate_limit_buckets PRIMARY KEY (id),
    CONSTRAINT booking_rate_limit_buckets_scope_key UNIQUE (scope, key_digest),
    CONSTRAINT ck_booking_rate_limit_buckets_booking_rate_limit_buckets_count_non_negative
        CHECK (request_count >= 0)
)

;
CREATE INDEX ix_booking_rate_limit_buckets_window
    ON booking_rate_limit_buckets (scope, window_started_at);

CREATE TABLE booking_slot_reservations (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	branch_id UUID NOT NULL,
	specialist_id UUID NOT NULL,
	customer_id UUID,
	service_id UUID NOT NULL,
	starts_at TIMESTAMP WITH TIME ZONE NOT NULL,
	ends_at TIMESTAMP WITH TIME ZONE NOT NULL,
	busy_starts_at TIMESTAMP WITH TIME ZONE NOT NULL,
	busy_ends_at TIMESTAMP WITH TIME ZONE NOT NULL,
	type VARCHAR(16) NOT NULL,
	status VARCHAR(16) NOT NULL,
	appointment_id UUID,
	expires_at TIMESTAMP WITH TIME ZONE,
	owner_key VARCHAR(128),
	idempotency_key VARCHAR(128),
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_booking_slot_reservations PRIMARY KEY (id),
	CONSTRAINT ck_booking_slot_reservations_booking_reservations_servi_baae CHECK (ends_at > starts_at),
	CONSTRAINT ck_booking_slot_reservations_booking_reservations_busy_interval CHECK (busy_ends_at > busy_starts_at),
	CONSTRAINT ck_booking_slot_reservations_booking_reservations_busy__7d17 CHECK (busy_starts_at <= starts_at AND busy_ends_at >= ends_at),
	CONSTRAINT ck_booking_slot_reservations_booking_reservations_expir_d40f CHECK ((type = 'hold' AND expires_at IS NOT NULL) OR (type = 'appointment' AND expires_at IS NULL)),
	CONSTRAINT booking_reservations_no_active_overlap EXCLUDE USING gist (organization_id WITH =, specialist_id WITH =, tstzrange(busy_starts_at, busy_ends_at, '[)') WITH &&) WHERE (status = 'active'),
	CONSTRAINT uq_booking_slot_reservations_appointment_id UNIQUE (appointment_id)
)

;
CREATE INDEX ix_booking_reservations_specialist_busy ON booking_slot_reservations (organization_id, specialist_id, status, busy_starts_at);
CREATE UNIQUE INDEX uq_booking_reservations_active_idempotency ON booking_slot_reservations (organization_id, owner_key, idempotency_key) WHERE idempotency_key IS NOT NULL AND status = 'active' AND type = 'hold';

CREATE TABLE booking_appointments (
	id UUID NOT NULL,
	public_number VARCHAR(40) NOT NULL,
	organization_id UUID NOT NULL,
	branch_id UUID NOT NULL,
	customer_id UUID NOT NULL,
	specialist_id UUID NOT NULL,
	service_id UUID NOT NULL,
	reservation_id UUID NOT NULL,
	status VARCHAR(16) NOT NULL,
	source VARCHAR(32) NOT NULL,
	starts_at TIMESTAMP WITH TIME ZONE NOT NULL,
	ends_at TIMESTAMP WITH TIME ZONE NOT NULL,
	busy_starts_at TIMESTAMP WITH TIME ZONE NOT NULL,
	busy_ends_at TIMESTAMP WITH TIME ZONE NOT NULL,
	service_name_snapshot VARCHAR(200) NOT NULL,
	specialist_name_snapshot VARCHAR(200) NOT NULL,
	duration_minutes_snapshot SMALLINT NOT NULL,
	price_snapshot NUMERIC(14, 2) NOT NULL,
	currency_snapshot VARCHAR(3) NOT NULL,
	customer_note TEXT,
	internal_note TEXT,
	cancellation_reason VARCHAR(500),
	cancelled_by UUID,
	created_by UUID,
	confirmed_at TIMESTAMP WITH TIME ZONE,
	checked_in_at TIMESTAMP WITH TIME ZONE,
	completed_at TIMESTAMP WITH TIME ZONE,
	cancelled_at TIMESTAMP WITH TIME ZONE,
	no_show_at TIMESTAMP WITH TIME ZONE,
	version INTEGER NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_booking_appointments PRIMARY KEY (id),
	CONSTRAINT ck_booking_appointments_booking_appointments_service_interval CHECK (ends_at > starts_at),
	CONSTRAINT ck_booking_appointments_booking_appointments_busy_interval CHECK (busy_ends_at > busy_starts_at),
	CONSTRAINT ck_booking_appointments_booking_appointments_price_non_negative CHECK (price_snapshot >= 0),
	CONSTRAINT ck_booking_appointments_booking_appointments_duration_positive CHECK (duration_minutes_snapshot > 0),
	CONSTRAINT ck_booking_appointments_booking_appointments_version_positive CHECK (version > 0),
	CONSTRAINT uq_booking_appointments_public_number UNIQUE (public_number),
	CONSTRAINT uq_booking_appointments_reservation_id UNIQUE (reservation_id)
)

;
CREATE INDEX ix_booking_appointments_organization_status_start ON booking_appointments (organization_id, status, starts_at);
CREATE INDEX ix_booking_appointments_specialist_status_start ON booking_appointments (organization_id, specialist_id, status, starts_at);
CREATE INDEX ix_booking_appointments_customer_status_start ON booking_appointments (organization_id, customer_id, status, starts_at);

CREATE TABLE booking_settings (
	organization_id UUID NOT NULL,
	currency VARCHAR(3) NOT NULL,
	slot_step_minutes SMALLINT NOT NULL,
	min_booking_lead_minutes INTEGER NOT NULL,
	max_booking_horizon_days SMALLINT NOT NULL,
	hold_ttl_seconds INTEGER NOT NULL,
	client_cancellation_cutoff_minutes INTEGER NOT NULL,
	auto_confirm_booking BOOLEAN NOT NULL,
	require_client_phone BOOLEAN NOT NULL,
	prevent_customer_overlapping_appointments BOOLEAN NOT NULL,
	max_upcoming_appointments_per_customer SMALLINT NOT NULL,
	reminder_offsets_minutes JSONB NOT NULL,
	daily_staff_agenda_time TIME WITHOUT TIME ZONE NOT NULL,
	allow_negative_stock BOOLEAN NOT NULL,
	require_open_cash_shift_for_cash_payment BOOLEAN NOT NULL,
	default_locale VARCHAR(16) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_booking_settings PRIMARY KEY (organization_id),
	CONSTRAINT ck_booking_settings_booking_settings_slot_step_positive CHECK (slot_step_minutes > 0),
	CONSTRAINT ck_booking_settings_booking_settings_lead_non_negative CHECK (min_booking_lead_minutes >= 0),
	CONSTRAINT ck_booking_settings_booking_settings_horizon_non_negative CHECK (max_booking_horizon_days >= 0),
	CONSTRAINT ck_booking_settings_booking_settings_hold_ttl_positive CHECK (hold_ttl_seconds > 0),
	CONSTRAINT ck_booking_settings_booking_settings_upcoming_limit_positive CHECK (max_upcoming_appointments_per_customer > 0),
	CONSTRAINT fk_booking_settings_organization_id_booking_organizations FOREIGN KEY(organization_id) REFERENCES booking_organizations (id) ON DELETE CASCADE
)

;

CREATE TABLE booking_branches (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	name VARCHAR(160) NOT NULL,
	address VARCHAR(500),
	timezone VARCHAR(64),
	phone VARCHAR(32),
	is_active BOOLEAN NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_booking_branches PRIMARY KEY (id),
	CONSTRAINT booking_branches_organization_name UNIQUE (organization_id, name),
	CONSTRAINT fk_booking_branches_organization_id_booking_organizations FOREIGN KEY(organization_id) REFERENCES booking_organizations (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_booking_branches_organization_active ON booking_branches (organization_id, is_active);

CREATE TABLE booking_service_categories (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	name VARCHAR(160) NOT NULL,
	sort_order INTEGER NOT NULL,
	is_active BOOLEAN NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_booking_service_categories PRIMARY KEY (id),
	CONSTRAINT booking_service_categories_organization_name UNIQUE (organization_id, name),
	CONSTRAINT fk_booking_service_categories_organization_id_booking_o_3305 FOREIGN KEY(organization_id) REFERENCES booking_organizations (id) ON DELETE CASCADE
)

;

CREATE TABLE booking_specialists (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	core_user_id UUID,
	display_name VARCHAR(200) NOT NULL,
	description TEXT,
	phone VARCHAR(32),
	is_active BOOLEAN NOT NULL,
	accepts_bookings BOOLEAN NOT NULL,
	archived_at TIMESTAMP WITH TIME ZONE,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_booking_specialists PRIMARY KEY (id),
	CONSTRAINT fk_booking_specialists_organization_id_booking_organizations FOREIGN KEY(organization_id) REFERENCES booking_organizations (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_booking_specialists_organization_active ON booking_specialists (organization_id, is_active, accepts_bookings);

CREATE TABLE booking_customers (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	first_name VARCHAR(160) NOT NULL,
	last_name VARCHAR(160),
	normalized_phone VARCHAR(32),
	locale VARCHAR(16) NOT NULL,
	timezone VARCHAR(64),
	notes TEXT,
	is_blocked BOOLEAN NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_booking_customers PRIMARY KEY (id),
	CONSTRAINT fk_booking_customers_organization_id_booking_organizations FOREIGN KEY(organization_id) REFERENCES booking_organizations (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_booking_customers_organization_phone ON booking_customers (organization_id, normalized_phone);
CREATE INDEX ix_booking_customers_organization_created ON booking_customers (organization_id, created_at);

CREATE TABLE booking_appointment_history (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	appointment_id UUID NOT NULL,
	event_type VARCHAR(64) NOT NULL,
	old_status VARCHAR(16),
	new_status VARCHAR(16),
	old_starts_at TIMESTAMP WITH TIME ZONE,
	new_starts_at TIMESTAMP WITH TIME ZONE,
	actor_type VARCHAR(16) NOT NULL,
	actor_id UUID,
	reason VARCHAR(500),
	metadata_json JSONB NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_booking_appointment_history PRIMARY KEY (id),
	CONSTRAINT fk_booking_appointment_history_appointment_id_booking_a_8681 FOREIGN KEY(appointment_id) REFERENCES booking_appointments (id) ON DELETE CASCADE,
	CONSTRAINT fk_booking_appointment_history_organization_id_booking_organizations FOREIGN KEY(organization_id) REFERENCES booking_organizations (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_booking_appointment_history_appointment_created ON booking_appointment_history (organization_id, appointment_id, created_at);

CREATE TABLE booking_idempotency_records (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	actor_id UUID,
	operation VARCHAR(80) NOT NULL,
	key VARCHAR(128) NOT NULL,
	request_hash VARCHAR(64) NOT NULL,
	response_status SMALLINT NOT NULL,
	response_payload JSONB NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_booking_idempotency_records PRIMARY KEY (id),
	CONSTRAINT booking_idempotency_scope UNIQUE (organization_id, actor_id, operation, key),
	CONSTRAINT ck_booking_idempotency_records_booking_idempotency_resp_145b CHECK (response_status >= 200 AND response_status < 600),
	CONSTRAINT fk_booking_idempotency_records_organization_id_booking__0e25 FOREIGN KEY(organization_id) REFERENCES booking_organizations (id) ON DELETE CASCADE
)

;

CREATE TABLE booking_notification_outbox (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	appointment_id UUID,
	event_type VARCHAR(80) NOT NULL,
	channel VARCHAR(32) NOT NULL,
	recipient_type VARCHAR(32) NOT NULL,
	recipient_id UUID,
	bot_app_id VARCHAR(63) NOT NULL,
	chat_id VARCHAR(128),
	locale VARCHAR(16) NOT NULL,
	template_key VARCHAR(160) NOT NULL,
	payload JSONB NOT NULL,
	scheduled_at TIMESTAMP WITH TIME ZONE NOT NULL,
	status VARCHAR(16) NOT NULL,
	attempts SMALLINT NOT NULL,
	max_attempts SMALLINT NOT NULL,
	dedupe_key VARCHAR(200) NOT NULL,
	last_error VARCHAR(500),
	sent_at TIMESTAMP WITH TIME ZONE,
	locked_at TIMESTAMP WITH TIME ZONE,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_booking_notification_outbox PRIMARY KEY (id),
	CONSTRAINT booking_notification_outbox_dedupe UNIQUE (organization_id, dedupe_key),
	CONSTRAINT ck_booking_notification_outbox_booking_outbox_attempts__8962 CHECK (attempts >= 0),
	CONSTRAINT ck_booking_notification_outbox_booking_outbox_max_attem_56ad CHECK (max_attempts > 0),
	CONSTRAINT fk_booking_notification_outbox_organization_id_booking__ae30 FOREIGN KEY(organization_id) REFERENCES booking_organizations (id) ON DELETE CASCADE,
	CONSTRAINT fk_booking_notification_outbox_appointment_id_booking_a_e3da FOREIGN KEY(appointment_id) REFERENCES booking_appointments (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_booking_notification_outbox_poll ON booking_notification_outbox (status, scheduled_at, created_at);

CREATE TABLE booking_products (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	name VARCHAR(200) NOT NULL,
	sku VARCHAR(100),
	unit VARCHAR(32) NOT NULL,
	low_stock_threshold NUMERIC(16, 3),
	is_active BOOLEAN NOT NULL,
	track_stock BOOLEAN NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_booking_products PRIMARY KEY (id),
	CONSTRAINT ck_booking_products_booking_products_low_stock_non_negative CHECK (low_stock_threshold IS NULL OR low_stock_threshold >= 0),
	CONSTRAINT fk_booking_products_organization_id_booking_organizations FOREIGN KEY(organization_id) REFERENCES booking_organizations (id) ON DELETE CASCADE
)

;
CREATE UNIQUE INDEX uq_booking_products_organization_sku ON booking_products (organization_id, sku) WHERE sku IS NOT NULL;
CREATE INDEX ix_booking_products_organization_active ON booking_products (organization_id, is_active);

CREATE TABLE booking_telegram_update_receipts (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	bot_app_id VARCHAR(63) NOT NULL,
	provider_update_id VARCHAR(128) NOT NULL,
	processed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_booking_telegram_update_receipts PRIMARY KEY (id),
	CONSTRAINT booking_telegram_update_receipts_scope UNIQUE (organization_id, bot_app_id, provider_update_id),
	CONSTRAINT fk_booking_telegram_update_receipts_organization_id_boo_92e9 FOREIGN KEY(organization_id) REFERENCES booking_organizations (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_booking_telegram_update_receipts_processed ON booking_telegram_update_receipts (organization_id, processed_at);

CREATE TABLE booking_audit_log (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	event_type VARCHAR(80) NOT NULL,
	actor_type VARCHAR(16) NOT NULL,
	actor_id UUID,
	target_type VARCHAR(64),
	target_id UUID,
	reason VARCHAR(500),
	metadata_json JSONB NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_booking_audit_log PRIMARY KEY (id),
	CONSTRAINT fk_booking_audit_log_organization_id_booking_organizations FOREIGN KEY(organization_id) REFERENCES booking_organizations (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_booking_audit_log_target ON booking_audit_log (organization_id, target_type, target_id);
CREATE INDEX ix_booking_audit_log_organization_created ON booking_audit_log (organization_id, created_at);

CREATE TABLE booking_access_grants (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	subject_id UUID NOT NULL,
	role VARCHAR(32) NOT NULL,
	permissions JSONB NOT NULL,
	customer_id UUID,
	specialist_id UUID,
	is_active BOOLEAN NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_booking_access_grants PRIMARY KEY (id),
	CONSTRAINT booking_access_grants_organization_subject UNIQUE (organization_id, subject_id),
	CONSTRAINT fk_booking_access_grants_organization_id_booking_organizations FOREIGN KEY(organization_id) REFERENCES booking_organizations (id) ON DELETE CASCADE,
	CONSTRAINT fk_booking_access_grants_customer_id_booking_customers FOREIGN KEY(customer_id) REFERENCES booking_customers (id) ON DELETE SET NULL,
	CONSTRAINT fk_booking_access_grants_specialist_id_booking_specialists FOREIGN KEY(specialist_id) REFERENCES booking_specialists (id) ON DELETE SET NULL
)

;
CREATE INDEX ix_booking_access_grants_organization_active ON booking_access_grants (organization_id, is_active);

CREATE TABLE booking_services (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	category_id UUID,
	name VARCHAR(200) NOT NULL,
	description TEXT,
	default_duration_minutes SMALLINT NOT NULL,
	default_price NUMERIC(14, 2) NOT NULL,
	currency VARCHAR(3) NOT NULL,
	buffer_before_minutes SMALLINT NOT NULL,
	buffer_after_minutes SMALLINT NOT NULL,
	is_active BOOLEAN NOT NULL,
	booking_enabled BOOLEAN NOT NULL,
	sort_order INTEGER NOT NULL,
	archived_at TIMESTAMP WITH TIME ZONE,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_booking_services PRIMARY KEY (id),
	CONSTRAINT ck_booking_services_booking_services_duration_positive CHECK (default_duration_minutes > 0),
	CONSTRAINT ck_booking_services_booking_services_price_non_negative CHECK (default_price >= 0),
	CONSTRAINT ck_booking_services_booking_services_buffer_before_non_negative CHECK (buffer_before_minutes >= 0),
	CONSTRAINT ck_booking_services_booking_services_buffer_after_non_negative CHECK (buffer_after_minutes >= 0),
	CONSTRAINT fk_booking_services_organization_id_booking_organizations FOREIGN KEY(organization_id) REFERENCES booking_organizations (id) ON DELETE CASCADE,
	CONSTRAINT fk_booking_services_category_id_booking_service_categories FOREIGN KEY(category_id) REFERENCES booking_service_categories (id) ON DELETE SET NULL
)

;
CREATE INDEX ix_booking_services_organization_active ON booking_services (organization_id, is_active, booking_enabled);

CREATE TABLE booking_working_schedules (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	specialist_id UUID NOT NULL,
	branch_id UUID NOT NULL,
	weekday SMALLINT NOT NULL,
	local_start_time TIME WITHOUT TIME ZONE NOT NULL,
	local_end_time TIME WITHOUT TIME ZONE NOT NULL,
	is_active BOOLEAN NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_booking_working_schedules PRIMARY KEY (id),
	CONSTRAINT ck_booking_working_schedules_booking_schedule_weekday_range CHECK (weekday >= 0 AND weekday <= 6),
	CONSTRAINT ck_booking_working_schedules_booking_schedule_same_day_interval CHECK (local_end_time > local_start_time),
	CONSTRAINT booking_working_schedules_no_active_overlap EXCLUDE USING gist (organization_id WITH =, specialist_id WITH =, branch_id WITH =, weekday WITH =, tsrange((DATE '2000-01-03' + local_start_time), (DATE '2000-01-03' + local_end_time), '[)') WITH &&) WHERE (is_active),
	CONSTRAINT fk_booking_working_schedules_organization_id_booking_or_55a6 FOREIGN KEY(organization_id) REFERENCES booking_organizations (id) ON DELETE CASCADE,
	CONSTRAINT fk_booking_working_schedules_specialist_id_booking_specialists FOREIGN KEY(specialist_id) REFERENCES booking_specialists (id) ON DELETE CASCADE,
	CONSTRAINT fk_booking_working_schedules_branch_id_booking_branches FOREIGN KEY(branch_id) REFERENCES booking_branches (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_booking_working_schedules_scope ON booking_working_schedules (organization_id, specialist_id, branch_id, weekday);

CREATE TABLE booking_availability_exceptions (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	specialist_id UUID NOT NULL,
	branch_id UUID NOT NULL,
	type VARCHAR(32) NOT NULL,
	starts_at TIMESTAMP WITH TIME ZONE NOT NULL,
	ends_at TIMESTAMP WITH TIME ZONE NOT NULL,
	reason VARCHAR(500),
	created_by UUID,
	is_active BOOLEAN NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_booking_availability_exceptions PRIMARY KEY (id),
	CONSTRAINT ck_booking_availability_exceptions_booking_availability_ebd5 CHECK (ends_at > starts_at),
	CONSTRAINT fk_booking_availability_exceptions_organization_id_book_83ca FOREIGN KEY(organization_id) REFERENCES booking_organizations (id) ON DELETE CASCADE,
	CONSTRAINT fk_booking_availability_exceptions_specialist_id_bookin_99a1 FOREIGN KEY(specialist_id) REFERENCES booking_specialists (id) ON DELETE CASCADE,
	CONSTRAINT fk_booking_availability_exceptions_branch_id_booking_branches FOREIGN KEY(branch_id) REFERENCES booking_branches (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_booking_availability_exceptions_lookup ON booking_availability_exceptions (organization_id, specialist_id, branch_id, starts_at);

CREATE TABLE booking_customer_identities (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	customer_id UUID NOT NULL,
	provider VARCHAR(32) NOT NULL,
	bot_app_id VARCHAR(63) NOT NULL,
	external_user_id VARCHAR(128) NOT NULL,
	external_chat_id VARCHAR(128),
	username VARCHAR(64),
	metadata_json JSONB NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_booking_customer_identities PRIMARY KEY (id),
	CONSTRAINT booking_customer_identities_provider_user UNIQUE (organization_id, provider, bot_app_id, external_user_id),
	CONSTRAINT fk_booking_customer_identities_organization_id_booking__63cf FOREIGN KEY(organization_id) REFERENCES booking_organizations (id) ON DELETE CASCADE,
	CONSTRAINT fk_booking_customer_identities_customer_id_booking_customers FOREIGN KEY(customer_id) REFERENCES booking_customers (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_booking_customer_identities_customer ON booking_customer_identities (organization_id, customer_id);

CREATE TABLE booking_staff_telegram_bindings (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	specialist_id UUID NOT NULL,
	bot_app_id VARCHAR(63) NOT NULL,
	telegram_user_id VARCHAR(128) NOT NULL,
	telegram_chat_id VARCHAR(128),
	is_active BOOLEAN NOT NULL,
	bound_by UUID,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_booking_staff_telegram_bindings PRIMARY KEY (id),
	CONSTRAINT fk_booking_staff_telegram_bindings_organization_id_book_fad1 FOREIGN KEY(organization_id) REFERENCES booking_organizations (id) ON DELETE CASCADE,
	CONSTRAINT fk_booking_staff_telegram_bindings_specialist_id_bookin_397c FOREIGN KEY(specialist_id) REFERENCES booking_specialists (id) ON DELETE CASCADE
)

;
CREATE UNIQUE INDEX uq_booking_staff_bindings_active_specialist ON booking_staff_telegram_bindings (organization_id, specialist_id, bot_app_id) WHERE is_active;
CREATE UNIQUE INDEX uq_booking_staff_bindings_active_telegram ON booking_staff_telegram_bindings (organization_id, bot_app_id, telegram_user_id) WHERE is_active;

CREATE TABLE booking_staff_bind_codes (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	specialist_id UUID NOT NULL,
	code_digest VARCHAR(64) NOT NULL,
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
	used_at TIMESTAMP WITH TIME ZONE,
	created_by UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_booking_staff_bind_codes PRIMARY KEY (id),
	CONSTRAINT ck_booking_staff_bind_codes_booking_bind_codes_expiry CHECK (expires_at > created_at),
	CONSTRAINT fk_booking_staff_bind_codes_organization_id_booking_org_ffdc FOREIGN KEY(organization_id) REFERENCES booking_organizations (id) ON DELETE CASCADE,
	CONSTRAINT fk_booking_staff_bind_codes_specialist_id_booking_specialists FOREIGN KEY(specialist_id) REFERENCES booking_specialists (id) ON DELETE CASCADE,
	CONSTRAINT uq_booking_staff_bind_codes_code_digest UNIQUE (code_digest)
)

;
CREATE INDEX ix_booking_staff_bind_codes_lookup ON booking_staff_bind_codes (organization_id, specialist_id, expires_at);

CREATE TABLE booking_cashboxes (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	branch_id UUID NOT NULL,
	name VARCHAR(160) NOT NULL,
	currency VARCHAR(3) NOT NULL,
	is_active BOOLEAN NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_booking_cashboxes PRIMARY KEY (id),
	CONSTRAINT booking_cashboxes_scope_name UNIQUE (organization_id, branch_id, name),
	CONSTRAINT fk_booking_cashboxes_organization_id_booking_organizations FOREIGN KEY(organization_id) REFERENCES booking_organizations (id) ON DELETE CASCADE,
	CONSTRAINT fk_booking_cashboxes_branch_id_booking_branches FOREIGN KEY(branch_id) REFERENCES booking_branches (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_booking_cashboxes_organization_branch ON booking_cashboxes (organization_id, branch_id);

CREATE TABLE booking_warehouses (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	branch_id UUID NOT NULL,
	name VARCHAR(160) NOT NULL,
	is_default BOOLEAN NOT NULL,
	is_active BOOLEAN NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_booking_warehouses PRIMARY KEY (id),
	CONSTRAINT booking_warehouses_scope_name UNIQUE (organization_id, branch_id, name),
	CONSTRAINT fk_booking_warehouses_organization_id_booking_organizations FOREIGN KEY(organization_id) REFERENCES booking_organizations (id) ON DELETE CASCADE,
	CONSTRAINT fk_booking_warehouses_branch_id_booking_branches FOREIGN KEY(branch_id) REFERENCES booking_branches (id) ON DELETE CASCADE
)

;
CREATE UNIQUE INDEX uq_booking_warehouses_default_branch ON booking_warehouses (branch_id) WHERE is_default AND is_active;

CREATE TABLE booking_conversations (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	bot_app_id VARCHAR(63) NOT NULL,
	telegram_user_id VARCHAR(128) NOT NULL,
	telegram_chat_id VARCHAR(128) NOT NULL,
	customer_id UUID,
	state VARCHAR(32) NOT NULL,
	data JSONB NOT NULL,
	callback_nonce VARCHAR(64) NOT NULL,
	expires_at TIMESTAMP WITH TIME ZONE,
	version INTEGER NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_booking_conversations PRIMARY KEY (id),
	CONSTRAINT booking_conversations_scope UNIQUE (organization_id, bot_app_id, telegram_user_id, telegram_chat_id),
	CONSTRAINT ck_booking_conversations_booking_conversations_version_positive CHECK (version > 0),
	CONSTRAINT fk_booking_conversations_organization_id_booking_organizations FOREIGN KEY(organization_id) REFERENCES booking_organizations (id) ON DELETE CASCADE,
	CONSTRAINT fk_booking_conversations_customer_id_booking_customers FOREIGN KEY(customer_id) REFERENCES booking_customers (id) ON DELETE SET NULL
)

;
CREATE INDEX ix_booking_conversations_expiry ON booking_conversations (organization_id, expires_at);

CREATE TABLE booking_specialist_services (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	specialist_id UUID NOT NULL,
	service_id UUID NOT NULL,
	branch_id UUID NOT NULL,
	custom_duration_minutes SMALLINT,
	custom_price NUMERIC(14, 2),
	custom_buffer_before_minutes SMALLINT,
	custom_buffer_after_minutes SMALLINT,
	is_active BOOLEAN NOT NULL,
	booking_enabled BOOLEAN NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_booking_specialist_services PRIMARY KEY (id),
	CONSTRAINT booking_specialist_services_scope UNIQUE (organization_id, specialist_id, service_id, branch_id),
	CONSTRAINT ck_booking_specialist_services_booking_specialist_servi_28e8 CHECK (custom_duration_minutes IS NULL OR custom_duration_minutes > 0),
	CONSTRAINT ck_booking_specialist_services_booking_specialist_servi_9a5c CHECK (custom_price IS NULL OR custom_price >= 0),
	CONSTRAINT ck_booking_specialist_services_booking_specialist_servi_07d1 CHECK (custom_buffer_before_minutes IS NULL OR custom_buffer_before_minutes >= 0),
	CONSTRAINT ck_booking_specialist_services_booking_specialist_servi_777b CHECK (custom_buffer_after_minutes IS NULL OR custom_buffer_after_minutes >= 0),
	CONSTRAINT fk_booking_specialist_services_organization_id_booking__dc8b FOREIGN KEY(organization_id) REFERENCES booking_organizations (id) ON DELETE CASCADE,
	CONSTRAINT fk_booking_specialist_services_specialist_id_booking_sp_4d99 FOREIGN KEY(specialist_id) REFERENCES booking_specialists (id) ON DELETE RESTRICT,
	CONSTRAINT fk_booking_specialist_services_service_id_booking_services FOREIGN KEY(service_id) REFERENCES booking_services (id) ON DELETE RESTRICT,
	CONSTRAINT fk_booking_specialist_services_branch_id_booking_branches FOREIGN KEY(branch_id) REFERENCES booking_branches (id) ON DELETE RESTRICT
)

;
CREATE INDEX ix_booking_specialist_services_lookup ON booking_specialist_services (organization_id, branch_id, service_id, is_active);

CREATE TABLE booking_cash_shifts (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	cashbox_id UUID NOT NULL,
	opened_by UUID NOT NULL,
	opened_at TIMESTAMP WITH TIME ZONE NOT NULL,
	opening_amount NUMERIC(14, 2) NOT NULL,
	closed_by UUID,
	closed_at TIMESTAMP WITH TIME ZONE,
	expected_closing_amount NUMERIC(14, 2),
	actual_closing_amount NUMERIC(14, 2),
	difference NUMERIC(14, 2),
	status VARCHAR(16) NOT NULL,
	notes VARCHAR(500),
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_booking_cash_shifts PRIMARY KEY (id),
	CONSTRAINT ck_booking_cash_shifts_booking_cash_shifts_opening_non_negative CHECK (opening_amount >= 0),
	CONSTRAINT fk_booking_cash_shifts_organization_id_booking_organizations FOREIGN KEY(organization_id) REFERENCES booking_organizations (id) ON DELETE CASCADE,
	CONSTRAINT fk_booking_cash_shifts_cashbox_id_booking_cashboxes FOREIGN KEY(cashbox_id) REFERENCES booking_cashboxes (id) ON DELETE RESTRICT
)

;
CREATE INDEX ix_booking_cash_shifts_organization_status ON booking_cash_shifts (organization_id, status, opened_at);
CREATE UNIQUE INDEX uq_booking_cash_shifts_one_open ON booking_cash_shifts (cashbox_id) WHERE status = 'open';

CREATE TABLE booking_stock_balances (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	warehouse_id UUID NOT NULL,
	product_id UUID NOT NULL,
	quantity NUMERIC(16, 3) NOT NULL,
	version INTEGER NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_booking_stock_balances PRIMARY KEY (id),
	CONSTRAINT booking_stock_balances_scope UNIQUE (warehouse_id, product_id),
	CONSTRAINT ck_booking_stock_balances_booking_stock_balances_versio_6824 CHECK (version > 0),
	CONSTRAINT fk_booking_stock_balances_organization_id_booking_organizations FOREIGN KEY(organization_id) REFERENCES booking_organizations (id) ON DELETE CASCADE,
	CONSTRAINT fk_booking_stock_balances_warehouse_id_booking_warehouses FOREIGN KEY(warehouse_id) REFERENCES booking_warehouses (id) ON DELETE CASCADE,
	CONSTRAINT fk_booking_stock_balances_product_id_booking_products FOREIGN KEY(product_id) REFERENCES booking_products (id) ON DELETE CASCADE
)

;
CREATE INDEX ix_booking_stock_balances_product ON booking_stock_balances (organization_id, product_id);

CREATE TABLE booking_stock_movements (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	warehouse_id UUID NOT NULL,
	type VARCHAR(32) NOT NULL,
	reference_type VARCHAR(64),
	reference_id UUID,
	reason VARCHAR(500),
	created_by UUID,
	idempotency_key VARCHAR(128),
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_booking_stock_movements PRIMARY KEY (id),
	CONSTRAINT fk_booking_stock_movements_organization_id_booking_orga_aa3f FOREIGN KEY(organization_id) REFERENCES booking_organizations (id) ON DELETE RESTRICT,
	CONSTRAINT fk_booking_stock_movements_warehouse_id_booking_warehouses FOREIGN KEY(warehouse_id) REFERENCES booking_warehouses (id) ON DELETE RESTRICT
)

;
CREATE INDEX ix_booking_stock_movements_warehouse_created ON booking_stock_movements (warehouse_id, created_at);
CREATE UNIQUE INDEX uq_booking_stock_movements_idempotency ON booking_stock_movements (organization_id, idempotency_key) WHERE idempotency_key IS NOT NULL;

CREATE TABLE booking_service_materials (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	service_id UUID NOT NULL,
	product_id UUID NOT NULL,
	warehouse_id UUID,
	quantity_required NUMERIC(16, 3) NOT NULL,
	is_active BOOLEAN NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_booking_service_materials PRIMARY KEY (id),
	CONSTRAINT booking_service_materials_scope UNIQUE NULLS NOT DISTINCT (organization_id, service_id, product_id, warehouse_id),
	CONSTRAINT ck_booking_service_materials_booking_service_materials__8ce6 CHECK (quantity_required > 0),
	CONSTRAINT fk_booking_service_materials_organization_id_booking_or_2927 FOREIGN KEY(organization_id) REFERENCES booking_organizations (id) ON DELETE CASCADE,
	CONSTRAINT fk_booking_service_materials_service_id_booking_services FOREIGN KEY(service_id) REFERENCES booking_services (id) ON DELETE CASCADE,
	CONSTRAINT fk_booking_service_materials_product_id_booking_products FOREIGN KEY(product_id) REFERENCES booking_products (id) ON DELETE RESTRICT,
	CONSTRAINT fk_booking_service_materials_warehouse_id_booking_warehouses FOREIGN KEY(warehouse_id) REFERENCES booking_warehouses (id) ON DELETE RESTRICT
)

;

CREATE TABLE booking_appointment_material_snapshots (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	appointment_id UUID NOT NULL,
	product_id UUID NOT NULL,
	warehouse_id UUID,
	quantity_required NUMERIC(16, 3) NOT NULL,
	CONSTRAINT pk_booking_appointment_material_snapshots PRIMARY KEY (id),
	CONSTRAINT booking_appointment_material_snapshots_scope UNIQUE NULLS NOT DISTINCT (appointment_id, product_id, warehouse_id),
	CONSTRAINT ck_booking_appointment_material_snapshots_booking_appoi_902c CHECK (quantity_required > 0),
	CONSTRAINT fk_booking_appointment_material_snapshots_organization_id_booking_organizations FOREIGN KEY(organization_id) REFERENCES booking_organizations (id) ON DELETE CASCADE,
	CONSTRAINT fk_booking_appointment_material_snapshots_appointment_i_ff8c FOREIGN KEY(appointment_id) REFERENCES booking_appointments (id) ON DELETE CASCADE,
	CONSTRAINT fk_booking_appointment_material_snapshots_product_id_bo_7166 FOREIGN KEY(product_id) REFERENCES booking_products (id) ON DELETE RESTRICT,
	CONSTRAINT fk_booking_appointment_material_snapshots_warehouse_id__83fe FOREIGN KEY(warehouse_id) REFERENCES booking_warehouses (id) ON DELETE RESTRICT
)

;

CREATE TABLE booking_payments (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	appointment_id UUID NOT NULL,
	amount NUMERIC(14, 2) NOT NULL,
	currency VARCHAR(3) NOT NULL,
	method VARCHAR(16) NOT NULL,
	cash_shift_id UUID,
	created_by UUID,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	idempotency_key VARCHAR(128) NOT NULL,
	external_reference VARCHAR(200),
	note VARCHAR(500),
	CONSTRAINT pk_booking_payments PRIMARY KEY (id),
	CONSTRAINT ck_booking_payments_booking_payments_amount_positive CHECK (amount > 0),
	CONSTRAINT booking_payments_idempotency UNIQUE (organization_id, created_by, idempotency_key),
	CONSTRAINT fk_booking_payments_organization_id_booking_organizations FOREIGN KEY(organization_id) REFERENCES booking_organizations (id) ON DELETE RESTRICT,
	CONSTRAINT fk_booking_payments_appointment_id_booking_appointments FOREIGN KEY(appointment_id) REFERENCES booking_appointments (id) ON DELETE RESTRICT,
	CONSTRAINT fk_booking_payments_cash_shift_id_booking_cash_shifts FOREIGN KEY(cash_shift_id) REFERENCES booking_cash_shifts (id) ON DELETE RESTRICT
)

;
CREATE INDEX ix_booking_payments_appointment_created ON booking_payments (organization_id, appointment_id, created_at);

CREATE TABLE booking_cash_transactions (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	cashbox_id UUID NOT NULL,
	cash_shift_id UUID,
	type VARCHAR(32) NOT NULL,
	amount_delta NUMERIC(14, 2) NOT NULL,
	currency VARCHAR(3) NOT NULL,
	reference_type VARCHAR(64),
	reference_id UUID,
	reason VARCHAR(500),
	created_by UUID,
	idempotency_key VARCHAR(128),
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	CONSTRAINT pk_booking_cash_transactions PRIMARY KEY (id),
	CONSTRAINT fk_booking_cash_transactions_organization_id_booking_or_3b48 FOREIGN KEY(organization_id) REFERENCES booking_organizations (id) ON DELETE RESTRICT,
	CONSTRAINT fk_booking_cash_transactions_cashbox_id_booking_cashboxes FOREIGN KEY(cashbox_id) REFERENCES booking_cashboxes (id) ON DELETE RESTRICT,
	CONSTRAINT fk_booking_cash_transactions_cash_shift_id_booking_cash_shifts FOREIGN KEY(cash_shift_id) REFERENCES booking_cash_shifts (id) ON DELETE RESTRICT
)

;
CREATE INDEX ix_booking_cash_transactions_cashbox_created ON booking_cash_transactions (cashbox_id, created_at);
CREATE UNIQUE INDEX uq_booking_cash_transactions_idempotency ON booking_cash_transactions (organization_id, idempotency_key) WHERE idempotency_key IS NOT NULL;

CREATE TABLE booking_stock_movement_items (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	movement_id UUID NOT NULL,
	product_id UUID NOT NULL,
	quantity_delta NUMERIC(16, 3) NOT NULL,
	unit_cost NUMERIC(14, 2),
	CONSTRAINT pk_booking_stock_movement_items PRIMARY KEY (id),
	CONSTRAINT ck_booking_stock_movement_items_booking_stock_movement__9ac8 CHECK (quantity_delta <> 0),
	CONSTRAINT ck_booking_stock_movement_items_booking_stock_movement__7a66 CHECK (unit_cost IS NULL OR unit_cost >= 0),
	CONSTRAINT fk_booking_stock_movement_items_organization_id_booking_organizations FOREIGN KEY(organization_id) REFERENCES booking_organizations (id) ON DELETE RESTRICT,
	CONSTRAINT fk_booking_stock_movement_items_movement_id_booking_sto_7489 FOREIGN KEY(movement_id) REFERENCES booking_stock_movements (id) ON DELETE CASCADE,
	CONSTRAINT fk_booking_stock_movement_items_product_id_booking_products FOREIGN KEY(product_id) REFERENCES booking_products (id) ON DELETE RESTRICT
)

;
CREATE INDEX ix_booking_stock_movement_items_product ON booking_stock_movement_items (organization_id, product_id);

CREATE TABLE booking_refunds (
	id UUID NOT NULL,
	organization_id UUID NOT NULL,
	payment_id UUID NOT NULL,
	amount NUMERIC(14, 2) NOT NULL,
	currency VARCHAR(3) NOT NULL,
	cash_shift_id UUID,
	reason VARCHAR(500) NOT NULL,
	created_by UUID,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	idempotency_key VARCHAR(128) NOT NULL,
	CONSTRAINT pk_booking_refunds PRIMARY KEY (id),
	CONSTRAINT ck_booking_refunds_booking_refunds_amount_positive CHECK (amount > 0),
	CONSTRAINT booking_refunds_idempotency UNIQUE (organization_id, created_by, idempotency_key),
	CONSTRAINT fk_booking_refunds_organization_id_booking_organizations FOREIGN KEY(organization_id) REFERENCES booking_organizations (id) ON DELETE RESTRICT,
	CONSTRAINT fk_booking_refunds_payment_id_booking_payments FOREIGN KEY(payment_id) REFERENCES booking_payments (id) ON DELETE RESTRICT,
	CONSTRAINT fk_booking_refunds_cash_shift_id_booking_cash_shifts FOREIGN KEY(cash_shift_id) REFERENCES booking_cash_shifts (id) ON DELETE RESTRICT
)

;
CREATE INDEX ix_booking_refunds_payment_created ON booking_refunds (payment_id, created_at);
ALTER TABLE booking_appointments ADD CONSTRAINT fk_booking_appointments_service_id_booking_services FOREIGN KEY(service_id) REFERENCES booking_services (id) ON DELETE RESTRICT;
ALTER TABLE booking_appointments ADD CONSTRAINT fk_booking_appointments_organization_id_booking_organizations FOREIGN KEY(organization_id) REFERENCES booking_organizations (id) ON DELETE RESTRICT;
ALTER TABLE booking_appointments ADD CONSTRAINT fk_booking_appointments_customer_id_booking_customers FOREIGN KEY(customer_id) REFERENCES booking_customers (id) ON DELETE RESTRICT;
ALTER TABLE booking_slot_reservations ADD CONSTRAINT fk_booking_slot_reservations_service_id_booking_services FOREIGN KEY(service_id) REFERENCES booking_services (id) ON DELETE RESTRICT;
ALTER TABLE booking_slot_reservations ADD CONSTRAINT fk_booking_slot_reservations_specialist_id_booking_specialists FOREIGN KEY(specialist_id) REFERENCES booking_specialists (id) ON DELETE RESTRICT;
ALTER TABLE booking_slot_reservations ADD CONSTRAINT fk_booking_slot_reservations_organization_id_booking_or_5f7f FOREIGN KEY(organization_id) REFERENCES booking_organizations (id) ON DELETE CASCADE;
ALTER TABLE booking_appointments ADD CONSTRAINT fk_booking_appointments_branch_id_booking_branches FOREIGN KEY(branch_id) REFERENCES booking_branches (id) ON DELETE RESTRICT;
ALTER TABLE booking_appointments ADD CONSTRAINT fk_booking_appointments_reservation_id_booking_slot_res_8098 FOREIGN KEY(reservation_id) REFERENCES booking_slot_reservations (id) ON DELETE RESTRICT;
ALTER TABLE booking_appointments ADD CONSTRAINT fk_booking_appointments_specialist_id_booking_specialists FOREIGN KEY(specialist_id) REFERENCES booking_specialists (id) ON DELETE RESTRICT;
ALTER TABLE booking_slot_reservations ADD CONSTRAINT fk_booking_slot_reservations_appointment_id_booking_app_909e FOREIGN KEY(appointment_id) REFERENCES booking_appointments (id) ON DELETE SET NULL;
ALTER TABLE booking_slot_reservations ADD CONSTRAINT fk_booking_slot_reservations_customer_id_booking_customers FOREIGN KEY(customer_id) REFERENCES booking_customers (id) ON DELETE SET NULL;
ALTER TABLE booking_slot_reservations ADD CONSTRAINT fk_booking_slot_reservations_branch_id_booking_branches FOREIGN KEY(branch_id) REFERENCES booking_branches (id) ON DELETE RESTRICT;
"""

_TABLES = (
    "booking_refunds",
    "booking_stock_movement_items",
    "booking_cash_transactions",
    "booking_payments",
    "booking_appointment_material_snapshots",
    "booking_service_materials",
    "booking_stock_movements",
    "booking_stock_balances",
    "booking_cash_shifts",
    "booking_specialist_services",
    "booking_conversations",
    "booking_warehouses",
    "booking_cashboxes",
    "booking_staff_bind_codes",
    "booking_staff_telegram_bindings",
    "booking_customer_identities",
    "booking_availability_exceptions",
    "booking_working_schedules",
    "booking_services",
    "booking_access_grants",
    "booking_audit_log",
    "booking_telegram_update_receipts",
    "booking_products",
    "booking_notification_outbox",
    "booking_idempotency_records",
    "booking_appointment_history",
    "booking_customers",
    "booking_specialists",
    "booking_service_categories",
    "booking_branches",
    "booking_settings",
    "booking_appointments",
    "booking_slot_reservations",
    "booking_rate_limit_buckets",
    "booking_telegram_bot_installations",
    "booking_organizations",
)


def _execute_statements(script: str) -> None:
    """Execute one PostgreSQL DDL statement at a time through Alembic."""

    for statement in script.split(";"):
        normalized = statement.strip()
        if normalized:
            op.execute(sa.text(normalized))


def upgrade() -> None:
    """Create booking tables, indexes, and PostgreSQL exclusion protection."""

    _execute_statements(_UPGRADE_SQL)


def downgrade() -> None:
    """Drop only booking-owned tables while keeping the shared btree_gist extension."""

    for table_name in _TABLES:
        op.execute(sa.text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
