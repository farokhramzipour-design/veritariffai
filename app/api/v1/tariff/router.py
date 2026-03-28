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

from app.infrastructure.database.models import CertificateCode, DutyUnit, HSCode, Origin, TariffMeasure, VATRate
from app.infrastructure.database.session import get_session
from app.infrastructure.ingestion.origins import ensure_origin
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


def _normalize_origin_iso2(code: str) -> str:
    c = (code or "").strip().upper()
    if c == "UK":
        return "GB"
    return c


def _origin_groups(origin: str) -> set[str]:
    iso2 = origin.upper().strip()
    groups = {iso2}
    if is_eu(iso2):
        groups.add("EU")
        groups.add("1011")
    return groups


async def _resolve_origin_codes_for_country(db: AsyncSession, iso2: str) -> list[str]:
    cc = iso2.upper().strip()
    codes: list[str] = []
    if cc:
        codes.append(cc)
        if is_eu(cc):
            codes.append("EU")

    res = await db.execute(
        select(Origin.origin_code)
        .where(
            Origin.is_group.is_(True),
            Origin.member_iso2_codes.is_not(None),
            Origin.member_iso2_codes.contains([cc]),
        )
    )
    codes.extend([c for c in res.scalars().all() if isinstance(c, str)])

    codes.append("1011")
    seen: set[str] = set()
    out: list[str] = []
    for c in codes:
        c = (c or "").strip().upper()
        if not c or c in seen:
            continue
        seen.add(c)
        out.append(c)
    return out


def _origin_specificity(origin_code: str | None) -> int:
    code = (origin_code or "").strip().upper()
    if not code or code == "1011":
        return 5
    if len(code) == 2 and code.isalpha():
        return 1
    if len(code) == 4 and code.isdigit():
        if code.startswith("4"):
            return 3
        if code.startswith("5"):
            return 4
        return 2
    return 6


def _hs_candidates(hs_code: str) -> list[str]:
    hs = _digits(hs_code)
    candidates: list[str] = []
    for n in (10, 8, 6, 4, 2):
        if len(hs) >= n:
            cand = hs[:n]
            if cand and cand not in candidates:
                candidates.append(cand)
    return candidates


def _measure_has_any_duty(m: TariffMeasure) -> bool:
    if m.rate_ad_valorem is not None or m.rate_specific_amount is not None:
        return True
    if isinstance(m.measure_condition, dict):
        duty_meta = m.measure_condition.get("duty")
        if isinstance(duty_meta, dict):
            if duty_meta.get("is_nihil"):
                return True
            if duty_meta.get("siv_bands") or duty_meta.get("has_entry_price"):
                return True
            if duty_meta.get("duty_unit") or duty_meta.get("duty_expression_code"):
                return True
            raw_expression = duty_meta.get("raw_expression")
            if isinstance(raw_expression, str) and raw_expression.strip():
                return True
    return False


def _measure_origin_code(m: TariffMeasure) -> str:
    code = (m.country_of_origin or "1011").strip().upper()
    return code or "1011"


def _measure_duty_meta(m: TariffMeasure) -> dict | None:
    if not isinstance(m.measure_condition, dict):
        return None
    duty_meta = m.measure_condition.get("duty")
    if not isinstance(duty_meta, dict):
        return None
    return duty_meta


def _measure_is_nihil(m: TariffMeasure) -> bool:
    duty_meta = _measure_duty_meta(m)
    return bool(duty_meta.get("is_nihil")) if duty_meta else False


def _measure_duty_rate_pct(m: TariffMeasure) -> float | None:
    if m.rate_ad_valorem is not None:
        return float(m.rate_ad_valorem)
    if _measure_is_nihil(m):
        return 0.0
    return None


def _rate_basis_for_measure(*, measure_type: str | None, origin_code: str | None) -> str | None:
    oc = (origin_code or "").strip().upper()
    mt = (measure_type or "").strip().upper()
    if not oc or not mt:
        return None
    if oc == "1011":
        return "MFN"
    if mt == "PREFERENTIAL":
        return "bilateral_preference" if (len(oc) == 2 and oc.isalpha()) else "group_preference"
    if mt in ("ANTI_DUMPING", "COUNTERVAILING"):
        return "anti_dumping"
    if mt == "ADDITIONAL":
        return "additional"
    if mt == "SAFEGUARD":
        return "safeguard"
    return mt.lower()


