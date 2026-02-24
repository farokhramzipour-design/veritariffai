# 12 — Testing Strategy

## Overview

The testing strategy is designed specifically around the calculation accuracy targets (90%+ confidence). Traditional application testing is necessary but not sufficient — we need a dedicated **accuracy test suite** that validates against known-correct customs calculations.

---

## Test Pyramid

```
           ┌─────────────┐
           │   E2E Tests  │  ~20 tests — full API round-trips
           ├─────────────┤
           │ Integration  │  ~200 tests — DB + cache + external mocks
           │    Tests     │
           ├─────────────┤
           │  Unit Tests  │  ~800 tests — pure engine logic
           ├─────────────┤
           │  Accuracy    │  ~500 tests — real-world calculation scenarios
           │   Tests      │
           └─────────────┘
```

---

## Unit Tests

**Target coverage:** 90%+ for `engines/` and `domain/` directories

### What to unit test
- All 10 calculation engines in isolation
- Every branch of duty calculation logic (ad valorem, specific, mixed, anti-dumping, etc.)
- Incoterm gap logic for all 11 main Incoterms
- Customs value additions (assists, royalties, commissions)
- VAT base construction
- Origin rule validation logic
- Money arithmetic (Decimal precision, currency mismatch rejection)
- Confidence score calculation
- AuditStep generation (verify formula descriptions are populated)

### Engine Test Pattern
```python
# tests/unit/engines/test_tariff_measure.py

class TestMixedDutyCalculation:
    def test_mixed_duty_within_min_max(self):
        result = TariffMeasureEngine.calculate(
            hs_code="2204210100",
            customs_value=Money(Decimal("10000"), "GBP"),
            quantity=Decimal("500"),
            quantity_unit="liter",
            measure=TariffMeasure(
                rate_ad_valorem=Decimal("0.032"),   # 3.2%
                rate_specific_amount=Decimal("3.50"),
                rate_specific_unit="liter",
                rate_minimum=Decimal("50"),
                rate_maximum=Decimal("800"),
            )
        )
        # duty = (10000 × 0.032) + (500 × 3.50) = 320 + 1750 = 2070
        # max = 800, so capped at 800
        assert result.duty_amount == Money(Decimal("800"), "GBP")
        assert "capped at maximum" in result.audit_steps[-1].formula_description
```

### Key Edge Cases to Test
- Zero duty rate (suspension active)
- Anti-dumping ON TOP of standard duty
- Quota in-rate vs out-of-quota rate switching
- Related party transaction flag
- Mixed origin shipment (line 1 CN, line 2 US — different anti-dumping)
- Agricultural component on top of ad valorem
- Incoterm: DDP (subtract duty from invoice value)
- Currency conversion with official vs market rate producing different results
- Proof of origin missing → MFN fallback from TCA preference
- CBAM calculation with carbon factor

---

## Integration Tests

**Scope:** Database operations, Redis cache, external API mocks, Celery task dispatch

### Key Integration Tests
- User upsert on Google OAuth (new user vs returning user)
- Plan gate enforcement at API level (test all plan-gated endpoints return 403 for free users)
- Calculation request → Celery task → CalculationResult written to DB
- Tariff data ingestion: mock TARIC API response → verify DB upsert + cache invalidation
- FX rate lookup: Redis miss → DB query → Redis cache write
- Stripe webhook: test all 5 critical event types (checkout, renewal, cancellation, etc.)
- Rate limiting: 11th request within 1 hour window returns 429

### Test Database
- Pytest fixture spins up PostgreSQL in Docker (testcontainers-python)
- Each test function gets a fresh transaction, rolled back after test
- Seed data for tariff records, FX rates, HS codes provided as fixtures

### External API Mocking
- `respx` library for mocking httpx calls (TARIC, UKGT, Firebase, ECB)
- All external HTTP calls go through httpx (not requests) — mockable
- Firebase token verification: mock `verify_id_token()` to return test user dict

---

## Accuracy Tests

This is the most important test suite for a $50M customs calculation product.

**Purpose:** Validate that the system produces results within acceptable tolerance of known-correct customs calculations.

