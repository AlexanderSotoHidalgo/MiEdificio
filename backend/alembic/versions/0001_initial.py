"""Complete MiEdificio MVP schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-05
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

fee_status = postgresql.ENUM(
    "Pendiente", "Pago en revisión", "Pagada", "Anulada", name="fee_status", create_type=False
)
payment_status = postgresql.ENUM(
    "En revisión", "Aprobado", "Observado", name="payment_status", create_type=False
)
payment_action = postgresql.ENUM(
    "Reportado", "Aprobado", "Observado", "Reenviado", name="payment_action", create_type=False
)
fee_audit_action = postgresql.ENUM(
    "Creada", "Ajustada", "Anulada", name="fee_audit_action", create_type=False
)


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in (fee_status, payment_status, payment_action, fee_audit_action):
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(30), nullable=False, unique=True),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *timestamps(),
    )
    op.create_table(
        "buildings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("legal_name", sa.String(200)),
        sa.Column("tax_id", sa.String(11), unique=True),
        sa.Column("address", sa.String(300), nullable=False),
        sa.Column("district", sa.String(100), nullable=False),
        sa.Column("province", sa.String(100), server_default="Lima", nullable=False),
        sa.Column("department", sa.String(100), server_default="Lima", nullable=False),
        sa.Column("currency", sa.String(3), server_default="PEN", nullable=False),
        sa.Column("timezone", sa.String(60), server_default="America/Lima", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *timestamps(),
    )
    op.create_index("ix_buildings_is_active", "buildings", ["is_active"])
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("building_id", sa.Integer(), sa.ForeignKey("buildings.id", ondelete="RESTRICT")),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(30)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        *timestamps(),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_building_id", "users", ["building_id"])
    op.create_index("ix_users_is_active", "users", ["is_active"])
    op.create_index("ix_users_building_role", "users", ["building_id", "role_id"])
    op.create_table(
        "invitations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("building_id", sa.Integer(), sa.ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("invited_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *timestamps(),
    )
    op.create_index("ix_invitations_email", "invitations", ["email"])
    for table_name in ("refresh_tokens", "password_reset_tokens"):
        op.create_table(
            table_name,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at" if table_name == "refresh_tokens" else "used_at", sa.DateTime(timezone=True)),
            *timestamps(),
        )
        op.create_index(f"ix_{table_name}_user_id", table_name, ["user_id"])

    op.create_table(
        "units",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("building_id", sa.Integer(), sa.ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(30), nullable=False),
        sa.Column("floor", sa.String(20)),
        sa.Column("area_m2", sa.Numeric(10, 2), nullable=False),
        sa.Column("participation_coefficient", sa.Numeric(12, 8), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *timestamps(),
        sa.CheckConstraint("area_m2 > 0", name="ck_unit_area_positive"),
        sa.CheckConstraint("participation_coefficient >= 0", name="ck_unit_coefficient_nonnegative"),
        sa.UniqueConstraint("building_id", "code", name="uq_unit_building_code"),
    )
    op.create_index("ix_units_building_active", "units", ["building_id", "is_active"])
    op.create_table(
        "unit_residents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("unit_id", sa.Integer(), sa.ForeignKey("units.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resident_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("is_owner", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *timestamps(),
        sa.CheckConstraint("end_date IS NULL OR end_date >= start_date", name="ck_residency_dates"),
        sa.UniqueConstraint("unit_id", "resident_id", "start_date", name="uq_unit_resident_period"),
    )
    op.create_index("ix_unit_resident_active", "unit_residents", ["resident_id", "unit_id", "end_date"])

    op.create_table(
        "fee_concepts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("building_id", sa.Integer(), sa.ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("building_id", "code", name="uq_concept_building_code"),
    )
    op.create_table(
        "maintenance_fees",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("building_id", sa.Integer(), sa.ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("unit_id", sa.Integer(), sa.ForeignKey("units.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("concept_id", sa.Integer(), sa.ForeignKey("fee_concepts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), server_default="PEN", nullable=False),
        sa.Column("status", fee_status, server_default="Pendiente", nullable=False),
        sa.Column("cancellation_reason", sa.Text()),
        *timestamps(),
        sa.CheckConstraint("amount > 0", name="ck_fee_amount_positive"),
        sa.CheckConstraint("currency = 'PEN'", name="ck_fee_currency_pen"),
        sa.UniqueConstraint("unit_id", "period", "concept_id", name="uq_fee_unit_period_concept"),
    )
    op.create_index("ix_fee_unit_period", "maintenance_fees", ["unit_id", "period"])
    op.create_index("ix_fee_status_created", "maintenance_fees", ["status", "created_at"])
    op.create_table(
        "fee_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fee_id", sa.Integer(), sa.ForeignKey("maintenance_fees.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("admin_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("action", fee_audit_action, nullable=False),
        sa.Column("previous_amount", sa.Numeric(12, 2)),
        sa.Column("new_amount", sa.Numeric(12, 2)),
        sa.Column("reason", sa.Text(), nullable=False),
        *timestamps(),
    )

    op.create_table(
        "payment_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("building_id", sa.Integer(), sa.ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resident_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), server_default="PEN", nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("operation_number", sa.String(80), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("status", payment_status, server_default="En revisión", nullable=False),
        sa.Column("observation_reason", sa.Text()),
        sa.Column("reviewed_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.CheckConstraint("amount > 0", name="ck_payment_amount_positive"),
        sa.CheckConstraint("currency = 'PEN'", name="ck_payment_currency_pen"),
        sa.UniqueConstraint("building_id", "operation_number", "amount", "payment_date", name="uq_payment_operation_amount_date"),
        sa.UniqueConstraint("building_id", "file_hash", name="uq_payment_file_hash"),
    )
    op.create_index("ix_payment_status_created", "payment_reports", ["status", "created_at"])
    op.create_index("ix_payment_building_status", "payment_reports", ["building_id", "status"])
    op.create_table(
        "payment_allocations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payment_report_id", sa.Integer(), sa.ForeignKey("payment_reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fee_id", sa.Integer(), sa.ForeignKey("maintenance_fees.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), server_default="PEN", nullable=False),
        *timestamps(),
        sa.CheckConstraint("amount > 0", name="ck_allocation_amount_positive"),
        sa.CheckConstraint("currency = 'PEN'", name="ck_allocation_currency_pen"),
        sa.UniqueConstraint("payment_report_id", "fee_id", name="uq_payment_allocation_fee"),
    )
    op.create_index("ix_allocation_fee", "payment_allocations", ["fee_id"])
    op.create_table(
        "payment_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payment_report_id", sa.Integer(), sa.ForeignKey("payment_reports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("admin_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT")),
        sa.Column("previous_status", sa.String(40)),
        sa.Column("new_status", sa.String(40), nullable=False),
        sa.Column("action", payment_action, nullable=False),
        sa.Column("amount_snapshot", sa.Numeric(12, 2), nullable=False),
        sa.Column("reason", sa.Text()),
        *timestamps(),
    )
    op.create_index("ix_payment_audit_report_created", "payment_audit_logs", ["payment_report_id", "created_at"])
    op.execute(
        """
        CREATE FUNCTION reject_payment_audit_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'payment_audit_logs is append-only';
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER payment_audit_logs_append_only
        BEFORE UPDATE OR DELETE ON payment_audit_logs
        FOR EACH ROW EXECUTE FUNCTION reject_payment_audit_mutation();
        """
    )
    op.create_table(
        "receipts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("building_id", sa.Integer(), sa.ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("payment_report_id", sa.Integer(), sa.ForeignKey("payment_reports.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("number", sa.String(30), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("building_id", "number", name="uq_receipt_building_number"),
    )
    op.create_table(
        "receipt_sequences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("building_id", sa.Integer(), sa.ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("last_number", sa.Integer(), server_default="0", nullable=False),
        *timestamps(),
        sa.UniqueConstraint("building_id", "year", name="uq_receipt_sequence_year"),
    )
    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("endpoint", sa.String(120), nullable=False),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("response_status", sa.Integer()),
        sa.Column("response_body", sa.JSON()),
        *timestamps(),
        sa.UniqueConstraint("user_id", "endpoint", "key", name="uq_idempotency_user_endpoint_key"),
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS reject_payment_audit_mutation() CASCADE")
    tables = [
        "idempotency_records", "receipt_sequences", "receipts", "payment_audit_logs",
        "payment_allocations", "payment_reports", "fee_audit_logs", "maintenance_fees",
        "fee_concepts", "unit_residents", "units", "password_reset_tokens", "refresh_tokens",
        "invitations", "users", "buildings", "roles",
    ]
    for table_name in tables:
        op.drop_table(table_name)
    bind = op.get_bind()
    for enum_type in (fee_audit_action, payment_action, payment_status, fee_status):
        enum_type.drop(bind, checkfirst=True)