async def _pick_best_duty(
    db: AsyncSession,
    *,
    hs_code: str,
    market: str,
    origin: str,
) -> TariffMeasure | None:
    today = date.today()
    resolved_codes = await _resolve_origin_codes_for_country(db, origin)
    candidates = _hs_candidates(hs_code)
    res = await db.execute(
        select(TariffMeasure)
        .where(
            TariffMeasure.hs_code.in_(candidates),
            TariffMeasure.jurisdiction == market,
            TariffMeasure.valid_from <= today,
            sa.or_(TariffMeasure.valid_to.is_(None), TariffMeasure.valid_to >= today),
        )
        .order_by(sa.func.length(TariffMeasure.hs_code).desc(), TariffMeasure.ingested_at.desc())
    )
    measures = res.scalars().all()
    if not measures:
        return None

    def matches_origin(m: TariffMeasure) -> bool:
        code = (m.country_of_origin or "1011").strip().upper()
        return code in resolved_codes

    preferential = [
        m for m in measures
        if m.measure_type == "PREFERENTIAL" and matches_origin(m) and _measure_has_any_duty(m)
    ]
    if preferential:
        pref_av = [m for m in preferential if m.rate_ad_valorem is not None]
        if pref_av:
            return sorted(
                pref_av,
                key=lambda m: (_origin_specificity(m.country_of_origin), m.rate_ad_valorem, m.ingested_at),
                reverse=False,
            )[0]
        return sorted(preferential, key=lambda m: (_origin_specificity(m.country_of_origin), m.ingested_at), reverse=False)[0]

    additional = [
        m for m in measures
        if m.measure_type in ("ANTI_DUMPING", "COUNTERVAILING", "ADDITIONAL") and matches_origin(m)
        and _measure_has_any_duty(m)
    ]
    if additional:
        add_av = [m for m in additional if m.rate_ad_valorem is not None]
        if add_av:
            return sorted(add_av, key=lambda m: (m.rate_ad_valorem, m.ingested_at), reverse=True)[0]
        return sorted(additional, key=lambda m: m.ingested_at, reverse=True)[0]

    mfn = [
        m for m in measures
        if m.measure_type == "MFN"
        and ((m.country_of_origin or "1011").strip().upper() == "1011")
        and _measure_has_any_duty(m)
    ]
    if mfn:
        return sorted(mfn, key=lambda m: m.ingested_at, reverse=True)[0]
    return None


async def _other_measures(
    db: AsyncSession,
    *,
    hs_code: str,
    market: str,
    origin: str,
    destination_country: str,
    limit: int = 30,
) -> list[dict]:
    today = date.today()
    resolved_codes = await _resolve_origin_codes_for_country(db, origin)
    candidates = _hs_candidates(hs_code)
    types = ("TARIFF_QUOTA", "SAFEGUARD", "IMPORT_CONTROL")

    res = await db.execute(
        select(TariffMeasure)
        .where(
            TariffMeasure.hs_code.in_(candidates),
            TariffMeasure.jurisdiction == market,
            TariffMeasure.measure_type.in_(types),
            TariffMeasure.valid_from <= today,
            sa.or_(TariffMeasure.valid_to.is_(None), TariffMeasure.valid_to >= today),
        )
        .order_by(sa.func.length(TariffMeasure.hs_code).desc(), TariffMeasure.ingested_at.desc())
        .limit(limit)
    )
    measures = res.scalars().all()

    def matches_origin(m: TariffMeasure) -> bool:
        code = (m.country_of_origin or "1011").strip().upper()
        return code in resolved_codes

    out: list[dict] = []
    for m in measures:
        if not matches_origin(m):
            continue
        raw = m.raw_json if isinstance(m.raw_json, dict) else {}
        out.append(
            {
                "hs_code": m.hs_code,
                "destination_market": market,
                "destination_country": destination_country.upper(),
                "origin_country": m.country_of_origin,
                "measure_type": m.measure_type,
                "rate_ad_valorem": float(m.rate_ad_valorem) if m.rate_ad_valorem is not None else None,
                "rate_specific_amount": float(m.rate_specific_amount) if m.rate_specific_amount is not None else None,
                "rate_specific_unit": m.rate_specific_unit,
                "valid_from": m.valid_from.isoformat() if m.valid_from else None,
                "valid_to": m.valid_to.isoformat() if m.valid_to else None,
                "source": m.source_dataset,
                "details": {
                    "order_no": raw.get("Order No.") or raw.get("Order No") or raw.get("Order number"),
                    "add_code": raw.get("Add code") or raw.get("Add code."),
                    "legal_base": raw.get("Legal base") or raw.get("Legal basis"),
                    "duty_text": raw.get("Duty"),
                    "measure_type_text": raw.get("Measure type"),
                    "measure_type_code": raw.get("Meas. type code") or raw.get("Meas type code"),
                    "origin_text": raw.get("Origin"),
                    "origin_code": raw.get("Origin code"),
                },
            }
        )
    return out


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


def _split_currency(unit: str | None) -> str | None:
    if not unit:
        return None
    u = unit.strip().upper()
    if len(u) >= 3 and u[:3].isalpha():
        return u[:3]
    return None


async def _certificate_descriptions(db: AsyncSession, codes: list[str]) -> dict[str, str]:
    uniq = sorted({c for c in codes if isinstance(c, str) and c})
    if not uniq:
        return {}
    res = await db.execute(select(CertificateCode).where(CertificateCode.code.in_(uniq)))
    rows = res.scalars().all()
    m = {r.code: r.description for r in rows}
    for c in uniq:
        if c not in m:
            m[c] = f"Unknown — code {c}"
    return m


def _render_duty_conditions(conditions: list[dict], cert_map: dict[str, str]) -> list[dict]:
    out: list[dict] = []
    for c in conditions:
        ctype = c.get("condition_type")
        logic = c.get("condition_logic")
        cert = c.get("certificate_code")
        expr = c.get("duty_expression_code")
        met = c.get("duty_rate_if_met")
        not_met = c.get("duty_rate_if_not_met")

        item: dict = {
            "condition_type": ctype,
            "condition_logic": logic,
            "certificate_code": cert,
            "certificate_description": cert_map.get(cert) if isinstance(cert, str) else None,
            "duty_expression_code": expr,
            "duty_rate_if_met": met,
            "duty_rate_if_not_met": not_met,
        }
        if ctype == "A" and cert and met is not None and not_met is not None:
            item["fallback_rate_type"] = "MFN"
            item["note"] = f"{met}% applies ONLY if {cert} certificate presented. Without it, fallback rate of {not_met}% applies."
        elif ctype == "Y":
            item["note"] = "This measure does NOT apply if any one of the listed certificates is presented."
        out.append(item)
    return out


