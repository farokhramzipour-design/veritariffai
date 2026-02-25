# Backend Implementation Spec
## AI Autofill + HS Code Field

> **Scope:** Two backend endpoints that power the visible UI in the screenshot:
> 1. `POST /api/autofill` — parses the NL textarea and returns all field values
> 2. `POST /api/hs-lookup` — classifies a product description into an 8-digit HS code with confidence score
>
> **Stack:** FastAPI · Python 3.11 · Anthropic SDK · Redis · Pydantic v2

---

## What the UI Sends and Expects

### Button: "Autofill fields with AI"
User types in the textarea, clicks the button. The frontend calls:
```
POST /api/autofill
Body: { "description": "leather shoes from Birmingham to Paris, £2,000" }
```
Expected response fills ALL calculator fields at once:
```json
{
  "product_description": "Leather shoes",
  "hs_code": "6403510000",
  "hs_confidence": 94,
  "hs_description": "Footwear with outer soles of rubber and uppers of leather",
  "origin_country": "GB",
  "destination_country": "FR",
  "declared_value": 2000.00,
  "currency": "GBP"
}
```

### Field: "HS CODE (8-DIGIT)" with 🔍 button
When user manually edits the HS code field or clicks the lookup button, the frontend calls:
```
POST /api/hs-lookup
Body: { "product_description": "Leather shoes", "origin_country": "GB" }
```
Expected response updates the HS code field and confidence bar:
```json
{
  "hs_code": "6403510000",
  "confidence": 94,
  "description": "Footwear with outer soles of rubber and uppers of leather",
  "alternatives": [
    { "hs_code": "6403991100", "confidence": 71, "description": "Other footwear..." },
    { "hs_code": "6404110000", "confidence": 45, "description": "Sports footwear..." }
  ],
  "cached": false
}
```

---

## File 1 — `schemas/models.py`
### Add these Pydantic models

```python
from pydantic import BaseModel, Field
from typing import Optional

# ── /api/autofill ──────────────────────────────────────────────

class AutofillRequest(BaseModel):
    description: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Free-text shipment description from the NL textarea"
    )

class AutofillResponse(BaseModel):
    product_description: Optional[str] = None
    hs_code: Optional[str] = None
    hs_confidence: Optional[int] = None          # 0–100
    hs_description: Optional[str] = None
    origin_country: Optional[str] = None         # ISO 2-letter: "GB"
    destination_country: Optional[str] = None    # ISO 2-letter: "FR"
    declared_value: Optional[float] = None
    currency: Optional[str] = None               # "GBP" | "EUR" | "USD"
    incoterms: Optional[str] = None              # "EXW"|"FOB"|"CIF"|"DDP"
    parse_confidence: int = Field(
        ...,
        description="How confident AI was in parsing the NL input overall (0–100)"
    )
    unparsed_fields: list[str] = Field(
        default=[],
        description="Fields the AI could not determine from the description"
    )

# ── /api/hs-lookup ─────────────────────────────────────────────

class HSLookupRequest(BaseModel):
    product_description: str = Field(..., min_length=2, max_length=300)
    origin_country: Optional[str] = None        # ISO 2-letter, helps refine code

class HSAlternative(BaseModel):
    hs_code: str
    confidence: int
    description: str

class HSLookupResponse(BaseModel):
    hs_code: str                                 # 10-digit zero-padded e.g. "6403510000"
    confidence: int                              # 0–100
    description: str                             # human-readable commodity description
    chapter: str                                 # e.g. "64"
    chapter_description: str                     # e.g. "Footwear, gaiters and the like"
    alternatives: list[HSAlternative] = []       # up to 3 alternatives
    cached: bool = False                         # true if served from Redis
    source: str = "claude"                       # "claude" | "fpo_api" | "cache"
```

---

## File 2 — `services/ai_agent.py`
### Claude API wrapper — two functions

