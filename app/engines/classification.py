from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Callable, Optional
from .base import EngineResult, AuditStep, EngineError


@dataclass(frozen=True)
class HSInfo:
    code: str
    description: str
    supplementary_unit: Optional[str]
    valid_from: date
    valid_to: Optional[date]


def _normalize_code(code: str) -> str:
    digits = "".join(ch for ch in code if ch.isdigit())
    if len(digits) > 10:
        digits = digits[:10]
    return digits.ljust(10, "0")


def classify(
    hs_code: str,
    jurisdiction: str,
    description: str,
    quantity_unit: str,
    *,
    pro: bool = False,
    hs_lookup: Optional[Callable[[str, str], Optional[HSInfo]]] = None,
) -> EngineResult:
    steps: list[AuditStep] = []
    warnings: list[str] = []

    normalized = _normalize_code(hs_code)
    steps.append(
        AuditStep(
            step_name="normalize",
            formula_description="Strip non-digits, pad to 10 digits",
            input_snapshot={"hs_code": hs_code},
            output_snapshot={"normalized": normalized},
        )
    )

    info: Optional[HSInfo] = None
    if hs_lookup is not None:
        info = hs_lookup(normalized, jurisdiction)
        if info is None:
            raise EngineError("INVALID_HS_CODE", "HS code not found")
        today = date.today()
        if info.valid_to is not None and (info.valid_to - today).days <= 30:
            warnings.append("HS code expires within 30 days")
    else:
        warnings.append("HS dataset unavailable; validation skipped")
        info = HSInfo(code=normalized, description=description, supplementary_unit=None, valid_from=date.today(), valid_to=None)

    supp_unit_required = info.supplementary_unit is not None
    if supp_unit_required and quantity_unit != info.supplementary_unit:
        warnings.append("Quantity unit does not match required supplementary unit")

    output = {
        "validated_code": info.code,
        "description": info.description,
        "supplementary_unit": info.supplementary_unit,
        "supplementary_unit_required": supp_unit_required,
    }

    if pro:
        misclassification_risk = "LOW"
        output["misclassification_risk"] = misclassification_risk
        output["alternative_codes"] = []

    return EngineResult(success=True, output=output, audit_steps=steps, warnings=warnings)
