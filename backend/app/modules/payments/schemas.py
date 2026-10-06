from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class AllocationIn(BaseModel):
    fee_id: int
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class AllocationOut(BaseModel):
    fee_id: int
    unit_code: str
    concept: str
    period: date
    amount: Decimal


class PaymentReportOut(BaseModel):
    id: int
    resident_id: int
    resident_name: str
    resident_email: str
    amount: Decimal
    currency: str
    payment_date: date
    operation_number: str
    original_filename: str
    content_type: str
    status: str
    observation_reason: str | None
    reviewed_at: datetime | None
    created_at: datetime
    allocations: list[AllocationOut]
    receipt_number: str | None = None


class PaymentReviewIn(BaseModel):
    action: str = Field(pattern=r"^(approve|observe)$")
    reason: str | None = Field(default=None, max_length=1000)


class PaymentReviewOut(BaseModel):
    payment_id: int
    payment_status: str
    fee_statuses: dict[int, str]
    receipt_number: str | None = None
    idempotent: bool = False


class ObservationReasonOut(BaseModel):
    code: str
    label: str
