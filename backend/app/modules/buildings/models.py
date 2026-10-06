from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.shared.mixins import TimestampMixin


class Building(TimestampMixin, Base):
    __tablename__ = "buildings"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(200))
    tax_id: Mapped[str | None] = mapped_column(String(11), unique=True)
    address: Mapped[str] = mapped_column(String(300), nullable=False)
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    province: Mapped[str] = mapped_column(String(100), default="Lima", nullable=False)
    department: Mapped[str] = mapped_column(String(100), default="Lima", nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="PEN", nullable=False)
    timezone: Mapped[str] = mapped_column(String(60), default="America/Lima", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    users = relationship("User", back_populates="building")
    units = relationship("Unit", back_populates="building")
    fee_concepts = relationship("FeeConcept", back_populates="building")
