from decimal import Decimal

from pydantic import BaseModel


class FinancialSummary(BaseModel):
    issued: Decimal
    collected: Decimal
    pending: Decimal
    currency: str = "PEN"


class DelinquencyRow(BaseModel):
    unit_id: int
    unit_code: str
    period: str
    issued: Decimal
    paid: Decimal
    overdue: Decimal
