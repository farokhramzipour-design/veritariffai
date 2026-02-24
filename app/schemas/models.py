from pydantic import BaseModel


class DutyRateRequest(BaseModel):
    hs_code: str
    origin_country: str
    destination_country: str


class DutyRateResponse(BaseModel):
    duty_rate: float
    duty_type: str
    source: str
    cached: bool

