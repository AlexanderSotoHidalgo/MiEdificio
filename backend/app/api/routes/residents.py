from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import AdminUser, DbSession
from app.core.security import hash_password
from app.models import Role, User
from app.schemas.residents import ResidentCreate, ResidentOut

router = APIRouter(prefix="/residents", tags=["Residentes"])


@router.get("", response_model=list[ResidentOut])
def list_residents(_: AdminUser, db: DbSession) -> list[User]:
    return list(
        db.scalars(
            select(User).join(User.role).where(Role.name == "residente").order_by(User.full_name)
        )
    )


@router.post("", response_model=ResidentOut, status_code=201)
def create_resident(payload: ResidentCreate, _: AdminUser, db: DbSession) -> User:
    role = db.scalar(select(Role).where(Role.name == "residente"))
    if role is None:
        raise HTTPException(status_code=503, detail="El rol residente aún no está configurado")
    resident = User(
        full_name=payload.full_name.strip(),
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role_id=role.id,
    )
    db.add(resident)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe un usuario con ese correo")
    db.refresh(resident)
    return resident
