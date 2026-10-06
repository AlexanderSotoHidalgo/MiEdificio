import argparse

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import Building, Role, User


def create_initial_admin() -> None:
    with SessionLocal() as db:
        role = db.scalar(select(Role).where(Role.name == "administrador"))
        if role is None:
            role = Role(name="administrador", description="Administración completa del edificio")
            db.add(role)
            db.flush()
        building = db.scalar(select(Building).order_by(Building.id))
        if building is None:
            building = Building(
                name=settings.initial_building_name,
                address=settings.initial_building_address,
                district=settings.initial_building_district,
            )
            db.add(building)
            db.flush()
        admin = db.scalar(select(User).where(User.email == settings.initial_admin_email.lower()))
        if admin is None:
            db.add(
                User(
                    building_id=building.id,
                    role_id=role.id,
                    full_name=settings.initial_admin_name,
                    email=settings.initial_admin_email.lower(),
                    password_hash=hash_password(settings.initial_admin_password),
                )
            )
            db.commit()
            print(f"Administrador creado: {settings.initial_admin_email}")
        else:
            print(f"El administrador ya existe: {settings.initial_admin_email}")


def main() -> None:
    parser = argparse.ArgumentParser(description="MiEdificio management CLI")
    parser.add_argument("command", choices=["create-admin", "seed-demo"])
    args = parser.parse_args()
    if args.command == "create-admin":
        create_initial_admin()
    else:
        from app.seed import seed

        seed(force=True)


if __name__ == "__main__":
    main()
