"""Initial MiEdificio schema.

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
    "Pendiente", "Pago en revisión", "Pagada", name="fee_status", create_type=False
)
payment_status = postgresql.ENUM(
    "Pendiente", "Aprobado", "Observado", name="payment_status", create_type=False
)
payment_action = postgresql.ENUM(
    "Aprobado", "Observado", name="payment_action", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    fee_status.create(bind, checkfirst=True)
    payment_status.create(bind, checkfirst=True)
    payment_action.create(bind, checkfirst=True)

    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(30), nullable=False, unique=True),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_table(
        "units",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(30), nullable=False, unique=True),
        sa.Column("resident_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_units_resident_id", "units", ["resident_id"])
    op.create_table(
        "maintenance_fees",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("unit_id", sa.Integer(), sa.ForeignKey("units.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_year", sa.Integer(), nullable=False),
        sa.Column("period_month", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("paid_amount", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("status", fee_status, server_default="Pendiente", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("period_month BETWEEN 1 AND 12", name="ck_fee_month"),
        sa.CheckConstraint("amount >= 0", name="ck_fee_amount_nonnegative"),
        sa.CheckConstraint("paid_amount >= 0", name="ck_fee_paid_nonnegative"),
        sa.CheckConstraint("paid_amount <= amount", name="ck_fee_paid_not_over_amount"),
        sa.UniqueConstraint("unit_id", "period_year", "period_month", name="uq_fee_unit_period"),
    )
    op.create_index("ix_fee_period", "maintenance_fees", ["period_year", "period_month"])
    op.create_table(
        "payment_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fee_id", sa.Integer(), sa.ForeignKey("maintenance_fees.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("resident_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("operation_number", sa.String(80), nullable=False),
        sa.Column("receipt_path", sa.String(500), nullable=False),
        sa.Column("receipt_original_name", sa.String(255), nullable=False),
        sa.Column("receipt_content_type", sa.String(100), nullable=False),
        sa.Column("status", payment_status, server_default="Pendiente", nullable=False),
        sa.Column("review_comment", sa.Text()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_payment_amount_positive"),
        sa.UniqueConstraint("resident_id", "operation_number", name="uq_payment_resident_operation"),
    )
    op.create_index("ix_payment_status_created", "payment_reports", ["status", "created_at"])
    op.create_table(
        "payment_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payment_report_id", sa.Integer(), sa.ForeignKey("payment_reports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("admin_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("action", payment_action, nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("payment_report_id", name="uq_audit_payment_report"),
    )


def downgrade() -> None:
    op.drop_table("payment_audit_logs")
    op.drop_index("ix_payment_status_created", table_name="payment_reports")
    op.drop_table("payment_reports")
    op.drop_index("ix_fee_period", table_name="maintenance_fees")
    op.drop_table("maintenance_fees")
    op.drop_index("ix_units_resident_id", table_name="units")
    op.drop_table("units")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_table("roles")
    payment_action.drop(op.get_bind(), checkfirst=True)
    payment_status.drop(op.get_bind(), checkfirst=True)
    fee_status.drop(op.get_bind(), checkfirst=True)
