from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal
from typing import List


class Line(BaseModel):
    hs_code: str
    description: str | None = None
    customs_value: Decimal = Field(default=Decimal("0"))
    quantity: Decimal = Field(default=Decimal("1"))
    currency: str = "USD"


class CalculationRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    destination: str
    origin: str
    lines: List[Line]
    fx_date: str | None = None


class CalculationBreakdown(BaseModel):
    duty: Decimal
    vat: Decimal
    total: Decimal


class CalculationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    breakdown: CalculationBreakdown
    confidence: int = 0
    audit_id: str | None = None
