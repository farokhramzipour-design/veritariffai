# 06 — Calculation Engines

## Engine Design Principles

1. **Pure functions** — engines take typed inputs, return typed outputs, no side effects
2. **No framework imports** — engines import only from Python stdlib and `decimal`
3. **Audit-by-design** — every step logs a formula description that a customs officer could follow
4. **Fail-explicit** — engines raise typed `EngineError` with structured reason, never silently return zero
5. **Decimal arithmetic only** — never use `float` for monetary values
6. **Composable** — engines can be called standalone or chained by the orchestrator

---

## Base Types

```python
# All engines use these shared base types

@dataclass
class Money:
    amount: Decimal
    currency: str  # ISO 4217

@dataclass
class AuditStep:
    step_name: str
    formula_description: str
    input_snapshot: dict
    output_snapshot: dict

@dataclass
class EngineResult:
    success: bool
    output: dict
    audit_steps: list[AuditStep]
    warnings: list[str]

class EngineError(Exception):
    code: str
    message: str
    recoverable: bool
```

---

## Engine 1: Classification Engine

**Plan:** Free (basic) + Pro (full)

### Responsibility
Validate and enrich HS code data for each shipment line.

### Inputs
- `hs_code: str` — 8–10 digit
- `jurisdiction: str` — UK or EU
- `description: str` — goods description
- `quantity_unit: str`

### Outputs
- `validated_code: str` — canonical 10-digit code
- `description: str` — official tariff description
- `supplementary_unit: str | None` — required unit for this heading
- `supplementary_unit_required: bool`
- `misclassification_risk: str` — LOW | MEDIUM | HIGH (Pro only)
- `alternative_codes: list[str]` — Pro only

### Logic Steps
1. **Normalize** — strip dots, spaces, pad to 10 digits with zeros
2. **Validate** — lookup in `hs_codes` table; fail if not found (`INVALID_HS_CODE`)
3. **Check validity dates** — warn if code expires within 30 days
4. **Detect supplementary unit** — load from `hs_codes.supplementary_unit`
5. **Validate unit match** — if supplementary unit required, check `quantity_unit` matches; warn if mismatch
6. **Risk scoring (Pro)** — rule-based check: does description keyword match the HS heading?

### Free vs Pro
| Feature | Free | Pro |
|---|---|---|
| Code validation | ✅ | ✅ |
| Supplementary unit detection | ✅ | ✅ |
| Description match validation | ❌ | ✅ |
| Misclassification risk score | ❌ | ✅ |
| Alternative code suggestions | ❌ | ✅ |

---

## Engine 2: Customs Valuation Engine

**Plan:** PRO only

### Responsibility
Compute the correct Customs Value per the WTO Customs Valuation Agreement (Transaction Value method as primary).

### Inputs
- `invoice_value: Money`
- `incoterm: str`
- `freight_cost: Money`
- `insurance_cost: Money`
- `handling_cost: Money`
- `packing_costs: Money`
- `royalties: Money`
- `assists: Money`
- `buying_commission: Money`
- `selling_commission: Money`
- `is_related_party: bool`
- `origin_country: str`
- `destination_country: str`

### Outputs
- `customs_value: Money` — in destination currency (GBP for UK, EUR for EU)
- `incoterm_adjustments: list[AdjustmentItem]` — itemized additions to reach CIF

### Logic Steps

#### Step 1: Incoterm Gap Analysis
Different Incoterms result in different cost elements being included in the invoice. The engine must add missing elements to reach CIF (Cost + Insurance + Freight) border value.

| Incoterm | Freight in invoice? | Insurance in invoice? | Adjustment needed |
|---|---|---|---|
| EXW | No | No | Add freight + insurance + handling |
| FCA | No | No | Add freight + insurance |
| FOB | No | No | Add freight + insurance |
| CFR | Yes | No | Add insurance |
| CIF | Yes | Yes | None — already correct |
| DAP | Yes | Yes | Subtract inland portion (estimate) |
| DDP | Yes | Yes | Subtract duty + inland |

