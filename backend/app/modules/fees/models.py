from datetime import date
from decimal import Decimal
from enum import Enum as PythonEnum

from sqlalchemy import (
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.shared.enums import FeeAuditAction, FeeStatus
from app.shared.mixins import TimestampMixin


def enum_values(enum_class: type[PythonEnum]) -> list[str]:
    return [item.value for item in enum_class]


class FeeConcept(TimestampMixin, Base):
    __tablename__ = "fee_concepts"
    __table_args__ = (UniqueConstraint("building_id", "code", name="uq_concept_building_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    building = relationship("Building", back_populates="fee_concepts")
    fees = relationship("MaintenanceFee", back_populates="concept")


class MaintenanceFee(TimestampMixin, Base):
    __tablename__ = "maintenance_fees"
    __table_args__ = (
        UniqueConstraint("unit_id", "period", "concept_id", name="uq_fee_unit_period_concept"),
        CheckConstraint("amount > 0", name="ck_fee_amount_positive"),
        CheckConstraint("currency = 'PEN'", name="ck_fee_currency_pen"),
        Index("ix_fee_unit_period", "unit_id", "period"),
        Index("ix_fee_status_created", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id", ondelete="CASCADE"))
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id", ondelete="RESTRICT"))
    concept_id: Mapped[int] = mapped_column(ForeignKey("fee_concepts.id", ondelete="RESTRICT"))
    period: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="PEN", nullable=False)
    status: Mapped[FeeStatus] = mapped_column(
        Enum(FeeStatus, name="fee_status", values_callable=enum_values),
        default=FeeStatus.PENDING,
        nullable=False,
    )
    cancellation_reason: Mapped[str | None] = mapped_column(Text)

    unit = relationship("Unit", back_populates="fees")
    concept = relationship("FeeConcept", back_populates="fees")
    allocations = relationship("PaymentAllocation", back_populates="fee")
    audit_logs = relationship("FeeAuditLog", back_populates="fee")


class FeeAuditLog(TimestampMixin, Base):
    __tablename__ = "fee_audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    fee_id: Mapped[int] = mapped_column(ForeignKey("maintenance_fees.id", ondelete="RESTRICT"))
    admin_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    action: Mapped[FeeAuditAction] = mapped_column(
        Enum(FeeAuditAction, name="fee_audit_action", values_callable=enum_values), nullable=False
    )
    previous_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    new_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    reason: Mapped[str] = mapped_column(Text, nullable=False)

    fee = relationship("MaintenanceFee", back_populates="audit_logs")
    admin = relationship("User")