@router.get("/lookup")
async def tariff_lookup(
    hs_code: str = Query(...),
    origin: str = Query(...),
    destination: str = Query(...),
    cif_price_eur_per_dtn: float | None = Query(None),
    full_report: bool = Query(False, description="Include full measure record list for this HS code"),
    db: AsyncSession = Depends(get_session),
):
    hs = _digits(hs_code)
    if len(hs) < 6:
        raise HTTPException(status_code=422, detail="hs_code must be at least 6 digits")

    origin_input = origin.upper().strip()
    origin_cc = _normalize_origin_iso2(origin_input)
    if not (len(origin_cc) == 2 and origin_cc.isalpha()):
        raise HTTPException(status_code=422, detail="origin must be a 2-letter ISO country code")
    dest_cc = destination.upper()
    market = _destination_market(dest_cc)
    if not market:
        raise HTTPException(status_code=422, detail="destination must be an EU country or GB/UK")

    await ensure_origin(db, origin_code=origin_cc, origin_name=origin_cc)
    await ensure_origin(db, origin_code="1011", origin_name="ERGA OMNES")
    await db.commit()

    res = await db.execute(select(Origin).where(Origin.origin_code == origin_cc).limit(1))
    origin_row = res.scalar_one_or_none()

    resolved_origin_codes = await _resolve_origin_codes_for_country(db, origin_cc)
    res = await db.execute(select(Origin).where(Origin.origin_code.in_(resolved_origin_codes)))
    origin_rows = res.scalars().all()
    origin_map: dict[str, Origin] = {o.origin_code: o for o in origin_rows}
    origin_resolution: list[dict] = []
    for code in resolved_origin_codes:
        row = origin_map.get(code)
        origin_resolution.append(
            {
                "origin_code": code,
                "exists": row is not None,
                "origin_name": row.origin_name if row else f"Unknown — code {code}",
                "origin_code_type": row.origin_code_type if row else None,
                "is_group": bool(row.is_group) if row else None,
                "is_erga_omnes": bool(row.is_erga_omnes) if row else (code == "1011"),
                "group_category": row.group_category if row else None,
            }
        )

    duty = await _pick_best_duty(db, hs_code=hs, market=market, origin=origin_cc)
    vat = await _pick_vat(db, hs_code=hs, market=market, country_code=dest_cc)
    other_measures = await _other_measures(
        db,
        hs_code=hs,
        market=market,
        origin=origin_cc,
        destination_country=dest_cc,
        limit=30,
    )
    tariff_quotas = [m for m in other_measures if isinstance(m, dict) and m.get("measure_type") == "TARIFF_QUOTA"]
    non_tariff_measures = [
        m for m in other_measures
        if isinstance(m, dict) and m.get("measure_type") in ("SAFEGUARD", "IMPORT_CONTROL")
    ]

    res = await db.execute(select(HSCode.description).where(HSCode.code == hs).limit(1))
    description = res.scalar_one_or_none() or f"HS {hs}"
    res = await db.execute(
        select(HSCode.supplementary_unit)
        .where(HSCode.code == hs, HSCode.jurisdiction == market)
        .limit(1)
    )
    supplementary_unit = res.scalar_one_or_none()
    supplementary_units = []
    if supplementary_unit:
        supplementary_units.append(
            {
                "hs_code": hs,
                "market": market,
                "unit_code": supplementary_unit,
                "unit_description": None,
                "declaration_type": "supplementary unit",
            }
        )

    duty_amount = float(duty.rate_specific_amount) if duty and duty.rate_specific_amount is not None else None
    duty_currency = _split_currency(duty.rate_specific_unit) if duty and duty.rate_specific_unit else None
    duty_unit = None
    duty_unit_description = None
    if duty and duty.rate_specific_unit and "/" in duty.rate_specific_unit:
        duty_unit = duty.rate_specific_unit.split("/", 1)[1].strip().upper() or None
    if duty_unit:
        res = await db.execute(select(DutyUnit.description).where(DutyUnit.code == duty_unit).limit(1))
        duty_unit_description = res.scalar_one_or_none()

    duty_human_readable = None
    duty_meta = None
    if duty and isinstance(duty.measure_condition, dict):
        duty_meta = duty.measure_condition.get("duty") if isinstance(duty.measure_condition.get("duty"), dict) else None
    if duty_meta and isinstance(duty_meta.get("human_readable"), str):
        duty_human_readable = duty_meta.get("human_readable")

    def _meta_float(key: str) -> float | None:
        if not duty_meta or not isinstance(duty_meta, dict):
            return None
        v = duty_meta.get(key)
        if v is None:
            return None
        try:
            return float(v)
        except Exception:
            try:
                return float(str(v))
            except Exception:
                return None

    if duty_meta and not duty_unit and isinstance(duty_meta.get("duty_unit"), str):
        duty_unit = str(duty_meta.get("duty_unit")).upper().strip() or None
    duty_unit_secondary = None
    if duty_meta and isinstance(duty_meta.get("duty_unit_secondary"), str):
        duty_unit_secondary = str(duty_meta.get("duty_unit_secondary")).upper().strip() or None

    duty_amount_secondary = _meta_float("duty_amount_secondary")
    _min_meta = _meta_float("duty_min_amount")
    _max_meta = _meta_float("duty_max_amount")
    duty_min_amount = _min_meta if _min_meta is not None else (float(duty.rate_minimum) if duty and duty.rate_minimum is not None else None)
    duty_max_amount = _max_meta if _max_meta is not None else (float(duty.rate_maximum) if duty and duty.rate_maximum is not None else None)
    duty_min_rate = _meta_float("duty_min_rate")
    duty_max_rate = _meta_float("duty_max_rate")
    duty_max_total_rate = _meta_float("duty_max_total_rate")
    has_entry_price = bool(duty_meta.get("has_entry_price")) if duty_meta else False
    entry_price_type = duty_meta.get("entry_price_type") if duty_meta else None
    is_nihil = bool(duty_meta.get("is_nihil")) if duty_meta else False
    is_alcohol_duty = bool(duty_meta.get("is_alcohol_duty")) if duty_meta else False
    anti_dumping_specific = bool(duty_meta.get("anti_dumping_specific")) if duty_meta else False
    requires_import_licence = bool(duty_meta.get("requires_import_licence")) if duty_meta else False
    siv_bands = duty_meta.get("siv_bands") if duty_meta and isinstance(duty_meta.get("siv_bands"), list) else None

    effective_duty_rate = None
    effective_duty_amount = None
    effective_duty_unit = None
    variable_rate_evaluated = False
    if isinstance(cif_price_eur_per_dtn, (int, float)) and siv_bands:
        bands: list[dict] = [b for b in siv_bands if isinstance(b, dict)]
        bands_sorted = sorted(
            bands,
            key=lambda b: float(b.get("threshold") or 0.0),
            reverse=True,
        )
        chosen = None
        for b in bands_sorted:
            try:
                th = float(b.get("threshold") or 0.0)
            except Exception:
                th = 0.0
            if cif_price_eur_per_dtn >= th:
                chosen = b
                break
        if chosen is None and bands_sorted:
            chosen = bands_sorted[-1]
        if chosen is not None:
            effective_duty_rate = chosen.get("duty_rate")
            effective_duty_amount = chosen.get("duty_amount")
            effective_duty_unit = chosen.get("duty_unit")
            variable_rate_evaluated = True

    warnings: list[str] = []
    if duty is None:
        if not all_measures:
            warnings.append("No tariff measures found for this HS code in the database for this market. Run EU TARIC ingestion (or duties_import XLSX) to populate tariff_measures.")
        else:
            warnings.append("No duty record matched the resolved origin codes. Try another origin or review full_report records.")
    if siv_bands:
        warnings.append("Rate is determined by SIV price bands. Provide your declared CIF price for an indicative rate.")
    if has_entry_price:
        warnings.append("An agricultural entry price (EA) component applies. Exact amount cannot be pre-calculated — depends on declared CIF import price.")
    if duty_min_amount is not None and duty_unit:
        warnings.append(f"Minimum EUR {duty_min_amount} per {duty_unit} applies — rate cannot be less than this.")
    if duty_max_amount is not None and duty_unit:
        warnings.append(f"Maximum EUR {duty_max_amount} per {duty_unit} applies — rate cannot be more than this.")
    if anti_dumping_specific and duty_amount is not None and duty_unit:
        warnings.append(f"An anti-dumping specific duty (EUR {duty_amount} per {duty_unit}) applies in addition to the ad valorem rate.")
    if is_alcohol_duty:
        warnings.append("Duty includes an alcohol-strength component — amount varies with actual % vol.")
    if requires_import_licence:
        warnings.append("An import licence is required for this rate to apply.")
    if is_nihil:
        warnings.append("No duty is payable (explicitly nil by regulation).")
    if duty_meta and duty_meta.get("duty_expression_code") in ("03", "04"):
        warnings.append("Duty is calculated as a combination of ad valorem percentage AND a specific per-unit amount — both components apply simultaneously.")

    duty_conditions: list[dict] = []
    cert_codes: list[str] = []
    if duty and isinstance(duty.measure_condition, dict):
        conds = duty.measure_condition.get("conditions")
        if isinstance(conds, list):
            for c in conds:
                if isinstance(c, dict):
                    cc = c.get("certificate_code")
                    if isinstance(cc, str) and cc:
                        cert_codes.append(cc)
            cert_map = await _certificate_descriptions(db, cert_codes)
            duty_conditions = _render_duty_conditions([c for c in conds if isinstance(c, dict)], cert_map)
            if any(isinstance(c, dict) and c.get("certificate_code") == "N-990" for c in conds):
                warnings.append("This rate requires a valid Tariff Rate Quota licence (N-990). Check quota balance before shipping.")

    duty_origin_code = (duty.country_of_origin or "1011").strip().upper() if duty else None
    duty_origin_name = None
    if duty_origin_code:
        res = await db.execute(select(Origin.origin_name).where(Origin.origin_code == duty_origin_code).limit(1))
        duty_origin_name = res.scalar_one_or_none()

    rate_basis = _rate_basis_for_measure(measure_type=duty.measure_type if duty else None, origin_code=duty_origin_code)

    today = date.today()
    candidates = _hs_candidates(hs)
    res = await db.execute(
        select(TariffMeasure)
        .where(
            TariffMeasure.hs_code.in_(candidates),
            TariffMeasure.jurisdiction == market,
            TariffMeasure.valid_from <= today,
            sa.or_(TariffMeasure.valid_to.is_(None), TariffMeasure.valid_to >= today),
        )
        .order_by(sa.func.length(TariffMeasure.hs_code).desc(), TariffMeasure.ingested_at.desc())
    )
    all_measures = res.scalars().all()
    measures_for_origin = [
        m
        for m in all_measures
        if _measure_origin_code(m) in resolved_origin_codes and _measure_has_any_duty(m)
    ]

    cert_codes_all: list[str] = []
    for m in measures_for_origin:
        if isinstance(m.measure_condition, dict):
            conds = m.measure_condition.get("conditions")
            if isinstance(conds, list):
                for c in conds:
                    if isinstance(c, dict):
                        cc = c.get("certificate_code")
                        if isinstance(cc, str) and cc:
                            cert_codes_all.append(cc)
    cert_map_all = await _certificate_descriptions(db, cert_codes_all)

    def _best_for_origin(code: str) -> TariffMeasure | None:
        pool = [m for m in measures_for_origin if _measure_origin_code(m) == code]
        if not pool and code == "1011":
            pool = [m for m in all_measures if (m.country_of_origin is None) and m.measure_type == "MFN" and _measure_has_any_duty(m)]
        if not pool:
            return None
        pref = [m for m in pool if m.measure_type == "PREFERENTIAL"]
        if pref:
            pref_av = [m for m in pref if m.rate_ad_valorem is not None]
            if pref_av:
                return sorted(pref_av, key=lambda m: (float(m.rate_ad_valorem), m.ingested_at), reverse=False)[0]
            return sorted(pref, key=lambda m: m.ingested_at, reverse=True)[0]
        mfn_pool = [m for m in pool if m.measure_type == "MFN"]
        if mfn_pool:
            return sorted(mfn_pool, key=lambda m: m.ingested_at, reverse=True)[0]
        return sorted(pool, key=lambda m: m.ingested_at, reverse=True)[0]

    rates_by_origin: list[dict] = []
    for code in resolved_origin_codes:
        m = _best_for_origin(code)
        row = origin_map.get(code)
        origin_name_val = row.origin_name if row else ("ERGA OMNES" if code == "1011" else f"Unknown — code {code}")
        origin_code_type_val = row.origin_code_type if row else None
        duty_meta_entry = _measure_duty_meta(m) if m else None
        human = duty_meta_entry.get("human_readable") if duty_meta_entry and isinstance(duty_meta_entry.get("human_readable"), str) else None
        raw_expr = duty_meta_entry.get("raw_expression") if duty_meta_entry and isinstance(duty_meta_entry.get("raw_expression"), str) else None
        conds_rendered: list[dict] = []
        if m and isinstance(m.measure_condition, dict):
            conds = m.measure_condition.get("conditions")
            if isinstance(conds, list):
                conds_rendered = _render_duty_conditions([c for c in conds if isinstance(c, dict)], cert_map_all)
        rates_by_origin.append(
            {
                "origin_code": code,
                "origin_name": origin_name_val,
                "origin_code_type": origin_code_type_val,
                "rate_basis": _rate_basis_for_measure(measure_type=m.measure_type if m else None, origin_code=code),
                "rate_type": m.measure_type if m else None,
                "duty_rate": _measure_duty_rate_pct(m) if m else None,
                "duty_amount": float(m.rate_specific_amount) if m and m.rate_specific_amount is not None else None,
                "duty_unit": m.rate_specific_unit if m else None,
                "valid_from": m.valid_from.isoformat() if m else None,
                "valid_to": m.valid_to.isoformat() if m and m.valid_to else None,
                "source": m.source_dataset if m else None,
                "duty_expression": raw_expr,
                "human_readable": human,
                "conditions": conds_rendered,
            }
        )

    mfn_entry = next((r for r in rates_by_origin if r.get("origin_code") == "1011"), None)
    best_rate = None
    if duty and mfn_entry:
        try:
            best_val = float(duty.rate_ad_valorem) if duty.rate_ad_valorem is not None else (0.0 if is_nihil else None)
        except Exception:
            best_val = None
        mfn_val = mfn_entry.get("duty_rate")
        if isinstance(best_val, (int, float)) and isinstance(mfn_val, (int, float)):
            saving_vs_mfn = float(mfn_val) - float(best_val)
            saving_pct = (saving_vs_mfn / float(mfn_val) * 100.0) if float(mfn_val) > 0 else None
            best_rate = {
                "origin_code": duty_origin_code,
                "rate_basis": rate_basis,
                "duty_rate": best_val,
                "saving_vs_mfn": saving_vs_mfn,
                "saving_pct": saving_pct,
            }

    records: list[dict] = []
    if full_report:
        def _record_for_measure(m: TariffMeasure) -> dict:
            origin_code_val = _measure_origin_code(m)
            origin_row_val = origin_map.get(origin_code_val)
            origin_name_val = origin_row_val.origin_name if origin_row_val else ("ERGA OMNES" if origin_code_val == "1011" else origin_code_val)
            raw = m.raw_json if isinstance(m.raw_json, dict) else {}
            duty_meta_entry = _measure_duty_meta(m)
            duty_expr = duty_meta_entry.get("raw_expression") if duty_meta_entry and isinstance(duty_meta_entry.get("raw_expression"), str) else None
            return {
                "hs_code": m.hs_code,
                "market": market,
                "origin_code": origin_code_val,
                "origin_name": origin_name_val,
                "origin_code_type": origin_row_val.origin_code_type if origin_row_val else None,
                "measure_type": m.measure_type,
                "rate_basis": _rate_basis_for_measure(measure_type=m.measure_type, origin_code=origin_code_val),
                "duty_rate": _measure_duty_rate_pct(m),
                "duty_amount": float(m.rate_specific_amount) if m.rate_specific_amount is not None else None,
                "rate_specific_unit": m.rate_specific_unit,
                "valid_from": m.valid_from.isoformat() if m.valid_from else None,
                "valid_to": m.valid_to.isoformat() if m.valid_to else None,
                "source": m.source_dataset,
                "ingested_at": m.ingested_at.isoformat() if m.ingested_at else None,
                "details": {
                    "measure_type_text": raw.get("Measure type") or raw.get("measure_type_text"),
                    "measure_type_code": raw.get("Meas. type code") or raw.get("Meas type code") or raw.get("measure_type_id"),
                    "origin_text": raw.get("Origin") or raw.get("origin"),
                    "origin_code_raw": raw.get("Origin code") or raw.get("geographical_area_id"),
                    "legal_base": raw.get("Legal base") or raw.get("Legal basis") or raw.get("legal_base"),
                    "regulation": raw.get("Regulation") or raw.get("regulation"),
                    "additional_code": raw.get("Add code") or raw.get("Add code.") or raw.get("add_code"),
                    "order_no": raw.get("Order No.") or raw.get("Order No") or raw.get("Order number"),
                    "duty_text": raw.get("Duty") or duty_expr,
                },
            }

        records = [_record_for_measure(m) for m in all_measures]
        records = sorted(
            records,
            key=lambda r: (
                len(str(r.get("hs_code") or "")),
                _origin_specificity(str(r.get("origin_code") or "")),
                str(r.get("measure_type") or ""),
                r.get("ingested_at") or "",
            ),
            reverse=True,
        )[:300]

    payload = {
        "hs_code": hs,
        "description": description,
        "origin_country": origin_cc,
        "origin_input": origin_input,
        "destination_country": dest_cc,
        "destination_market": market,
        "origin": {
            "origin_code": origin_cc,
            "origin_name": origin_row.origin_name if origin_row else None,
            "origin_code_type": origin_row.origin_code_type if origin_row else "country",
            "iso2": origin_row.iso2 if origin_row else origin_cc,
            "iso3": origin_row.iso3 if origin_row else None,
            "is_erga_omnes": bool(origin_row.is_erga_omnes) if origin_row else False,
            "is_group": bool(origin_row.is_group) if origin_row else False,
            "group_category": origin_row.group_category if origin_row else None,
            "exists": origin_row is not None,
        },
        "origin_resolution": origin_resolution,
        "rates_by_origin": rates_by_origin,
        "best_rate": best_rate,
        "records": records,
        "duty": {
            "rate_type": duty.measure_type if duty else None,
            "duty_rate": (
                float(duty.rate_ad_valorem)
                if duty and duty.rate_ad_valorem is not None
                else (0.0 if duty and is_nihil else None)
            ),
            "duty_amount": duty_amount,
            "currency": duty_currency,
            "duty_unit": duty_unit,
            "duty_unit_description": duty_unit_description,
            "duty_amount_secondary": duty_amount_secondary,
            "duty_unit_secondary": duty_unit_secondary,
            "duty_min_amount": duty_min_amount,
            "duty_max_amount": duty_max_amount,
            "duty_min_rate": duty_min_rate,
            "duty_max_rate": duty_max_rate,
            "duty_max_total_rate": duty_max_total_rate,
            "has_entry_price": has_entry_price,
            "entry_price_type": entry_price_type,
            "is_nihil": is_nihil,
            "is_alcohol_duty": is_alcohol_duty,
            "anti_dumping_specific": anti_dumping_specific,
            "siv_bands": siv_bands,
            "trade_agreement": duty.preferential_agreement if duty else None,
            "financial_charge": True if duty else None,
            "source": duty.source_dataset if duty else None,
            "origin_code": duty_origin_code,
            "origin_name": duty_origin_name,
            "rate_basis": rate_basis,
            "conditions": duty_conditions,
            "human_readable": duty_human_readable,
        },
        "vat": {
            "country_code": vat.country_code if vat else dest_cc,
            "rate_type": vat.rate_type if vat else None,
            "vat_rate": float(vat.vat_rate) if vat else None,
            "hs_code_prefix": vat.hs_code_prefix if vat else None,
            "source": vat.source if vat else None,
        },
        "calculated": {
            "duty_on_goods_value_pct": (
                float(duty.rate_ad_valorem)
                if duty and duty.rate_ad_valorem is not None
                else (0.0 if duty and is_nihil else None)
            ),
            "effective_duty_rate": effective_duty_rate,
            "effective_duty_amount": effective_duty_amount,
            "effective_duty_unit": effective_duty_unit,
            "variable_rate_evaluated": variable_rate_evaluated,
            "entry_price_component": has_entry_price,
            "vat_applies_to": "goods_value + duty",
            "note": "VAT is assessed on CIF value + customs duty",
            "warnings": warnings,
        },
        "data_freshness": {
            "duty_last_updated": duty.ingested_at.date().isoformat() if duty else None,
            "vat_last_updated": vat.ingested_at.date().isoformat() if vat else None,
        },
        "other_measures": other_measures,
        "tariff_quotas": tariff_quotas,
        "non_tariff_measures": non_tariff_measures,
        "supplementary_units": supplementary_units,
        "price_measures": (
            [
                {
                    "hs_code": hs,
                    "market": market,
                    "origin_country": origin_cc,
                    "has_entry_price": has_entry_price,
                    "entry_price_type": entry_price_type,
                    "siv_bands": siv_bands,
                    "human_readable": duty_human_readable,
                }
            ]
            if (has_entry_price or siv_bands)
            else []
        ),
    }

    return ok(payload)


