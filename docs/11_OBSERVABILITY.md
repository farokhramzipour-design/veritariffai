# 11 — Observability

## Pillars

| Pillar | Tool | Purpose |
|---|---|---|
| **Logs** | AWS CloudWatch Logs + structured JSON | Debug, audit, compliance |
| **Metrics** | AWS CloudWatch Metrics + custom namespace | Performance, business KPIs |
| **Traces** | AWS X-Ray via OpenTelemetry | Latency, engine bottlenecks |
| **Errors** | Sentry | Exception tracking, alerting |

---

## Structured Logging

### Format
All logs emit JSON to stdout. Example:

```json
{
  "timestamp": "2026-02-23T14:23:01.234Z",
  "level": "INFO",
  "service": "tce-api",
  "environment": "production",
  "request_id": "uuid",
  "trace_id": "otel-trace-id",
  "span_id": "otel-span-id",
  "user_id": "uuid",
  "endpoint": "POST /api/v1/calculations/sync",
  "duration_ms": 342,
  "response_code": 200,
  "plan": "pro",
  "engines_used": ["classification", "customs_valuation", "tariff_measure", "vat"],
  "confidence_score": 0.91,
  "hs_codes": ["8471300000"],
  "jurisdiction": "UK"
}
```

### Log Levels
- `DEBUG`: Engine intermediate steps (disabled in production by default, togglable)
- `INFO`: Request/response, task completion, ingestion success
- `WARNING`: Engine fallback (e.g., MFN fallback), stale data, rate limit approaching
- `ERROR`: Engine failure, external API failure, unhandled exception
- `CRITICAL`: Data entirely unavailable, database unreachable

### Masked Fields
Never log: `authorization`, `id_token`, `refresh_token`, `stripe_secret`, `password`, `email`, `phone`

### Correlation
- Propagate and log `request_id`, `trace_id`, and `span_id` on every request, task, and log line.
- Accept `X-Request-ID` from clients when present; otherwise, generate one and return it in the response header.
- Ensure trace context is forwarded across FastAPI, Celery, SQLAlchemy, and Redis spans.

### Log Groups (CloudWatch)
```
/tce/{env}/api           — API request logs
/tce/{env}/workers       — Celery task logs
/tce/{env}/ingestion     — Tariff/FX ingestion logs
/tce/{env}/errors        — ERROR and CRITICAL only (for fast alerting)
```

Retention: 90 days (prod), 30 days (staging)

---

## Metrics

### CloudWatch Custom Namespace: `TCE/{ENV}`

| Metric | Unit | Dimensions | Description |
|---|---|---|---|
| `CalculationsPerMinute` | Count | Plan, Jurisdiction | Calculation throughput |
| `CalculationDuration` | Milliseconds | Plan, EngineSet | P50/P95/P99 latency |
| `CalculationConfidenceScore` | None (0–1) | Plan | Distribution |
| `CalculationErrors` | Count | ErrorCode | By error type |
| `EngineExecutionDuration` | Milliseconds | EngineName | Per-engine timing |
| `TariffDataAgeHours` | Hours | Source | Data freshness |
| `FXDataAgeHours` | Hours | Source, Currency | FX freshness |
| `QueueDepth` | Count | QueueName | Celery queue sizes |
| `ActiveProUsers` | Count | — | Business KPI |
| `DailyCalculations` | Count | Plan | Business KPI |
| `PlanConversions` | Count | — | Free→Pro conversions |

Export methods:
- Embedded Metric Format (EMF) via stdout for high-throughput metrics
- Direct `PutMetricData` for low-frequency business KPIs

---

## Tracing (OpenTelemetry + AWS X-Ray)

### Instrumentation Points
- FastAPI: all requests automatically traced
- SQLAlchemy: all database queries (query text + duration)
- Redis: all cache operations
- Celery: all task execution
- Each engine: manual span with attributes

### Engine Trace Attributes
```python
with tracer.start_as_current_span("engine.tariff_measure") as span:
    span.set_attribute("engine.name", "tariff_measure")
    span.set_attribute("engine.hs_code", hs_code)
    span.set_attribute("engine.jurisdiction", jurisdiction)
    span.set_attribute("engine.measures_found", len(measures))
    span.set_attribute("engine.duty_amount_gbp", str(duty_amount))
    span.set_attribute("request.id", request_id)
```

### Sampling
- Production: 5% of requests (cost control)
- Error requests: 100% (never sample away errors)
- Slow requests (> 2s): 100%

Sampler configuration:
```bash
# Environment variables (ECS task definition)
OTEL_TRACES_SAMPLER=parentbased_traceidratio
OTEL_TRACES_SAMPLER_ARG=0.05
```

```python
# Python SDK example
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
sampler = ParentBased(TraceIdRatioBased(0.05))
```

Ensure X-Ray sampling rules align so that error and slow traces are kept at 100%.

---

## Alerting

### PagerDuty (P1 — Immediate Response)
| Condition | Severity |
|---|---|
| API 5xx rate > 5% over 5 min | P1 |
| Database unreachable | P1 |
| Redis unreachable | P1 |
| Tariff data age > 48 hours | P1 |

### Slack (P2 — Business Hours Response)
| Condition |
|---|
| API 5xx rate > 1% over 15 min |
| Worker queue depth > 200 |
| Tariff data age > 26 hours |
| Ingestion failed 2× in a row |
| Confidence score P50 drops below 0.80 |
| Any CRITICAL log event |

### Daily Summary (Slack, 09:00 UTC)
- Calculations processed (Free vs Pro)
- Average confidence score
- Any ingestion warnings from past 24h
- New Pro subscriptions
- Error rate summary

---

## Health Dashboard (CloudWatch Dashboard)

Pre-built dashboard: `TCE-{ENV}-Health`

Widgets:
1. API request rate + error rate
2. Calculation latency (P50/P95/P99)
3. Confidence score distribution
4. Queue depths (all queues)
5. Database connections + query duration
6. Cache hit rate
7. Tariff data age
8. FX data age
9. Active ECS task count

---

## Sentry Configuration

```python
sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    environment=settings.ENVIRONMENT,
    traces_sample_rate=0.05,  # 5% of transactions
    profiles_sample_rate=0.05,
    send_default_pii=False,
    before_send=scrub_sensitive_fields,  # Remove PII before sending
)
```

**PII Scrubbing:** Sentry before_send hook removes: `email`, `authorization`, any field matching `*token*`, `*secret*`, `*password*`

**Issue routing:**
- Engine errors → `#alerts-engine` Slack channel
- Auth errors → `#alerts-security`
- Data ingestion errors → `#alerts-data`
- General errors → `#alerts-general`
