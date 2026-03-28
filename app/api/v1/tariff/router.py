from __future__ import annotations
from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException
from app.core.responses import ok
from pydantic import BaseModel, Field
from typing import List, Optional
from app.config import settings
import hashlib
import json
import re
import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import TariffMeasure, VATRate
from app.infrastructure.database.session import get_session
from app.utils.country import is_eu

try:
    import redis
    from openai import OpenAI
except ImportError:
    redis = None
    OpenAI = None

router = APIRouter()

# --- Models ---

class HSLookupRequest(BaseModel):
    product_description: str = Field(..., description="Detailed description of the product")
    origin_country: str = Field(..., description="Country of origin for the product")

class HSLookupResponse(BaseModel):
    hs_code: str = Field(..., description="The 8-digit HS code")
    confidence: float = Field(..., description="Confidence score between 0 and 100")
    description: str = Field(..., description="Description of the HS code")
    warnings: List[str] = Field(default_factory=list, description="Any warnings or notes about the classification")

# --- Services ---

def get_redis_client():
    if redis:
        try:
            return redis.Redis.from_url(settings.redis_url)
        except Exception:
            return None
    return None

def calculate_confidence(hs_code: str) -> float:
    """
    Simple confidence scoring based on HS code length.
    8-digit or more = High confidence (90+)
    6-digit = Medium confidence (70-80)
    4-digit = Low confidence (50-60)
    """
    clean_code = re.sub(r'\D', '', hs_code)
    length = len(clean_code)
    
    if length >= 8:
        return 95.0
    elif length >= 6:
        return 75.0
    elif length >= 4:
        return 55.0
    else:
        return 30.0

async def get_hs_code_from_ai(description: str, origin: str) -> HSLookupResponse:
    if not settings.openai_api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    client = OpenAI(api_key=settings.openai_api_key)
    
    prompt = f"""
    You are an expert customs broker and trade compliance specialist.
    Classify the following product into an 8-digit Harmonized System (HS) code.
    
    Product Description: {description}
    Country of Origin: {origin}
    
    Return the result in strict JSON format with the following keys:
    - hs_code: The 8-digit HS code (string)
    - description: A brief official description of this HS code (string)
    - warnings: A list of strings containing any ambiguities or warnings (list of strings)
    
    Do not include any markdown formatting or explanation outside the JSON.
    """
    
    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that outputs JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1, # Low temperature for more deterministic results
        )
        
        content = response.choices[0].message.content.strip()
        
        # Clean up potential markdown code blocks if the model ignores instructions
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
            
        data = json.loads(content)
        
        hs_code = data.get("hs_code", "")
        confidence = calculate_confidence(hs_code)
        
        return HSLookupResponse(
            hs_code=hs_code,
            confidence=confidence,
            description=data.get("description", ""),
            warnings=data.get("warnings", [])
        )
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="Failed to parse AI response")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI Service Error: {str(e)}")

# --- Endpoints ---

@router.post("/hs-lookup", response_model=dict)
async def lookup_hs_code(payload: HSLookupRequest):
    """
    Look up an HS code for a product description using AI, with caching.
    """
    
    # 1. Check Cache
    redis_client = get_redis_client()
    cache_key = None
    
    if redis_client:
        # Create a deterministic hash of the input
        input_str = f"{payload.product_description.lower().strip()}:{payload.origin_country.lower().strip()}"
        input_hash = hashlib.md5(input_str.encode()).hexdigest()
        cache_key = f"hs:{input_hash}"
        
        cached_data = redis_client.get(cache_key)
        if cached_data:
            try:
                data = json.loads(cached_data)
                return ok(data)
            except Exception:
                pass # Cache corrupted, proceed to fetch fresh
    
    # 2. Call AI Service
    result = await get_hs_code_from_ai(payload.product_description, payload.origin_country)
    
    # 3. Cache Result
    if redis_client and cache_key:
        try:
            # Cache for 7 days (604800 seconds)
            redis_client.setex(cache_key, 604800, json.dumps(result.model_dump()))
        except Exception:
            pass # Cache failure shouldn't fail the request
            
    return ok(result.model_dump())


@router.get("/hs-codes/search")
async def hs_search(q: str = Query(""), jurisdiction: str = Query("UK"), limit: int = Query(10)):
    return ok({"results": [{"code": "8471300000", "description": "Portable automatic data processing machines", "level": 10, "supplementary_unit": "p/st"}], "total": 1})


@router.get("/hs-codes/{code}")
async def hs_detail(code: str, jurisdiction: str = Query("UK")):
    return ok({"code": code, "description": "...", "measures": [{"measure_type": "AD_VALOREM", "rate_ad_valorem": 0.0, "country_of_origin": None, "valid_from": "2024-01-01", "valid_to": None}], "supplementary_unit": "p/st"})


def _digits(hs_code: str) -> str:
    return "".join(ch for ch in hs_code if ch.isdigit())


def _destination_market(dest: str) -> str | None:
    d = dest.upper()
    if d in ("GB", "UK"):
        return "GB"
    if is_eu(d):
        return "EU"
    return None


def _origin_groups(origin: str) -> set[str]:
    iso2 = origin.upper().strip()
    groups = {iso2}
    if is_eu(iso2):
        groups.add("EU")
        groups.add("1011")
    return groups


