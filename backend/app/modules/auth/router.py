from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, update

from app.api.deps import AdminUser, CurrentUser, DbSession
from app.core.config import settings
from app.core.rate_limit import login_limiter
from app.core.security import generate_opaque_token, hash_password, token_digest, verify_password
from app.models import PasswordResetToken, RefreshToken, User
from app.modules.auth.schemas import (
    ForgotPasswordIn,
    InvitationAccept,
    InvitationCreate,
    InvitationCreated,
    MessageOut,
    RefreshIn,
    ResetPasswordIn,
    TokenPair,
    UserOut,
)
from app.modules.auth.service import (
    consume_invitation,
    create_invitation,
    issue_tokens,
    serialize_user,
)
from app.modules.notifications import send_email

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=TokenPair)
def login(
    request: Request,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession,
) -> TokenPair:
    email = form.username.strip().lower()
    key = f"{request.client.host if request.client else 'unknown'}:{email}"
    login_limiter.check(key)
    user = db.scalar(select(User).where(User.email == email, User.is_active.is_(True)))
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    login_limiter.reset(key)
    user.last_login_at = datetime.now(UTC)
    return issue_tokens(db, user)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshIn, db: DbSession) -> TokenPair:
    now = datetime.now(UTC)
    stored = db.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == token_digest(payload.refresh_token))
        .with_for_update()
    )
    if stored is None or stored.revoked_at is not None or stored.expires_at <= now:
        raise HTTPException(status_code=401, detail="Refresh token inválido o vencido")
    user = db.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuario inactivo")
    stored.revoked_at = now
    return issue_tokens(db, user)


@router.post("/logout", response_model=MessageOut)
def logout(payload: RefreshIn, db: DbSession) -> MessageOut:
    stored = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_digest(payload.refresh_token))
    )
    if stored and stored.revoked_at is None:
        stored.revoked_at = datetime.now(UTC)
        db.commit()
    return MessageOut(message="Sesión cerrada")


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return serialize_user(user)


@router.get("/users", response_model=list[UserOut])
def list_users(admin: AdminUser, db: DbSession, role: str | None = None) -> list[UserOut]:
    query = select(User).where(
        User.building_id == admin.building_id,
        User.is_active.is_(True),
    )
    if role:
        from app.models import Role

        query = query.join(User.role).where(Role.name == role)
    return [serialize_user(user) for user in db.scalars(query.order_by(User.full_name))]


@router.post("/invitations", response_model=InvitationCreated, status_code=201)
def invite(
    payload: InvitationCreate, admin: AdminUser, db: DbSession, background: BackgroundTasks
) -> InvitationCreated:
    invitation, raw_token = create_invitation(db, admin, str(payload.email), payload.role)
    link = f"{settings.frontend_url}/accept-invitation?token={raw_token}"
    background.add_task(
        send_email,
        invitation.email,
        "Invitación a MiEdificio",
        f"Has sido invitado a MiEdificio. Completa tu registro en: {link}\nEl enlace vence en 48 horas.",
    )
    return InvitationCreated(
        id=invitation.id, email=invitation.email, expires_at=invitation.expires_at.isoformat()
    )


@router.post("/invitations/accept", response_model=TokenPair)
def accept_invitation(payload: InvitationAccept, db: DbSession) -> TokenPair:
    user = consume_invitation(db, payload.token, payload.full_name, payload.password, payload.phone)
    return issue_tokens(db, user)


@router.post("/password/forgot", response_model=MessageOut, status_code=202)
def forgot_password(
    payload: ForgotPasswordIn, db: DbSession, background: BackgroundTasks
) -> MessageOut:
    user = db.scalar(
        select(User).where(User.email == str(payload.email).lower(), User.is_active.is_(True))
    )
    if user:
        raw_token = generate_opaque_token()
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=token_digest(raw_token),
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )
        db.commit()
        link = f"{settings.frontend_url}/reset-password?token={raw_token}"
        background.add_task(
            send_email,
            user.email,
            "Restablece tu contraseña",
            f"Usa este enlace durante la próxima hora: {link}",
        )
    return MessageOut(message="Si el correo está registrado, recibirá instrucciones")


@router.post("/password/reset", response_model=MessageOut)
def reset_password(payload: ResetPasswordIn, db: DbSession) -> MessageOut:
    now = datetime.now(UTC)
    stored = db.scalar(
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == token_digest(payload.token))
        .with_for_update()
    )
    if stored is None or stored.used_at is not None or stored.expires_at <= now:
        raise HTTPException(status_code=400, detail="El enlace es inválido o ha vencido")
    user = db.get(User, stored.user_id)
    if user is None:
        raise HTTPException(status_code=400, detail="El enlace es inválido")
    user.password_hash = hash_password(payload.new_password)
    stored.used_at = now
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    db.commit()
    return MessageOut(message="Contraseña actualizada")
