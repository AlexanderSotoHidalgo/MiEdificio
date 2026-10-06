import csv
from datetime import date
from decimal import Decimal, InvalidOperation
from io import StringIO
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.api.deps import AdminUser, DbSession
from app.models import Role, Unit, UnitResident, User
from app.modules.units.schemas import (
    CsvImportResult,
    CsvRowError,
    ResidentLinkOut,
    UnitCreate,
    UnitOut,
)

router = APIRouter(prefix="/units", tags=["Unidades"])


def serialize_unit(unit: Unit) -> UnitOut:
    return UnitOut(
        id=unit.id,
        building_id=unit.building_id,
        code=unit.code,
        floor=unit.floor,
        area_m2=unit.area_m2,
        participation_coefficient=unit.participation_coefficient,
        is_active=unit.is_active,
        residents=[
            ResidentLinkOut(
                id=link.id,
                resident_id=link.resident_id,
                resident_name=link.resident.full_name,
                resident_email=link.resident.email,
                is_owner=link.is_owner,
                start_date=link.start_date,
                end_date=link.end_date,
                is_active=link.is_active,
            )
            for link in unit.resident_links
        ],
    )


@router.get("", response_model=list[UnitOut])
def list_units(admin: AdminUser, db: DbSession, include_inactive: bool = False) -> list[UnitOut]:
    query = (
        select(Unit)
        .where(Unit.building_id == admin.building_id)
        .options(selectinload(Unit.resident_links).selectinload(UnitResident.resident))
        .order_by(Unit.code)
    )
    if not include_inactive:
        query = query.where(Unit.is_active.is_(True))
    return [serialize_unit(unit) for unit in db.scalars(query).unique()]


@router.post("", response_model=UnitOut, status_code=201)
def create_unit(payload: UnitCreate, admin: AdminUser, db: DbSession) -> UnitOut:
    residents = []
    for link in payload.residents:
        resident = db.scalar(
            select(User)
            .join(User.role)
            .where(
                User.id == link.resident_id,
                User.building_id == admin.building_id,
                Role.name == "residente",
                User.is_active.is_(True),
            )
        )
        if resident is None:
            raise HTTPException(status_code=422, detail=f"Residente {link.resident_id} no válido")
        residents.append((link, resident))
    unit = Unit(
        building_id=admin.building_id,
        code=payload.code.strip().upper(),
        floor=payload.floor,
        area_m2=payload.area_m2,
        participation_coefficient=payload.participation_coefficient,
    )
    db.add(unit)
    try:
        db.flush()
        for link, _resident in residents:
            db.add(UnitResident(unit_id=unit.id, **link.model_dump()))
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="La unidad o vinculación ya existe") from exc
    loaded_unit = db.scalar(
        select(Unit)
        .where(Unit.id == unit.id)
        .options(selectinload(Unit.resident_links).selectinload(UnitResident.resident))
    )
    assert loaded_unit is not None
    return serialize_unit(loaded_unit)


@router.delete("/{unit_id}", status_code=204)
def deactivate_unit(unit_id: int, admin: AdminUser, db: DbSession) -> None:
    unit = db.scalar(select(Unit).where(Unit.id == unit_id, Unit.building_id == admin.building_id))
    if unit is None:
        raise HTTPException(status_code=404, detail="Unidad no encontrada")
    unit.is_active = False
    for link in unit.resident_links:
        link.is_active = False
        link.end_date = link.end_date or date.today()
    db.commit()


@router.post("/import", response_model=CsvImportResult)
async def import_units(
    file: Annotated[UploadFile, File()], admin: AdminUser, db: DbSession
) -> CsvImportResult:
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=415, detail="El archivo debe ser CSV")
    content = await file.read(2 * 1024 * 1024 + 1)
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="El CSV supera 2 MB")
    try:
        reader = csv.DictReader(StringIO(content.decode("utf-8-sig")))
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="El CSV debe usar UTF-8") from exc
    required = {"unit_code", "area_m2", "coefficient", "resident_email", "is_owner"}
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        raise HTTPException(
            status_code=422, detail=f"Columnas obligatorias: {', '.join(sorted(required))}"
        )
    resident_map = {
        user.email: user
        for user in db.scalars(
            select(User).where(User.building_id == admin.building_id, User.is_active.is_(True))
        )
    }
    existing_codes = set(
        db.scalars(select(Unit.code).where(Unit.building_id == admin.building_id)).all()
    )
    seen: set[str] = set()
    valid_rows: list[tuple[dict[str, object], User | None]] = []
    errors: list[CsvRowError] = []
    for row_number, row in enumerate(reader, start=2):
        try:
            code = row["unit_code"].strip().upper()
            if not code or code in existing_codes or code in seen:
                raise ValueError("Código vacío o duplicado")
            area = Decimal(row["area_m2"])
            coefficient = Decimal(row["coefficient"])
            if area <= 0 or coefficient < 0:
                raise ValueError("Área y coeficiente deben ser válidos")
            email = row["resident_email"].strip().lower()
            resident = resident_map.get(email) if email else None
            if email and resident is None:
                raise ValueError("El residente no existe o no pertenece al edificio")
            is_owner = row["is_owner"].strip().lower() in {"1", "true", "sí", "si", "yes"}
            start = date.fromisoformat(row.get("start_date") or date.today().isoformat())
            valid_rows.append(
                (
                    {
                        "code": code,
                        "floor": (row.get("floor") or "").strip() or None,
                        "area_m2": area,
                        "participation_coefficient": coefficient,
                        "is_owner": is_owner,
                        "start_date": start,
                    },
                    resident,
                )
            )
            seen.add(code)
        except (InvalidOperation, ValueError, TypeError) as exc:
            errors.append(CsvRowError(row=row_number, message=str(exc)))
    created = 0
    try:
        for data, resident in valid_rows:
            unit = Unit(
                building_id=admin.building_id,
                code=data["code"],
                floor=data["floor"],
                area_m2=data["area_m2"],
                participation_coefficient=data["participation_coefficient"],
            )
            db.add(unit)
            db.flush()
            if resident:
                db.add(
                    UnitResident(
                        unit_id=unit.id,
                        resident_id=resident.id,
                        is_owner=data["is_owner"],
                        start_date=data["start_date"],
                    )
                )
            created += 1
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Conflicto durante la importación") from exc
    return CsvImportResult(created=created, errors=errors)
