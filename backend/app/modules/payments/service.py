from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from json import dumps
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Building,
    IdempotencyRecord,
    MaintenanceFee,
    PaymentAction,
    PaymentAllocation,
    PaymentAuditLog,
    PaymentReport,
    PaymentStatus,
    Receipt,
    ReceiptSequence,
    Unit,
    UnitResident,
    User,
)
from app.modules.fees.service import approved_total_for_fee, persisted_fee_status
from app.modules.payments.receipt_generator import generate_receipt_pdf
from app.modules.payments.receipt_validator import ValidatedReceipt
from app.modules.payments.schemas import (
    AllocationIn,
    AllocationOut,
    PaymentReportOut,
    PaymentReviewOut,
)
from app.modules.storage.base import StorageBackend

CENT = Decimal("0.01")


def load_report(db: Session, report_id: int) -> PaymentReport | None:
    return db.scalar(
        select(PaymentReport)
        .where(PaymentReport.id == report_id)
        .options(
            selectinload(PaymentReport.resident),
            selectinload(PaymentReport.allocations)
            .selectinload(PaymentAllocation.fee)
            .selectinload(MaintenanceFee.unit),
            selectinload(PaymentReport.allocations)
            .selectinload(PaymentAllocation.fee)
            .selectinload(MaintenanceFee.concept),
            selectinload(PaymentReport.receipt),
        )
    )


def serialize_report(report: PaymentReport) -> PaymentReportOut:
    return PaymentReportOut(
        id=report.id,
        resident_id=report.resident_id,
        resident_name=report.resident.full_name,
        resident_email=report.resident.email,
        amount=report.amount,
        currency=report.currency,
        payment_date=report.payment_date,
        operation_number=report.operation_number,
        original_filename=report.original_filename,
        content_type=report.content_type,
        status=report.status.value,
        observation_reason=report.observation_reason,
        reviewed_at=report.reviewed_at,
        created_at=report.created_at,
        allocations=[
            AllocationOut(
                fee_id=item.fee_id,
                unit_code=item.fee.unit.code,
                concept=item.fee.concept.name,
                period=item.fee.period,
                amount=item.amount,
            )
            for item in report.allocations
        ],
        receipt_number=report.receipt.number if report.receipt else None,
    )


def pending_total_for_fee(
    db: Session, fee_id: int, exclude_report_id: int | None = None
) -> Decimal:
    query = (
        select(func.coalesce(func.sum(PaymentAllocation.amount), 0))
        .join(PaymentAllocation.payment_report)
        .where(PaymentAllocation.fee_id == fee_id, PaymentReport.status == PaymentStatus.IN_REVIEW)
    )
    if exclude_report_id is not None:
        query = query.where(PaymentReport.id != exclude_report_id)
    return Decimal(db.scalar(query)).quantize(CENT)


