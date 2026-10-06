from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_opaque_token,
    hash_password,
    token_digest,
)
from app.models import Invitation, RefreshToken, Role, User
from app.modules.auth.schemas import TokenPair, UserOut


def serialize_user(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        building_id=user.building_id,
        full_name=user.full_name,
        email=user.email,
        role=user.role.name,
    )


def issue_tokens(db: Session, user: User) -> TokenPair:
    raw_refresh = generate_opaque_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=token_digest(raw_refresh),
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    db.commit()
    return TokenPair(
        access_token=create_access_token(str(user.id)),
        refresh_token=raw_refresh,
        expires_in=settings.jwt_expire_minutes * 60,
        user=serialize_user(user),
    )


def consume_invitation(
    db: Session, raw_token: str, full_name: str, password: str, phone: str | None
) -> User:
    now = datetime.now(UTC)
    invitation = db.scalar(
        select(Invitation).where(Invitation.token_hash == token_digest(raw_token)).with_for_update()
    )
    if (
        invitation is None
        or not invitation.is_active
        or invitation.accepted_at is not None
        or invitation.expires_at <= now
    ):
        raise HTTPException(status_code=400, detail="La invitación es inválida o ha vencido")
    if db.scalar(select(User.id).where(User.email == invitation.email)):
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con este correo")
    user = User(
        building_id=invitation.building_id,
        role_id=invitation.role_id,
        full_name=full_name.strip(),
        email=invitation.email,
        phone=phone,
        password_hash=hash_password(password),
    )
    invitation.accepted_at = now
    invitation.is_active = False
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_invitation(
    db: Session, admin: User, email: str, role_name: str
) -> tuple[Invitation, str]:
    role = db.scalar(select(Role).where(Role.name == role_name, Role.is_active.is_(True)))
    if role is None:
        raise HTTPException(status_code=422, detail="El rol indicado no existe")
    raw_token = generate_opaque_token()
    invitation = Invitation(
        building_id=admin.building_id,
        role_id=role.id,
        email=email.lower(),
        token_hash=token_digest(raw_token),
        invited_by_id=admin.id,
        expires_at=datetime.now(UTC) + timedelta(hours=48),
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return invitation, raw_token