```python
import anthropic
import json
import re
from typing import Optional

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env automatically

# ── PROMPT 1: Parse NL description into structured fields ───────

AUTOFILL_SYSTEM_PROMPT = """
You are a customs and trade expert. A user has typed a free-text description
of a shipment. Extract structured fields from it.

You MUST respond with ONLY a valid JSON object — no preamble, no markdown,
no explanation. If you cannot determine a field, set it to null.

Rules:
- hs_code: Best 10-digit HS/commodity code you can suggest (zero-padded).
  If unsure, give your best guess at the 6-digit level padded to 10 digits.
- hs_confidence: Integer 0–100. 90+ means you are certain. 
  Below 70 means the user should verify.
- origin_country / destination_country: ISO 3166-1 alpha-2 code (e.g. "GB", "FR", "DE").
- declared_value: Numeric only (no currency symbol).
- currency: "GBP", "EUR", or "USD". Infer from symbols: £=GBP, €=EUR, $=USD.
- incoterms: "EXW", "FOB", "CIF", or "DDP". Null if not mentioned.
- parse_confidence: How confident you are in the OVERALL parsing (0–100).
- unparsed_fields: List of field names you could not determine.

Response format (JSON only):
{
  "product_description": "string or null",
  "hs_code": "string or null",
  "hs_confidence": integer or null,
  "hs_description": "string or null",
  "origin_country": "string or null",
  "destination_country": "string or null",
  "declared_value": number or null,
  "currency": "string or null",
  "incoterms": "string or null",
  "parse_confidence": integer,
  "unparsed_fields": ["field_name", ...]
}
"""

def parse_nl_description(description: str) -> dict:
    """
    Sends the NL textarea content to Claude.
    Returns a dict matching AutofillResponse fields.
    """
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=AUTOFILL_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Parse this shipment description:\n\n{description}"
            }
        ]
    )

    raw = message.content[0].text.strip()

    # Strip markdown code fences if Claude wraps in ```json
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    return json.loads(raw)


# ── PROMPT 2: HS Code classification only ──────────────────────

HS_LOOKUP_SYSTEM_PROMPT = """
You are an expert customs classifier with deep knowledge of the Harmonized
System (HS) and the UK Combined Nomenclature.

You MUST respond with ONLY a valid JSON object — no preamble, no markdown,
no explanation.

Rules:
- hs_code: 10-digit commodity code, zero-padded. Must be a real, declarable code.
- confidence: Integer 0–100.
  95–100: You are certain this is the correct code.
  80–94:  Very likely correct, minor ambiguity.
  65–79:  Probably correct but product details are vague.
  Below 65: User must verify — you are guessing.
- description: Official commodity description for this code.
- chapter / chapter_description: The 2-digit chapter number and its title.
- alternatives: Up to 3 other plausible codes with their confidence and description.
  Only include alternatives if confidence < 90.

Response format (JSON only):
{
  "hs_code": "string",
  "confidence": integer,
  "description": "string",
  "chapter": "string",
  "chapter_description": "string",
  "alternatives": [
    { "hs_code": "string", "confidence": integer, "description": "string" }
  ]
}
"""

def classify_hs_code(product_description: str, origin_country: Optional[str] = None) -> dict:
    """
    Classifies a product description into an HS code.
    Returns a dict matching HSLookupResponse fields.
    """
    user_content = f"Product: {product_description}"
    if origin_country:
        user_content += f"\nOrigin country: {origin_country}"

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=HS_LOOKUP_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": user_content
            }
        ]
    )

    raw = message.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    return json.loads(raw)
```

---

## File 3 — `services/cache.py`
### Redis cache helpers

```python
import redis
import json
import hashlib
import os
from typing import Optional

r = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379"),
    decode_responses=True
)

# TTL constants (in seconds)
TTL_HS_LOOKUP  = 60 * 60 * 24 * 7   # 7 days  — HS codes rarely change
TTL_AUTOFILL   = 60 * 60 * 24        # 24 hours — NL parses can be reused

def _make_key(prefix: str, *parts: str) -> str:
    """Build a cache key, hashing long strings to keep keys short."""
    raw = ":".join(str(p).lower().strip() for p in parts)
    hashed = hashlib.md5(raw.encode()).hexdigest()[:16]
    return f"{prefix}:{hashed}"

# ── HS Lookup cache ─────────────────────────────────────────────

def get_hs_cache(product_description: str, origin_country: Optional[str]) -> Optional[dict]:
    key = _make_key("hs", product_description, origin_country or "")
    value = r.get(key)
    return json.loads(value) if value else None

def set_hs_cache(product_description: str, origin_country: Optional[str], data: dict) -> None:
    key = _make_key("hs", product_description, origin_country or "")
    r.setex(key, TTL_HS_LOOKUP, json.dumps(data))

