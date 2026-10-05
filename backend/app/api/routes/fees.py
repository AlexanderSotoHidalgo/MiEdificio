from decimal import Decimal

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import selectinload

from app.api.deps import AdminUser, DbSession, ResidentUser
from app.models import MaintenanceFee, Unit
from app.schemas.schemas import FeeAccountOut, FeeBatchCreate, FeeBatchResult, PaymentSummary

router = APIRouter(prefix="/fees", tags=["Cuotas"])


@router.post("/batch", response_model=FeeBatchResult, status_code=201)
def create_batch(payload: FeeBatchCreate, _: AdminUser, db: DbSession) -> FeeBatchResult:
    unit_ids = list(db.scalars(select(Unit.id)))
    rows = [
        {
            "unit_id": unit_id,
            "period_year": payload.period_year,
            "period_month": payload.period_month,
            "due_date": payload.due_date,
            "amount": payload.amount,
            "paid_amount": Decimal("0.00"),
            "status": "Pendiente",
        }
        for unit_id in unit_ids
    ]
    if not rows:
        return FeeBatchResult(created=0, skipped=0)
    statement = (
        insert(MaintenanceFee)
        .values(rows)
        .on_conflict_do_nothing(constraint="uq_fee_unit_period")
        .returning(MaintenanceFee.id)
    )
    created = len(db.scalars(statement).all())
    db.commit()
    return FeeBatchResult(created=created, skipped=len(rows) - created)


@router.get("/my-account", response_model=list[FeeAccountOut])
def my_account(user: ResidentUser, db: DbSession) -> list[FeeAccountOut]:
    statement = (
        select(MaintenanceFee)
        .join(MaintenanceFee.unit)
        .where(Unit.resident_id == user.id)
        .options(selectinload(MaintenanceFee.unit), selectinload(MaintenanceFee.payment_reports))
        .order_by(MaintenanceFee.period_year.desc(), MaintenanceFee.period_month.desc(), Unit.code)
    )
    fees = db.scalars(statement).unique().all()
    return [
        FeeAccountOut(
            id=fee.id,
            unit_id=fee.unit_id,
            unit_code=fee.unit.code,
            period_year=fee.period_year,
            period_month=fee.period_month,
            due_date=fee.due_date,
            amount=fee.amount,
            paid_amount=fee.paid_amount,
            balance=fee.balance,
            status=fee.status,
            payment_reports=[
                PaymentSummary(
                    id=report.id,
                    status=report.status,
                    amount=report.amount,
                    operation_number=report.operation_number,
                    review_comment=report.review_comment,
                    created_at=report.created_at,
                )
                for report in sorted(fee.payment_reports, key=lambda item: item.created_at, reverse=True)
            ],
        )
        for fee in fees
    ]
