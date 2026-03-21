from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal
from typing import List, Optional, Any
from datetime import datetime


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


# ── Calculation Profile schemas ───────────────────────────────────────────────

class ProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Human-readable label for this calculation")
    description: Optional[str] = Field(None, max_length=1000)
    shipment_data: dict = Field(..., description="Shipment fields: origin, destination, fx_date")
    lines_data: List[dict] = Field(..., min_length=1, description="Line items for the calculation")


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    shipment_data: Optional[dict] = None
    lines_data: Optional[List[dict]] = None
    last_result: Optional[dict] = None


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str
    name: str
    description: Optional[str]
    shipment_data: dict
    lines_data: List[dict]
    last_result: Optional[dict]
    created_at: datetime
    updated_at: datetime


class ProfileListResponse(BaseModel):
    results: List[ProfileResponse]
    total: int
    limit: int
    offset: int
    has_more: bool