# ── Autofill cache ──────────────────────────────────────────────

def get_autofill_cache(description: str) -> Optional[dict]:
    key = _make_key("autofill", description)
    value = r.get(key)
    return json.loads(value) if value else None

def set_autofill_cache(description: str, data: dict) -> None:
    key = _make_key("autofill", description)
    r.setex(key, TTL_AUTOFILL, json.dumps(data))
```

---

## File 4 — `services/confidence.py`
### HS confidence scorer

```python
def score_hs_confidence(hs_code: str, ai_confidence: int) -> int:
    """
    Adjusts AI-reported confidence based on code specificity.
    A full 10-digit declarable code scores higher than a partial one.

    Args:
        hs_code:       The HS/commodity code string
        ai_confidence: Raw confidence from Claude (0–100)

    Returns:
        Final adjusted confidence score (0–100)
    """
    if not hs_code:
        return 0

    # Remove any dots or spaces
    code = hs_code.replace(".", "").replace(" ", "")
    digits = len(code.rstrip("0"))

    # Specificity multiplier:
    # 10 non-zero digits = full code        → no penalty
    # 8 digits                              → -5
    # 6 digits (heading level)              → -15
    # 4 digits or fewer                     → -25
    if digits >= 10:
        penalty = 0
    elif digits >= 8:
        penalty = 5
    elif digits >= 6:
        penalty = 15
    else:
        penalty = 25

    return max(0, min(100, ai_confidence - penalty))
```

---

## File 5 — `routers/autofill.py`
### POST /api/autofill endpoint

```python
from fastapi import APIRouter, HTTPException
from schemas.models import AutofillRequest, AutofillResponse
from services.ai_agent import parse_nl_description
from services.cache import get_autofill_cache, set_autofill_cache
from services.confidence import score_hs_confidence
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/api/autofill", response_model=AutofillResponse)
async def autofill(request: AutofillRequest):
    """
    Parses a free-text shipment description and returns all calculator
    field values. Powers the 'Autofill fields with AI' button.

    Flow:
      1. Check Redis cache (key: hash of description)
      2. Cache miss → call Claude to parse NL description
      3. Adjust HS confidence using score_hs_confidence()
      4. Cache the result for 24 hours
      5. Return AutofillResponse
    """

    # Step 1 — Cache check
    cached = get_autofill_cache(request.description)
    if cached:
        logger.info(f"Autofill cache HIT for description hash")
        return AutofillResponse(**cached, cached=True)

    # Step 2 — Call Claude
    try:
        result = parse_nl_description(request.description)
    except Exception as e:
        logger.error(f"Claude autofill failed: {e}")
        raise HTTPException(
            status_code=502,
            detail="AI service unavailable. Please fill fields manually."
        )

    # Step 3 — Adjust HS confidence
    if result.get("hs_code") and result.get("hs_confidence"):
        result["hs_confidence"] = score_hs_confidence(
            result["hs_code"],
            result["hs_confidence"]
        )

    # Step 4 — Cache result
    set_autofill_cache(request.description, result)

    # Step 5 — Return
    return AutofillResponse(**result)
```

---

## File 6 — `routers/hs_lookup.py`
### POST /api/hs-lookup endpoint

```python
from fastapi import APIRouter, HTTPException
from schemas.models import HSLookupRequest, HSLookupResponse
from services.ai_agent import classify_hs_code
from services.cache import get_hs_cache, set_hs_cache
from services.confidence import score_hs_confidence
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/api/hs-lookup", response_model=HSLookupResponse)
async def hs_lookup(request: HSLookupRequest):
    """
    Classifies a product description into an 8/10-digit HS code.
    Powers the HS CODE field confidence bar and the 🔍 lookup button.

    Flow:
      1. Check Redis cache (key: hash of description + origin)
      2. Cache miss → call Claude to classify HS code
      3. Adjust confidence using score_hs_confidence()
      4. Cache for 7 days
      5. Return HSLookupResponse
    """

    # Step 1 — Cache check
    cached = get_hs_cache(request.product_description, request.origin_country)
    if cached:
        logger.info(f"HS lookup cache HIT")
        return HSLookupResponse(**cached, cached=True, source="cache")

    # Step 2 — Call Claude
    try:
        result = classify_hs_code(
            request.product_description,
            request.origin_country
        )
    except Exception as e:
        logger.error(f"Claude HS lookup failed: {e}")
        raise HTTPException(
            status_code=502,
            detail="AI classification unavailable. Please enter HS code manually."
        )

    # Step 3 — Adjust confidence
    result["confidence"] = score_hs_confidence(
        result["hs_code"],
        result["confidence"]
    )

    # Step 4 — Cache
    set_hs_cache(request.product_description, request.origin_country, result)

    # Step 5 — Return
    return HSLookupResponse(**result, cached=False, source="claude")
