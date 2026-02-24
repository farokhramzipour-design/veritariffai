# 09 — Infrastructure

## Cloud Provider: AWS

All infrastructure defined as Terraform code in `/infrastructure/` directory.

---

## Service Architecture

```
                         ┌─────────────────┐
                         │   CloudFront CDN │
                         └────────┬────────┘
                                  │
                         ┌────────▼────────┐
                         │  Application    │
                         │  Load Balancer  │
                         │  (ALB, HTTPS)   │
                         └────────┬────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │     ECS Fargate             │
                    │                             │
                    │  ┌──────────────────────┐   │
                    │  │  API Workers         │   │
                    │  │  (FastAPI, 2–10 tasks)│  │
                    │  └──────────────────────┘   │
                    │  ┌──────────────────────┐   │
                    │  │  Celery Workers       │   │
                    │  │  (per queue, 2–8 tasks)│  │
                    │  └──────────────────────┘   │
                    └──────────────┬──────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
    ┌─────────▼────────┐  ┌────────▼────────┐  ┌───────▼───────┐
    │   RDS PostgreSQL  │  │ ElastiCache     │  │   S3 Buckets  │
    │   (Multi-AZ)      │  │ Redis Cluster   │  │               │
    │   db.r6g.large    │  │ cache.r6g.large │  │ - reports     │
    │   (prod)          │  │                 │  │ - backups     │
    └──────────────────┘  └─────────────────┘  └───────────────┘
```

---

## ECS Services

### API Service
```hcl
service_name = "tce-api"
task_cpu     = 512
task_memory  = 1024
desired_count = 2
min_capacity = 2
max_capacity = 10

health_check_path = "/api/v1/health"
health_check_interval = 30

auto_scaling:
  metric: ALBRequestCountPerTarget
  target: 500 requests per minute per task
  scale_out_cooldown: 60s
  scale_in_cooldown: 300s
```

### Celery Calculation Workers
```hcl
service_name = "tce-worker-calculations"
task_cpu     = 1024
task_memory  = 2048
desired_count = 2
min_capacity = 2
max_capacity = 8

auto_scaling:
  metric: Custom/CeleryQueueDepth (calculations queue)
  target: < 50 pending tasks
```

### Celery Ingestion Workers
```hcl
service_name = "tce-worker-ingestion"
task_cpu     = 512
task_memory  = 1024
desired_count = 2
min_capacity = 2
max_capacity = 2  # Fixed — predictable schedule
```

---

## Database

### RDS PostgreSQL
```
Instance: db.r6g.large (prod), db.t3.medium (staging)
PostgreSQL version: 16
Storage: 100GB gp3, auto-scaling to 1TB
Multi-AZ: true (prod), false (staging)
Backup: Daily automated, 7 day retention (prod: 30 days)
Encryption: AES-256 at rest
Parameter group: custom (shared_buffers, work_mem tuned)
```

### Connection Pooling
- **PgBouncer** sidecar in ECS task (transaction pooling mode)
- Max connections to RDS: 100
- FastAPI async pool size: 20 per worker
- Celery workers: 5 per worker process

---

## Redis (ElastiCache)

```
Cluster mode: enabled (3 shards × 1 replica)
Instance: cache.r6g.large (prod), cache.t3.micro (local/staging)
Redis version: 7.x
Encryption: in-transit + at-rest
Eviction policy: allkeys-lru
Max memory: 80% of instance RAM

Logical database separation:
  DB 0: Application cache (tariff data, FX, user sessions)
  DB 1: Celery broker
  DB 2: Celery results backend
  DB 3: Rate limiting counters
```

---

## Networking

```
VPC: /16 CIDR
  Public subnets (ALB): 2 AZs
  Private subnets (ECS, RDS, Redis): 2 AZs
  
Security Groups:
  ALB: inbound 443 from 0.0.0.0/0
  ECS API: inbound 8000 from ALB SG only
  ECS Workers: no inbound
  RDS: inbound 5432 from ECS SG only
  Redis: inbound 6379 from ECS SG only

NAT Gateway: 1 per AZ (for outbound from private subnets)
VPC Endpoints: S3, Secrets Manager, ECR (reduce NAT costs)
```

---

## Secrets Management

**All secrets in AWS Secrets Manager. Zero secrets in code, config files, or environment variable files.**

| Secret Name | Contents |
|---|---|
| `tce/prod/database` | DB host, port, name, user, password |
| `tce/prod/redis` | Redis endpoint, auth token |
| `tce/prod/jwt` | RSA private key (PEM), public key |
| `tce/prod/firebase` | Firebase Admin SDK service account JSON |
| `tce/prod/stripe` | API key, webhook signing secret |
| `tce/prod/hmrc` | Any HMRC API credentials |

Secrets are fetched at container startup via AWS SDK and injected as environment variables. No secrets in task definition environment.

---

## Container Registry

- **ECR (Elastic Container Registry)** — one repo per service
- Image tagging: `{service}:{git_sha}`
- Lifecycle policy: keep last 10 images, delete untagged after 1 day
- Vulnerability scanning: enabled on push

---

## Environments

| Env | ECS | RDS | Redis | Notes |
|---|---|---|---|---|
| `local` | Docker Compose | postgres container | redis container | Developer machines |
| `staging` | Fargate | db.t3.medium | cache.t3.micro | Auto-deploy on main branch |
| `production` | Fargate (Multi-AZ) | db.r6g.large (Multi-AZ) | cache.r6g.large cluster | Manual deploy approval |

---

## CI/CD Pipeline (GitHub Actions)

```
On: push to any branch
  → Run: unit tests + linting + type checking

On: push to main
  → Build Docker image
  → Push to ECR
  → Deploy to staging (ECS rolling update)
  → Run integration tests against staging
  → Notify Slack

On: release tag (vX.Y.Z)
  → Requires manual approval in GitHub
  → Deploy to production
  → Run smoke tests
  → Notify Slack + PagerDuty
```

---

## Cost Estimates (Monthly, Production)

| Service | Specification | Est. Cost |
|---|---|---|
| ECS Fargate API (2 tasks avg) | 2 × 0.5 vCPU, 1GB | ~$40 |
| ECS Fargate Workers (4 tasks avg) | 4 × 1 vCPU, 2GB | ~$100 |
| RDS PostgreSQL Multi-AZ | db.r6g.large | ~$300 |
| ElastiCache Redis cluster | 3 × cache.r6g.large | ~$400 |
| ALB | Standard | ~$25 |
| NAT Gateways (2×) | Data transfer | ~$80 |
| S3 + CloudFront | Reports, assets | ~$20 |
| Secrets Manager | ~20 secrets | ~$5 |
| CloudWatch Logs + Metrics | Standard | ~$50 |
| **Total** | | **~$1,020/month** |

Scale projections: linear with ECS task count. Redis and RDS are the scaling bottlenecks to watch.
