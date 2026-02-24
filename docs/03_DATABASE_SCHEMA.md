# 03 — Database Schema

## Technology
- **Database:** PostgreSQL 16
- **ORM:** SQLAlchemy 2.x (async with asyncpg driver)
- **Migrations:** Alembic
- **Naming Convention:** snake_case, plural table names, singular column names

---

## Schema: `identity`

### `users`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK, default gen_random_uuid() | |
| `google_sub` | VARCHAR(255) | UNIQUE NOT NULL | Google Subject ID |
| `email` | VARCHAR(320) | UNIQUE NOT NULL | |
| `display_name` | VARCHAR(255) | | From Google profile |
| `avatar_url` | TEXT | | From Google profile |
| `plan` | VARCHAR(20) | NOT NULL DEFAULT 'free' | 'free' or 'pro' |
| `plan_expires_at` | TIMESTAMPTZ | nullable | null = active indefinitely |
| `stripe_customer_id` | VARCHAR(255) | UNIQUE nullable | |
| `stripe_subscription_id` | VARCHAR(255) | UNIQUE nullable | |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | |
| `last_seen_at` | TIMESTAMPTZ | | Updated on each API call |
| `is_active` | BOOLEAN | NOT NULL DEFAULT true | Soft delete |

**Indexes:**
- `idx_users_google_sub` on `google_sub`
- `idx_users_email` on `email`
- `idx_users_stripe_customer_id` on `stripe_customer_id`

---

## Schema: `subscriptions`

### `subscription_events`
Append-only log of all plan state changes. Source of truth for audit.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `user_id` | UUID | FK users.id NOT NULL | |
| `event_type` | VARCHAR(50) | NOT NULL | 'upgraded', 'downgraded', 'renewed', 'cancelled', 'trial_started' |
| `from_plan` | VARCHAR(20) | | |
| `to_plan` | VARCHAR(20) | | |
| `stripe_event_id` | VARCHAR(255) | UNIQUE nullable | Idempotency |
| `metadata` | JSONB | | Raw Stripe payload |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

---

## Schema: `calculations`

### `calculation_requests`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `user_id` | UUID | FK users.id NOT NULL | |
| `plan_snapshot` | VARCHAR(20) | NOT NULL | Plan at request time |
| `status` | VARCHAR(20) | NOT NULL DEFAULT 'pending' | pending/processing/complete/failed |
| `shipment_data` | JSONB | NOT NULL | Full Shipment value object |
| `lines_data` | JSONB | NOT NULL | Array of ShipmentLine |
| `requested_engines` | TEXT[] | NOT NULL | Engine list |
| `error_message` | TEXT | nullable | If failed |
| `celery_task_id` | VARCHAR(255) | nullable | For async requests |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | |
| `completed_at` | TIMESTAMPTZ | nullable | |

**Indexes:**
- `idx_calc_requests_user_id` on `user_id`
- `idx_calc_requests_status` on `status` WHERE status NOT IN ('complete', 'failed')
- `idx_calc_requests_created_at` on `created_at`

### `calculation_results`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `request_id` | UUID | FK calculation_requests.id UNIQUE NOT NULL | 1:1 |
| `user_id` | UUID | FK users.id NOT NULL | Denormalized for fast user history queries |
| `line_results` | JSONB | NOT NULL | Array of LineResult |
| `engine_results` | JSONB | NOT NULL | Map engine→result |
| `totals` | JSONB | NOT NULL | AggregatedTotals |
| `audit_trail` | JSONB | NOT NULL | Ordered AuditStep array |
| `confidence_score` | NUMERIC(4,3) | NOT NULL | 0.000–1.000 |
| `warnings` | JSONB | NOT NULL DEFAULT '[]' | ComplianceFlag array |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | Immutable |

**Indexes:**
- `idx_calc_results_user_id` on `user_id`
- `idx_calc_results_created_at` on `created_at`

---

## Schema: `tariff`

### `hs_codes`
Master list of valid HS/CN/UKGT codes.

| Column | Type | Constraints |
|---|---|---|
| `code` | VARCHAR(12) | PK |
| `jurisdiction` | VARCHAR(5) | NOT NULL — 'UK' or 'EU' |
| `description` | TEXT | NOT NULL |
| `parent_code` | VARCHAR(12) | FK hs_codes.code nullable |
| `level` | SMALLINT | NOT NULL — 2,4,6,8,10 |
| `supplementary_unit` | VARCHAR(50) | nullable |
| `valid_from` | DATE | NOT NULL |
| `valid_to` | DATE | nullable |

### `tariff_measures`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `hs_code` | VARCHAR(12) | FK hs_codes.code NOT NULL | |
| `jurisdiction` | VARCHAR(5) | NOT NULL | |
| `measure_type` | VARCHAR(50) | NOT NULL | See measure types below |
| `country_of_origin` | VARCHAR(5) | nullable | null = all countries |
| `preferential_agreement` | VARCHAR(100) | nullable | |
| `rate_ad_valorem` | NUMERIC(8,4) | nullable | Percentage |
| `rate_specific_amount` | NUMERIC(14,4) | nullable | |
| `rate_specific_unit` | VARCHAR(50) | nullable | e.g., '100kg', 'unit' |
| `rate_minimum` | NUMERIC(14,4) | nullable | For compound duties |
| `rate_maximum` | NUMERIC(14,4) | nullable | |
| `agricultural_component` | NUMERIC(14,4) | nullable | |
| `quota_id` | UUID | FK tariff_quotas.id nullable | |
| `suspension` | BOOLEAN | NOT NULL DEFAULT false | |
| `measure_condition` | JSONB | nullable | License/cert requirements |
| `valid_from` | DATE | NOT NULL | |
| `valid_to` | DATE | nullable | |
| `source_dataset` | VARCHAR(20) | NOT NULL | 'TARIC' or 'UKGT' |
| `source_measure_id` | VARCHAR(100) | | Original dataset ID |
| `ingested_at` | TIMESTAMPTZ | NOT NULL | |

