from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List
from .base import EngineResult, AuditStep, EngineError, Money


@dataclass(frozen=True)
class Measure:
    measure_type: str
    rate_ad_valorem: Optional[Decimal] = None
    rate_specific_amount: Optional[Decimal] = None
    rate_specific_unit: Optional[str] = None
    rate_minimum: Optional[Decimal] = None
    rate_maximum: Optional[Decimal] = None
    agricultural_component: Optional[Decimal] = None
    suspension: bool = False
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None


def compute_duty(
    hs_code: str,
    jurisdiction: str,
    country_of_origin: str,
    customs_value: Money,
    quantity: Decimal,
    quantity_unit: str,
    gross_weight_kg: Decimal,
    calculation_date: date,
    preferential_agreement: Optional[str] = None,
    quota_status: Optional[str] = None,
    measures: Optional[List[Measure]] = None,
    *,
    free_tier: bool = False,
) -> EngineResult:
    steps: List[AuditStep] = []
    warnings: List[str] = []

    if measures is None or len(measures) == 0:
        steps.append(AuditStep("no_measures", "No tariff measures provided", {}, {}))
        return EngineResult(success=True, output={"applicable_measures": [], "duty_amount": {"amount": "0.00", "currency": customs_value.currency}, "measure_conditions": []}, audit_steps=steps, warnings=warnings)

    applicable: List[dict] = []
    duty_total = Decimal("0.00")
    for m in measures:
        if m.valid_from and calculation_date < m.valid_from:
            continue
        if m.valid_to and calculation_date > m.valid_to:
            continue
        if m.suspension:
            applicable.append({"measure_type": m.measure_type, "duty": "0.00", "suspension": True})
            steps.append(AuditStep("suspension", "Suspension active, duty set to zero", {"measure_type": m.measure_type}, {"duty": "0.00"}))
            continue
        if free_tier and m.measure_type != "AD_VALOREM":
            continue
        duty_component = Decimal("0.00")
        if m.measure_type == "AD_VALOREM" and m.rate_ad_valorem is not None:
            duty_component = (customs_value.amount * m.rate_ad_valorem).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            steps.append(AuditStep("ad_valorem", "Duty = customs_value × rate", {"rate": str(m.rate_ad_valorem), "customs_value": str(customs_value.amount)}, {"duty": str(duty_component)}))
        elif not free_tier and m.measure_type == "SPECIFIC" and m.rate_specific_amount is not None:
            basis = quantity
            duty_component = (basis * m.rate_specific_amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            steps.append(AuditStep("specific", "Duty = quantity × rate_specific_amount", {"rate": str(m.rate_specific_amount), "quantity": str(basis)}, {"duty": str(duty_component)}))
        elif not free_tier and m.measure_type == "MIXED":
            ad = (customs_value.amount * (m.rate_ad_valorem or Decimal("0"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            sp = (quantity * (m.rate_specific_amount or Decimal("0"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            duty_component = ad + sp
            if m.rate_minimum is not None:
                duty_component = max(duty_component, m.rate_minimum)
            if m.rate_maximum is not None:
                duty_component = min(duty_component, m.rate_maximum)
            steps.append(AuditStep("mixed", "Duty = ad_valorem + specific with min/max", {"ad": str(ad), "sp": str(sp)}, {"duty": str(duty_component)}))
        elif not free_tier and m.measure_type in {"ANTI_DUMPING", "COUNTERVAILING"} and m.rate_ad_valorem is not None:
            addl = (customs_value.amount * m.rate_ad_valorem).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            duty_component = addl
            steps.append(AuditStep("trade_defense", "Additional duty = customs_value × rate", {"rate": str(m.rate_ad_valorem)}, {"duty": str(duty_component)}))
        elif not free_tier and m.measure_type == "SAFEGUARD" and m.rate_ad_valorem is not None:
            addl = (customs_value.amount * m.rate_ad_valorem).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            duty_component = addl
            steps.append(AuditStep("safeguard", "Additional safeguard duty", {"rate": str(m.rate_ad_valorem)}, {"duty": str(duty_component)}))
        else:
            continue
        duty_total += duty_component
        applicable.append({"measure_type": m.measure_type, "duty": str(duty_component)})

    if not free_tier:
        agri = [m for m in measures if m.agricultural_component]
        if agri:
            ac = sum([(m.agricultural_component or Decimal("0")) for m in agri], Decimal("0"))
            addl = (ac * (gross_weight_kg / Decimal("100"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            duty_total += addl
            steps.append(AuditStep("agricultural_component", "Add agricultural component per 100kg", {"component": str(ac), "gross_weight_kg": str(gross_weight_kg)}, {"duty_addition": str(addl)}))

    output = {"applicable_measures": applicable, "duty_amount": {"amount": str(duty_total), "currency": customs_value.currency}, "measure_conditions": []}
    return EngineResult(success=True, output=output, audit_steps=steps, warnings=warnings)
