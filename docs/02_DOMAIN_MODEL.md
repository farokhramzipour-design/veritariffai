# 02 — Domain Model

## Core Aggregates

### CalculationRequest (Aggregate Root)
The primary input artifact. Represents a user's request to calculate trade costs for a shipment.

**Fields:**
- `id` — UUID
- `user_id` — FK to User
- `plan_snapshot` — plan tier at time of calculation (free | pro)
- `shipment` — Shipment value object
- `lines` — list of ShipmentLine entities
- `requested_engines` — which engines to run (plan-gated)
- `status` — PENDING | PROCESSING | COMPLETE | FAILED
- `created_at`, `updated_at`

**Invariants:**
- Free users may only submit 1 line with restricted engine set
- Pro users may submit up to 500 lines
- All monetary values must carry explicit currency codes

---

### CalculationResult (Aggregate Root)
The complete output artifact. Immutable once written.

**Fields:**
- `id` — UUID
- `request_id` — FK to CalculationRequest
- `user_id`
- `engine_results` — map of engine name → EngineResult
- `line_results` — list of LineResult (one per ShipmentLine)
- `totals` — AggregatedTotals value object
- `audit_trail` — ordered list of AuditStep records
- `confidence_score` — 0.0–1.0 computed from engine coverage + data quality
- `warnings` — list of ComplianceFlag
- `created_at` — immutable

**Business Rules:**
- Once status is COMPLETE, the result is immutable
- Confidence score must be recalculated if input changes
- Audit trail is append-only; never modified

---

### User (Aggregate Root)

**Fields:**
- `id` — UUID
- `google_sub` — Google subject identifier (unique, immutable)
- `email`
- `plan` — FREE | PRO
- `plan_expires_at` — nullable (null = never, for annual plans)
- `stripe_customer_id` — nullable
- `created_at`
- `last_seen_at`

---

### TariffRecord (Aggregate Root)

**Fields:**
- `id` — UUID
- `hs_code` — 10-digit string
- `jurisdiction` — UK | EU
- `measure_type` — AD_VALOREM | SPECIFIC | MIXED | ANTI_DUMPING | COUNTERVAILING | SAFEGUARD | QUOTA
- `rate_ad_valorem` — Decimal nullable
- `rate_specific_amount` — Decimal nullable
- `rate_specific_unit` — string nullable (e.g., "100kg", "unit", "liter")
- `country_of_origin` — nullable (null = applies to all)
- `preferential_agreement` — nullable (e.g., "UK-EU TCA")
- `quota_volume` — nullable
- `quota_in_rate` — nullable
- `quota_out_rate` — nullable
- `valid_from` — date
- `valid_to` — date nullable
- `suspension` — boolean
- `agricultural_component` — Decimal nullable
- `source_dataset` — "TARIC" | "UKGT"
- `ingested_at`

---

## Value Objects

### Money
```
Money:
  amount: Decimal          # Always Decimal, never float
  currency: CurrencyCode   # ISO 4217
```
Operations: add, subtract, multiply by scalar, convert (requires FXRate). Immutable.

### Shipment
```
Shipment:
  incoterm: IncoTerms       # EXW | FCA | FOB | CIF | DAP | DDP | etc.
  origin_country: str       # ISO 3166-1 alpha-2
  destination_country: str  # ISO 3166-1 alpha-2
  port_of_entry: str        # LOCODE
  freight_cost: Money
  insurance_cost: Money
  handling_cost: Money
```

### ShipmentLine
```
ShipmentLine:
  line_number: int
  hs_code: str              # 8–10 digits
  description: str
  invoice_value: Money
  quantity: Decimal
  quantity_unit: str        # kg, units, liters, m2, etc.
  gross_weight_kg: Decimal
  country_of_origin: str
  has_proof_of_origin: bool
  royalties: Money
  assists: Money
  buying_commission: Money
  selling_commission: Money
  is_related_party: bool
```

### AuditStep
```
AuditStep:
  sequence: int
  engine: str
  step_name: str
  input_snapshot: dict      # JSON snapshot of inputs
  output_snapshot: dict     # JSON snapshot of output
  formula_description: str  # Human-readable calculation narrative
  timestamp: datetime
```

### ComplianceFlag
```
ComplianceFlag:
  severity: INFO | WARNING | BLOCK
  code: str                 # e.g., "RESTRICTED_GOODS_CITES"
  description: str
  affected_hs_codes: list[str]
  action_required: str
```

### OriginRule
```
OriginRule:
  hs_code_range_start: str
  hs_code_range_end: str
  agreement: str
  rule_type: CTH | CTSH | RVC | WHOLLY_OBTAINED | SPECIFIC
  rvc_threshold: Decimal    # nullable
  additional_conditions: str
```

---

## Domain Events

These events are emitted by aggregates and consumed by other parts of the system:

| Event | Emitted By | Consumers |
|---|---|---|
| `CalculationCompleted` | CalculationResult | Reporting, Analytics |
| `CalculationFailed` | CalculationRequest | Error tracking, user notification |
| `UserUpgradedToPro` | User | Subscription service, analytics |
| `UserDowngradedToFree` | User | Subscription service |
| `TariffDataRefreshed` | TariffRecord | Cache invalidation |
| `FXRateUpdated` | FXRate | Cache invalidation |

---

## Plan Gate Model

The plan gate is implemented as a pure function at the application boundary:

```
requires_plan(required: PlanTier) → Dependency

PlanTier:
  FREE = "free"
  PRO = "pro"

Gate logic:
  - FREE endpoints: any authenticated user
  - PRO endpoints: user.plan == PRO and (plan_expires_at is null OR plan_expires_at > now())
  - Raises PlanUpgradeRequired(required_plan, upgrade_url) if check fails
```

**Free Tier Engine Restrictions:**
- ClassificationEngine — basic lookup only (no misclassification AI)
- TariffMeasureEngine — ad valorem only, single measure
- VATEngine — standard rate only, no postponed accounting
- FXEngine — market rate only (not official customs rate)

**Engines Locked to Pro:**
- CustomsValuationEngine
- RulesOfOriginEngine
- ExciseEngine
- ClearanceEngine
- LineLevelAggregator (multi-line)
- ComplianceFlagEngine
- Anti-dumping, safeguard, quota measures
- Official HMRC/EU customs FX rates
