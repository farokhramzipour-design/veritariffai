from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import Origin


_KNOWN_GROUPS: dict[str, dict] = {
    "1006": {"group_category": "trade_agreement", "member_iso2_codes": ["CA"]},
    "1007": {"group_category": "trade_agreement", "member_iso2_codes": ["CH"]},
    "1033": {"group_category": "trade_agreement", "member_iso2_codes": ["AG", "BB", "BZ", "DM", "DO", "GD", "GY", "HT", "JM", "KN", "LC", "SR", "TT", "VC"]},
    "1034": {"group_category": "trade_agreement", "member_iso2_codes": ["CF", "KM", "MG", "MU", "RW", "SC", "SD", "UG", "ZM", "ZW"]},
    "1035": {"group_category": "trade_agreement", "member_iso2_codes": ["BW", "LS", "MZ", "NA", "SZ", "ZA"]},
    "1098": {"group_category": "other", "member_iso2_codes": ["AL", "BA", "ME", "MK", "XK", "XS"]},
    "2000": {"group_category": "trade_agreement", "member_iso2_codes": ["MA"]},
    "2012": {"group_category": "trade_agreement", "member_iso2_codes": ["IS", "LI", "NO"]},
    "2014": {"group_category": "trade_agreement", "member_iso2_codes": ["IS"]},
    "2200": {"group_category": "trade_agreement", "member_iso2_codes": ["CR", "SV", "GT", "HN", "NI", "PA"]},
    "5005": {"group_category": "safeguard", "member_iso2_codes": None},
    "5007": {"group_category": "safeguard", "member_iso2_codes": None},
}


def classify_origin_code(origin_code: str | None) -> str:
    code = (origin_code or "").strip().upper()
    if not code:
        return "unknown"
    if code == "1011":
        return "erga_omnes"
    if len(code) == 2 and code.isalpha():
        return "country"
    if len(code) == 4 and code.isdigit():
        if code.startswith("4"):
            return "phytosanitary"
        if code.startswith("5"):
            return "safeguard"
        if code[0] in {"1", "2", "3"}:
            return "group_numeric"
    return "unknown"


async def ensure_origin(
    db: AsyncSession,
    *,
    origin_code: str | None,
    origin_name: str | None = None,
) -> None:
    code = (origin_code or "").strip().upper()
    if not code:
        return

    name = (origin_name or "").strip() or code
    code_type = classify_origin_code(code)
    is_erga_omnes = code == "1011"
    is_group = code_type in {"group_numeric", "phytosanitary", "safeguard"}
    iso2 = code if code_type == "country" else None
    known = _KNOWN_GROUPS.get(code) if is_group else None
    group_category = "erga_omnes" if is_erga_omnes else (known.get("group_category") if known else ("other" if is_group else None))
    member_iso2_codes = known.get("member_iso2_codes") if known else None

    stmt = (
        insert(Origin)
        .values(
            origin_code=code,
            origin_name=name,
            origin_code_type=code_type,
            iso2=iso2,
            iso3=None,
            is_eu_member=False,
            is_erga_omnes=is_erga_omnes,
            is_group=is_group,
            member_iso2_codes=member_iso2_codes,
            group_category=group_category,
            notes=None,
            last_updated=datetime.utcnow(),
        )
        .on_conflict_do_nothing(index_elements=[Origin.origin_code])
    )
    await db.execute(stmt)
    if member_iso2_codes is not None:
        await db.execute(
            sa.update(Origin)
            .where(Origin.origin_code == code, Origin.member_iso2_codes.is_(None))
            .values(member_iso2_codes=member_iso2_codes, group_category=group_category, is_group=True)
        )
