from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from app.domain.plan import PlanTier
from app.domain.value_objects import (
    Shipment,
    ShipmentLine,
    AggregatedTotals,
    LineResult,
    AuditStep,
    ComplianceFlag,
)


class CalculationStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


@dataclass
class CalculationRequest:
    id: UUID
    user_id: UUID
    plan_snapshot: PlanTier
    shipment: Shipment
    lines: List[ShipmentLine]
    requested_engines: List[str]
    status: CalculationStatus = CalculationStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def validate(self) -> None:
        if self.plan_snapshot == PlanTier.FREE:
            if len(self.lines) > 1:
                raise ValueError("free plan allows only 1 line")
        else:
            if len(self.lines) > 500:
                raise ValueError("pro plan supports a maximum of 500 lines")
        for line in self.lines:
            if not line.invoice_value.currency:
                raise ValueError("monetary values must include currency")

    @staticmethod
    def new(
        user_id: UUID,
        plan_snapshot: PlanTier,
        shipment: Shipment,
        lines: List[ShipmentLine],
        requested_engines: List[str],
    ) -> "CalculationRequest":
        cr = CalculationRequest(
            id=uuid4(),
            user_id=user_id,
            plan_snapshot=plan_snapshot,
            shipment=shipment,
            lines=lines,
            requested_engines=requested_engines,
        )
        cr.validate()
        return cr


@dataclass(frozen=True)
class CalculationResult:
    id: UUID
    request_id: UUID
    user_id: UUID
    engine_results: Dict[str, dict]
    line_results: List[LineResult]
    totals: AggregatedTotals
    audit_trail: List[AuditStep]
    confidence_score: float
    warnings: List[ComplianceFlag]
    created_at: datetime


@dataclass
class User:
    id: UUID
    google_sub: str
    email: str
    plan: PlanTier
    plan_expires_at: Optional[datetime]
    stripe_customer_id: Optional[str]
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_seen_at: Optional[datetime] = None


class MeasureType(str, Enum):
    AD_VALOREM = "AD_VALOREM"
    SPECIFIC = "SPECIFIC"
    MIXED = "MIXED"
    ANTI_DUMPING = "ANTI_DUMPING"
    COUNTERVAILING = "COUNTERVAILING"
    SAFEGUARD = "SAFEGUARD"
    QUOTA = "QUOTA"


class Jurisdiction(str, Enum):
    UK = "UK"
    EU = "EU"


@dataclass
class TariffRecord:
    id: UUID
    hs_code: str
    jurisdiction: Jurisdiction
    measure_type: MeasureType
    rate_ad_valorem: Optional[Decimal]
    rate_specific_amount: Optional[Decimal]
    rate_specific_unit: Optional[str]
    country_of_origin: Optional[str]
    preferential_agreement: Optional[str]
    quota_volume: Optional[Decimal]
    quota_in_rate: Optional[Decimal]
    quota_out_rate: Optional[Decimal]
    valid_from: datetime
    valid_to: Optional[datetime]
    suspension: bool
    agricultural_component: Optional[Decimal]
    source_dataset: str
    ingested_at: datetime
