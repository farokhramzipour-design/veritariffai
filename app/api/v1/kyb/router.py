from __future__ import annotations
from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, constr, conlist
import requests
from app.core.deps import require_plan
from app.domain.plan import PlanTier
from app.config import settings


router = APIRouter()


class UKCompanySnapshotRequest(BaseModel):
    company_number: constr(strip_whitespace=True, min_length=1, max_length=16)


class CompanyRegister(BaseModel):
    name: Optional[str] = None
    items: Optional[Any] = None


class CompanySnapshot(BaseModel):
    company_number: str
    company_name: Optional[str] = None
    status: Optional[str] = None
    sic_codes: list[str] = []
    registered_office_address: Optional[dict] = None
    filing_history: Optional[dict] = None
    officers: Optional[dict] = None
    persons_with_significant_control: Optional[dict] = None
    charges: Optional[dict] = None
    insolvency: Optional[dict] = None
    registers: Optional[dict] = None


def _ch_auth():
    api_key = settings.companies_house_api_key
    if not api_key:
        return None
    return (api_key, "")


def _ch_get(path: str):
    if not settings.companies_house_api_key:
        raise HTTPException(status_code=503, detail="Companies House not configured")
    base = "https://api.company-information.service.gov.uk"
    url = f"{base}{path}"
    r = requests.get(url, auth=_ch_auth(), timeout=15)
    if r.status_code == 404:
        raise HTTPException(status_code=404, detail="Company not found")
    if r.status_code >= 400:
        raise HTTPException(status_code=502, detail="Companies House error")
    return r.json()


@router.post("/uk/company-snapshot", response_model=CompanySnapshot)
async def uk_company_snapshot(
    body: UKCompanySnapshotRequest,
    user=Depends(require_plan(PlanTier.PRO)),
):
    overview = _ch_get(f"/company/{body.company_number}")
    status = (overview.get("company_status") or "").lower()
    if status != "active":
        raise HTTPException(status_code=403, detail="Company is not active")
    filing = _ch_get(f"/company/{body.company_number}/filing-history")
    officers = _ch_get(f"/company/{body.company_number}/officers")
    psc = _ch_get(f"/company/{body.company_number}/persons-with-significant-control")
    charges = _ch_get(f"/company/{body.company_number}/charges")
    insolvency = None
    try:
        insolvency = _ch_get(f"/company/{body.company_number}/insolvency")
    except HTTPException as e:
        if e.status_code != 404:
            raise
    registers = None
    try:
        registers = _ch_get(f"/company/{body.company_number}/registers")
    except HTTPException as e:
        if e.status_code != 404:
            raise
    return CompanySnapshot(
        company_number=body.company_number,
        company_name=overview.get("company_name"),
        status=overview.get("company_status"),
        sic_codes=overview.get("sic_codes") or [],
        registered_office_address=overview.get("registered_office_address"),
        filing_history=filing,
        officers=officers,
        persons_with_significant_control=psc,
        charges=charges,
        insolvency=insolvency,
        registers=registers,
    )


class UKGuessEORIRequest(BaseModel):
    vat_number: constr(strip_whitespace=True, min_length=5, max_length=20)


class EORIValidationResult(BaseModel):
    eori: str
    active: bool
    company_name: Optional[str] = None
    address: Optional[dict] = None
    source: str


def _hmrc_check_eori(eori: str) -> EORIValidationResult:
    base_url = settings.hmrc_eori_base_url or ""
    auth_token = settings.hmrc_api_key
    if base_url and auth_token:
        headers = {
            "Accept": "application/vnd.hmrc.1.0+json",
            "Authorization": f"Bearer {auth_token}",
        }
        url = f"{base_url}/checks/{eori}"
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 404:
            return EORIValidationResult(eori=eori, active=False, source="hmrc")
        if r.status_code >= 400:
            raise HTTPException(status_code=502, detail="HMRC EORI error")
        data = r.json()
        details = data.get("eoriParty", {})
        name = details.get("name")
        addr = details.get("address")
        return EORIValidationResult(eori=eori, active=True, company_name=name, address=addr, source="hmrc")
    if eori.upper().startswith("GB123456789000"):
        return EORIValidationResult(eori=eori, active=True, company_name="Test Company Ltd", address={"countryCode": "GB"}, source="stub")
    return EORIValidationResult(eori=eori, active=False, source="stub")


@router.post("/uk/eori/validate", response_model=EORIValidationResult)
async def uk_eori_validate(
    body: UKGuessEORIRequest,
    user=Depends(require_plan(PlanTier.PRO)),
):
    guessed = f"GB{body.vat_number}000"
    return _hmrc_check_eori(guessed)


class EUVatCheckRequest(BaseModel):
    country_code: constr(pattern=r"^[A-Z]{2}$")
    vat_number: constr(strip_whitespace=True, min_length=5, max_length=20)


class EUVatCheckResult(BaseModel):
    active: bool
    name: Optional[str] = None
    company_id: Optional[str] = None
    source: str


def _vies_check_vat(country_code: str, vat_number: str) -> EUVatCheckResult:
    if settings.vies_wsdl_url:
        raise HTTPException(status_code=501, detail="VIES live integration not implemented")
    if vat_number.endswith("000"):
        return EUVatCheckResult(active=True, name="EU Test Company", company_id="TEST123", source="stub")
    return EUVatCheckResult(active=False, source="stub")


@router.post("/eu/vat/validate", response_model=EUVatCheckResult)
async def eu_vat_validate(
    body: EUVatCheckRequest,
    user=Depends(require_plan(PlanTier.PRO)),
):
    return _vies_check_vat(body.country_code, body.vat_number)


class ProfileIntakeRequest(BaseModel):
    products: conlist(str, min_length=0, max_length=5) = []
    countries: list[str] = []
    role: constr(pattern="^(importer|exporter)$")
    vat_number: Optional[str] = None
    aeo_status: Optional[bool] = None
    forwarder: Optional[str] = None
    dda_account: Optional[bool] = None


class ProfileIntakeResponse(BaseModel):
    accepted: bool
    guessed_eori: Optional[str] = None
    eori_validation: Optional[EORIValidationResult] = None


@router.post("/profile", response_model=ProfileIntakeResponse)
async def profile_intake(
    body: ProfileIntakeRequest,
    user=Depends(require_plan(PlanTier.PRO)),
):
    guessed = None
    validation = None
    if body.vat_number and body.role in ("importer", "exporter"):
        guessed = f"GB{body.vat_number}000"
        try:
            validation = _hmrc_check_eori(guessed)
        except HTTPException:
            validation = None
    return ProfileIntakeResponse(accepted=True, guessed_eori=guessed, eori_validation=validation)
