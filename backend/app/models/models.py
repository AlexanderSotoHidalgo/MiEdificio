import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FeeStatus(str, enum.Enum):
    PENDING = "Pendiente"
    IN_REVIEW = "Pago en revisión"
    PAID = "Pagada"


class PaymentStatus(str, enum.Enum):
    PENDING = "Pendiente"
    APPROVED = "Aprobado"
    OBSERVED = "Observado"


class PaymentAction(str, enum.Enum):
    APPROVED = "Aprobado"
    OBSERVED = "Observado"


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    users: Mapped[list["User"]] = relationship(back_populates="role")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    role: Mapped[Role] = relationship(back_populates="users", lazy="joined")
    units: Mapped[list["Unit"]] = relationship(back_populates="resident")
    payment_reports: Mapped[list["PaymentReport"]] = relationship(back_populates="resident")


class Unit(Base):
    __tablename__ = "units"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    resident_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    resident: Mapped[User | None] = relationship(back_populates="units")
    fees: Mapped[list["MaintenanceFee"]] = relationship(back_populates="unit")


class MaintenanceFee(Base):
    __tablename__ = "maintenance_fees"
    __table_args__ = (
        UniqueConstraint("unit_id", "period_year", "period_month", name="uq_fee_unit_period"),
        CheckConstraint("period_month BETWEEN 1 AND 12", name="ck_fee_month"),
        CheckConstraint("amount >= 0", name="ck_fee_amount_nonnegative"),
        CheckConstraint("paid_amount >= 0", name="ck_fee_paid_nonnegative"),
        CheckConstraint("paid_amount <= amount", name="ck_fee_paid_not_over_amount"),
        Index("ix_fee_period", "period_year", "period_month"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id", ondelete="CASCADE"), nullable=False)
    period_year: Mapped[int] = mapped_column(nullable=False)
    period_month: Mapped[int] = mapped_column(nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    status: Mapped[FeeStatus] = mapped_column(
        Enum(FeeStatus, name="fee_status", values_callable=lambda values: [item.value for item in values]),
        default=FeeStatus.PENDING,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    unit: Mapped[Unit] = relationship(back_populates="fees")
    payment_reports: Mapped[list["PaymentReport"]] = relationship(back_populates="fee")

    @property
    def balance(self) -> Decimal:
        return self.amount - self.paid_amount


class PaymentReport(Base):
    __tablename__ = "payment_reports"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payment_amount_positive"),
        UniqueConstraint("resident_id", "operation_number", name="uq_payment_resident_operation"),
        Index("ix_payment_status_created", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    fee_id: Mapped[int] = mapped_column(ForeignKey("maintenance_fees.id", ondelete="RESTRICT"), nullable=False)
    resident_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    operation_number: Mapped[str] = mapped_column(String(80), nullable=False)
    receipt_path: Mapped[str] = mapped_column(String(500), nullable=False)
    receipt_original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    receipt_content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status", values_callable=lambda values: [item.value for item in values]),
        default=PaymentStatus.PENDING,
        nullable=False,
    )
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    fee: Mapped[MaintenanceFee] = relationship(back_populates="payment_reports")
    resident: Mapped[User] = relationship(back_populates="payment_reports")
    audit_logs: Mapped[list["PaymentAuditLog"]] = relationship(back_populates="payment_report")


class PaymentAuditLog(Base):
    __tablename__ = "payment_audit_logs"
    __table_args__ = (
        UniqueConstraint("payment_report_id", name="uq_audit_payment_report"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_report_id: Mapped[int] = mapped_column(
        ForeignKey("payment_reports.id", ondelete="RESTRICT"), nullable=False
    )
    admin_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    action: Mapped[PaymentAction] = mapped_column(
        Enum(PaymentAction, name="payment_action", values_callable=lambda values: [item.value for item in values]),
        nullable=False,
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    payment_report: Mapped[PaymentReport] = relationship(back_populates="audit_logs")
    admin: Mapped[User] = relationship()
