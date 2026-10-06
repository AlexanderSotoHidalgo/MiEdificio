from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, selectinload

from app.models import (
    FeeAuditAction,
    FeeAuditLog,
    FeeConcept,
    FeeStatus,
    MaintenanceFee,
    PaymentAllocation,
    PaymentReport,
    PaymentStatus,
    Unit,
)
from app.modules.fees.schemas import (
    FeeAccountOut,
    FeeBatchCreate,
    FeeBatchResult,
    FeeBatchSkipped,
    PaymentSummary,
)

CENT = Decimal("0.01")


def calculate_fee_status(
    stored_status: FeeStatus,
    due_date: date,
    amount: Decimal,
    approved_amount: Decimal,
    in_review_amount: Decimal,
    today: date | None = None,
) -> str:
    if stored_status == FeeStatus.CANCELLED:
        return FeeStatus.CANCELLED.value
    balance = max(Decimal("0.00"), amount - approved_amount)
    if balance == 0:
        return FeeStatus.PAID.value
    if in_review_amount > 0:
        return FeeStatus.IN_REVIEW.value
    if due_date < (today or date.today()):
        return "Vencida"
    return FeeStatus.PENDING.value


def persisted_fee_status(
    stored_status: FeeStatus,
    amount: Decimal,
    approved_amount: Decimal,
    in_review_amount: Decimal,
) -> FeeStatus:
    if stored_status == FeeStatus.CANCELLED:
        return FeeStatus.CANCELLED
    if approved_amount >= amount:
        return FeeStatus.PAID
    if in_review_amount > 0:
        return FeeStatus.IN_REVIEW
    return FeeStatus.PENDING


def allocation_totals(fee: MaintenanceFee) -> tuple[Decimal, Decimal]:
    approved = Decimal("0.00")
    reviewing = Decimal("0.00")
    for allocation in fee.allocations:
        status = allocation.payment_report.status
        if status == PaymentStatus.APPROVED:
            approved += allocation.amount
        elif status == PaymentStatus.IN_REVIEW:
            reviewing += allocation.amount
    return approved.quantize(CENT), reviewing.quantize(CENT)


def serialize_fee(fee: MaintenanceFee) -> FeeAccountOut:
    approved, reviewing = allocation_totals(fee)
    balance = max(Decimal("0.00"), fee.amount - approved).quantize(CENT)
    return FeeAccountOut(
        id=fee.id,
        unit_id=fee.unit_id,
        unit_code=fee.unit.code,
        concept=fee.concept.name,
        period=fee.period,
        due_date=fee.due_date,
        amount=fee.amount,
        paid_amount=approved,
        in_review_amount=reviewing,
        balance=balance,
        available_to_report=max(Decimal("0.00"), balance - reviewing).quantize(CENT),
        currency=fee.currency,
        status=calculate_fee_status(fee.status, fee.due_date, fee.amount, approved, reviewing),
        payment_reports=[
            PaymentSummary(
                id=allocation.payment_report.id,
                status=allocation.payment_report.status.value,
                amount=allocation.amount,
                operation_number=allocation.payment_report.operation_number,
                observation_reason=allocation.payment_report.observation_reason,
                receipt_number=(
                    allocation.payment_report.receipt.number
                    if allocation.payment_report.receipt
                    else None
                ),
                created_at=allocation.payment_report.created_at,
            )
            for allocation in sorted(
                fee.allocations, key=lambda item: item.payment_report.created_at, reverse=True
            )
        ],
    )


def resident_fees_query(user_id: int):
    from app.models import UnitResident

    return (
        select(MaintenanceFee)
        .join(MaintenanceFee.unit)
        .join(Unit.resident_links)
        .where(
            UnitResident.resident_id == user_id,
            UnitResident.is_active.is_(True),
            UnitResident.start_date <= date.today(),
            (UnitResident.end_date.is_(None) | (UnitResident.end_date >= date.today())),
        )
        .options(
            selectinload(MaintenanceFee.unit),
            selectinload(MaintenanceFee.concept),
            selectinload(MaintenanceFee.allocations).selectinload(PaymentAllocation.payment_report),
            selectinload(MaintenanceFee.allocations)
            .selectinload(PaymentAllocation.payment_report)
            .selectinload(PaymentReport.receipt),
        )
        .order_by(MaintenanceFee.period.desc(), Unit.code, MaintenanceFee.id)
    )


def generate_batch(
    db: Session, building_id: int, admin_id: int, payload: FeeBatchCreate
) -> FeeBatchResult:
    concept = db.scalar(
        select(FeeConcept).where(
            FeeConcept.building_id == building_id,
            FeeConcept.code == payload.concept_code.upper(),
            FeeConcept.is_active.is_(True),
        )
    )
    if concept is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail="Concepto de cobro no encontrado")
    units = list(
        db.scalars(
            select(Unit)
            .where(Unit.building_id == building_id, Unit.is_active.is_(True))
            .order_by(Unit.id)
        )
    )
    skipped: list[FeeBatchSkipped] = []
    rows: list[dict] = []
    for unit in units:
        amount = payload.amount
        if payload.calculation == "coefficient":
            amount = (payload.amount * unit.participation_coefficient).quantize(
                CENT, rounding=ROUND_HALF_UP
            )
        if amount <= 0:
            skipped.append(
                FeeBatchSkipped(unit_id=unit.id, unit_code=unit.code, reason="Coeficiente en cero")
            )
            continue
        rows.append(
            {
                "building_id": building_id,
                "unit_id": unit.id,
                "concept_id": concept.id,
                "period": payload.period,
                "due_date": payload.due_date,
                "amount": amount,
                "currency": "PEN",
                "status": FeeStatus.PENDING,
            }
        )
    if not rows:
        return FeeBatchResult(created=0, skipped=skipped)
    statement = (
        insert(MaintenanceFee)
        .values(rows)
        .on_conflict_do_nothing(constraint="uq_fee_unit_period_concept")
        .returning(MaintenanceFee.id, MaintenanceFee.unit_id, MaintenanceFee.amount)
    )
    inserted = list(db.execute(statement))
    created_unit_ids = {row.unit_id for row in inserted}
    unit_by_id = {unit.id: unit for unit in units}
    for row in rows:
        if row["unit_id"] not in created_unit_ids:
            unit = unit_by_id[row["unit_id"]]
            skipped.append(
                FeeBatchSkipped(unit_id=unit.id, unit_code=unit.code, reason="Cuota ya existente")
            )
    for fee_id, _unit_id, amount in inserted:
        db.add(
            FeeAuditLog(
                fee_id=fee_id,
                admin_id=admin_id,
                action=FeeAuditAction.CREATED,
                new_amount=amount,
                reason="Generación por lote",
            )
        )
    db.commit()
    return FeeBatchResult(created=len(inserted), skipped=skipped)


def approved_total_for_fee(db: Session, fee_id: int) -> Decimal:
    value = db.scalar(
        select(func.coalesce(func.sum(PaymentAllocation.amount), 0))
        .join(PaymentAllocation.payment_report)
        .where(PaymentAllocation.fee_id == fee_id, PaymentReport.status == PaymentStatus.APPROVED)
    )
    return Decimal(value or 0).quantize(CENT)
