from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class FeeConceptCreate(BaseModel):
    code: str = Field(min_length=2, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=1000)


class FeeConceptOut(BaseModel):
    id: int
    code: str
    name: str
    description: str | None
    is_active: bool


class FeeBatchCreate(BaseModel):
    period: date
    due_date: date
    concept_code: str = Field(default="ORDINARIA", min_length=2, max_length=40)
    calculation: Literal["fixed", "coefficient"] = "fixed"
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)

    @field_validator("period")
    @classmethod
    def first_day_of_month(cls, value: date) -> date:
        if value.day != 1:
            raise ValueError("El periodo debe ser el primer día del mes")
        return value


class FeeBatchSkipped(BaseModel):
    unit_id: int
    unit_code: str
    reason: str


class FeeBatchResult(BaseModel):
    created: int
    skipped: list[FeeBatchSkipped]


class FeeAdjustmentIn(BaseModel):
    action: Literal["adjust", "cancel"]
    amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    reason: str = Field(min_length=5, max_length=1000)


class PaymentSummary(BaseModel):
    id: int
    status: str
    amount: Decimal
    operation_number: str
    observation_reason: str | None
    receipt_number: str | None
    created_at: datetime


class FeeAccountOut(BaseModel):
    id: int
    unit_id: int
    unit_code: str
    concept: str
    period: date
    due_date: date
    amount: Decimal
    paid_amount: Decimal
    in_review_amount: Decimal
    balance: Decimal
    available_to_report: Decimal
    currency: str
    status: str
    payment_reports: list[PaymentSummary]