@router.get("/quotas/{hs_code}")
async def tariff_quotas(
    hs_code: str,
    market: str = Query("EU"),
    origin: str | None = Query(None),
    db: AsyncSession = Depends(get_session),
):
    hs = _digits(hs_code)
    mkt = market.upper()
    origin_cc = origin.upper() if isinstance(origin, str) else ""
    groups = _origin_groups(origin_cc) if origin_cc else set()
    today = date.today()

    res = await db.execute(
        select(TariffMeasure)
        .where(
            TariffMeasure.jurisdiction == mkt,
            TariffMeasure.hs_code.in_(_hs_candidates(hs)),
            TariffMeasure.measure_type == "TARIFF_QUOTA",
            TariffMeasure.valid_from <= today,
            sa.or_(TariffMeasure.valid_to.is_(None), TariffMeasure.valid_to >= today),
        )
        .order_by(sa.func.length(TariffMeasure.hs_code).desc(), TariffMeasure.ingested_at.desc())
        .limit(200)
    )
    measures = res.scalars().all()
    out: list[dict] = []
    for tm in measures:
        if origin_cc and tm.country_of_origin and tm.country_of_origin.upper() not in groups:
            continue
        raw = tm.raw_json if isinstance(tm.raw_json, dict) else {}
        out.append(
            {
                "hs_code": tm.hs_code,
                "market": mkt,
                "origin_country": tm.country_of_origin,
                "quota_order_number": raw.get("Order No.") or raw.get("Order No") or raw.get("Order number"),
                "duty_rate": float(tm.rate_ad_valorem) if tm.rate_ad_valorem is not None else None,
                "duty_amount": float(tm.rate_specific_amount) if tm.rate_specific_amount is not None else None,
                "duty_unit": tm.rate_specific_unit,
                "valid_from": tm.valid_from.isoformat() if tm.valid_from else None,
                "valid_to": tm.valid_to.isoformat() if tm.valid_to else None,
                "source": tm.source_dataset,
                "raw": raw,
            }
        )
    return ok({"count": len(out), "items": out})


