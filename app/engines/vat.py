from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP
from .base import EngineResult, AuditStep, Money


def compute_vat(
    customs_value: Money,
    duty_amount: Money,
    jurisdiction: str,
    vat_registration_status: str,
    postponed_accounting_requested: bool,
    goods_category: str = "STANDARD",
    *,
    standard_rate_uk: Decimal = Decimal("0.20"),
    standard_rate_eu: Decimal = Decimal("0.20"),
) -> EngineResult:
    steps: list[AuditStep] = []
    warnings: list[str] = []

    vat_base_amount = (customs_value.amount + duty_amount.amount).quantize(Decimal("0.01"))
    steps.append(AuditStep("vat_base", "VAT base = customs_value + duty", {"customs_value": str(customs_value.amount), "duty": str(duty_amount.amount)}, {"vat_base": str(vat_base_amount)}))

    if goods_category in {"ZERO", "EXEMPT"}:
        vat_rate = Decimal("0.00")
    elif goods_category == "REDUCED":
        vat_rate = Decimal("0.05")
    else:
        vat_rate = standard_rate_uk if jurisdiction == "UK" else standard_rate_eu

    vat_amount = (vat_base_amount * vat_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    steps.append(AuditStep("apply_rate", "VAT amount = vat_base × vat_rate", {"rate": str(vat_rate)}, {"vat_amount": str(vat_amount)}))

    is_postponed = False
    deductible = False
    if jurisdiction == "UK" and vat_registration_status == "REGISTERED" and postponed_accounting_requested and goods_category == "STANDARD":
        is_postponed = True
        deductible = True

    output = {
        "vat_base": {"amount": str(vat_base_amount), "currency": customs_value.currency},
        "vat_rate": str(vat_rate),
        "vat_amount": {"amount": str(vat_amount), "currency": customs_value.currency},
        "is_postponed": is_postponed,
        "deductible": deductible,
    }
    return EngineResult(success=True, output=output, audit_steps=steps, warnings=warnings)