#### Step 2: Add Dutiable Additions
```
Customs Value = CIF Border Value
              + packing_costs
              + royalties (if related to the goods and condition of sale)
              + assists (tools, molds, etc. supplied by buyer)
              + selling_commission (NOT buying commission)
```

#### Step 3: Related Party Check
- If `is_related_party = true`, flag for review
- Apply test values check logic (simplified for MVP; flag to manual review)
- Output `related_party_flag: true` and warning in audit

#### Step 4: Currency Conversion
- Convert invoice_value to destination currency using official customs FX rate
- Source: HMRC monthly rate (UK) or ECB rate (EU)
- Log: date of rate, rate applied, source

### Free Tier Equivalent
Free tier skips this engine and uses invoice value directly with market FX rate. This is disclosed to the user via a warning.

---

## Engine 3: Tariff Measure Engine

**Plan:** Free (ad valorem only) + Pro (all measure types)

### Responsibility
Look up applicable tariff measures for a given HS code and compute duty.

### Inputs
- `hs_code: str`
- `jurisdiction: str`
- `country_of_origin: str`
- `customs_value: Money`
- `quantity: Decimal`
- `quantity_unit: str`
- `gross_weight_kg: Decimal`
- `calculation_date: date`
- `preferential_agreement: str | None` — if origin engine confirmed preference
- `quota_status: str | None` — IN_QUOTA | OUT_OF_QUOTA | NOT_APPLICABLE

### Outputs
- `applicable_measures: list[MeasureResult]`
- `duty_amount: Money`
- `measure_conditions: list[str]` — license/cert requirements

### Measure Calculation Logic

#### Ad Valorem (`AD_VALOREM`)
```
duty = customs_value × rate_ad_valorem
```

#### Specific (`SPECIFIC`)
```
duty = quantity_in_unit × rate_specific_amount
# Example: 2,000 kg × £3.50/100kg = £70.00
# Must normalize quantity to the rate unit (e.g., divide kg by 100)
```

#### Mixed/Compound (`MIXED`)
```
duty_ad_valorem = customs_value × rate_ad_valorem
duty_specific = quantity_in_unit × rate_specific_amount
duty = duty_ad_valorem + duty_specific
# Apply minimum/maximum if set
if rate_minimum: duty = max(duty, rate_minimum)
if rate_maximum: duty = min(duty, rate_maximum)
```

#### Anti-Dumping / Countervailing (`ANTI_DUMPING`, `COUNTERVAILING`)
```
# These are ADDITIONAL to the standard import duty
# Must check country_of_origin match on measure
# Must check if specific exporter TARIC code is set (some are exporter-specific)
additional_duty = customs_value × rate_ad_valorem
total_duty = standard_duty + additional_duty
```

#### Safeguard (`SAFEGUARD`)
```
# Similar to anti-dumping but triggered by import volumes
# Check if safeguard is currently active (valid_from/valid_to)
# Apply additional duty on top of standard
```

#### Quota Logic
```
if quota_status == "IN_QUOTA":
    use tariff_measures WHERE measure_type = 'QUOTA_IN'
    (usually preferential or zero rate)
elif quota_status == "OUT_OF_QUOTA":
    use tariff_measures WHERE measure_type = 'QUOTA_OUT'
    (usually the full MFN rate)
else:
    use standard measures (no quota)
```

#### Agricultural Components
```
total_duty = standard_duty + agricultural_component_per_100kg × (gross_weight_kg / 100)
```

### Suspension Logic
If a measure has `suspension = true` and is within its validity period:
- Apply zero duty for that measure
- Log suspension active: code, valid dates