@router.get("/supplementary-units/{hs_code}")
async def tariff_supplementary_units(
    hs_code: str,
    market: str = Query("EU"),
    db: AsyncSession = Depends(get_session),
):
    hs = _digits(hs_code)
    mkt = market.upper()
    res = await db.execute(
        select(HSCode)
        .where(HSCode.code.in_(_hs_candidates(hs)), HSCode.jurisdiction == mkt)
        .order_by(sa.func.length(HSCode.code).desc())
        .limit(20)
    )
    rows = res.scalars().all()
    items: list[dict] = []
    for r in rows:
        if not r.supplementary_unit:
            continue
        items.append(
            {
                "hs_code": r.code,
                "market": mkt,
                "unit_code": r.supplementary_unit,
                "unit_description": None,
                "declaration_type": "supplementary unit",
                "source": "HS_CODE",
            }
        )
    return ok({"count": len(items), "items": items})


@router.get("/price-measures/{hs_code}")
async def tariff_price_measures(
    hs_code: str,
    market: str = Query("EU"),
    origin: str | None = Query(None),
    db: AsyncSession = Depends(get_session),
):
    hs = _digits(hs_code)
    mkt = market.upper()
    origin_cc = origin.upper() if isinstance(origin, str) else ""
    groups = _origin_groups(origin_cc) if origin_cc else set()
    today = date.today()

    res = await db.execute(
        select(TariffMeasure)
        .where(
            TariffMeasure.jurisdiction == mkt,
            TariffMeasure.hs_code.in_(_hs_candidates(hs)),
            TariffMeasure.valid_from <= today,
            sa.or_(TariffMeasure.valid_to.is_(None), TariffMeasure.valid_to >= today),
        )
        .order_by(sa.func.length(TariffMeasure.hs_code).desc(), TariffMeasure.ingested_at.desc())
        .limit(300)
    )
    measures = res.scalars().all()
    out: list[dict] = []
    for tm in measures:
        if origin_cc and tm.country_of_origin and tm.country_of_origin.upper() not in groups:
            continue
        duty_meta = None
        if isinstance(tm.measure_condition, dict) and isinstance(tm.measure_condition.get("duty"), dict):
            duty_meta = tm.measure_condition.get("duty")
        if not duty_meta:
            continue
        has_ep = bool(duty_meta.get("has_entry_price"))
        has_siv = isinstance(duty_meta.get("siv_bands"), list) and bool(duty_meta.get("siv_bands"))
        if not (has_ep or has_siv):
            continue
        out.append(
            {
                "hs_code": tm.hs_code,
                "market": mkt,
                "origin_country": tm.country_of_origin,
                "measure_type": tm.measure_type,
                "has_entry_price": has_ep,
                "entry_price_type": duty_meta.get("entry_price_type"),
                "siv_bands": duty_meta.get("siv_bands") if has_siv else None,
                "human_readable": duty_meta.get("human_readable"),
                "valid_from": tm.valid_from.isoformat() if tm.valid_from else None,
                "valid_to": tm.valid_to.isoformat() if tm.valid_to else None,
                "source": tm.source_dataset,
            }
        )
    return ok({"count": len(out), "items": out})


