from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from app.domain.shared.money import Money


class IncoTerms(str, Enum):
    EXW = "EXW"
    FCA = "FCA"
    FOB = "FOB"
    CIF = "CIF"
    DAP = "DAP"
    DDP = "DDP"


class Severity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    BLOCK = "BLOCK"


class OriginRuleType(str, Enum):
    CTH = "CTH"
    CTSH = "CTSH"
    RVC = "RVC"
    WHOLLY_OBTAINED = "WHOLLY_OBTAINED"
    SPECIFIC = "SPECIFIC"


@dataclass(frozen=True)
class Shipment:
    incoterm: IncoTerms
    origin_country: str
    destination_country: str
    port_of_entry: str
    freight_cost: Money
    insurance_cost: Money
    handling_cost: Money


@dataclass(frozen=True)
class ShipmentLine:
    line_number: int
    hs_code: str
    description: str
    invoice_value: Money
    quantity: Decimal
    quantity_unit: str
    gross_weight_kg: Decimal
    country_of_origin: str
    has_proof_of_origin: bool
    royalties: Money
    assists: Money
    buying_commission: Money
    selling_commission: Money
    is_related_party: bool


@dataclass(frozen=True)
class AuditStep:
    sequence: int
    engine: str
    step_name: str
    input_snapshot: dict
    output_snapshot: dict
    formula_description: str
    timestamp: datetime


@dataclass(frozen=True)
class ComplianceFlag:
    severity: Severity
    code: str
    description: str
    affected_hs_codes: List[str]
    action_required: str


@dataclass(frozen=True)
class OriginRule:
    hs_code_range_start: str
    hs_code_range_end: str
    agreement: str
    rule_type: OriginRuleType
    rvc_threshold: Optional[Decimal]
    additional_conditions: str


@dataclass(frozen=True)
class AggregatedTotals:
    duty: Money
    vat: Money
    total: Money


@dataclass(frozen=True)
class LineResult:
    line_number: int
    duty: Money
    vat: Money
    total: Money
