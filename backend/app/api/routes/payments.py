from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.api.deps import AdminUser, CurrentUser, DbSession, ResidentUser
from app.core.config import settings
from app.models import (
    FeeStatus,
    MaintenanceFee,
    PaymentAction,
    PaymentAuditLog,
    PaymentReport,
    PaymentStatus,
    Unit,
)
from app.schemas.schemas import PaymentReportOut, PaymentReviewIn, PaymentReviewOut

router = APIRouter(prefix="/payments", tags=["Pagos"])

ALLOWED_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def _has_valid_signature(content_type: str, header: bytes) -> bool:
    signatures = {
        "application/pdf": (b"%PDF-",),
        "image/jpeg": (b"\xff\xd8\xff",),
        "image/png": (b"\x89PNG\r\n\x1a\n",),
        "image/webp": (b"RIFF",),
    }
    if not any(header.startswith(signature) for signature in signatures[content_type]):
        return False
    return content_type != "image/webp" or header[8:12] == b"WEBP"


def _serialize_payment(report: PaymentReport) -> PaymentReportOut:
    return PaymentReportOut(
        id=report.id,
        fee_id=report.fee_id,
        unit_code=report.fee.unit.code,
        resident_name=report.resident.full_name,
        resident_email=report.resident.email,
        amount=report.amount,
        payment_date=report.payment_date,
        operation_number=report.operation_number,
        receipt_original_name=report.receipt_original_name,
        receipt_content_type=report.receipt_content_type,
        status=report.status,
        review_comment=report.review_comment,
        reviewed_at=report.reviewed_at,
        created_at=report.created_at,
    )


@router.post("/report", response_model=PaymentReportOut, status_code=201)
async def report_payment(
    db: DbSession,
    user: ResidentUser,
    fee_id: Annotated[int, Form()],
    amount: Annotated[Decimal, Form(gt=0, max_digits=12, decimal_places=2)],
    payment_date: Annotated[date, Form()],
    operation_number: Annotated[str, Form(min_length=1, max_length=80)],
    receipt: Annotated[UploadFile, File()],
) -> PaymentReportOut:
    fee = db.scalar(
        select(MaintenanceFee)
        .join(MaintenanceFee.unit)
        .where(MaintenanceFee.id == fee_id, Unit.resident_id == user.id)
        .options(joinedload(MaintenanceFee.unit))
    )
    if fee is None:
        raise HTTPException(status_code=404, detail="Cuota no encontrada")
    if fee.status == FeeStatus.PAID:
        raise HTTPException(status_code=409, detail="La cuota ya está pagada")
    if fee.status == FeeStatus.IN_REVIEW:
        raise HTTPException(status_code=409, detail="La cuota ya tiene un pago en revisión")
    if amount > fee.balance:
        raise HTTPException(status_code=422, detail="El monto supera el saldo pendiente")

    content_type = (receipt.content_type or "").lower()
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="Use un comprobante PDF, JPG, PNG o WEBP")

    upload_dir = settings.upload_dir.resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4().hex}{ALLOWED_TYPES[content_type]}"
    destination = upload_dir / stored_name
    temp_destination = upload_dir / f"{stored_name}.part"
    max_bytes = settings.max_upload_mb * 1024 * 1024
    total = 0
    header = b""
    try:
        with temp_destination.open("wb") as output:
            while chunk := await receipt.read(1024 * 1024):
                if not header:
                    header = chunk[:16]
                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"El archivo supera el máximo de {settings.max_upload_mb} MB",
                    )
                output.write(chunk)
        if total == 0 or not _has_valid_signature(content_type, header):
            raise HTTPException(status_code=422, detail="El contenido del comprobante no es válido")
        temp_destination.replace(destination)
    except Exception:
        temp_destination.unlink(missing_ok=True)
        destination.unlink(missing_ok=True)
        raise
    finally:
        await receipt.close()

    report = PaymentReport(
        fee_id=fee.id,
        resident_id=user.id,
        amount=amount,
        payment_date=payment_date,
        operation_number=operation_number.strip(),
        receipt_path=stored_name,
        receipt_original_name=Path(receipt.filename or stored_name).name[:255],
        receipt_content_type=content_type,
    )
    fee.status = FeeStatus.IN_REVIEW
    db.add(report)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=409, detail="El número de operación ya fue reportado")
    db.refresh(report)
    report.fee = fee
    report.resident = user
    return _serialize_payment(report)


