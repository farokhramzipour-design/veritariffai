# VeriTariff — AI Agent Prompt
## Feature: Tariff & VAT Data Pipeline (EU + UK)

---

## YOUR ROLE

You are a senior Python backend engineer implementing a tariff data pipeline for **VeriTariff**, a web application that allows users to look up import duty rates and VAT by HS code, origin country, and destination country.

Your task is to build a **production-ready data pipeline in Python / FastAPI** that fetches, normalises, stores, and refreshes tariff and VAT data from free official sources for the **EU and UK markets**.

---

## DATA SOURCES TO INTEGRATE

### 1. UK Trade Tariff API (free, no auth required)
- **Commodity detail**: `GET https://www.trade-tariff.service.gov.uk/api/v2/commodities/{hs_code}`
- **Sections list**: `GET https://www.trade-tariff.service.gov.uk/api/v2/sections`
- Returns: duty rates, VAT rates, trade agreement preferences, quotas, all in JSON.
- Update frequency: pull daily.

### 2. EU TARIC Data (free XML bulk download)
- **Daily delta XML**: `https://ec.europa.eu/taxation_customs/dds2/taric/xml/taric_download.jsp`
- Alternatively use the TARIC consultation API endpoint:
  `GET https://ec.europa.eu/taxation_customs/dds2/taric/taric_consultation.jsp?Lang=en&Taric={hs_code}&LangDescr=EN`
- Returns: MFN duty rates, preferential rates, trade defence measures, suspensions.
- Update frequency: pull daily (EC publishes daily deltas).
- Note: TARIC does NOT include VAT rates — store VAT separately (see below).

### 3. EU VAT Rates (euvatrates.com — open source JSON)
- **Endpoint**: `GET https://euvatrates.com/rates.json`
- Returns: standard_rate, reduced_rate, reduced_rate_alt, super_reduced_rate, parking_rate per EU country.
- Update frequency: pull weekly (rates change rarely).

### 4. EU VAT — TEDB (Tax and Duties Database, official EC source)
- Use as a validation/backup source for EU VAT rates.
- URL: `https://taxsud.ec.europa.eu/tedb/`

---

## DATABASE SCHEMA

Design and create the following PostgreSQL tables using SQLAlchemy (async) with Alembic migrations:

```sql
-- Commodity codes master table
CREATE TABLE commodity_codes (
    id SERIAL PRIMARY KEY,
    hs_code VARCHAR(12) NOT NULL,           -- 6-10 digit code
    market VARCHAR(2) NOT NULL,             -- 'EU' or 'GB'
    description TEXT,
    parent_code VARCHAR(12),
    last_updated TIMESTAMP DEFAULT NOW()
);

-- Duty rates per HS code + origin country
CREATE TABLE duty_rates (
    id SERIAL PRIMARY KEY,
    hs_code VARCHAR(12) NOT NULL,
    market VARCHAR(2) NOT NULL,             -- destination market: 'EU' or 'GB'
    origin_country VARCHAR(2),              -- ISO2, NULL = applies to all (MFN)
    rate_type VARCHAR(30),                  -- 'MFN', 'preferential', 'anti-dumping', 'suspension'
    duty_rate NUMERIC(8,4),                 -- percentage, e.g. 12.5000
    duty_amount NUMERIC(12,4),              -- for specific (non-%) duties
    currency VARCHAR(3),                    -- for specific duties, e.g. 'EUR'
    trade_agreement VARCHAR(100),           -- e.g. 'EU-UK TCA', 'GSP'
    valid_from DATE,
    valid_to DATE,
    source VARCHAR(20),                     -- 'TARIC', 'UK_TARIFF'
    raw_json JSONB,                         -- store full source response
    last_updated TIMESTAMP DEFAULT NOW()
);

-- VAT rates per country (and optionally per HS category)
CREATE TABLE vat_rates (
    id SERIAL PRIMARY KEY,
    country_code VARCHAR(2) NOT NULL,       -- ISO2
    market VARCHAR(2) NOT NULL,             -- 'EU' or 'GB'
    rate_type VARCHAR(20) NOT NULL,         -- 'standard', 'reduced', 'reduced_alt', 'super_reduced', 'parking'
    vat_rate NUMERIC(6,3) NOT NULL,         -- percentage, e.g. 20.000
    hs_code_prefix VARCHAR(6),              -- NULL = applies to all goods; set for category-specific rates
    valid_from DATE,
    source VARCHAR(30),
    last_updated TIMESTAMP DEFAULT NOW()
);

-- Pipeline run log
CREATE TABLE pipeline_runs (
    id SERIAL PRIMARY KEY,
    source VARCHAR(30) NOT NULL,
    status VARCHAR(10) NOT NULL,            -- 'success', 'failed', 'partial'
    records_fetched INTEGER,
    records_upserted INTEGER,
    error_message TEXT,
    started_at TIMESTAMP,
    finished_at TIMESTAMP
);
```

---

## PIPELINE MODULES TO BUILD

Build each as a separate Python module under `app/pipeline/`:

