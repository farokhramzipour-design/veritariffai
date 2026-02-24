# Trade Cost Engine — Backend Project Overview

## Project Identity

| Field | Value |
|---|---|
| Project Name | Trade Cost Engine (TCE) |
| Stack | Python 3.12 · FastAPI · PostgreSQL · Redis · Celery |
| Auth | Google OAuth 2.0 via Firebase Auth |
| Deployment Target | AWS (ECS Fargate + RDS + ElastiCache) |
| Evaluation Stage | Seed/Series A — $50M |
| Architecture Style | Domain-Driven Design (DDD) + Hexagonal Architecture |

---

## Document Index

| File | Scope |
|---|---|
| `00_PROJECT_OVERVIEW.md` | This file — goals, principles, doc index |
| `01_ARCHITECTURE.md` | System architecture, layers, service boundaries |
| `02_DOMAIN_MODEL.md` | Core entities, aggregates, value objects |
| `03_DATABASE_SCHEMA.md` | PostgreSQL schema design |
| `04_API_DESIGN.md` | REST API contract, versioning, error formats |
| `05_AUTH_AND_SUBSCRIPTIONS.md` | Google OAuth, JWT, Free vs Pro gate logic |
| `06_CALCULATION_ENGINES.md` | All 11 calculation engine specifications |
| `07_DATA_INTEGRATION.md` | TARIC / UKGT ingestion, FX feeds, update pipelines |
| `08_BACKGROUND_JOBS.md` | Celery tasks, scheduling, retry logic |
| `09_INFRASTRUCTURE.md` | AWS services, IaC, environments, secrets |
| `10_SECURITY.md` | Auth hardening, rate limiting, PII handling |
| `11_OBSERVABILITY.md` | Logging, metrics, tracing, alerting |
| `12_TESTING_STRATEGY.md` | Unit, integration, e2e, calculation accuracy tests |
| `13_FEATURE_FLAGS_AND_ROLLOUT.md` | Free vs Pro gating, LaunchDarkly/Unleash |

---

## Business Context

### Core Product
A customs-grade trade cost engine that allows importers, brokers, and freight forwarders to calculate the true landed cost of goods across jurisdictions (UK, EU initially).

### Tier Model

| Tier | Access | Calculation Engines Available |
|---|---|---|
| **Free** | Google login required | Commodity lookup, basic ad valorem duty, basic VAT (standard rate), single currency, single HS line |
| **Pro** | Paid subscription | All 11 engines: customs valuation, mixed duties, anti-dumping, origin/preference, excise, FX, line-level, compliance flags |

### Non-Negotiable Accuracy Targets

| Shipment Type | Target Accuracy |
|---|---|
| Simple (single HS, standard duty) | 95%+ |
| Standard commercial | 90–94% |
| Complex regulated goods | 85–92% |

---

## Core Architecture Principles

1. **Domain-first** — calculation engines are pure domain logic with zero framework dependency
2. **Engine isolation** — each calculation engine is independently testable and replaceable
3. **Audit-complete** — every calculation step is stored and replayable
4. **Data currency** — TARIC/UKGT data updated automatically; stale data is a system failure
5. **Plan-gate at API layer** — free vs pro is enforced by a dependency-injected plan checker, never scattered across business logic
6. **Horizontal scalability** — stateless API workers, async job workers, shared Redis state
7. **12-Factor compliance** — config from env, logs to stdout, disposable processes

---

## Technology Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Web framework | FastAPI | Async-native, OpenAPI auto-generation, type safety via Pydantic |
| ORM | SQLAlchemy 2.x (async) | Mature, supports complex queries, async-native in v2 |
| Migrations | Alembic | Industry standard for SQLAlchemy |
| Task queue | Celery + Redis broker | Proven, supports scheduled tasks and complex workflows |
| Cache | Redis | Session data, rate limits, tariff lookup cache |
| Auth | Firebase Auth (Google OAuth) + in-house JWT | Firebase handles token exchange; we issue our own JWTs with plan claims |
| Payments | Stripe | Webhooks drive plan state changes |
| Secrets | AWS Secrets Manager | Never in env files in production |
| Container | Docker + ECS Fargate | Serverless containers, no EC2 management |
| IaC | Terraform | All infra as code |
| Observability | AWS CloudWatch + OpenTelemetry + Sentry | Full tracing, error tracking, custom business metrics |
