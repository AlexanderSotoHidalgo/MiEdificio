from datetime import date, datetime
from decimal import Decimal
from enum import Enum as PythonEnum

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.shared.enums import PaymentAction, PaymentStatus
from app.shared.mixins import TimestampMixin


def enum_values(enum_class: type[PythonEnum]) -> list[str]:
    return [item.value for item in enum_class]


class PaymentReport(TimestampMixin, Base):
    __tablename__ = "payment_reports"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payment_amount_positive"),
        CheckConstraint("currency = 'PEN'", name="ck_payment_currency_pen"),
        UniqueConstraint(
            "building_id",
            "operation_number",
            "amount",
            "payment_date",
            name="uq_payment_operation_amount_date",
        ),
        UniqueConstraint("building_id", "file_hash", name="uq_payment_file_hash"),
        Index("ix_payment_status_created", "status", "created_at"),
        Index("ix_payment_building_status", "building_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id", ondelete="CASCADE"))
    resident_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="PEN", nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    operation_number: Mapped[str] = mapped_column(String(80), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status", values_callable=enum_values),
        default=PaymentStatus.IN_REVIEW,
        nullable=False,
    )
    observation_reason: Mapped[str | None] = mapped_column(Text)
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    reviewed_at: Mapped[datetime | None]

    resident = relationship("User", back_populates="payment_reports", foreign_keys=[resident_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
    allocations = relationship("PaymentAllocation", back_populates="payment_report")
    audit_logs = relationship("PaymentAuditLog", back_populates="payment_report")
    receipt = relationship("Receipt", back_populates="payment_report", uselist=False)


class PaymentAllocation(TimestampMixin, Base):
    __tablename__ = "payment_allocations"
    __table_args__ = (
        UniqueConstraint("payment_report_id", "fee_id", name="uq_payment_allocation_fee"),
        CheckConstraint("amount > 0", name="ck_allocation_amount_positive"),
        CheckConstraint("currency = 'PEN'", name="ck_allocation_currency_pen"),
        Index("ix_allocation_fee", "fee_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_report_id: Mapped[int] = mapped_column(
        ForeignKey("payment_reports.id", ondelete="CASCADE")
    )
    fee_id: Mapped[int] = mapped_column(ForeignKey("maintenance_fees.id", ondelete="RESTRICT"))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="PEN", nullable=False)

    payment_report = relationship("PaymentReport", back_populates="allocations")
    fee = relationship("MaintenanceFee", back_populates="allocations")


class PaymentAuditLog(TimestampMixin, Base):
    __tablename__ = "payment_audit_logs"
    __table_args__ = (Index("ix_payment_audit_report_created", "payment_report_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_report_id: Mapped[int] = mapped_column(
        ForeignKey("payment_reports.id", ondelete="RESTRICT")
    )
    admin_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    previous_status: Mapped[str | None] = mapped_column(String(40))
    new_status: Mapped[str] = mapped_column(String(40), nullable=False)
    action: Mapped[PaymentAction] = mapped_column(
        Enum(PaymentAction, name="payment_action", values_callable=enum_values), nullable=False
    )
    amount_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)

    payment_report = relationship("PaymentReport", back_populates="audit_logs")
    admin = relationship("User")


class Receipt(TimestampMixin, Base):
    __tablename__ = "receipts"
    __table_args__ = (UniqueConstraint("building_id", "number", name="uq_receipt_building_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id", ondelete="CASCADE"))
    payment_report_id: Mapped[int] = mapped_column(
        ForeignKey("payment_reports.id", ondelete="RESTRICT"), unique=True
    )
    number: Mapped[str] = mapped_column(String(30), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    payment_report = relationship("PaymentReport", back_populates="receipt")


class ReceiptSequence(TimestampMixin, Base):
    __tablename__ = "receipt_sequences"
    __table_args__ = (UniqueConstraint("building_id", "year", name="uq_receipt_sequence_year"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id", ondelete="CASCADE"))
    year: Mapped[int] = mapped_column(nullable=False)
    last_number: Mapped[int] = mapped_column(default=0, nullable=False)


class IdempotencyRecord(TimestampMixin, Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint("user_id", "endpoint", "key", name="uq_idempotency_user_endpoint_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    endpoint: Mapped[str] = mapped_column(String(120), nullable=False)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response_status: Mapped[int | None] = mapped_column(Integer)
    response_body: Mapped[dict | None] = mapped_column(JSON)
