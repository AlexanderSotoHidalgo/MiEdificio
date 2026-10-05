from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import MaintenanceFee, Role, Unit, User


def seed() -> None:
    if not settings.seed_demo_data:
        return
    with SessionLocal() as db:
        roles: dict[str, Role] = {}
        for name in ("administrador", "residente"):
            role = db.scalar(select(Role).where(Role.name == name))
            if role is None:
                role = Role(name=name)
                db.add(role)
                db.flush()
            roles[name] = role

        admin = db.scalar(select(User).where(User.email == "admin@miedificio.pe"))
        if admin is None:
            admin = User(
                full_name="Andrea Administradora",
                email="admin@miedificio.pe",
                password_hash=hash_password("Admin123!"),
                role_id=roles["administrador"].id,
            )
            db.add(admin)

        resident = db.scalar(select(User).where(User.email == "residente@miedificio.pe"))
        if resident is None:
            resident = User(
                full_name="Renato Rivera",
                email="residente@miedificio.pe",
                password_hash=hash_password("Residente123!"),
                role_id=roles["residente"].id,
            )
            db.add(resident)
            db.flush()

        unit = db.scalar(select(Unit).where(Unit.code == "D-302"))
        if unit is None:
            unit = Unit(code="D-302", resident_id=resident.id)
            db.add(unit)
            db.flush()

        existing_fee = db.scalar(
            select(MaintenanceFee).where(
                MaintenanceFee.unit_id == unit.id,
                MaintenanceFee.period_year == 2026,
                MaintenanceFee.period_month == 10,
            )
        )
        if existing_fee is None:
            db.add(
                MaintenanceFee(
                    unit_id=unit.id,
                    period_year=2026,
                    period_month=10,
                    due_date=date(2026, 10, 15),
                    amount=Decimal("280.00"),
                )
            )
        db.commit()


if __name__ == "__main__":
    seed()

