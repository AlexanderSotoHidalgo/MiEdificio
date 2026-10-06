from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

from app.models import PaymentReport


def generate_receipt_pdf(report: PaymentReport, number: str, building_name: str) -> bytes:
    output = BytesIO()
    canvas = Canvas(output, pagesize=A4)
    width, height = A4
    canvas.setTitle(f"Recibo {number}")
    canvas.setFont("Helvetica-Bold", 18)
    canvas.drawString(55, height - 70, building_name)
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawRightString(width - 55, height - 70, f"RECIBO {number}")
    canvas.setFont("Helvetica", 10)
    canvas.drawString(55, height - 105, f"Residente: {report.resident.full_name}")
    canvas.drawString(55, height - 123, f"Operación: {report.operation_number}")
    canvas.drawString(55, height - 141, f"Fecha de pago: {report.payment_date:%d/%m/%Y}")
    canvas.drawString(55, height - 159, f"Monto total: S/ {report.amount:.2f}")
    y = height - 205
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(55, y, "Aplicación")
    y -= 22
    canvas.setFont("Helvetica", 9)
    for allocation in report.allocations:
        fee = allocation.fee
        label = f"Unidad {fee.unit.code} · {fee.concept.name} · {fee.period:%m/%Y}"
        canvas.drawString(55, y, label)
        canvas.drawRightString(width - 55, y, f"S/ {allocation.amount:.2f}")
        y -= 18
    canvas.setFont("Helvetica-Oblique", 8)
    canvas.drawString(55, 65, "Documento generado electrónicamente por MiEdificio.")
    canvas.showPage()
    canvas.save()
    return output.getvalue()
