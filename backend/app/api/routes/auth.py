from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.security import create_access_token, verify_password
from app.models import User
from app.schemas.schemas import Token, UserOut

router = APIRouter(prefix="/auth", tags=["Autenticación"])


def serialize_user(user: User) -> UserOut:
    return UserOut(id=user.id, full_name=user.full_name, email=user.email, role=user.role.name)


@router.post("/login", response_model=Token)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession) -> Token:
    email = form.username.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(str(user.id)), user=serialize_user(user))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return serialize_user(user)

