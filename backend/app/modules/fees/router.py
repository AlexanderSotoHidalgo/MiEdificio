from fastapi import APIRouter, BackgroundTasks, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import AdminUser, DbSession, ResidentUser
from app.models import (
    FeeAuditAction,
    FeeAuditLog,
    FeeConcept,
    FeeStatus,
    MaintenanceFee,
    Role,
    User,
)
from app.modules.fees.schemas import (
    FeeAccountOut,
    FeeAdjustmentIn,
    FeeBatchCreate,
    FeeBatchResult,
    FeeConceptCreate,
    FeeConceptOut,
)
from app.modules.fees.service import (
    approved_total_for_fee,
    generate_batch,
    resident_fees_query,
    serialize_fee,
)
from app.modules.notifications import send_email

router = APIRouter(prefix="/fees", tags=["Cuotas"])


@router.get("/concepts", response_model=list[FeeConceptOut])
def list_concepts(admin: AdminUser, db: DbSession) -> list[FeeConcept]:
    return list(
        db.scalars(
            select(FeeConcept)
            .where(FeeConcept.building_id == admin.building_id, FeeConcept.is_active.is_(True))
            .order_by(FeeConcept.name)
        )
    )


@router.post("/concepts", response_model=FeeConceptOut, status_code=201)
def create_concept(payload: FeeConceptCreate, admin: AdminUser, db: DbSession) -> FeeConcept:
    concept = FeeConcept(
        building_id=admin.building_id,
        code=payload.code.strip().upper(),
        name=payload.name.strip(),
        description=payload.description,
    )
    db.add(concept)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="El concepto ya existe") from exc
    db.refresh(concept)
    return concept


@router.post("/batch", response_model=FeeBatchResult, status_code=201)
def create_batch(
    payload: FeeBatchCreate, admin: AdminUser, db: DbSession, background: BackgroundTasks
) -> FeeBatchResult:
    assert admin.building_id is not None
    result = generate_batch(db, admin.building_id, admin.id, payload)
    if result.created:
        recipients = db.scalars(
            select(User.email)
            .join(User.role)
            .where(
                User.building_id == admin.building_id,
                User.is_active.is_(True),
                Role.name == "residente",
            )
        ).all()
        for email in recipients:
            background.add_task(
                send_email,
                email,
                "Nueva cuota en MiEdificio",
                f"Se generó la cuota de {payload.period:%m/%Y}. Ingresa a MiEdificio para revisar tu estado de cuenta.",
            )
    return result


@router.get("/my-account", response_model=list[FeeAccountOut])
def my_account(user: ResidentUser, db: DbSession) -> list[FeeAccountOut]:
    return [serialize_fee(fee) for fee in db.scalars(resident_fees_query(user.id)).unique()]


@router.post("/{fee_id}/adjust", response_model=FeeAccountOut)
def adjust_fee(
    fee_id: int, payload: FeeAdjustmentIn, admin: AdminUser, db: DbSession
) -> FeeAccountOut:
    fee = db.scalar(
        select(MaintenanceFee)
        .where(MaintenanceFee.id == fee_id, MaintenanceFee.building_id == admin.building_id)
        .with_for_update()
    )
    if fee is None:
        raise HTTPException(status_code=404, detail="Cuota no encontrada")
    previous = fee.amount
    approved = approved_total_for_fee(db, fee.id)
    if payload.action == "cancel":
        if approved > 0:
            raise HTTPException(
                status_code=409, detail="No se puede anular una cuota con pagos aprobados"
            )
        fee.status = FeeStatus.CANCELLED
        fee.cancellation_reason = payload.reason
        action = FeeAuditAction.CANCELLED
    else:
        if payload.amount is None:
            raise HTTPException(status_code=422, detail="El nuevo monto es obligatorio")
        if payload.amount < approved:
            raise HTTPException(
                status_code=422, detail="El monto no puede ser menor que lo ya pagado"
            )
        fee.amount = payload.amount
        action = FeeAuditAction.ADJUSTED
    db.add(
        FeeAuditLog(
            fee_id=fee.id,
            admin_id=admin.id,
            action=action,
            previous_amount=previous,
            new_amount=fee.amount,
            reason=payload.reason,
        )
    )
    db.commit()
    # Load the same relationships used by the account serializer.
    from sqlalchemy.orm import selectinload

    from app.models import PaymentAllocation

    fee = db.scalar(
        select(MaintenanceFee)
        .where(MaintenanceFee.id == fee_id)
        .options(
            selectinload(MaintenanceFee.unit),
            selectinload(MaintenanceFee.concept),
            selectinload(MaintenanceFee.allocations).selectinload(PaymentAllocation.payment_report),
        )
    )
    assert fee is not None
    return serialize_fee(fee)
