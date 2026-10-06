from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from hashlib import sha256

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import (
    Building,
    FeeConcept,
    FeeStatus,
    MaintenanceFee,
    PaymentAction,
    PaymentAllocation,
    PaymentAuditLog,
    PaymentReport,
    PaymentStatus,
    Receipt,
    ReceiptSequence,
    Role,
    Unit,
    UnitResident,
    User,
)
from app.modules.storage import get_storage


def month_start(offset: int) -> date:
    current = date.today().replace(day=1)
    for _ in range(abs(offset)):
        current = (
            (current - timedelta(days=1)).replace(day=1)
            if offset < 0
            else (current.replace(day=28) + timedelta(days=4)).replace(day=1)
        )
    return current


def seed(force: bool = False) -> None:
    if not settings.seed_demo_data and not force:
        return
    with SessionLocal() as db:
        roles: dict[str, Role] = {}
        for name, description in (
            ("administrador", "Gestión integral del edificio"),
            ("residente", "Consulta y reporte de pagos"),
            ("tesorero", "Lectura financiera futura"),
            ("portero", "Operación de accesos futura"),
        ):
            role = db.scalar(select(Role).where(Role.name == name))
            if role is None:
                role = Role(name=name, description=description)
                db.add(role)
                db.flush()
            roles[name] = role
        building = db.scalar(
            select(Building).where(Building.name == settings.initial_building_name)
        )
        if building is None:
            building = Building(
                name=settings.initial_building_name,
                legal_name="Junta de Propietarios Los Cedros",
                tax_id="20601234567",
                address=settings.initial_building_address,
                district=settings.initial_building_district,
            )
            db.add(building)
            db.flush()
        admin = db.scalar(select(User).where(User.email == settings.initial_admin_email.lower()))
        if admin is None:
            admin = User(
                building_id=building.id,
                role_id=roles["administrador"].id,
                full_name=settings.initial_admin_name,
                email=settings.initial_admin_email.lower(),
                password_hash=hash_password(settings.initial_admin_password),
            )
            db.add(admin)
            db.flush()
        residents: list[User] = []
        resident_data = [
            ("Renato Rivera", "residente@miedificio.pe"),
            ("María Salazar", "maria@miedificio.pe"),
            ("José Huamán", "jose@miedificio.pe"),
            ("Carla Medina", "carla@miedificio.pe"),
            ("Luis Torres", "luis@miedificio.pe"),
        ]
        for full_name, email in resident_data:
            resident = db.scalar(select(User).where(User.email == email))
            if resident is None:
                resident = User(
                    building_id=building.id,
                    role_id=roles["residente"].id,
                    full_name=full_name,
                    email=email,
                    password_hash=hash_password("Residente123!"),
                )
                db.add(resident)
                db.flush()
            residents.append(resident)
        concepts: dict[str, FeeConcept] = {}
        for code, name in (
            ("ORDINARIA", "Cuota ordinaria"),
            ("EXTRAORDINARIA", "Cuota extraordinaria"),
            ("RESERVA", "Fondo de reserva"),
            ("MULTA", "Multa"),
        ):
            concept = db.scalar(
                select(FeeConcept).where(
                    FeeConcept.building_id == building.id, FeeConcept.code == code
                )
            )
            if concept is None:
                concept = FeeConcept(building_id=building.id, code=code, name=name)
                db.add(concept)
                db.flush()
            concepts[code] = concept
        units: list[Unit] = []
        for index in range(1, 21):
            code = f"{((index - 1) // 4) + 1}0{((index - 1) % 4) + 1}"
            unit = db.scalar(select(Unit).where(Unit.building_id == building.id, Unit.code == code))
            if unit is None:
                unit = Unit(
                    building_id=building.id,
                    code=code,
                    floor=str(((index - 1) // 4) + 1),
                    area_m2=Decimal("78.00") + index,
                    participation_coefficient=Decimal("0.05000000"),
                )
                db.add(unit)
                db.flush()
            resident = residents[(index - 1) // 4]
            link = db.scalar(
                select(UnitResident).where(
                    UnitResident.unit_id == unit.id, UnitResident.resident_id == resident.id
                )
            )
            if link is None:
                db.add(
                    UnitResident(
                        unit_id=unit.id,
                        resident_id=resident.id,
                        is_owner=True,
                        start_date=date(date.today().year - 2, 1, 1),
                    )
                )
            units.append(unit)
        db.flush()
        periods = [month_start(-2), month_start(-1), month_start(0)]
        fees: list[MaintenanceFee] = []
        for period in periods:
            for unit in units:
                fee = db.scalar(
                    select(MaintenanceFee).where(
                        MaintenanceFee.unit_id == unit.id,
                        MaintenanceFee.period == period,
                        MaintenanceFee.concept_id == concepts["ORDINARIA"].id,
                    )
                )
                if fee is None:
                    fee = MaintenanceFee(
                        building_id=building.id,
                        unit_id=unit.id,
                        concept_id=concepts["ORDINARIA"].id,
                        period=period,
                        due_date=period.replace(day=15),
                        amount=Decimal("280.00") + Decimal(unit.id % 3) * Decimal("10.00"),
                    )
                    db.add(fee)
                    db.flush()
                fees.append(fee)
        db.commit()

        # Three distinct reports make every review state visible in demos.
        demo_states = [PaymentStatus.APPROVED, PaymentStatus.IN_REVIEW, PaymentStatus.OBSERVED]
        storage = get_storage()
        for index, state in enumerate(demo_states):
            operation = f"DEMO-{state.name}-001"
            if db.scalar(
                select(PaymentReport.id).where(PaymentReport.operation_number == operation)
            ):
                continue
            fee = fees[index * 4]
            resident = residents[index]
            content = f"%PDF-1.4\n% MiEdificio demo {state.value}\n%%EOF".encode()
            digest = sha256(content).hexdigest()
            key = f"payment-proofs/{building.id}/demo-{state.name.lower()}.pdf"
            storage.save(key, content, "application/pdf")
            report = PaymentReport(
                building_id=building.id,
                resident_id=resident.id,
                amount=Decimal("140.00") if state != PaymentStatus.APPROVED else fee.amount,
                payment_date=date.today() - timedelta(days=index),
                operation_number=operation,
                storage_key=key,
                original_filename=f"demo-{state.name.lower()}.pdf",
                content_type="application/pdf",
                file_size=len(content),
                file_hash=digest,
                status=state,
                observation_reason="El número de operación no es legible"
                if state == PaymentStatus.OBSERVED
                else None,
                reviewed_by_id=admin.id if state != PaymentStatus.IN_REVIEW else None,
                reviewed_at=(datetime.now(UTC) if state != PaymentStatus.IN_REVIEW else None),
            )
            db.add(report)
            db.flush()
            db.add(
                PaymentAllocation(payment_report_id=report.id, fee_id=fee.id, amount=report.amount)
            )
            db.add(
                PaymentAuditLog(
                    payment_report_id=report.id,
                    admin_id=admin.id if state != PaymentStatus.IN_REVIEW else None,
                    previous_status=None,
                    new_status=state.value,
                    action=(
                        PaymentAction.APPROVED
                        if state == PaymentStatus.APPROVED
                        else PaymentAction.OBSERVED
                        if state == PaymentStatus.OBSERVED
                        else PaymentAction.REPORTED
                    ),
                    amount_snapshot=report.amount,
                    reason=report.observation_reason,
                )
            )
            if state == PaymentStatus.APPROVED:
                year = date.today().year
                receipt_content = b"%PDF-1.4\n% MiEdificio demo receipt\n%%EOF"
                receipt_key = f"receipts/{building.id}/{year}/demo-approved.pdf"
                storage.save(receipt_key, receipt_content, "application/pdf")
                db.add(
                    Receipt(
                        building_id=building.id,
                        payment_report_id=report.id,
                        number=f"REC-{year}-000001",
                        storage_key=receipt_key,
                        file_hash=sha256(receipt_content).hexdigest(),
                    )
                )
                if not db.scalar(
                    select(ReceiptSequence.id).where(
                        ReceiptSequence.building_id == building.id,
                        ReceiptSequence.year == year,
                    )
                ):
                    db.add(
                        ReceiptSequence(
                            building_id=building.id,
                            year=year,
                            last_number=1,
                        )
                    )
            fee.status = (
                FeeStatus.PAID
                if state == PaymentStatus.APPROVED
                else FeeStatus.IN_REVIEW
                if state == PaymentStatus.IN_REVIEW
                else FeeStatus.PENDING
            )
        db.commit()


if __name__ == "__main__":
    seed()
