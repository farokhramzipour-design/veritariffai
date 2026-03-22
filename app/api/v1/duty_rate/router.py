from __future__ import annotations
import logging
from fastapi import APIRouter, Query, HTTPException, Response
from app.core.responses import ok
from app.schemas.models import DutyRateResponse
from app.services import cache as cache_service
from app.services.uk_tariff_client import fetch_duty_rate as fetch_uk
from app.services.eu_taric_client import fetch_duty_rate as fetch_eu
from app.engines.tariff_lookup import lookup_commodity
import json

logger = logging.getLogger(__name__)


router = APIRouter()


EU_COUNTRIES = {
    "AT",
    "BE",
    "BG",
    "HR",
    "CY",
    "CZ",
    "DK",
    "EE",
    "FI",
    "FR",
    "DE",
    "GR",
    "HU",
    "IE",
    "IT",
    "LV",
    "LT",
    "LU",
    "MT",
    "NL",
    "PL",
    "PT",
    "RO",
    "SK",
    "SI",
    "ES",
    "SE",
}


def is_eu(code: str) -> bool:
    return code.upper() in EU_COUNTRIES


@router.get("/duty-rate", response_model=dict)
async def get_duty_rate(
    hs_code: str = Query(...),
    origin_country: str = Query(...),
    destination_country: str = Query(...),
    response: Response = None,
):
    hs = "".join(ch for ch in hs_code if ch.isdigit())
    if not hs or len(hs) < 4:
        raise HTTPException(status_code=422, detail="Invalid hs_code")
    origin = origin_country.upper()
    dest = destination_country.upper()
    cache_key = f"duty:{hs}:{origin}:{dest}"
    cached_blob = cache_service.get(cache_key)
    if cached_blob:
        try:
            data = json.loads(cached_blob)
            return ok(data)
        except Exception:
            pass
    source = ""
    duty_rate = 0.0
    duty_type = "UNKNOWN"
    try:
        if dest in {"GB", "UK"}:
            result = await fetch_uk(hs, origin)
            if result:
                duty_rate, duty_type = result
                source = "UK Tariff"
        elif is_eu(dest):
            result = await fetch_eu(hs, origin)
            if result:
                duty_rate, duty_type = result
                source = "TARIC"
    except Exception:
        pass
    cached = False
    if not source:
        source = "fallback"
        if response:
            response.headers["X-Warning"] = "Fallback duty rate used"
    payload = DutyRateResponse(
        duty_rate=float(duty_rate),
        duty_type=duty_type,
        source=source,
        cached=cached,
    ).model_dump()
    cache_service.setex(cache_key, cache_service.TTL_24H, json.dumps(payload))
    return ok(payload)


@router.get("/duty-rate/lookup", response_model=dict, summary="Live duty + VAT lookup from UK Trade Tariff")
async def duty_rate_lookup(
    hs_code: str = Query(..., description="HS commodity code (6–10 digits)"),
    origin_country: str = Query(..., description="ISO-2 country of origin"),
    destination_country: str = Query(..., description="ISO-2 destination country"),
):
    """
    Fetch live duty and VAT data from the UK Trade Tariff API for a given
    HS code, origin country, and destination.

    Returns:
    - **mfn_duty_pct**: standard third-country (MFN) duty %
    - **preferential_duty_pct**: preferential rate if origin has a UK trade agreement
    - **applicable_duty_pct**: the rate that actually applies (preferential if available, else MFN)
    - **duty_type**: PREFERENTIAL | MFN | UNKNOWN
    - **additional_duties**: any surcharges (e.g. Russia/Belarus +35%)
    - **total_duty_pct**: applicable + additional duties combined
    - **vat_pct**: VAT rate (typically 20% for GB imports)
    - **controls**: suspensions or end-use reliefs available
    - **warnings**: sanctions advisories, missing data notes
    """
    hs = "".join(ch for ch in hs_code if ch.isdigit())
    if len(hs) < 6:
        raise HTTPException(status_code=422, detail="hs_code must be at least 6 digits.")

    logger.info(
        "duty_rate_lookup: hs=%s origin=%s dest=%s",
        hs, origin_country.upper(), destination_country.upper(),
    )
    try:
        result = await lookup_commodity(
            hs_code=hs,
            origin_country=origin_country,
            destination_country=destination_country,
        )
    except Exception as exc:
        import traceback, sys
        tb = traceback.format_exc()
        print(f"[duty_rate_lookup ERROR] {type(exc).__name__}: {exc}\n{tb}", file=sys.stderr, flush=True)
        logger.exception("duty_rate_lookup: unhandled error hs=%s origin=%s dest=%s", hs, origin_country, destination_country)
        raise

    logger.info(
        "duty_rate_lookup: result hs=%s duty_type=%s applicable_duty=%s vat=%s warnings=%d",
        hs, result.get("duty_type"), result.get("applicable_duty_pct"),
        result.get("vat_pct"), len(result.get("warnings", [])),
    )
    return ok(result)

