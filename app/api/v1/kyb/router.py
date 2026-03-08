from fastapi import APIRouter, HTTPException, Query
from app.config import settings
import requests

router = APIRouter()


@router.get("/uk/company/{company_number}")
def get_uk_company_snapshot(company_number: str):
    if not settings.companies_house_api_key:
        raise HTTPException(status_code=500, detail="Companies House API key not configured")
    base = settings.companies_house_base_url.rstrip("/")
    url = f"{base}/company/{company_number}"
    try:
        resp = requests.get(url, auth=(settings.companies_house_api_key, ""))
    except Exception:
        raise HTTPException(status_code=502, detail="Companies House request failed")
    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="Company not found")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Companies House error")
    data = resp.json()
    status = (data.get("company_status") or "").lower()
    if status != "active":
        raise HTTPException(status_code=400, detail="Company not active")
    snapshot = {
        "company_number": data.get("company_number"),
        "company_name": data.get("company_name"),
        "company_status": data.get("company_status"),
        "registered_office_address": data.get("registered_office_address"),
        "sic_codes": data.get("sic_codes") or [],
        "date_of_creation": data.get("date_of_creation"),
        "last_full_members_list_date": data.get("last_full_members_list_date"),
    }
    return {"ok": True, "snapshot": snapshot}


@router.get("/eu/vies/check")
def vies_check(country_code: str = Query(..., min_length=2, max_length=2), vat_number: str = Query(...)):
    result = {
        "ok": True,
        "source": "mock",
        "valid": True,
        "country_code": country_code.upper(),
        "vat_number": vat_number,
        "company_name": None,
        "company_address": None,
    }
    return result


@router.get("/eori/check")
def eori_check(vat_number: str = Query(...)):
    guessed = f"GB{vat_number}000"
    return {"ok": True, "guessed_eori": guessed, "active": None, "company_name": None, "company_address": None, "source": "mock"}