**Source of truth:** Real import declarations, broker-verified calculations, HMRC test cases.

### Accuracy Test Dataset
Maintain a dataset of ~500 manually verified calculation scenarios:

```
tests/accuracy/
  fixtures/
    simple_electronics_uk.json     — single HS, standard duty
    uk_eu_tca_wine_preference.json — preferential origin, wine
    antidumping_solar_panels.json  — anti-dumping from CN
    multi_line_mixed_origin.json   — 10 lines, 3 countries
    agricultural_cheese.json       — agricultural component
    excise_spirits_uk.json         — excise + VAT on spirits
    cbam_steel_eu.json             — Carbon Border Adjustment
    quota_in_range_uk.json         — in-quota preferential rate
    related_party_transaction.json — valuation adjustment
    ... (500 total)
```

### Each Fixture Contains
```json
{
  "scenario_id": "uk_eu_tca_wine_preference_001",
  "description": "Still wine from France under UK-EU TCA preferential rate",
  "input": {
    "shipment": { ... },
    "lines": [ ... ]
  },
  "expected": {
    "customs_value_gbp": "8250.00",
    "duty_gbp": "0.00",
    "vat_gbp": "1650.00",
    "total_landed_cost_gbp": "10000.00",
    "confidence_score_min": 0.88
  },
  "tolerance_pct": 0.5,
  "verified_by": "Jane Smith, Licensed Customs Broker",
  "verified_date": "2026-01-15",
  "notes": "TCA preference applied, REX origin declaration assumed"
}
```

### Accuracy Test Runner
```python
# tests/accuracy/test_accuracy.py

@pytest.mark.parametrize("fixture", load_accuracy_fixtures())
def test_calculation_accuracy(fixture):
    result = CalculationOrchestrator.run(fixture["input"])
    
    assert result.status == "complete"
    
    for field, expected in fixture["expected"].items():
        actual = getattr(result.totals, field)
        tolerance = fixture.get("tolerance_pct", 1.0) / 100
        
        assert is_within_tolerance(actual, expected, tolerance), \
            f"{field}: expected {expected}, got {actual} (tolerance {tolerance*100}%)"
    
    assert result.confidence_score >= fixture["expected"]["confidence_score_min"]
```

### Accuracy Reporting
CI pipeline generates an accuracy report on every run:

```
Accuracy Test Report
====================
Total scenarios: 500
Passed: 487 (97.4%)
Failed: 13 (2.6%)

By category:
  Simple (1 line, ad valorem): 100/100 ✅
  Standard commercial: 180/185 (97.3%)
  Complex regulated: 207/215 (96.3%)

Confidence score distribution:
  P50: 0.91
  P90: 0.87
  P10: 0.96

Failed scenarios:
  - cbam_steel_complex_alloy_003: duty off by 2.3% (tolerance 1%)
  - antidumping_solar_tiered_rate_007: wrong exporter-specific code applied
  ... (11 more)
```

---

## E2E Tests

**Scope:** Full HTTP API round-trips against a running test server with seeded test DB.

Key scenarios:
1. New user Google login → JWT issued → calculation submitted → result retrieved
2. Free user attempts Pro endpoint → 403 returned
3. User upgrades via Stripe webhook → plan changes → Pro endpoint now succeeds
4. Multi-line async calculation → poll until complete → retrieve result → audit trail
5. Tariff lookup → search and retrieve HS code details
6. Rate limit enforcement: submit 11 calculations rapidly → 10 succeed, 1 returns 429

---

## CI Test Execution

```yaml
# .github/workflows/test.yml

stages:
  lint:
    - ruff check .
    - mypy app/
    - bandit -r app/ (security linting)
  
  unit:
    - pytest tests/unit/ -x --cov=app/engines --cov=app/domain
    - coverage threshold: 90%
    
  integration:
    - docker-compose up -d postgres redis
    - pytest tests/integration/ --timeout=60
    
  accuracy:
    - pytest tests/accuracy/ --timeout=120
    - python scripts/generate_accuracy_report.py
    - fail if accuracy < 90% on any category
    
  e2e:
    - run only on main branch and release branches
    - pytest tests/e2e/ against staging environment
```