@router.get("/pending", response_model=list[PaymentReportOut])
def pending_payments(_: AdminUser, db: DbSession) -> list[PaymentReportOut]:
    statement = (
        select(PaymentReport)
        .where(PaymentReport.status == PaymentStatus.PENDING)
        .options(
            joinedload(PaymentReport.fee).joinedload(MaintenanceFee.unit),
            joinedload(PaymentReport.resident),
        )
        .order_by(PaymentReport.created_at)
    )
    return [_serialize_payment(report) for report in db.scalars(statement).unique()]


@router.get("/{payment_id}/receipt", response_class=FileResponse)
def get_receipt(payment_id: int, user: CurrentUser, db: DbSession) -> FileResponse:
    report = db.get(PaymentReport, payment_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    if user.role.name != "administrador" and report.resident_id != user.id:
        raise HTTPException(status_code=403, detail="No tiene acceso a este comprobante")
    receipt_path = (settings.upload_dir.resolve() / report.receipt_path).resolve()
    if receipt_path.parent != settings.upload_dir.resolve() or not receipt_path.is_file():
        raise HTTPException(status_code=404, detail="Comprobante no disponible")
    return FileResponse(
        receipt_path,
        media_type=report.receipt_content_type,
        filename=report.receipt_original_name,
        content_disposition_type="inline",
    )


@router.post("/{payment_id}/review", response_model=PaymentReviewOut)
def review_payment(
    payment_id: int,
    payload: PaymentReviewIn,
    admin: AdminUser,
    db: DbSession,
) -> PaymentReviewOut:
    try:
        report = db.scalar(
            select(PaymentReport).where(PaymentReport.id == payment_id).with_for_update()
        )
        if report is None:
            raise HTTPException(status_code=404, detail="Pago no encontrado")
        fee = db.scalar(
            select(MaintenanceFee).where(MaintenanceFee.id == report.fee_id).with_for_update()
        )
        if fee is None:
            raise HTTPException(status_code=404, detail="Cuota no encontrada")

        requested_status = (
            PaymentStatus.APPROVED if payload.action == "approve" else PaymentStatus.OBSERVED
        )
        if report.status != PaymentStatus.PENDING:
            if report.status != requested_status:
                raise HTTPException(status_code=409, detail="El pago ya fue revisado con otra decisión")
            db.rollback()
            return PaymentReviewOut(
                payment_id=report.id,
                payment_status=report.status,
                fee_status=fee.status,
                paid_amount=fee.paid_amount,
                balance=fee.balance,
                idempotent=True,
            )

        reason = payload.reason.strip() if payload.reason else None
        if payload.action == "observe" and not reason:
            raise HTTPException(status_code=422, detail="Debe indicar el motivo de la observación")

        now = datetime.now(timezone.utc)
        report.status = requested_status
        report.review_comment = reason
        report.reviewed_at = now
        if requested_status == PaymentStatus.APPROVED:
            applied = min(report.amount, fee.balance)
            fee.paid_amount += applied
            fee.status = FeeStatus.PAID if fee.balance == Decimal("0.00") else FeeStatus.PENDING
            action = PaymentAction.APPROVED
        else:
            has_other_pending = db.scalar(
                select(
                    exists().where(
                        PaymentReport.fee_id == fee.id,
                        PaymentReport.id != report.id,
                        PaymentReport.status == PaymentStatus.PENDING,
                    )
                )
            )
            fee.status = FeeStatus.IN_REVIEW if has_other_pending else FeeStatus.PENDING
            action = PaymentAction.OBSERVED

        db.add(
            PaymentAuditLog(
                payment_report_id=report.id,
                admin_id=admin.id,
                action=action,
                reason=reason,
            )
        )
        db.commit()
        return PaymentReviewOut(
            payment_id=report.id,
            payment_status=report.status,
            fee_status=fee.status,
            paid_amount=fee.paid_amount,
            balance=fee.balance,
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