### Free vs Pro Measures
| Measure Type | Free | Pro |
|---|---|---|
| Ad Valorem (standard) | ✅ | ✅ |
| Specific duties | ❌ | ✅ |
| Mixed/compound | ❌ | ✅ |
| Anti-dumping | ❌ | ✅ |
| Countervailing | ❌ | ✅ |
| Safeguard | ❌ | ✅ |
| Quota logic | ❌ | ✅ |
| Agricultural component | ❌ | ✅ |
| Suspension detection | ❌ | ✅ |

---

## Engine 4: Rules of Origin Engine

**Plan:** PRO only

### Responsibility
Determine whether goods qualify for preferential duty treatment under a trade agreement.

### Inputs
- `hs_code: str`
- `country_of_origin: str`
- `destination_country: str`
- `has_proof_of_origin: bool`
- `invoice_value: Money`
- `is_related_party: bool`

### Outputs
- `preference_available: bool`
- `preference_applicable: bool` — preference_available AND proof_of_origin AND rule_met
- `applicable_agreement: str | None`
- `product_specific_rule: str | None` — the PSR text
- `rule_type: str | None` — CTH | CTSH | RVC | WHOLLY_OBTAINED
- `proof_required: str` — 'REX', 'EUR.1', 'ORIGIN_DECLARATION', 'NONE'
- `mfn_fallback: bool` — true if falling back to MFN rate

### Logic Steps

1. **Agreement detection** — lookup active trade agreements for origin↔destination pair
   - Priority: UK-EU TCA, UK-Japan CEPA, UK-AUS FTA, UK-NZ FTA, GSP, etc.
   - Some HS codes may have multiple applicable agreements (pick most favorable)

2. **Product-specific rule retrieval** — query `origin_rules` for the HS code range

3. **Rule validation** — simplified rule checking:
   - **CTH (Change of Tariff Heading)**: verify HS heading (4-digit) of output ≠ inputs. Cannot auto-verify without full BoM; flag for manual confirmation
   - **CTSH (Change of Tariff Sub-Heading)**: similar to CTH at 6-digit level
   - **RVC (Regional Value Content)**: `(invoice_value - non_originating_inputs) / invoice_value ≥ threshold`
   - **WHOLLY_OBTAINED**: no computation, just confirm country claim

4. **Proof of origin check** — if `has_proof_of_origin = false`, preference cannot be applied; flag warning

5. **Decision**:
   - If preference_available AND rule_met AND has_proof_of_origin → `preference_applicable = true`
   - Otherwise → `mfn_fallback = true`

6. **Return preferred rate to TariffMeasureEngine** — pass `preferential_agreement` so engine selects in-preference measure

---

## Engine 5: VAT Engine

**Plan:** Free (standard rate only) + Pro (all)

### Responsibility
Calculate import VAT correctly using the customs VAT base.

### Inputs
- `customs_value: Money`
- `duty_amount: Money`
- `jurisdiction: str`
- `vat_registration_status: str` — REGISTERED | NOT_REGISTERED
- `postponed_accounting_requested: bool` — Pro only
- `goods_category: str` — STANDARD | REDUCED | ZERO | EXEMPT

### Outputs
- `vat_base: Money`
- `vat_rate: Decimal`
- `vat_amount: Money`
- `is_postponed: bool`
- `deductible: bool`

### Logic

#### VAT Base Calculation
```
VAT Base = customs_value
         + import_duty
         + excise_duty (if applicable)
         + any border charges included in customs value computation

# UK: VAT base = CIF customs value + duty + excise
# EU: Same logic, per each member state's implementation
```

#### Standard Rate Application
```
vat_amount = vat_base × vat_rate
# UK standard: 20%
# EU: varies by member state (17%–27%)
```

#### Postponed VAT Accounting (Pro)
- UK: available to VAT-registered importers via PIVA
- `is_postponed = true` → vat_amount is accounted, not physically paid at border
- Flag `deductible = true` for VAT-registered businesses

#### Reduced / Zero / Exempt (Pro)
- Lookup goods_category against HS code VAT schedule
- Apply correct rate (0%, 5%, or 20% for UK)