```

---

## File 7 — `main.py`
### Register both routers

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.autofill import router as autofill_router
from routers.hs_lookup import router as hs_lookup_router

app = FastAPI(title="Export Calculator API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(autofill_router)
app.include_router(hs_lookup_router)
```

---

## File 8 — `requirements.txt`
### Dependencies needed

```
fastapi==0.111.0
uvicorn[standard]==0.30.1
pydantic==2.7.1
anthropic==0.28.0
redis==5.0.4
python-dotenv==1.0.1
httpx==0.27.0
```

---

## File 9 — `.env`
### Environment variables

```
ANTHROPIC_API_KEY=sk-ant-...
REDIS_URL=redis://localhost:6379
```

---

## Complete Flow Diagram

```
USER TYPES: "leather shoes from Birmingham to Paris, £2,000"
                           │
                           ▼
                  Click "Autofill fields with AI"
                           │
              Frontend POST /api/autofill
              { description: "leather shoes..." }
                           │
                 ┌─────────▼──────────┐
                 │  Redis cache check │
                 │  key: hash(desc)   │
                 └─────────┬──────────┘
                     HIT ◄─┤─► MISS
                     │     │       │
                     │     │       ▼
                     │     │  Claude Sonnet
                     │     │  parse_nl_description()
                     │     │       │
                     │     │       ▼
                     │     │  score_hs_confidence()
                     │     │       │
                     │     └──────►│ set_autofill_cache()
                     │             │
                     └─────────────▼
                     AutofillResponse JSON
                           │
                    Frontend fills fields:
                    ✅ Product Description ← "Leather shoes"
                    ✅ HS Code            ← "6403510000"
                    ✅ Confidence bar     ← 94%
                    ✅ Origin Country     ← "GB" (United Kingdom)
                    ✅ Destination        ← "FR" (France)
                    ✅ Declared Value     ← 2000.00
                    ✅ Currency           ← "GBP"


USER CLICKS 🔍 (HS lookup button) or edits HS Code field:
                           │
              Frontend POST /api/hs-lookup
              { product_description: "Leather shoes", origin_country: "GB" }
                           │
                 ┌─────────▼──────────┐
                 │  Redis cache check │
                 │  TTL: 7 days       │
                 └─────────┬──────────┘
                     HIT ◄─┤─► MISS
                           │       │
                           │  Claude Sonnet
                           │  classify_hs_code()
                           │       │
                           │  score_hs_confidence()
                           │       │
                           │  set_hs_cache() TTL 7d
                           │
                     HSLookupResponse JSON
                           │
                    Frontend updates:
                    ✅ HS Code field   ← "6403510000"
                    ✅ Confidence bar  ← 94% (cyan/gold/red)
                    ✅ Description     ← "Footwear with outer soles..."
                    ✅ Alternatives    ← shown in drawer
```

---

## Error Handling Reference

| Scenario | HTTP Code | Frontend Behaviour |
|---|---|---|
| Claude API down | 502 | Show amber warning, keep fields editable manually |
| Redis down | 200 (degrade) | Log error, skip cache, call Claude directly |
| Description too short (<3 chars) | 422 | Pydantic validation, show inline field error |
| Claude returns invalid JSON | 502 | Retry once, then return 502 |
| HS code not found / very low confidence | 200 | Return result with confidence <50, UI shows red bar + warning |

---

## Testing the Endpoints

```bash
# Test autofill
curl -X POST http://localhost:8000/api/autofill \
  -H "Content-Type: application/json" \
  -d '{"description": "leather shoes from Birmingham to Paris, £2,000"}'

# Test hs-lookup
curl -X POST http://localhost:8000/api/hs-lookup \
  -H "Content-Type: application/json" \
  -d '{"product_description": "leather shoes", "origin_country": "GB"}'

# Start the server
uvicorn main:app --reload --port 8000
```
