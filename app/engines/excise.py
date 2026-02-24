from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP
from .base import EngineResult, AuditStep, Money


def compute_excise(
    hs_code: str,
    goods_category: str,
    quantity: Decimal,
    quantity_unit: str,
    abv: Decimal | None,
    tobacco_type: str | None,
    destination_country: str,
    currency: str = "GBP",
) -> EngineResult:
    steps: list[AuditStep] = []
    warnings: list[str] = []

    excise_amount = Decimal("0.00")
    excise_type = "NONE"
    rate_applied = "N/A"

    if goods_category == "ALCOHOL" and abv is not None and quantity_unit in {"liters", "l"}:
        rate = Decimal("0.19")
        excise_amount = (abv * quantity * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        excise_type = "ALCOHOL"
        rate_applied = "per_abv_per_liter"
        steps.append(AuditStep("alcohol_excise", "abv × liters × rate", {"abv": str(abv), "liters": str(quantity), "rate": str(rate)}, {"excise": str(excise_amount)}))

    output = {
        "excise_amount": {"amount": str(excise_amount), "currency": currency},
        "excise_type": excise_type,
        "rate_applied": rate_applied,
    }
    return EngineResult(success=True, output=output, audit_steps=steps, warnings=warnings)