### Free Tier
- Standard rate only (20% UK, user-specified EU)
- No postponed accounting
- Assumes standard goods category

---

## Engine 6: Excise Engine

**Plan:** PRO only

### Responsibility
Calculate excise duties for regulated product categories.

### Inputs
- `hs_code: str`
- `goods_category: str` — ALCOHOL | TOBACCO | ENERGY | PLASTIC_PACKAGING | OTHER
- `quantity: Decimal`
- `quantity_unit: str`
- `abv: Decimal | None` — alcohol by volume (%)
- `tobacco_type: str | None`
- `destination_country: str`

### Outputs
- `excise_amount: Money`
- `excise_type: str`
- `rate_applied: str`

### Logic by Category

#### Alcohol
```
UK Beer: duty = abv × volume_liters × rate_per_abv_per_liter
UK Wine (still, 11.5-14.5%): flat rate per liter
UK Spirits: rate per liter of pure alcohol
```
Rates sourced from HMRC excise notice tables, updated via data feed.

#### Tobacco
```
Cigarettes: specific duty per 1,000 cigarettes + ad valorem % of retail price
Cigars: duty per kg
Hand-rolling tobacco: duty per kg
```

#### Energy Products (CBAM / Carbon Border Adjustment)
- CBAM applies to: steel, cement, aluminium, fertilisers, electricity, hydrogen
- Calculate embedded carbon tonnes × CBAM rate
- Requires carbon content data from user or default factor

#### Plastic Packaging Tax (UK)
```
if recycled_plastic_content < 30%:
    tax = weight_kg × £200/tonne
```

---

## Engine 7: FX Engine

**Plan:** Free (market rate) + Pro (official customs rate)

### Responsibility
Convert monetary values between currencies using the correct exchange rate.

### Inputs
- `amount: Money`
- `target_currency: str`
- `calculation_date: date`
- `rate_type: str` — OFFICIAL_HMRC | OFFICIAL_ECB | MARKET

### Outputs
- `converted_amount: Money`
- `rate_applied: Decimal`
- `rate_date: date`
- `rate_source: str`

### Logic
- **HMRC Rate** (UK customs): Published monthly by HMRC. Use rate for the month of importation. Source: HMRC online exchange rates table.
- **ECB Rate** (EU customs): Daily reference rate from ECB. Use rate for the date of acceptance of customs declaration.
- **Market Rate** (free tier): Real-time rate from open API (e.g., exchangerate.host or ECB daily). Not accepted by customs authorities but used for indicative calculations.

### Rate Lookup Logic
```
1. Check Redis cache: fx:{base}:{quote}:{type}:{date}
2. If cache miss → query fx_rates table
3. If not found in table for exact date → use nearest prior date (look back up to 7 days)
4. If still not found → raise DataUnavailableError
5. Cache result for 1 hour (official rates don't change mid-day)
```

---

## Engine 8: Clearance & Logistics Engine

**Plan:** PRO only (basic estimate for Free)

### Responsibility
Estimate customs clearance and logistics costs.

### Inputs
- `goods_value: Money`
- `number_of_hs_lines: int`
- `port_of_entry: str`
- `transport_mode: str` — AIR | SEA | ROAD | RAIL
- `include_risk_modeling: bool`

### Outputs
- `broker_fee: Money`
- `declaration_fee: Money`
- `port_handling_fee: Money`
- `inspection_risk_fee: Money` — probability-weighted cost
- `inland_transport_estimate: Money`
- `total_clearance_estimate: Money`

### Logic
All fees are estimates based on standard market rates. These are:
- **Broker fee**: tiered by goods value and line count (configurable rate table)
- **Declaration fee**: flat fee per declaration + fee per additional line
- **Port handling**: variable by port and transport mode
- **Inspection risk**: `P(inspection) × avg_inspection_cost`
  - P(inspection) varies by HS code risk profile, country of origin, transport mode