def report_payment(
    db: Session,
    storage: StorageBackend,
    user: User,
    allocations: list[AllocationIn],
    amount: Decimal,
    payment_date,
    operation_number: str,
    receipt: ValidatedReceipt,
    idempotency_key: str,
) -> PaymentReportOut:
    normalized = sorted((item.fee_id, str(item.amount.quantize(CENT))) for item in allocations)
    request_hash = sha256(
        dumps(
            [
                normalized,
                str(amount.quantize(CENT)),
                str(payment_date),
                operation_number,
                receipt.sha256,
            ]
        ).encode()
    ).hexdigest()
    existing_key = db.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.user_id == user.id,
            IdempotencyRecord.endpoint == "POST /payments/report",
            IdempotencyRecord.key == idempotency_key,
        )
    )
    if existing_key:
        if existing_key.request_hash != request_hash:
            raise HTTPException(
                status_code=409, detail="Idempotency-Key ya fue usado con otros datos"
            )
        if existing_key.response_body:
            existing = load_report(db, existing_key.response_body["payment_id"])
            if existing:
                return serialize_report(existing)
    if not allocations or len({item.fee_id for item in allocations}) != len(allocations):
        raise HTTPException(status_code=422, detail="Incluye al menos una cuota sin repetirla")
    if sum((item.amount for item in allocations), Decimal("0")) != amount:
        raise HTTPException(
            status_code=422, detail="La suma de asignaciones no coincide con el monto"
        )
    fee_ids = [item.fee_id for item in allocations]
    fees = list(
        db.scalars(
            select(MaintenanceFee)
            .join(MaintenanceFee.unit)
            .join(Unit.resident_links)
            .where(
                MaintenanceFee.id.in_(fee_ids),
                UnitResident.resident_id == user.id,
                UnitResident.is_active.is_(True),
                MaintenanceFee.building_id == user.building_id,
            )
            .with_for_update(of=MaintenanceFee)
        ).unique()
    )
    fee_map = {fee.id: fee for fee in fees}
    if set(fee_ids) != set(fee_map):
        raise HTTPException(status_code=404, detail="Una o más cuotas no están disponibles")
    for item in allocations:
        fee = fee_map[item.fee_id]
        approved = approved_total_for_fee(db, fee.id)
        pending = pending_total_for_fee(db, fee.id)
        available = fee.amount - approved - pending
        if fee.status.value == "Anulada" or item.amount > available:
            raise HTTPException(
                status_code=422,
                detail=f"El monto para la cuota {fee.id} supera el saldo disponible de S/ {max(available, Decimal('0')):.2f}",
            )
    duplicate = db.scalar(
        select(PaymentReport.id).where(
            PaymentReport.building_id == user.building_id,
            (
                (PaymentReport.file_hash == receipt.sha256)
                | (
                    (PaymentReport.operation_number == operation_number)
                    & (PaymentReport.amount == amount)
                    & (PaymentReport.payment_date == payment_date)
                )
            ),
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="Este pago o comprobante ya fue reportado")
    key = f"payment-proofs/{user.building_id}/{uuid4().hex}{receipt.extension}"
    storage.save(key, receipt.content, receipt.content_type)
    try:
        report = PaymentReport(
            building_id=user.building_id,
            resident_id=user.id,
            amount=amount,
            currency="PEN",
            payment_date=payment_date,
            operation_number=operation_number.strip(),
            storage_key=key,
            original_filename=receipt.original_filename,
            content_type=receipt.content_type,
            file_size=receipt.size,
            file_hash=receipt.sha256,
        )
        db.add(report)
        db.flush()
        for item in allocations:
            db.add(
                PaymentAllocation(
                    payment_report_id=report.id, fee_id=item.fee_id, amount=item.amount
                )
            )
            fee_map[item.fee_id].status = persisted_fee_status(
                fee_map[item.fee_id].status,
                fee_map[item.fee_id].amount,
                approved_total_for_fee(db, item.fee_id),
                pending_total_for_fee(db, item.fee_id) + item.amount,
            )
        db.add(
            PaymentAuditLog(
                payment_report_id=report.id,
                previous_status=None,
                new_status=PaymentStatus.IN_REVIEW.value,
                action=PaymentAction.REPORTED,
                amount_snapshot=amount,
            )
        )
        idempotency = existing_key or IdempotencyRecord(
            user_id=user.id,
            endpoint="POST /payments/report",
            key=idempotency_key,
            request_hash=request_hash,
        )
        idempotency.response_status = 201
        idempotency.response_body = {"payment_id": report.id}
        db.add(idempotency)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        storage.delete(key)
        replay = db.scalar(
            select(IdempotencyRecord).where(
                IdempotencyRecord.user_id == user.id,
                IdempotencyRecord.endpoint == "POST /payments/report",
                IdempotencyRecord.key == idempotency_key,
            )
        )
        if replay and replay.request_hash == request_hash and replay.response_body:
            replayed_report = load_report(db, replay.response_body["payment_id"])
            if replayed_report:
                return serialize_report(replayed_report)
        raise HTTPException(
            status_code=409, detail="El pago o comprobante ya fue reportado"
        ) from exc
    except Exception:
        db.rollback()
        storage.delete(key)
        raise
    loaded_report = load_report(db, report.id)
    assert loaded_report is not None
    return serialize_report(loaded_report)


def review_payment(
    db: Session,
    storage: StorageBackend,
    report_id: int,
    admin: User,
    action: str,
    reason: str | None,
) -> PaymentReviewOut:
    report = db.scalar(
        select(PaymentReport)
        .where(PaymentReport.id == report_id, PaymentReport.building_id == admin.building_id)
        .with_for_update()
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    requested = PaymentStatus.APPROVED if action == "approve" else PaymentStatus.OBSERVED
    if report.status != PaymentStatus.IN_REVIEW:
        if report.status != requested:
            raise HTTPException(status_code=409, detail="El pago ya fue revisado con otra decisión")
        loaded = load_report(db, report.id)
        assert loaded is not None
        return PaymentReviewOut(
            payment_id=report.id,
            payment_status=report.status.value,
            fee_statuses={item.fee_id: item.fee.status.value for item in loaded.allocations},
            receipt_number=loaded.receipt.number if loaded.receipt else None,
            idempotent=True,
        )
    clean_reason = reason.strip() if reason else None
    if requested == PaymentStatus.OBSERVED and not clean_reason:
        raise HTTPException(status_code=422, detail="El motivo de observación es obligatorio")
    allocations = list(
        db.scalars(
            select(PaymentAllocation)
            .where(PaymentAllocation.payment_report_id == report.id)
            .options(selectinload(PaymentAllocation.fee))
        )
    )
    fee_ids = [item.fee_id for item in allocations]
    locked_fees = list(
        db.scalars(select(MaintenanceFee).where(MaintenanceFee.id.in_(fee_ids)).with_for_update())
    )
    fee_map = {fee.id: fee for fee in locked_fees}
    receipt_key: str | None = None
    receipt_number: str | None = None
    try:
        if requested == PaymentStatus.APPROVED:
            for item in allocations:
                available = fee_map[item.fee_id].amount - approved_total_for_fee(db, item.fee_id)
                if item.amount > available:
                    raise HTTPException(
                        status_code=409,
                        detail=f"La cuota {item.fee_id} ya no tiene saldo suficiente",
                    )
            report.status = PaymentStatus.APPROVED
            building = db.scalar(
                select(Building).where(Building.id == report.building_id).with_for_update()
            )
            assert building is not None
            year = datetime.now(UTC).year
            sequence = db.scalar(
                select(ReceiptSequence).where(
                    ReceiptSequence.building_id == report.building_id,
                    ReceiptSequence.year == year,
                )
            )
            if sequence is None:
                sequence = ReceiptSequence(building_id=report.building_id, year=year, last_number=0)
                db.add(sequence)
                db.flush()
            sequence.last_number += 1
            receipt_number = f"REC-{year}-{sequence.last_number:06d}"
            loaded = load_report(db, report.id)
            assert loaded is not None
            pdf = generate_receipt_pdf(loaded, receipt_number, building.name)
            receipt_key = f"receipts/{report.building_id}/{year}/{uuid4().hex}.pdf"
            storage.save(receipt_key, pdf, "application/pdf")
            db.add(
                Receipt(
                    building_id=report.building_id,
                    payment_report_id=report.id,
                    number=receipt_number,
                    storage_key=receipt_key,
                    file_hash=sha256(pdf).hexdigest(),
                )
            )
        else:
            report.status = PaymentStatus.OBSERVED
            report.observation_reason = clean_reason
        report.reviewed_by_id = admin.id
        report.reviewed_at = datetime.now(UTC)
        for item in allocations:
            approved = approved_total_for_fee(db, item.fee_id)
            pending = pending_total_for_fee(db, item.fee_id, exclude_report_id=report.id)
            fee_map[item.fee_id].status = persisted_fee_status(
                fee_map[item.fee_id].status, fee_map[item.fee_id].amount, approved, pending
            )
        db.add(
            PaymentAuditLog(
                payment_report_id=report.id,
                admin_id=admin.id,
                previous_status=PaymentStatus.IN_REVIEW.value,
                new_status=requested.value,
                action=PaymentAction.APPROVED
                if requested == PaymentStatus.APPROVED
                else PaymentAction.OBSERVED,
                amount_snapshot=report.amount,
                reason=clean_reason,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        if receipt_key:
            storage.delete(receipt_key)
        raise
    loaded = load_report(db, report.id)
    assert loaded is not None
    return PaymentReviewOut(
        payment_id=report.id,
        payment_status=report.status.value,
        fee_statuses={item.fee_id: item.fee.status.value for item in loaded.allocations},
        receipt_number=receipt_number,
    )