**Measure Types:**
`AD_VALOREM | SPECIFIC | MIXED | ANTI_DUMPING | COUNTERVAILING | SAFEGUARD | QUOTA_IN | QUOTA_OUT | AGRICULTURAL_LEVY | SUSPENSION`

**Indexes:**
- `idx_tariff_measures_hs_code` on `hs_code`
- `idx_tariff_measures_lookup` on `(hs_code, jurisdiction, country_of_origin, valid_from, valid_to)` — the hot path
- `idx_tariff_measures_valid` on `valid_to` WHERE valid_to IS NOT NULL (partial, for expiry cleanup)

### `tariff_quotas`
| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `quota_order_number` | VARCHAR(20) | UNIQUE NOT NULL |
| `jurisdiction` | VARCHAR(5) | NOT NULL |
| `description` | TEXT | |
| `volume` | NUMERIC(18,4) | NOT NULL |
| `volume_unit` | VARCHAR(20) | NOT NULL |
| `period_start` | DATE | NOT NULL |
| `period_end` | DATE | NOT NULL |
| `status` | VARCHAR(20) | NOT NULL — 'open', 'critical', 'exhausted' |
| `balance` | NUMERIC(18,4) | |
| `last_updated_at` | TIMESTAMPTZ | |

### `origin_rules`
| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `agreement` | VARCHAR(100) | NOT NULL — e.g., 'UK-EU TCA' |
| `hs_code_start` | VARCHAR(12) | NOT NULL |
| `hs_code_end` | VARCHAR(12) | NOT NULL |
| `rule_type` | VARCHAR(30) | NOT NULL |
| `rvc_threshold` | NUMERIC(5,2) | nullable |
| `rule_text` | TEXT | NOT NULL — official rule verbatim |
| `valid_from` | DATE | NOT NULL |
| `valid_to` | DATE | nullable |

---

## Schema: `fx`

### `fx_rates`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `base_currency` | CHAR(3) | NOT NULL | ISO 4217 |
| `quote_currency` | CHAR(3) | NOT NULL | ISO 4217 |
| `rate` | NUMERIC(18,8) | NOT NULL | |
| `rate_type` | VARCHAR(20) | NOT NULL | 'OFFICIAL_HMRC', 'OFFICIAL_ECB', 'MARKET' |
| `effective_date` | DATE | NOT NULL | |
| `source` | VARCHAR(100) | | URL or feed name |
| `ingested_at` | TIMESTAMPTZ | NOT NULL | |

**Unique constraint:** `(base_currency, quote_currency, rate_type, effective_date)`

**Indexes:**
- `idx_fx_rates_lookup` on `(base_currency, quote_currency, rate_type, effective_date DESC)`

---

## Schema: `compliance`

### `restricted_goods`
| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `hs_code_pattern` | VARCHAR(12) | NOT NULL — exact or prefix |
| `jurisdiction` | VARCHAR(5) | NOT NULL |
| `restriction_type` | VARCHAR(50) | NOT NULL |
| `description` | TEXT | NOT NULL |
| `license_required` | BOOLEAN | NOT NULL DEFAULT false |
| `certificate_required` | BOOLEAN | NOT NULL DEFAULT false |
| `outright_prohibited` | BOOLEAN | NOT NULL DEFAULT false |
| `valid_from` | DATE | NOT NULL |
| `valid_to` | DATE | nullable |

### `sanctions`
| Column | Type | Constraints |
|---|---|---|
| `id` | UUID | PK |
| `country_code` | CHAR(2) | NOT NULL |
| `jurisdiction` | VARCHAR(5) | NOT NULL |
| `sanction_type` | VARCHAR(50) | NOT NULL |
| `description` | TEXT | NOT NULL |
| `hs_code_scope` | TEXT[] | nullable — null = all goods |
| `valid_from` | DATE | NOT NULL |
| `valid_to` | DATE | nullable |

---

## Schema: `ingestion`

### `ingestion_runs`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `source` | VARCHAR(50) | NOT NULL | 'TARIC', 'UKGT', 'FX_HMRC', 'FX_ECB' |
| `status` | VARCHAR(20) | NOT NULL | 'running', 'success', 'failed' |
| `records_processed` | INTEGER | | |
| `records_inserted` | INTEGER | | |
| `records_updated` | INTEGER | | |
| `error_details` | TEXT | nullable | |
| `started_at` | TIMESTAMPTZ | NOT NULL | |
| `completed_at` | TIMESTAMPTZ | nullable | |

---

## Migration Strategy

1. All schema changes via Alembic migrations, never manual SQL in production
2. Migrations are backward-compatible (expand-and-contract pattern for breaking changes)
3. Each migration has an explicit `downgrade()` function
4. Staging runs migrations automatically on deploy; production requires explicit `alembic upgrade head` with approval
5. Migration naming: `YYYYMMDDHHMMSS_short_description.py`
