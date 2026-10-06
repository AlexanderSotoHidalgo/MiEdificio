from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.shared.mixins import TimestampMixin


class Unit(TimestampMixin, Base):
    __tablename__ = "units"
    __table_args__ = (
        UniqueConstraint("building_id", "code", name="uq_unit_building_code"),
        CheckConstraint("area_m2 > 0", name="ck_unit_area_positive"),
        CheckConstraint("participation_coefficient >= 0", name="ck_unit_coefficient_nonnegative"),
        Index("ix_units_building_active", "building_id", "is_active"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    building_id: Mapped[int] = mapped_column(ForeignKey("buildings.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    floor: Mapped[str | None] = mapped_column(String(20))
    area_m2: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    participation_coefficient: Mapped[Decimal] = mapped_column(
        Numeric(12, 8), default=Decimal("0"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    building = relationship("Building", back_populates="units")
    resident_links = relationship("UnitResident", back_populates="unit")
    fees = relationship("MaintenanceFee", back_populates="unit")


class UnitResident(TimestampMixin, Base):
    __tablename__ = "unit_residents"
    __table_args__ = (
        UniqueConstraint("unit_id", "resident_id", "start_date", name="uq_unit_resident_period"),
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="ck_residency_dates"),
        Index("ix_unit_resident_active", "resident_id", "unit_id", "end_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id", ondelete="CASCADE"))
    resident_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    is_owner: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    unit = relationship("Unit", back_populates="resident_links")
    resident = relationship("User", back_populates="unit_links")
