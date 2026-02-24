# 01 — System Architecture

## Layer Map

```
┌─────────────────────────────────────────────────────────────────┐
│  API LAYER (FastAPI)                                            │
│  Routes · Dependency Injection · Request Validation · Auth Gate │
├─────────────────────────────────────────────────────────────────┤
│  APPLICATION LAYER                                              │
│  Use Cases / Command Handlers · Plan Gate · Orchestrators       │
├───────────────────────┬─────────────────────────────────────────┤
│  DOMAIN LAYER         │  CALCULATION ENGINES (Pure Python)      │
│  Entities · Aggregates│  11 independent engines                 │
│  Value Objects        │  Zero framework dependency              │
│  Domain Events        │  Deterministic · Auditable              │
├───────────────────────┴─────────────────────────────────────────┤
│  INFRASTRUCTURE LAYER                                           │
│  PostgreSQL · Redis · Stripe · Firebase · TARIC/UKGT Feed       │
│  S3 · SES · CloudWatch · Celery Workers                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Service Boundaries

The backend is a single deployable service (monolith-first) structured internally as distinct bounded contexts. At $50M evaluation this avoids premature microservice complexity while keeping the door open for extraction.

### Bounded Contexts

| Context | Responsibility | Can Extract To Microservice |
|---|---|---|
| **Identity** | Users, Google OAuth, JWT issuance | Yes |
| **Subscription** | Plan state, Stripe webhooks, feature gates | Yes |
| **Calculation** | All 11 engines, audit trail, results | Yes — highest priority |
| **Tariff Data** | TARIC/UKGT ingestion, HS code lookup | Yes |
| **FX Data** | Official customs FX rates, history | Yes |
| **Compliance** | Restricted goods, sanctions, license flags | Yes |
| **Reporting** | PDF export, saved calculations, history | Later |

---

## Request Flow — Calculation

```
Client Request
     │
     ▼
FastAPI Router ──► AuthMiddleware (validate JWT, inject user)
     │
     ▼
PlanGateDependency ──► Check user.plan vs required_plan for endpoint
     │                    └─ 403 if insufficient plan
     ▼
CalculationOrchestrator (Application Layer)
     │
     ├──► ClassificationEngine
     ├──► CustomsValuationEngine
     ├──► TariffMeasureEngine
     ├──► RulesOfOriginEngine
     ├──► VATEngine
     ├──► ExciseEngine
     ├──► FXEngine
     ├──► ClearanceEngine
     ├──► LineLevelAggregator
     ├──► ComplianceFlagEngine
     │
     ▼
AuditTrailWriter ──► PostgreSQL (async)
     │
     ▼
CalculationResult ──► Response serializer ──► Client
```

---

## Async Architecture

### Synchronous Path (< 2 seconds target)
- Single HS line calculations
- Cached tariff lookups (Redis TTL: 1 hour)
- Simple ad valorem duty

### Asynchronous Path (Celery)
- Multi-line invoice processing (> 10 lines)
- PDF report generation
- TARIC/UKGT data refresh
- Stripe webhook processing
- FX rate ingestion
- Bulk re-calculation after tariff updates

```
POST /api/v1/calculations/async
     │
     ▼
Celery Task Created ──► task_id returned immediately (202 Accepted)
     │
     ▼
Worker Pool processes task
     │
     ▼
Result stored in PostgreSQL + Redis (with TTL)
     │
GET /api/v1/calculations/{task_id}/result ──► poll or websocket
```

---

## Directory Structure

```
app/
├── main.py                          # FastAPI app factory
├── config.py                        # Pydantic Settings (env vars)
├── dependencies.py                  # Shared FastAPI dependencies
│
├── api/                             # API Layer
│   └── v1/
│       ├── router.py
│       ├── calculations/
│       │   ├── router.py
│       │   ├── schemas.py           # Pydantic request/response models
│       │   └── dependencies.py
│       ├── auth/
│       ├── subscriptions/
│       ├── tariff/
│       └── health/
│
├── application/                     # Application Layer (Use Cases)
│   ├── calculations/
│   │   ├── orchestrator.py
│   │   ├── commands.py
│   │   └── results.py
│   ├── auth/
│   └── subscriptions/
│
├── domain/                          # Domain Layer
│   ├── calculation/
│   │   ├── entities.py
│   │   ├── value_objects.py
│   │   ├── aggregates.py
│   │   └── events.py
│   ├── tariff/
│   ├── origin/
│   └── shared/
│       └── money.py                 # Money value object (decimal-safe)
│
├── engines/                         # Calculation Engines (Pure Python)
│   ├── base.py                      # EngineResult, EngineError base types
│   ├── classification/
│   ├── customs_valuation/
│   ├── tariff_measure/
│   ├── rules_of_origin/
│   ├── vat/
│   ├── excise/
│   ├── fx/
│   ├── clearance/
│   ├── line_level/
│   └── compliance/
│
├── infrastructure/                  # Infrastructure Layer
│   ├── database/
│   │   ├── models.py                # SQLAlchemy ORM models
│   │   ├── repositories/
│   │   └── migrations/              # Alembic
│   ├── cache/
│   │   └── redis_client.py
│   ├── external/
│   │   ├── firebase_client.py
│   │   ├── stripe_client.py
│   │   ├── taric_client.py
│   │   ├── ukgt_client.py
│   │   └── fx_client.py
│   └── workers/
│       ├── celery_app.py
│       └── tasks/
│
└── tests/
    ├── unit/
    ├── integration/
    └── accuracy/                    # Calculation accuracy test suite
```

---

## Environment Tiers

| Environment | Purpose | Data |
|---|---|---|
| `local` | Developer machines via Docker Compose | Synthetic seeded data |
| `staging` | Pre-production, mirrors prod infra | Anonymized prod clone |
| `production` | Live | Real data, full observability |

All environments use identical Docker images. Config is 100% environment-variable driven (12-Factor).
