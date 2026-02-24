# 10 — Security

## Authentication Security

### JWT
- Algorithm: RS256 (asymmetric) — private key signs, public key verifies
- Access token TTL: 3600 seconds (1 hour)
- Refresh token TTL: 30 days, sliding window
- Refresh token stored as SHA-256 hash in Redis (never plaintext)
- RSA key size: 4096-bit
- Key rotation: automated every 90 days via AWS Secrets Manager rotation Lambda
- During key rotation: support 2 active public keys simultaneously (grace period)

### Token Validation (per request)
```
1. Extract Bearer token from Authorization header
2. Decode JWT header to get `kid` (key ID)
3. Fetch corresponding public key (from in-memory cache, refreshed hourly)
4. Verify signature
5. Verify `iss`, `aud` claims
6. Verify `exp` not in past
7. Check Redis blocklist for user_id
8. Return decoded claims
```

### Session Invalidation
Situations requiring immediate session invalidation:
- User reports account compromise
- Admin disables user account
- Stripe payment fraud detected

Mechanism: add `{user_id}` to Redis key `blocklist:{user_id}` with TTL = 3601 seconds. All token validation checks this key.

---

## API Security

### Rate Limiting
- Implemented via Redis counter: `ratelimit:{user_id}:{window}:{endpoint_group}`
- Window: sliding 1-hour window
- Limits enforced in FastAPI middleware before route handlers
- Return `429 Too Many Requests` with `Retry-After` header when exceeded

### Input Validation
- All request bodies validated by Pydantic v2 models
- All path/query parameters validated by FastAPI
- HS codes: pattern-validated (8–10 digits only)
- Monetary amounts: Decimal with configurable max (e.g., max customs value 50M)
- String fields: max length enforced, HTML stripped
- No eval, exec, or dynamic SQL construction anywhere in the codebase

### SQL Injection Prevention
- SQLAlchemy ORM with parameterized queries only
- Zero raw SQL strings with user input
- Alembic migrations reviewed for injection risk

### CORS
```python
allowed_origins = settings.CORS_ORIGINS  # List from env var
# Staging: ["https://staging.app.example.com"]
# Production: ["https://app.example.com"]
# Never "*" in production
```

---

## Data Security

### PII Handling
PII stored: email, display_name, avatar_url, Google sub

- Email: stored plaintext (required for login matching)
- Avatar URL: stored as Google CDN URL (no PII content)
- Calculation data: shipment details, HS codes — not considered PII
- Right to erasure (GDPR): delete/anonymize user record and all related calculations on request

### Data at Rest
- RDS: encrypted with AWS KMS (AES-256)
- S3: server-side encryption (SSE-S3)
- Redis: ElastiCache encryption at rest enabled
- EBS volumes: encrypted

### Data in Transit
- TLS 1.2 minimum, TLS 1.3 preferred (enforced at ALB)
- Redis: TLS in-transit enabled
- RDS: SSL required (verify-full)
- All external HTTP calls use HTTPS only

### Database Access
- RDS accessible only from within VPC
- No public endpoint
- Credentials rotated every 90 days via AWS Secrets Manager automatic rotation
- Separate read replica credentials for reporting queries (read-only role)
- Application user: SELECT, INSERT, UPDATE, DELETE only. No DDL rights.
- Migrations run by separate deployment role (DDL rights, time-limited)

---

## Stripe Webhook Security
```
1. Receive webhook at POST /api/v1/webhooks/stripe
2. Read raw request body BEFORE Pydantic parsing (Stripe signature covers raw bytes)
3. Validate: stripe.Webhook.construct_event(raw_body, stripe_signature_header, webhook_secret)
4. If validation fails: return 400, log warning
5. Check idempotency: query subscription_events for stripe_event_id
6. If already processed: return 200 (Stripe retry safety)
7. Dispatch to Celery task for async processing
8. Return 200 immediately (within Stripe's 5 second window)
```

---

## Dependency Security

### Python Dependencies
- Pinned versions in `requirements.txt` and `pyproject.toml`
- `pip audit` run in CI pipeline (fail build on HIGH severity CVEs)
- `dependabot` alerts enabled on GitHub
- Monthly dependency update review

### Container Security
- Base image: `python:3.12-slim` (minimal attack surface)
- Run as non-root user in container (`USER appuser`)
- No SSH in containers
- Read-only filesystem where possible
- ECR vulnerability scanning on every push

---

## Secrets Hygiene
- `.env` files are in `.gitignore` — never committed
- No secrets in Docker build args (use runtime env vars)
- No secrets in logs (structured logging masks sensitive fields: `password`, `token`, `secret`, `key`)
- AWS IAM roles follow least-privilege principle (task roles scope to specific resources)
- Developers access staging secrets via `aws secretsmanager get-secret-value` with MFA-required IAM policy

---

## Compliance Notes

### GDPR (if EU users)
- Data Processing Agreement with AWS
- Data residency: EU region (eu-west-1 or eu-central-1)
- Privacy policy includes tariff calculation data retention (12 months, then deletion)
- Right to erasure: implemented via `DELETE /api/v1/users/me` (soft delete → hard delete after 30 days)

### SOC 2 Readiness
At $50M valuation, SOC 2 Type II audit is recommended within 18 months:
- Access logging: all API calls logged with user_id, endpoint, response code
- Change management: all infrastructure changes via Terraform + PR review
- Incident response: documented runbook in Notion
- Background check policy: for all engineers with production access