async def _pick_best_duty(
    db: AsyncSession,
    *,
    hs_code: str,
    market: str,
    origin: str,
) -> TariffMeasure | None:
    today = date.today()
    groups = _origin_groups(origin)
    res = await db.execute(
        select(TariffMeasure)
        .where(
            TariffMeasure.hs_code == hs_code,
            TariffMeasure.jurisdiction == market,
            TariffMeasure.valid_from <= today,
            sa.or_(TariffMeasure.valid_to.is_(None), TariffMeasure.valid_to >= today),
        )
        .order_by(TariffMeasure.ingested_at.desc())
    )
    measures = res.scalars().all()
    if not measures:
        return None

    def matches_origin(m: TariffMeasure) -> bool:
        if m.country_of_origin is None:
            return True
        return str(m.country_of_origin).upper() in groups

    preferential = [
        m for m in measures
        if m.measure_type == "PREFERENTIAL" and matches_origin(m) and m.rate_ad_valorem is not None
    ]
    if preferential:
        return sorted(preferential, key=lambda m: (m.rate_ad_valorem, m.ingested_at), reverse=False)[0]

    additional = [
        m for m in measures
        if m.measure_type in ("ANTI_DUMPING", "COUNTERVAILING", "ADDITIONAL") and matches_origin(m)
        and m.rate_ad_valorem is not None
    ]
    if additional:
        return sorted(additional, key=lambda m: (m.rate_ad_valorem, m.ingested_at), reverse=True)[0]

    mfn = [
        m for m in measures
        if m.measure_type == "MFN" and (m.country_of_origin is None) and m.rate_ad_valorem is not None
    ]
    if mfn:
        return sorted(mfn, key=lambda m: m.ingested_at, reverse=True)[0]
    return None


async def _pick_vat(
    db: AsyncSession,
    *,
    hs_code: str,
    market: str,
    country_code: str,
) -> VATRate | None:
    today = date.today()
    cc = country_code.upper()

    prefix_stmt = (
        select(VATRate)
        .where(
            VATRate.country_code == cc,
            VATRate.jurisdiction == market,
            VATRate.hs_code_prefix.is_not(None),
            sa.literal(hs_code).like(sa.func.concat(VATRate.hs_code_prefix, "%")),
            sa.or_(VATRate.valid_from.is_(None), VATRate.valid_from <= today),
            sa.or_(VATRate.valid_to.is_(None), VATRate.valid_to >= today),
        )
        .order_by(sa.func.length(VATRate.hs_code_prefix).desc(), VATRate.ingested_at.desc())
        .limit(1)
    )
    res = await db.execute(prefix_stmt)
    vat = res.scalar_one_or_none()
    if vat:
        return vat

    fallback_stmt = (
        select(VATRate)
        .where(
            VATRate.country_code == cc,
            VATRate.jurisdiction == market,
            VATRate.hs_code_prefix.is_(None),
            sa.or_(VATRate.valid_from.is_(None), VATRate.valid_from <= today),
            sa.or_(VATRate.valid_to.is_(None), VATRate.valid_to >= today),
        )
        .order_by(sa.case((VATRate.rate_type == "standard", 0), else_=1), VATRate.ingested_at.desc())
        .limit(1)
    )
    res = await db.execute(fallback_stmt)
    return res.scalar_one_or_none()


@router.get("/lookup")
async def tariff_lookup(
    hs_code: str = Query(...),
    origin: str = Query(...),
    destination: str = Query(...),
    db: AsyncSession = Depends(get_session),
):
    hs = _digits(hs_code)
    if len(hs) < 6:
        raise HTTPException(status_code=422, detail="hs_code must be at least 6 digits")

    origin_cc = origin.upper()
    dest_cc = destination.upper()
    market = _destination_market(dest_cc)
    if not market:
        raise HTTPException(status_code=422, detail="destination must be an EU country or GB/UK")

    duty = await _pick_best_duty(db, hs_code=hs, market=market, origin=origin_cc)
    vat = await _pick_vat(db, hs_code=hs, market=market, country_code=dest_cc)

    payload = {
        "hs_code": hs,
        "origin_country": origin_cc,
        "destination_country": dest_cc,
        "destination_market": market,
        "duty": None,
        "vat": None,
        "calculated": {
            "duty_on_goods_value_pct": float(duty.rate_ad_valorem) if duty and duty.rate_ad_valorem is not None else None,
            "vat_applies_to": "goods_value + duty",
            "note": "VAT is assessed on CIF value + customs duty",
        },
        "data_freshness": {
            "duty_last_updated": duty.ingested_at.date().isoformat() if duty else None,
            "vat_last_updated": vat.ingested_at.date().isoformat() if vat else None,
        },
    }

    if duty:
        payload["duty"] = {
            "rate_type": duty.measure_type,
            "duty_rate": float(duty.rate_ad_valorem) if duty.rate_ad_valorem is not None else None,
            "trade_agreement": duty.preferential_agreement,
            "source": duty.source_dataset,
        }

    if vat:
        payload["vat"] = {
            "country_code": vat.country_code,
            "rate_type": vat.rate_type,
            "vat_rate": float(vat.vat_rate),
            "source": vat.source,
        }

    return ok(payload)
