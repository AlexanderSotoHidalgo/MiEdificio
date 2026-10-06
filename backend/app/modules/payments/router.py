import json
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import AdminUser, CurrentUser, DbSession, ResidentUser
from app.core.config import settings
from app.models import (
    MaintenanceFee,
    PaymentAllocation,
    PaymentReport,
    PaymentStatus,
    Receipt,
    Role,
    User,
)
from app.modules.notifications import send_email
from app.modules.payments.receipt_validator import validate_receipt
from app.modules.payments.schemas import (
    AllocationIn,
    ObservationReasonOut,
    PaymentReportOut,
    PaymentReviewIn,
    PaymentReviewOut,
)
from app.modules.payments.service import (
    load_report,
    report_payment,
    review_payment,
    serialize_report,
)
from app.modules.storage import get_storage

router = APIRouter(prefix="/payments", tags=["Pagos"])

OBSERVATION_REASONS = [
    ("ILLEGIBLE", "El comprobante no es legible"),
    ("AMOUNT_MISMATCH", "El monto no coincide"),
    ("OPERATION_NOT_FOUND", "La operación no fue encontrada"),
    ("DUPLICATE", "El comprobante corresponde a otro pago"),
    ("OTHER", "Otro motivo"),
]


def parse_allocations(raw: str) -> list[AllocationIn]:
    try:
        return TypeAdapter(list[AllocationIn]).validate_python(json.loads(raw))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(
            status_code=422, detail="Las asignaciones de cuotas no son válidas"
        ) from exc


@router.post("/report", response_model=PaymentReportOut, status_code=201)
async def create_report(
    background: BackgroundTasks,
    db: DbSession,
    user: ResidentUser,
    amount: Annotated[Decimal, Form(gt=0, max_digits=12, decimal_places=2)],
    payment_date: Annotated[date, Form()],
    operation_number: Annotated[str, Form(min_length=1, max_length=80)],
    allocations: Annotated[str, Form()],
    receipt: Annotated[UploadFile, File()],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=100)],
) -> PaymentReportOut:
    validated = await validate_receipt(receipt, settings.max_upload_mb)
    result = report_payment(
        db,
        get_storage(),
        user,
        parse_allocations(allocations),
        amount,
        payment_date,
        operation_number.strip(),
        validated,
        idempotency_key,
    )
    admins = db.scalars(
        select(User.email)
        .join(User.role)
        .where(
            User.building_id == user.building_id,
            Role.name == "administrador",
            User.is_active.is_(True),
        )
    ).all()
    for email in admins:
        background.add_task(
            send_email,
            email,
            "Nuevo pago por revisar",
            f"{user.full_name} reportó S/ {amount:.2f}, operación {operation_number}.",
        )
    return result


@router.get("", response_model=list[PaymentReportOut])
def list_payments(
    admin: AdminUser,
    db: DbSession,
    status: str = "En revisión",
    period: str | None = None,
    unit: str | None = None,
) -> list[PaymentReportOut]:
    query = (
        select(PaymentReport)
        .where(PaymentReport.building_id == admin.building_id)
        .options(
            selectinload(PaymentReport.resident),
            selectinload(PaymentReport.receipt),
            selectinload(PaymentReport.allocations)
            .selectinload(PaymentAllocation.fee)
            .selectinload(MaintenanceFee.unit),
            selectinload(PaymentReport.allocations)
            .selectinload(PaymentAllocation.fee)
            .selectinload(MaintenanceFee.concept),
        )
        .order_by(PaymentReport.created_at)
    )
    if status:
        try:
            query = query.where(PaymentReport.status == PaymentStatus(status))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Estado de pago inválido") from exc
    reports = list(db.scalars(query).unique())
    if period:
        try:
            year, month = (int(part) for part in period.split("-", 1))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Periodo inválido; use YYYY-MM") from exc
        reports = [
            report
            for report in reports
            if any(
                item.fee.period.year == year and item.fee.period.month == month
                for item in report.allocations
            )
        ]
    if unit:
        needle = unit.strip().lower()
        reports = [
            report
            for report in reports
            if any(needle in item.fee.unit.code.lower() for item in report.allocations)
        ]
    return [serialize_report(report) for report in reports]


@router.get("/pending", response_model=list[PaymentReportOut])
def pending_payments(admin: AdminUser, db: DbSession) -> list[PaymentReportOut]:
    return list_payments(admin, db, status=PaymentStatus.IN_REVIEW.value)


@router.get("/observation-reasons", response_model=list[ObservationReasonOut])
def observation_reasons(_: CurrentUser) -> list[ObservationReasonOut]:
    return [ObservationReasonOut(code=code, label=label) for code, label in OBSERVATION_REASONS]


@router.get("/{payment_id}/receipt")
def payment_receipt(payment_id: int, user: CurrentUser, db: DbSession) -> StreamingResponse:
    report = db.get(PaymentReport, payment_id)
    if report is None or report.building_id != user.building_id:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    if user.role.name != "administrador" and report.resident_id != user.id:
        raise HTTPException(status_code=403, detail="No tiene acceso a este comprobante")
    storage = get_storage()
    if not storage.exists(report.storage_key):
        raise HTTPException(status_code=404, detail="Comprobante no disponible")
    content = storage.read(report.storage_key)
    return StreamingResponse(
        iter([content]),
        media_type=report.content_type,
        headers={"Content-Disposition": f'inline; filename="{report.original_filename}"'},
    )


@router.get("/{payment_id}/acknowledgement")
def acknowledgement(payment_id: int, user: CurrentUser, db: DbSession) -> StreamingResponse:
    report = db.get(PaymentReport, payment_id)
    if report is None or report.building_id != user.building_id:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    if user.role.name != "administrador" and report.resident_id != user.id:
        raise HTTPException(status_code=403, detail="No tiene acceso a este recibo")
    receipt = db.scalar(select(Receipt).where(Receipt.payment_report_id == report.id))
    if receipt is None:
        raise HTTPException(status_code=404, detail="El recibo aún no está disponible")
    content = get_storage().read(receipt.storage_key)
    return StreamingResponse(
        iter([content]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{receipt.number}.pdf"'},
    )


@router.post("/{payment_id}/review", response_model=PaymentReviewOut)
def review(
    payment_id: int,
    payload: PaymentReviewIn,
    admin: AdminUser,
    db: DbSession,
    background: BackgroundTasks,
) -> PaymentReviewOut:
    result = review_payment(db, get_storage(), payment_id, admin, payload.action, payload.reason)
    report = load_report(db, payment_id)
    assert report is not None
    if not result.idempotent:
        if result.payment_status == PaymentStatus.APPROVED.value:
            subject = "Pago aprobado"
            body = (
                f"Tu pago de S/ {report.amount:.2f} fue aprobado. Recibo: {result.receipt_number}."
            )
        else:
            subject = "Pago observado"
            body = f"Tu pago fue observado. Motivo: {report.observation_reason}"
        background.add_task(send_email, report.resident.email, subject, body)
    return result