### `app/pipeline/uk_tariff.py`
- Fetch commodity data from the UK Trade Tariff API.
- For bulk ingest: iterate through all sections → chapters → commodities.
- For targeted fetch: accept an hs_code param and fetch that commodity.
- Parse and upsert into `duty_rates` and `vat_rates` tables.
- Handle pagination and rate limiting (add 200ms delay between requests).
- Log each run to `pipeline_runs`.

### `app/pipeline/eu_taric.py`
- Download and parse the daily TARIC XML delta file.
- Extract MFN rates, preferential rates, anti-dumping duties, suspensions.
- Upsert into `duty_rates` table with `source='TARIC'`.
- Handle XML namespaces and nested measure structures correctly.
- Log each run to `pipeline_runs`.

### `app/pipeline/eu_vat.py`
- Fetch `https://euvatrates.com/rates.json`.
- Map all rate types (standard, reduced, etc.) to `vat_rates` table.
- Set `hs_code_prefix = NULL` for country-level default rates.
- Log each run to `pipeline_runs`.

### `app/pipeline/scheduler.py`
- Use **APScheduler** (AsyncIOScheduler) to schedule:
  - `eu_taric` → every day at 06:00 UTC
  - `uk_tariff` → every day at 07:00 UTC
  - `eu_vat` → every Sunday at 08:00 UTC
- Expose a FastAPI startup event that starts the scheduler.

---

## FASTAPI ENDPOINTS TO EXPOSE (for the pipeline status/admin layer)

```
GET  /pipeline/status               → last run status for each source
POST /pipeline/trigger/{source}     → manually trigger a pipeline run
                                      source: 'uk_tariff' | 'eu_taric' | 'eu_vat'
GET  /pipeline/logs?source=&limit=  → recent pipeline_runs entries
```

These are **internal/admin endpoints** — protect them with a simple API key header (`X-Admin-Key`).

---

## LOOKUP ENDPOINT (core feature)

Once the pipeline is running, expose this endpoint:

```
GET /tariff/lookup?hs_code={code}&origin={ISO2}&destination={ISO2}
```

**Logic:**
1. Look up `duty_rates` for the given `hs_code` + `destination` market (EU or GB).
2. Find the best applicable rate in this priority order:
   - Preferential rate matching `origin_country` (trade agreement)
   - Anti-dumping / additional duty matching `origin_country`
   - MFN rate (origin_country IS NULL)
3. Look up `vat_rates` for the destination country. First try `hs_code_prefix` match, fall back to NULL (country default).
4. Return a structured JSON response:

```json
{
  "hs_code": "6403910000",
  "origin_country": "CN",
  "destination_country": "DE",
  "destination_market": "EU",
  "duty": {
    "rate_type": "MFN",
    "duty_rate": 8.0,
    "trade_agreement": null,
    "source": "TARIC"
  },
  "vat": {
    "country_code": "DE",
    "rate_type": "standard",
    "vat_rate": 19.0,
    "source": "euvatrates"
  },
  "calculated": {
    "duty_on_goods_value_pct": 8.0,
    "vat_applies_to": "goods_value + duty",
    "note": "VAT is assessed on CIF value + customs duty"
  },
  "data_freshness": {
    "duty_last_updated": "2026-03-27",
    "vat_last_updated": "2026-03-20"
  }
}
```

---

## PROJECT STRUCTURE

```
veritariff/
├── app/
│   ├── main.py                  # FastAPI app + lifespan startup
│   ├── database.py              # Async SQLAlchemy engine + session
│   ├── models.py                # SQLAlchemy ORM models (all 4 tables)
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── uk_tariff.py
│   │   ├── eu_taric.py
│   │   ├── eu_vat.py
│   │   └── scheduler.py
│   ├── routers/
│   │   ├── pipeline.py          # /pipeline/* admin endpoints
│   │   └── tariff.py            # /tariff/lookup endpoint
│   └── schemas.py               # Pydantic response models
├── alembic/                     # DB migrations
├── requirements.txt
└── .env                         # DATABASE_URL, ADMIN_API_KEY
```

---

## REQUIREMENTS & CONSTRAINTS

- Use **Python 3.11+**, **FastAPI**, **SQLAlchemy 2.x async**, **asyncpg**, **httpx** (async HTTP), **APScheduler**, **alembic**.
- All HTTP calls must be async (use `httpx.AsyncClient`).
- All DB operations must be async (use `async with session` pattern).
- Use **upsert** (INSERT ... ON CONFLICT DO UPDATE) not naive insert, to avoid duplicate records on re-runs.
- Add retry logic (3 retries with exponential backoff) on all external HTTP calls.
- Store the full raw API/XML response in `raw_json` column for auditability.
- Write a `requirements.txt` with pinned versions.
- Add a `README.md` section explaining how to run the first full pipeline ingest.

---

## WHAT TO DELIVER

1. All Python files for the structure above — fully working, no placeholders.
2. SQLAlchemy models matching the schema above.
3. Alembic `env.py` and an initial migration file.
4. `requirements.txt` with all dependencies pinned.
5. `.env.example` with all required environment variables.
6. A short `README.md` section: "Running the pipeline for the first time."

Do not leave TODO comments or stub functions. Every module must be fully implemented.