@router.get("/variable-rate/{hs_code}")
async def tariff_variable_rate(
    hs_code: str,
    market: str = Query("EU"),
    origin: str = Query("CN"),
    cif_price_eur_per_dtn: float | None = Query(None),
    db: AsyncSession = Depends(get_session),
):
    hs = _digits(hs_code)
    duty = await _pick_best_duty(db, hs_code=hs, market=market.upper(), origin=origin.upper())
    duty_meta = None
    if duty and isinstance(duty.measure_condition, dict) and isinstance(duty.measure_condition.get("duty"), dict):
        duty_meta = duty.measure_condition.get("duty")
    siv_bands = duty_meta.get("siv_bands") if duty_meta and isinstance(duty_meta.get("siv_bands"), list) else None
    evaluated = None
    if isinstance(cif_price_eur_per_dtn, (int, float)) and siv_bands:
        bands: list[dict] = [b for b in siv_bands if isinstance(b, dict)]
        bands_sorted = sorted(bands, key=lambda b: float(b.get("threshold") or 0.0), reverse=True)
        chosen = None
        for b in bands_sorted:
            try:
                th = float(b.get("threshold") or 0.0)
            except Exception:
                th = 0.0
            if cif_price_eur_per_dtn >= th:
                chosen = b
                break
        if chosen is None and bands_sorted:
            chosen = bands_sorted[-1]
        evaluated = chosen
    return ok(
        {
            "hs_code": hs,
            "market": market.upper(),
            "origin": origin.upper(),
            "measure_found": True if duty else False,
            "siv_bands": siv_bands,
            "cif_price_eur_per_dtn": cif_price_eur_per_dtn,
            "evaluated_band": evaluated,
        }
    )


