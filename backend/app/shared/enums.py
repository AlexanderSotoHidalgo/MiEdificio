import enum


class FeeStatus(str, enum.Enum):
    PENDING = "Pendiente"
    IN_REVIEW = "Pago en revisión"
    PAID = "Pagada"
    CANCELLED = "Anulada"


class PaymentStatus(str, enum.Enum):
    IN_REVIEW = "En revisión"
    APPROVED = "Aprobado"
    OBSERVED = "Observado"


class PaymentAction(str, enum.Enum):
    REPORTED = "Reportado"
    APPROVED = "Aprobado"
    OBSERVED = "Observado"
    RESUBMITTED = "Reenviado"


class FeeAuditAction(str, enum.Enum):
    CREATED = "Creada"
    ADJUSTED = "Ajustada"
    CANCELLED = "Anulada"
