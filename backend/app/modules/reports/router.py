import csv
from io import BytesIO, StringIO

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import AdminUser, DbSession, ResidentUser
from app.models import FeeStatus, MaintenanceFee, PaymentAllocation, Unit
from app.modules.fees.service import allocation_totals, resident_fees_query, serialize_fee
from app.modules.reports.schemas import DelinquencyRow, FinancialSummary

router = APIRouter(prefix="/reports", tags=["Reportes"])


def building_fees(db: DbSession, building_id: int) -> list[MaintenanceFee]:
    return list(
        db.scalars(
            select(MaintenanceFee)
            .join(MaintenanceFee.unit)
            .where(MaintenanceFee.building_id == building_id)
            .options(
                selectinload(MaintenanceFee.unit),
                selectinload(MaintenanceFee.allocations).selectinload(
                    PaymentAllocation.payment_report
                ),
            )
            .order_by(MaintenanceFee.period.desc(), Unit.code)
        ).unique()
    )


@router.get("/summary", response_model=FinancialSummary)
def summary(admin: AdminUser, db: DbSession, period: str | None = None) -> FinancialSummary:
    assert admin.building_id is not None
    fees = building_fees(db, admin.building_id)
    if period:
        fees = [fee for fee in fees if fee.period.strftime("%Y-%m") == period]
    active = [fee for fee in fees if fee.status != FeeStatus.CANCELLED]
    issued = sum((fee.amount for fee in active), start=0)
    collected = sum((allocation_totals(fee)[0] for fee in active), start=0)
    return FinancialSummary(issued=issued, collected=collected, pending=max(0, issued - collected))


def delinquency_rows(db: DbSession, building_id: int, period: str | None) -> list[DelinquencyRow]:
    rows: list[DelinquencyRow] = []
    for fee in building_fees(db, building_id):
        if fee.status == FeeStatus.CANCELLED or (period and fee.period.strftime("%Y-%m") != period):
            continue
        paid, _reviewing = allocation_totals(fee)
        overdue = (
            max(0, fee.amount - paid) if fee.due_date < __import__("datetime").date.today() else 0
        )
        if overdue:
            rows.append(
                DelinquencyRow(
                    unit_id=fee.unit_id,
                    unit_code=fee.unit.code,
                    period=fee.period.strftime("%Y-%m"),
                    issued=fee.amount,
                    paid=paid,
                    overdue=overdue,
                )
            )
    return rows


@router.get("/delinquency", response_model=list[DelinquencyRow])
def delinquency(admin: AdminUser, db: DbSession, period: str | None = None) -> list[DelinquencyRow]:
    assert admin.building_id is not None
    return delinquency_rows(db, admin.building_id, period)


@router.get("/delinquency.csv")
def delinquency_csv(
    admin: AdminUser, db: DbSession, period: str | None = None
) -> StreamingResponse:
    assert admin.building_id is not None
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["unidad", "periodo", "emitido_pen", "pagado_pen", "vencido_pen"])
    for row in delinquency_rows(db, admin.building_id, period):
        writer.writerow([row.unit_code, row.period, row.issued, row.paid, row.overdue])
    data = ("\ufeff" + output.getvalue()).encode("utf-8")
    return StreamingResponse(
        iter([data]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="morosidad.csv"'},
    )


@router.get("/my-account.pdf")
def my_account_pdf(user: ResidentUser, db: DbSession) -> StreamingResponse:
    fees = [serialize_fee(fee) for fee in db.scalars(resident_fees_query(user.id)).unique()]
    output = BytesIO()
    canvas = Canvas(output, pagesize=A4)
    width, height = A4
    canvas.setTitle("Estado de cuenta MiEdificio")
    canvas.setFont("Helvetica-Bold", 18)
    canvas.drawString(45, height - 55, "Estado de cuenta")
    canvas.setFont("Helvetica", 10)
    canvas.drawString(45, height - 75, user.full_name)
    y = height - 110
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(45, y, "UNIDAD")
    canvas.drawString(105, y, "PERIODO")
    canvas.drawString(165, y, "CONCEPTO")
    canvas.drawRightString(410, y, "IMPORTE")
    canvas.drawRightString(475, y, "PAGADO")
    canvas.drawRightString(width - 45, y, "SALDO")
    canvas.setFont("Helvetica", 8)
    for fee in fees:
        y -= 18
        if y < 55:
            canvas.showPage()
            y = height - 55
        canvas.drawString(45, y, fee.unit_code)
        canvas.drawString(105, y, fee.period.strftime("%m/%Y"))
        canvas.drawString(165, y, fee.concept[:30])
        canvas.drawRightString(410, y, f"S/ {fee.amount:.2f}")
        canvas.drawRightString(475, y, f"S/ {fee.paid_amount:.2f}")
        canvas.drawRightString(width - 45, y, f"S/ {fee.balance:.2f}")
    canvas.save()
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="estado-de-cuenta.pdf"'},
    )
