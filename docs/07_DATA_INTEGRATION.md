# 07 — Data Integration

## Overview

Tariff calculation accuracy is entirely dependent on data currency. Stale tariff data is treated as a system failure, not a data issue.

**Three critical data feeds:**
1. TARIC (EU tariff database)
2. UKGT (UK Global Tariff)
3. Official FX Rates (HMRC monthly + ECB daily)

---

## TARIC Integration (EU)

### Source
- **API:** European Commission's TARIC API
  - Base URL: `https://trade.ec.europa.eu/taxation_customs/dds2/taric/`
  - Also: EU Customs API (newer): `https://customs.ec.europa.eu/`
- **Format:** XML (primary) or JSON (newer endpoints)
- **Update frequency:** Daily (changes published each working day)
- **Full dataset:** ~40,000 measure records

### Data We Ingest
- HS code nomenclature (CN 8-digit + TARIC 10-digit)
- All tariff measures (ad valorem, specific, mixed)
- Anti-dumping measures (Regulation numbers, company-specific codes)
- Tariff quotas (order numbers, volumes, status)
- Suspensions
- Origin rules per agreement
- Measure conditions (licenses, certs)

### Ingestion Strategy
```
1. Daily delta ingestion (changes only, via TARIC changes endpoint)
2. Weekly full reconciliation (full snapshot, verify no drift)
3. On-demand manual trigger via admin endpoint

Delta ingestion flow:
  → Celery scheduled task: runs at 06:00 UTC daily
  → Fetch changes since last_ingested_at
  → Parse XML/JSON → validate records
  → Upsert into tariff_measures (by source_measure_id)
  → Update ingestion_runs record
  → Invalidate relevant Redis cache keys
  → Emit TariffDataRefreshed domain event
  → Alert if changes > 500 measures (potential full refresh needed)
```

### Error Handling
- Retry 3× with exponential backoff (15min, 30min, 60min)
- After 3 failures: send alert to ops team, mark tariff data as potentially stale
- If data is > 48 hours old: add `DATA_STALE` warning to all calculation responses
- If data is > 7 days old: reject calculations and return 503

---

## UKGT Integration (UK)

### Source
- **Primary:** HMRC Trade Tariff API
  - Base URL: `https://www.trade-tariff.service.gov.uk/api/v2/`
  - Publicly documented RESTful API
  - No API key required for reasonable usage
- **Secondary:** UK Trade Info bulk downloads as fallback
- **Update frequency:** Daily

### Endpoints Used
```
GET /api/v2/commodities/{commodity_code}
GET /api/v2/chapters
GET /api/v2/sections
GET /api/v2/quota_definitions
GET /api/v2/measures?goods_nomenclature_item_id={code}
```

### Data We Ingest
- Commodity codes (8 and 10 digit)
- Import measures (duties, anti-dumping, safeguards)
- Quota definitions and order numbers
- Geographical areas (country groups for measures)
- Trade agreements applicable to UK

### Ingestion Strategy
```
1. Daily incremental: poll /updates endpoint or compare ETags
2. Full refresh: weekly, Sunday 02:00 UTC
3. Rate limiting: max 5 req/sec to respect HMRC API

Parse → Validate → Transform to internal schema → Upsert → Cache invalidate
```

---

## FX Rate Integration

### HMRC Monthly Rates (UK Customs)

**Source:** `https://www.gov.uk/government/collections/exchange-rates-for-customs-and-vat`
Published: First working day of each month
Format: PDF and HTML table (requires parsing)

**Ingestion:**
```
1. Celery task: runs on 1st of each month at 09:00 UTC
2. Fetch HMRC exchange rates page
3. Parse HTML table (BeautifulSoup)
4. Upsert into fx_rates with rate_type='OFFICIAL_HMRC', effective_date=first_day_of_month
5. Cache in Redis with long TTL (28 days)
```

### ECB Daily Rates (EU Customs)

**Source:** `https://data-api.ecb.europa.eu/service/data/EXR/`
Published: Daily at ~16:00 CET
Format: XML (SDMX)

**Ingestion:**
```
1. Celery task: runs daily at 17:00 CET
2. Fetch ECB daily reference rates
3. Parse SDMX XML
4. Upsert into fx_rates with rate_type='OFFICIAL_ECB', effective_date=today
5. Cache in Redis with TTL until next day's publication
```

### Market Rates (Free Tier)

**Source:** Free/open FX API (e.g., open.er-api.com, or exchangerate.host)
**Ingestion:** On-demand at calculation time, cached in Redis for 15 minutes
**Usage:** Free tier only — not accepted by customs authorities

---

## Redis Caching Strategy

| Cache Key Pattern | Content | TTL | Invalidated By |
|---|---|---|---|
| `tariff:measure:{hs_code}:{jurisdiction}:{country}:{date}` | TariffMeasure list | 1 hour | TariffDataRefreshed event |
| `hs:code:{code}:{jurisdiction}` | HSCode details | 24 hours | Weekly full refresh |
| `fx:{base}:{quote}:{type}:{date}` | FX rate | 1 hour (official), 15min (market) | FXRateUpdated event |
| `quota:{order_number}` | Quota status | 30 min | Quota update |
| `user:{user_id}` | User profile (plan etc.) | 5 min | User update |
| `blocklist:{user_id}` | Token blocklist flag | 1 hour | TTL only |

---

## Data Quality Validation

All ingested records pass through validation before upsert:

### HS Code Validation
- Must be 8 or 10 digits
- Must have a valid parent at 6-digit level
- Description must be non-empty

### Tariff Measure Validation
- At least one of rate_ad_valorem or rate_specific_amount must be non-null (unless suspension)
- valid_from must precede valid_to
- source_measure_id must be unique per source_dataset

### FX Rate Validation
- Rate must be positive and non-zero
- Currency codes must be valid ISO 4217
- Effective date must not be in the future

### Validation Failures
- Individual record failures: log, skip, increment failed_count in ingestion_run
- If failed_count > 5% of total: abort ingestion run, alert ops, do not update tariff data
- All validation failures written to structured log with record details

---

## Admin Endpoints (Internal)

These endpoints require a separate admin JWT (not issued to regular users):

```
POST /internal/ingestion/taric/trigger     — Manual TARIC ingestion
POST /internal/ingestion/ukgt/trigger      — Manual UKGT ingestion  
POST /internal/ingestion/fx/trigger        — Manual FX refresh
GET  /internal/ingestion/status            — All ingestion run statuses
POST /internal/cache/invalidate            — Force cache invalidation
GET  /internal/data-quality/report         — Data quality metrics
```