- **Inland transport**: simple distance-based estimate using port → destination postcode

---

## Engine 9: Line-Level Aggregator

**Plan:** PRO only (Free restricted to 1 line)

### Responsibility
Run all engines per line, then aggregate to shipment totals.

### Inputs
- `lines: list[ShipmentLine]`
- `shipment: Shipment`
- `engine_results_per_line: list[LineEngineResults]`

### Outputs
- `line_results: list[LineResult]`
- `totals: AggregatedTotals`

### Logic
1. Allocate freight/insurance to lines pro-rata by weight or value (configurable)
2. Run all applicable engines per line independently
3. Each line gets its own:
   - Customs value (after freight allocation)
   - Duty (potentially different rates per HS code)
   - VAT base
   - Origin status
   - Compliance flags
4. Aggregate across lines:
   - Sum all duty amounts
   - Sum all VAT amounts
   - Sum all excise amounts
   - Sum clearance (at shipment level, not per line)
   - Compute total landed cost

### Freight Allocation Methods
- **By weight**: `line_freight = total_freight × (line_weight / total_weight)`
- **By value**: `line_freight = total_freight × (line_value / total_value)`
- **Equal split**: `line_freight = total_freight / n_lines`
- Default: by weight. Configurable per request.

---

## Engine 10: Compliance Flag Engine

**Plan:** PRO only

### Responsibility
Check all HS codes and countries against compliance requirements and generate structured warnings.

### Inputs
- `hs_codes: list[str]`
- `country_of_origin: str`
- `destination_country: str`
- `jurisdiction: str`

### Outputs
- `flags: list[ComplianceFlag]`
- `confidence_score_penalty: Decimal` — reduces overall confidence if compliance data is incomplete

### Checks
1. **Restricted goods** — query `restricted_goods` table, match by code prefix
2. **License requirements** — from `tariff_measures.measure_condition`
3. **Certificate requirements** — phytosanitary, veterinary, CE marking, etc.
4. **Sanctions check** — query `sanctions` table for country + HS code scope
5. **CITES** — Convention on International Trade in Endangered Species flag
6. **Dual-use goods** — export control classification flag

### Flag Severity
- `INFO` — informational, no action required at calculation time
- `WARNING` — action likely required before import (user must obtain license/cert)
- `BLOCK` — goods cannot be imported under current conditions; calculation marked as advisory only

---

## Engine Orchestrator

**File:** `app/application/calculations/orchestrator.py`

### Orchestration Order
```
1. ClassificationEngine (per line) — must succeed before others
2. FXEngine — currency conversion needed by others
3. CustomsValuationEngine (per line) — customs value needed by duty engines
4. RulesOfOriginEngine (per line) — determines preference for TariffMeasureEngine
5. TariffMeasureEngine (per line) — duty calculation
6. ExciseEngine (per line, if applicable)
7. VATEngine (per line) — needs customs value + duty
8. ClearanceEngine (at shipment level)
9. ComplianceFlagEngine (per line)
10. LineLevelAggregator — combine all line results
```

### Error Handling Strategy
- If ClassificationEngine fails on any line → abort entire calculation (cannot proceed)
- If CustomsValuationEngine fails → abort (all downstream depends on it)
- If RulesOfOriginEngine fails → fall back to MFN rate, log warning, continue
- If ExciseEngine fails → log warning, set excise = 0 with flag, continue
- If ComplianceFlagEngine fails → log warning, mark compliance flags as unavailable, continue
- All failures reduce the confidence score

### Confidence Score Formula
```
base_score = 1.0
penalties:
  - origin engine fallback to MFN: -0.05
  - compliance engine unavailable: -0.05
  - related party transaction: -0.03
  - proof of origin missing: -0.04
  - supplementary unit mismatch: -0.08
  - data older than 30 days: -0.10
  - any BLOCK flag active: -0.30

confidence_score = max(0.0, base_score + sum(penalties))
```
