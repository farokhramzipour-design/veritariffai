from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, List, Tuple
from .base import EngineResult, AuditStep, EngineError, Money


@dataclass(frozen=True)
class AdjustmentItem:
    name: str
    amount: Money


def compute_customs_value(
    invoice_value: Money,
    incoterm: str,
    freight_cost: Money,
    insurance_cost: Money,
    handling_cost: Money,
    packing_costs: Money,
    royalties: Money,
    assists: Money,
    buying_commission: Money,
    selling_commission: Money,
    is_related_party: bool,
    origin_country: str,
    destination_country: str,
    *,
    fx_rate: Optional[Decimal] = None,
    fx_source: Optional[str] = None,
) -> EngineResult:
    steps: List[AuditStep] = []
    warnings: List[str] = []

    adjustments: List[AdjustmentItem] = []
    cif_value_amount = invoice_value.amount

    if incoterm in {"EXW", "FCA", "FOB"}:
        cif_value_amount += freight_cost.amount
        adjustments.append(AdjustmentItem("freight_to_border", freight_cost))
        cif_value_amount += insurance_cost.amount
        adjustments.append(AdjustmentItem("insurance_to_border", insurance_cost))
        if incoterm == "EXW":
            cif_value_amount += handling_cost.amount
            adjustments.append(AdjustmentItem("handling_to_border", handling_cost))
    elif incoterm == "CFR":
        cif_value_amount += insurance_cost.amount
        adjustments.append(AdjustmentItem("insurance_to_border", insurance_cost))
    elif incoterm in {"CIF"}:
        pass
    elif incoterm in {"DAP", "DDP"}:
        warnings.append("DAP/DDP provided; inland portion not separated")

    steps.append(
        AuditStep(
            step_name="incoterm_gap",
            formula_description="Adjust to CIF border value based on incoterm",
            input_snapshot={"incoterm": incoterm, "invoice_value": {"amount": str(invoice_value.amount), "currency": invoice_value.currency}},
            output_snapshot={"cif_value": str(cif_value_amount)},
        )
    )

    dutiable_additions = packing_costs.amount + royalties.amount + assists.amount + selling_commission.amount
    customs_value_amount = cif_value_amount + dutiable_additions

    steps.append(
        AuditStep(
            step_name="dutiable_additions",
            formula_description="Add packing + royalties + assists + selling commission",
            input_snapshot={"packing": str(packing_costs.amount), "royalties": str(royalties.amount), "assists": str(assists.amount), "selling_commission": str(selling_commission.amount)},
            output_snapshot={"customs_value_before_fx": str(customs_value_amount)},
        )
    )

    related_party_flag = is_related_party
    if related_party_flag:
        warnings.append("Related party declared")

    dest_currency = "GBP" if destination_country == "GB" else "EUR"
    if invoice_value.currency != dest_currency:
        if fx_rate is None:
            warnings.append("No official FX rate provided; currency left unconverted")
            converted_amount = customs_value_amount
            dest_currency = invoice_value.currency
        else:
            converted_amount = (customs_value_amount * fx_rate).quantize(Decimal("0.01"))
            steps.append(
                AuditStep(
                    step_name="currency_conversion",
                    formula_description="Apply official customs FX rate to convert customs value",
                    input_snapshot={"rate": str(fx_rate), "source": fx_source or ""},
                    output_snapshot={"customs_value_converted": str(converted_amount), "currency": dest_currency},
                )
            )
    else:
        converted_amount = customs_value_amount

    output = {
        "customs_value": {"amount": str(converted_amount), "currency": dest_currency},
        "incoterm_adjustments": [{"name": a.name, "amount": {"amount": str(a.amount.amount), "currency": a.amount.currency}} for a in adjustments],
        "related_party_flag": related_party_flag,
    }

    return EngineResult(success=True, output=output, audit_steps=steps, warnings=warnings)
