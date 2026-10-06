from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ResidentLinkIn(BaseModel):
    resident_id: int
    is_owner: bool = False
    start_date: date
    end_date: date | None = None


class UnitCreate(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    floor: str | None = Field(default=None, max_length=20)
    area_m2: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    participation_coefficient: Decimal = Field(
        default=Decimal("0"), ge=0, max_digits=12, decimal_places=8
    )
    residents: list[ResidentLinkIn] = []


class ResidentLinkOut(BaseModel):
    id: int
    resident_id: int
    resident_name: str
    resident_email: EmailStr
    is_owner: bool
    start_date: date
    end_date: date | None
    is_active: bool


class UnitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    building_id: int
    code: str
    floor: str | None
    area_m2: Decimal
    participation_coefficient: Decimal
    is_active: bool
    residents: list[ResidentLinkOut] = []


class CsvRowError(BaseModel):
    row: int
    message: str


class CsvImportResult(BaseModel):
    created: int
    errors: list[CsvRowError]
