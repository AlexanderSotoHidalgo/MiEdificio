from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field

from app.models import FeeStatus, PaymentStatus


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: EmailStr
    role: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UnitCreate(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    resident_email: EmailStr | None = None


class UnitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    resident_id: int | None


class FeeBatchCreate(BaseModel):
    period_year: int = Field(ge=2020, le=2100)
    period_month: int = Field(ge=1, le=12)
    due_date: date
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class FeeBatchResult(BaseModel):
    created: int
    skipped: int


class PaymentSummary(BaseModel):
    id: int
    status: PaymentStatus
    amount: Decimal
    operation_number: str
    review_comment: str | None
    created_at: datetime


class FeeAccountOut(BaseModel):
    id: int
    unit_id: int
    unit_code: str
    period_year: int
    period_month: int
    due_date: date
    amount: Decimal
    paid_amount: Decimal
    balance: Decimal
    status: FeeStatus
    payment_reports: list[PaymentSummary] = []


class PaymentReportOut(BaseModel):
    id: int
    fee_id: int
    unit_code: str
    resident_name: str
    resident_email: str
    amount: Decimal
    payment_date: date
    operation_number: str
    receipt_original_name: str
    receipt_content_type: str
    status: PaymentStatus
    review_comment: str | None
    reviewed_at: datetime | None
    created_at: datetime


class PaymentReviewIn(BaseModel):
    action: Literal["approve", "observe"]
    reason: str | None = Field(default=None, max_length=1000)


class PaymentReviewOut(BaseModel):
    payment_id: int
    payment_status: PaymentStatus
    fee_status: FeeStatus
    paid_amount: Decimal
    balance: Decimal
    idempotent: bool = False
