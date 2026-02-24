# 05 — Auth & Subscriptions

## Authentication Architecture

### Flow Overview
```
1. Client authenticates with Google → receives Google ID Token
2. Client sends Google ID Token to POST /api/v1/auth/google
3. Backend verifies ID token with Firebase Admin SDK
4. Backend upserts User record (create if new, update last_seen if existing)
5. Backend issues two tokens:
   a. Access Token — short-lived JWT (1 hour), signed by app secret
   b. Refresh Token — long-lived opaque token (30 days), stored in Redis
6. Client uses Access Token as Bearer token on all subsequent requests
7. Client uses Refresh Token to get new Access Tokens silently
```

### Google OAuth via Firebase
- Use **Firebase Authentication** for Google token verification only
- We do NOT use Firebase for user storage — users are stored in our PostgreSQL
- Firebase Admin SDK call: `auth.verify_id_token(id_token)`
- Extract: `sub` (unique Google user ID), `email`, `name`, `picture`
- Never store Google ID Token; verify and discard immediately

### Application JWT Structure
```json
{
  "sub": "user-uuid",
  "email": "user@example.com",
  "plan": "pro",
  "plan_exp": 1767225600,
  "iss": "trade-cost-engine",
  "aud": "tce-api",
  "iat": 1740312000,
  "exp": 1740315600
}
```

**Key design decisions:**
- `plan` claim embedded in JWT avoids a DB hit on every request for plan checking
- `plan_exp` is the plan expiry timestamp (not token expiry)
- When a plan changes via Stripe webhook, old JWTs are still valid until they expire (max 1 hour lag) — this is acceptable
- If immediate plan revocation is required, add user ID to a Redis blocklist

### Refresh Token Handling
- Refresh tokens are opaque random strings (32 bytes, URL-safe base64)
- Stored in Redis: `refresh:{token_hash}` → `{user_id, issued_at, expires_at}`
- SHA-256 hash of token is stored (never raw token in DB)
- Redis TTL: 30 days (sliding window on use)
- One active refresh token per user (new login invalidates old)
- `DELETE /auth/session` removes refresh token from Redis

---

## FastAPI Auth Dependencies

### `get_current_user`
Validates JWT, returns User object. Used on all protected endpoints.

```
Dependencies chain:
  get_current_user
    → extract Bearer token from Authorization header
    → decode and verify JWT (PyJWT)
    → check Redis blocklist
    → load User from DB (or short-lived cache)
    → return User
```

### `require_plan(plan: PlanTier)`
Factory dependency. Returns a dependency that checks user plan.

```
require_plan("pro")
  → get_current_user (inner dependency)
  → check user.plan == "pro" AND plan not expired
  → if fail: raise HTTPException(403, PLAN_UPGRADE_REQUIRED)
  → if pass: return user
```

**Usage in route:**
```python
@router.post("/calculations/async")
async def create_async_calculation(
    body: CalculationRequest,
    user: User = Depends(require_plan("pro"))
):
    ...
```

### `require_auth`
Shorthand for `require_plan("free")` — any authenticated user.

---

## Subscription Management (Stripe)

### Plan State Machine
```
NEW_USER
   │
   ▼
  FREE ──────────────► PRO (checkout completed)
   ▲                     │
   │                     ▼
   └────────── PRO_CANCELLING (cancel_at_period_end=true)
                         │
                         ▼ (period ends)
                       FREE
```

### Stripe Integration Points

| Stripe Event | Action |
|---|---|
| `checkout.session.completed` | Set user.plan = 'pro', store stripe_subscription_id |
| `customer.subscription.updated` | Update plan_expires_at from current_period_end |
| `customer.subscription.deleted` | Set user.plan = 'free', clear plan_expires_at |
| `invoice.payment_failed` | Send email, set grace period (3 days) |
| `invoice.payment_succeeded` | Extend plan_expires_at |

### Stripe Webhook Security
- Validate Stripe-Signature header using `stripe.Webhook.construct_event()`
- Webhook secret stored in AWS Secrets Manager
- Idempotency: check `subscription_events.stripe_event_id` before processing
- All webhook processing in a Celery task (non-blocking response to Stripe)
- Respond 200 to Stripe within 5 seconds regardless of processing outcome

### Checkout Flow
```
POST /subscriptions/checkout
  → Create Stripe Customer if user.stripe_customer_id is null
  → Store stripe_customer_id on user
  → Create Stripe Checkout Session
    success_url: https://app.example.com/upgrade/success
    cancel_url: https://app.example.com/upgrade/cancelled
  → Return checkout_url to client
```

---

## Security Considerations

### JWT
- Algorithm: RS256 (asymmetric) — public key verifiable without secret
- Key rotation: 90-day RSA key rotation via AWS Secrets Manager
- Key ID (`kid`) included in JWT header for multi-key validation during rotation

### Token Blocklist (Redis)
- On password-equivalent events (Google account linking changes), add user UUID to blocklist
- Redis key: `blocklist:{user_id}` with TTL matching max access token age (1 hour)

### Session Security
- Refresh tokens sent only in HttpOnly, Secure, SameSite=Strict cookies (not in response body) for web clients
- Mobile clients receive refresh token in response body (stored in secure enclave)

### Google Account Linking
- If a new Google login arrives with existing email but different `google_sub`, reject and alert user — potential account takeover attempt
