from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import AdminUser, DbSession
from app.models import Unit, User
from app.schemas.schemas import UnitCreate, UnitOut

router = APIRouter(prefix="/units", tags=["Unidades"])


@router.get("", response_model=list[UnitOut])
def list_units(_: AdminUser, db: DbSession) -> list[Unit]:
    return list(db.scalars(select(Unit).order_by(Unit.code)))


@router.post("", response_model=UnitOut, status_code=201)
def create_unit(payload: UnitCreate, _: AdminUser, db: DbSession) -> Unit:
    resident_id = None
    if payload.resident_email:
        resident = db.scalar(select(User).where(User.email == payload.resident_email.lower()))
        if resident is None or resident.role.name != "residente":
            raise HTTPException(status_code=422, detail="El residente indicado no existe")
        resident_id = resident.id
    unit = Unit(code=payload.code.strip().upper(), resident_id=resident_id)
    db.add(unit)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe una unidad con ese código")
    db.refresh(unit)
    return unit

