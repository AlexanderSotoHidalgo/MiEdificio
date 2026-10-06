from pydantic import BaseModel, ConfigDict, Field


class BuildingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    legal_name: str | None
    tax_id: str | None
    address: str
    district: str
    province: str
    department: str
    currency: str
    timezone: str
    is_active: bool


class BuildingUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    legal_name: str | None = Field(default=None, max_length=200)
    tax_id: str | None = Field(default=None, pattern=r"^\d{11}$")
    address: str | None = Field(default=None, min_length=3, max_length=300)
    district: str | None = Field(default=None, min_length=2, max_length=100)
