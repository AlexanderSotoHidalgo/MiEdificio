import os
from collections.abc import Generator
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

import app.modules.payments.router as payments_router
from app.api.deps import get_db
from app.core.config import settings
from app.core.database import Base
from app.core.security import hash_password
from app.main import app
from app.models import Building, FeeConcept, MaintenanceFee, Role, Unit, UnitResident, User
from app.modules.storage.local import LocalStorage


def test_database_url() -> str:
    configured = os.getenv("TEST_DATABASE_URL")
    if configured:
        return configured
    return (
        make_url(settings.database_url)
        .set(database="miedificio_test")
        .render_as_string(hide_password=False)
    )


TEST_URL = make_url(test_database_url())
admin_engine = create_engine(TEST_URL.set(database="postgres"), isolation_level="AUTOCOMMIT")
with admin_engine.connect() as connection:
    exists = connection.scalar(text("SELECT 1 FROM pg_database WHERE datname = 'miedificio_test'"))
    if not exists:
        connection.execute(text("CREATE DATABASE miedificio_test"))
admin_engine.dispose()

test_engine = create_engine(TEST_URL, pool_pre_ping=True)
TestSession = sessionmaker(bind=test_engine, expire_on_commit=False)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def db_session_factory():
    return TestSession


@pytest.fixture(autouse=True)
def clean_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    yield


@pytest.fixture
def sample_data() -> dict[str, int]:
    with TestSession() as db:
        admin_role = Role(name="administrador")
        resident_role = Role(name="residente")
        building = Building(name="Edificio Test", address="Av. Pruebas 123", district="Lima")
        db.add_all([admin_role, resident_role, building])
        db.flush()
        admin = User(
            building_id=building.id,
            role_id=admin_role.id,
            full_name="Admin Test",
            email="admin@test.pe",
            password_hash=hash_password("AdminTest123!"),
        )
        resident = User(
            building_id=building.id,
            role_id=resident_role.id,
            full_name="Residente Uno",
            email="uno@test.pe",
            password_hash=hash_password("ResidentTest123!"),
        )
        other = User(
            building_id=building.id,
            role_id=resident_role.id,
            full_name="Residente Dos",
            email="dos@test.pe",
            password_hash=hash_password("ResidentTest123!"),
        )
        db.add_all([admin, resident, other])
        db.flush()
        unit = Unit(
            building_id=building.id,
            code="101",
            area_m2=Decimal("80"),
            participation_coefficient=Decimal("0.5"),
        )
        other_unit = Unit(
            building_id=building.id,
            code="102",
            area_m2=Decimal("70"),
            participation_coefficient=Decimal("0.5"),
        )
        concept = FeeConcept(building_id=building.id, code="ORDINARIA", name="Cuota ordinaria")
        db.add_all([unit, other_unit, concept])
        db.flush()
        db.add_all(
            [
                UnitResident(
                    unit_id=unit.id,
                    resident_id=resident.id,
                    is_owner=True,
                    start_date=date.today() - timedelta(days=365),
                ),
                UnitResident(
                    unit_id=other_unit.id,
                    resident_id=other.id,
                    is_owner=True,
                    start_date=date.today() - timedelta(days=365),
                ),
            ]
        )
        fee = MaintenanceFee(
            building_id=building.id,
            unit_id=unit.id,
            concept_id=concept.id,
            period=date.today().replace(day=1),
            due_date=date.today() + timedelta(days=10),
            amount=Decimal("100.00"),
        )
        other_fee = MaintenanceFee(
            building_id=building.id,
            unit_id=other_unit.id,
            concept_id=concept.id,
            period=date.today().replace(day=1),
            due_date=date.today() + timedelta(days=10),
            amount=Decimal("100.00"),
        )
        db.add_all([fee, other_fee])
        db.commit()
        return {
            "building": building.id,
            "admin": admin.id,
            "resident": resident.id,
            "other": other.id,
            "fee": fee.id,
            "other_fee": other_fee.id,
            "concept": concept.id,
        }


@pytest.fixture
def client(tmp_path, sample_data) -> Generator[TestClient, None, None]:
    def override_db() -> Generator[Session, None, None]:
        with TestSession() as session:
            yield session

    storage = LocalStorage(tmp_path / "uploads")
    app.dependency_overrides[get_db] = override_db
    original_storage = payments_router.get_storage
    payments_router.get_storage = lambda: storage
    with TestClient(app) as test_client:
        yield test_client
    payments_router.get_storage = original_storage
    app.dependency_overrides.clear()


def login_headers(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def admin_headers(client) -> dict[str, str]:
    return login_headers(client, "admin@test.pe", "AdminTest123!")


@pytest.fixture
def resident_headers(client) -> dict[str, str]:
    return login_headers(client, "uno@test.pe", "ResidentTest123!")


@pytest.fixture
def other_headers(client) -> dict[str, str]:
    return login_headers(client, "dos@test.pe", "ResidentTest123!")