@router.get("/certificates")
async def tariff_certificates(db: AsyncSession = Depends(get_session)):
    res = await db.execute(select(CertificateCode).order_by(CertificateCode.code.asc()))
    rows = res.scalars().all()
    return ok([{"code": r.code, "description": r.description, "category": r.category} for r in rows])


@router.get("/conditions/{hs_code}")
async def tariff_conditions(
    hs_code: str,
    market: str = Query("EU"),
    db: AsyncSession = Depends(get_session),
):
    hs = _digits(hs_code)
    mkt = market.upper()
    res = await db.execute(
        select(TariffMeasure)
        .where(TariffMeasure.jurisdiction == mkt, TariffMeasure.hs_code.in_(_hs_candidates(hs)))
        .order_by(sa.func.length(TariffMeasure.hs_code).desc(), TariffMeasure.ingested_at.desc())
        .limit(200)
    )
    measures = res.scalars().all()
    items: list[dict] = []
    for tm in measures:
        conds = None
        if isinstance(tm.measure_condition, dict) and isinstance(tm.measure_condition.get("conditions"), list):
            conds = tm.measure_condition.get("conditions")
        items.append(
            {
                "hs_code": tm.hs_code,
                "market": tm.jurisdiction,
                "measure_type": tm.measure_type,
                "origin_country": tm.country_of_origin,
                "source": tm.source_dataset,
                "conditions": conds or [],
            }
        )
    return ok({"count": len(items), "items": items})


