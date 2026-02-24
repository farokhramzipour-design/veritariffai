# 13 — Feature Flags & Rollout

## Strategy

Feature flagging serves two distinct purposes in this system:

1. **Plan Gating** — Free vs Pro engine access (permanent gates, not temporary flags)
2. **Progressive Rollout** — gradually releasing new engines or engine improvements

These are handled separately.

---

## Plan Gating (Permanent)

Plan gates are implemented as FastAPI dependencies — not feature flags. They are part of the core application logic.

See `05_AUTH_AND_SUBSCRIPTIONS.md` for implementation details.

### Engine Access Matrix

| Engine / Feature | Free | Pro |
|---|---|---|
| HS code search and validation | ✅ | ✅ |
| Basic ad valorem duty | ✅ | ✅ |
| Standard VAT rate (20% UK) | ✅ | ✅ |
| Market FX rate | ✅ | ✅ |
| Single HS line per calculation | ✅ | ✅ |
| Calculation history (last 5) | ✅ | ✅ |
| Customs Valuation Engine | ❌ | ✅ |
| Specific / Mixed / Compound duties | ❌ | ✅ |
| Anti-dumping / Countervailing / Safeguard | ❌ | ✅ |
| Tariff quota logic | ❌ | ✅ |
| Agricultural components | ❌ | ✅ |
| Suspension detection | ❌ | ✅ |
| Rules of Origin Engine | ❌ | ✅ |
| Preferential duty rates | ❌ | ✅ |
| VAT postponed accounting | ❌ | ✅ |
| Reduced / zero VAT rates | ❌ | ✅ |
| Excise Engine (alcohol, tobacco, energy) | ❌ | ✅ |
| CBAM calculation | ❌ | ✅ |
| Plastic Packaging Tax | ❌ | ✅ |
| Official customs FX rates (HMRC / ECB) | ❌ | ✅ |
| Multi-line invoice (up to 500 lines) | ❌ | ✅ |
| Compliance Flag Engine | ❌ | ✅ |
| Misclassification risk scoring | ❌ | ✅ |
| Full audit trail | ❌ | ✅ |
| PDF export | ❌ | ✅ |
| Calculation history (unlimited) | ❌ | ✅ |
| Async calculation API | ❌ | ✅ |

### Free Tier UX
When a Free user calls an engine that requires Pro, the response includes:
- Calculation result computed with available free engines
- `warnings` array with entries marking which engines were skipped
- `upgrade_prompt` field in response with upgrade URL
- No hard 403 rejection on the calculation itself (partial results are returned)

Hard 403 only returned on: `POST /calculations/async` (multi-line) and `GET /calculations/{id}/audit`

---

## Progressive Rollout (Feature Flags)

### Recommended Tool
**Unleash** (self-hosted, open source) or **LaunchDarkly** (SaaS).

For a $50M startup, **Unleash self-hosted on ECS** balances cost and control.

### Flag Evaluation
Flags are evaluated at the application layer, not the infrastructure layer. They are read from the Unleash API at startup and refreshed every 30 seconds (local cache).

```python
# app/dependencies.py

def get_feature_flags() -> FeatureFlags:
    return FeatureFlags(unleash_client)

# In route handler:
@router.post("/calculations/sync")
async def calculate(flags: FeatureFlags = Depends(get_feature_flags)):
    if flags.is_enabled("engine.cbam_v2", user_id=user.id):
        result = CBAMEngineV2.calculate(...)
    else:
        result = CBAMEngine.calculate(...)
```

### Active Feature Flags

| Flag Name | Purpose | Rollout Strategy |
|---|---|---|
| `engine.cbam_v2` | New CBAM calculation logic | Canary → 10% → 50% → 100% |
| `engine.ai_misclassification` | AI-powered misclassification detection | Beta users → Pro → All |
| `engine.quota_real_time` | Real-time quota balance from TARIC API | Canary only initially |
| `data.taric_v2_api` | Switch from TARIC v1 to v2 API | Internal → staging → prod |
| `ui.async_calculations` | Enable async calc UI flow (no-op for backend) | Frontend flag |
| `compliance.sanctions_v2` | Enhanced sanctions database | All users (data improvement) |

### Flag Lifecycle
1. **Created** — add to Unleash, default OFF
2. **Internal testing** — enable for engineering team user IDs
3. **Canary** — enable for 5% of Pro users
4. **Staged rollout** — 20% → 50% → 80% → 100%
5. **Cleanup** — remove flag code and flag from Unleash after 100% stable for 2 weeks

**No flag stays active indefinitely.** Stale flags are technical debt.

---

## Engine Versioning

When a calculation engine is significantly changed, run both versions in parallel for a period:

```
engine.tariff_measure.version = "v1"  # Current production
engine.tariff_measure.version = "v2"  # New logic under rollout

During parallel run:
  1. Execute both engines
  2. Compare results
  3. Log discrepancies to CloudWatch
  4. Route user response from v1 (stable)
  5. After 2 weeks with < 0.5% discrepancy: switch to v2
```

This "shadow mode" approach ensures engine updates do not surprise users with changed results.

---

## Rollout Checklist (New Engine or Major Change)

Before enabling in production:

- [ ] Unit tests pass (90%+ coverage)
- [ ] Accuracy tests pass (meets accuracy targets for affected scenarios)
- [ ] Integration tests pass
- [ ] Performance test: engine adds < 100ms to P99 latency
- [ ] Shadow mode run: < 0.5% result discrepancy vs previous version
- [ ] Canary: 5% of users for 48 hours with no anomalies
- [ ] Rollback plan documented (feature flag OFF = instant rollback)
- [ ] Monitoring dashboard updated with new engine metrics
- [ ] Release notes drafted for Pro users
