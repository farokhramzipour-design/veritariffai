from decimal import Decimal
from uuid import uuid4
from datetime import date
from app.api.v1.calculations.schemas import CalculationRequest, CalculationResponse, CalculationBreakdown
from app.engines.base import Money
from app.engines.classification import classify
from app.engines.customs_valuation import compute_customs_value
from app.engines.tariff_measure import compute_duty, Measure
from app.engines.vat import compute_vat


def calculate_sync(payload: CalculationRequest) -> CalculationResponse:
    duty = Decimal("0.00")
    vat = Decimal("0.00")
    total_value = sum([line.customs_value for line in payload.lines], Decimal("0.00"))
    total = total_value + duty + vat
    breakdown = CalculationBreakdown(duty=duty, vat=vat, total=total)
    return CalculationResponse(breakdown=breakdown, confidence=50, audit_id=str(uuid4()))