@router.get("/ntm/{hs_code}")
async def tariff_ntm(
    hs_code: str,
    market: str = Query("EU"),
    origin: str | None = Query(None),
    db: AsyncSession = Depends(get_session),
):
    hs = _digits(hs_code)
    mkt = market.upper()
    origin_cc = origin.upper() if isinstance(origin, str) else ""
    groups = _origin_groups(origin_cc) if origin_cc else set()
    res = await db.execute(
        select(TariffMeasure)
        .where(
            TariffMeasure.jurisdiction == mkt,
            TariffMeasure.hs_code.in_(_hs_candidates(hs)),
            TariffMeasure.measure_type.in_(("TARIFF_QUOTA", "SAFEGUARD", "IMPORT_CONTROL")),
        )
        .order_by(sa.func.length(TariffMeasure.hs_code).desc(), TariffMeasure.ingested_at.desc())
        .limit(200)
    )
    measures = res.scalars().all()
    out: list[dict] = []
    for tm in measures:
        if origin_cc and tm.country_of_origin and tm.country_of_origin.upper() not in groups:
            continue
        raw = tm.raw_json if isinstance(tm.raw_json, dict) else {}
        conds = []
        if isinstance(tm.measure_condition, dict) and isinstance(tm.measure_condition.get("conditions"), list):
            conds = [c for c in tm.measure_condition.get("conditions") if isinstance(c, dict)]
        certs = [c.get("certificate_code") for c in conds if isinstance(c.get("certificate_code"), str)]
        cert_map = await _certificate_descriptions(db, [c for c in certs if isinstance(c, str)])
        out.append(
            {
                "hs_code": tm.hs_code,
                "market": mkt,
                "origin_country": tm.country_of_origin,
                "measure_type_id": raw.get("Meas. type code"),
                "measure_type_description": raw.get("Measure type"),
                "financial_charge": False,
                "source": tm.source_dataset,
                "conditions": _render_duty_conditions(conds, cert_map) if conds else [],
            }
        )
    return ok({"count": len(out), "items": out})
