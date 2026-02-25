from pydantic import BaseModel, Field
from typing import Optional


class DutyRateRequest(BaseModel):
    hs_code: str
    origin_country: str
    destination_country: str


class DutyRateResponse(BaseModel):
    duty_rate: float
    duty_type: str
    source: str
    cached: bool


class AutofillRequest(BaseModel):
    description: str = Field(..., min_length=3, max_length=500)


class AutofillResponse(BaseModel):
    product_description: Optional[str] = None
    hs_code: Optional[str] = None
    hs_confidence: Optional[int] = None
    hs_description: Optional[str] = None
    origin_country: Optional[str] = None
    destination_country: Optional[str] = None
    declared_value: Optional[float] = None
    currency: Optional[str] = None
    incoterms: Optional[str] = None
    parse_confidence: int
    unparsed_fields: list[str] = []


class HSLookupRequest(BaseModel):
    product_description: str = Field(..., min_length=2, max_length=300)
    origin_country: Optional[str] = None


class HSAlternative(BaseModel):
    hs_code: str
    confidence: int
    description: str


class HSLookupResponse(BaseModel):
    hs_code: str
    confidence: int
    description: str
    chapter: str
    chapter_description: str
    alternatives: list[HSAlternative] = []
    cached: bool = False
    source: str = "openai"
