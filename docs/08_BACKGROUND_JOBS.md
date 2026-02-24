# 08 — Background Jobs

## Technology Stack
- **Task Queue:** Celery 5.x
- **Broker:** Redis (same instance as cache, separate logical DB)
- **Result Backend:** Redis (short-term) + PostgreSQL (permanent task records)
- **Monitoring:** Flower (Celery monitoring UI) + custom metrics to CloudWatch

---

## Celery App Configuration

```
app/infrastructure/workers/celery_app.py

Queues:
  - calculations     — high priority, async calculation jobs
  - data_ingestion   — tariff/FX data refresh
  - notifications    — emails, webhooks
  - reporting        — PDF generation, exports
  - maintenance      — cleanup, reconciliation

Worker pools:
  - calculations worker: 4 concurrent workers (CPU-bound)
  - ingestion worker: 2 concurrent workers (I/O-bound)
  - general worker: 2 concurrent workers
```

---

## Scheduled Tasks (Celery Beat)

| Task | Schedule | Queue | Description |
|---|---|---|---|
| `ingest_taric_delta` | Daily 06:00 UTC | data_ingestion | TARIC daily changes |
| `ingest_ukgt_delta` | Daily 06:30 UTC | data_ingestion | UKGT daily changes |
| `ingest_taric_full` | Weekly Sun 02:00 UTC | data_ingestion | TARIC full reconciliation |
| `ingest_ukgt_full` | Weekly Sun 03:00 UTC | data_ingestion | UKGT full reconciliation |
| `ingest_fx_hmrc` | Monthly 1st 09:00 UTC | data_ingestion | HMRC monthly FX rates |
| `ingest_fx_ecb` | Daily 17:00 CET | data_ingestion | ECB daily FX rates |
| `check_quota_status` | Daily 08:00 UTC | data_ingestion | Refresh quota balances |
| `expire_plans` | Every hour | maintenance | Mark expired Pro plans as free |
| `cleanup_stale_results` | Daily 01:00 UTC | maintenance | Delete results > 1 year old |
| `warm_cache` | Daily 07:00 UTC | maintenance | Pre-warm common HS code caches |
| `data_quality_check` | Daily 08:30 UTC | maintenance | Validate data freshness, alert if stale |

---

## Task Definitions

### `run_async_calculation`
**Queue:** calculations
**Triggered by:** `POST /api/v1/calculations/async`

```
Inputs: request_id (UUID)
Process:
  1. Load CalculationRequest from DB
  2. Instantiate CalculationOrchestrator
  3. Run engines per orchestration order (see engine doc)
  4. Write CalculationResult to DB
  5. Update CalculationRequest.status = 'complete'
  6. Cache result in Redis for 15 minutes (for fast polling)
  7. (Optional future) Send push notification / webhook to client

Retry policy:
  Max retries: 2
  Retry on: NetworkError, DatabaseTimeoutError
  No retry on: EngineError, ValidationError (user error)
  
On final failure:
  Update CalculationRequest.status = 'failed'
  Write error_message
  Emit CalculationFailed event
```

### `ingest_taric_delta`
**Queue:** data_ingestion

```
Process:
  1. Create ingestion_run record (status=running)
  2. Fetch TARIC API changes since last ingestion_run.started_at
  3. Parse and validate records
  4. Batch upsert (batch size: 500 records)
  5. Invalidate Redis tariff caches for updated HS codes
  6. Update ingestion_run (status=success, counts)
  7. Log metrics to CloudWatch

Retry policy:
  Max retries: 3
  Backoff: 15min, 30min, 60min
  On all retries exhausted: alert ops team, do not crash

Alerting:
  If records_updated > 500: send Slack alert (high change day)
  If ingestion fails twice in a row: PagerDuty alert
```

### `expire_plans`
**Queue:** maintenance

```
Process:
  1. SELECT users WHERE plan='pro' AND plan_expires_at < now() AND plan_expires_at IS NOT NULL
  2. For each user:
     a. Set plan='free'
     b. Create subscription_event(event_type='downgraded', from_plan='pro', to_plan='free')
     c. Emit UserDowngradedToFree event
  3. Log count of expired plans
```

### `generate_report_pdf`
**Queue:** reporting
**Triggered by:** `POST /api/v1/calculations/{id}/export/pdf`

```
Inputs: request_id, user_id
Process:
  1. Load CalculationResult
  2. Render PDF using WeasyPrint or ReportLab
  3. Upload to S3: reports/{user_id}/{request_id}/report.pdf
  4. Generate signed S3 URL (1 hour expiry)
  5. Return URL via polling endpoint or push notification
```

---

## Task Monitoring

### Flower Dashboard
- Internal only (not public-facing)
- URL: `http://internal-flower.tce.internal/`
- Auth: Basic auth via nginx
- Shows: active workers, task throughput, failure rates

### CloudWatch Metrics (custom)
Emitted by all tasks:

| Metric | Type | Description |
|---|---|---|
| `task.completed` | Counter | Per queue, per task name |
| `task.failed` | Counter | Per queue, per task name |
| `task.duration_ms` | Histogram | Task execution time |
| `ingestion.records_processed` | Counter | Per source |
| `ingestion.lag_hours` | Gauge | Hours since last successful ingestion |
| `calculation.confidence_score` | Histogram | Distribution of confidence scores |

### Alerting Rules
- `ingestion.lag_hours > 26` for any source → PagerDuty P2
- `task.failed rate > 5%` over 5 minutes → Slack alert
- `calculation worker queue depth > 100` → auto-scaling trigger

---

## Worker Scaling

Workers run on ECS Fargate. Auto-scaling based on:
- **calculations queue**: scale on SQS queue depth metric (target: < 50 pending)
- **data_ingestion queue**: fixed 2 workers (predictable schedule)
- **reporting queue**: scale on queue depth (target: < 10 pending)

Scale-in delay: 300 seconds (prevent thrashing during calculation bursts)
