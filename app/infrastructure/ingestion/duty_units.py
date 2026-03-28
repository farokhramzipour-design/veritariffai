from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import DutyUnit


_UNITS: list[dict] = [
    {"code": "DTN", "description": "per 100 kg (decitonnes)", "category": "mass", "base_si_unit": "KGM", "conversion_to_si": Decimal("100")},
    {"code": "TNE", "description": "per metric tonne (1000 kg)", "category": "mass", "base_si_unit": "KGM", "conversion_to_si": Decimal("1000")},
    {"code": "KGM", "description": "per kilogram", "category": "mass", "base_si_unit": "KGM", "conversion_to_si": Decimal("1")},
    {"code": "HLT", "description": "per hectolitre (100 litres)", "category": "volume", "base_si_unit": "LTR", "conversion_to_si": Decimal("100")},
    {"code": "LTR", "description": "per litre", "category": "volume", "base_si_unit": "LTR", "conversion_to_si": Decimal("1")},
    {"code": "MIL", "description": "per thousand items", "category": "count", "base_si_unit": "NAR", "conversion_to_si": Decimal("1000")},
    {"code": "NAR", "description": "per item (number of articles)", "category": "count", "base_si_unit": "NAR", "conversion_to_si": Decimal("1")},
    {"code": "MTQ", "description": "per cubic metre", "category": "volume", "base_si_unit": "MTQ", "conversion_to_si": Decimal("1")},
    {"code": "MTK", "description": "per square metre", "category": "area", "base_si_unit": "MTK", "conversion_to_si": Decimal("1")},
    {"code": "MTR", "description": "per linear metre", "category": "length", "base_si_unit": "MTR", "conversion_to_si": Decimal("1")},
    {"code": "GRM", "description": "per gram", "category": "mass", "base_si_unit": "KGM", "conversion_to_si": Decimal("0.001")},
    {"code": "KNS", "description": "kilogram net of sugars", "category": "mass", "base_si_unit": "KGM", "conversion_to_si": None},
    {"code": "KSD", "description": "kilogram of sucrose dry matter", "category": "mass", "base_si_unit": "KGM", "conversion_to_si": None},
    {"code": "KMA", "description": "kilogram of methylamine", "category": "mass", "base_si_unit": "KGM", "conversion_to_si": None},
    {"code": "KNI", "description": "kilogram of nitrogen", "category": "mass", "base_si_unit": "KGM", "conversion_to_si": None},
    {"code": "KPO", "description": "kilogram of potassium oxide", "category": "mass", "base_si_unit": "KGM", "conversion_to_si": None},
    {"code": "KPH", "description": "kilogram of phosphorus pentoxide", "category": "mass", "base_si_unit": "KGM", "conversion_to_si": None},
    {"code": "KSH", "description": "kilogram of shelled product", "category": "mass", "base_si_unit": "KGM", "conversion_to_si": None},
    {"code": "KPP", "description": "kilogram of diphosphorus pentoxide", "category": "mass", "base_si_unit": "KGM", "conversion_to_si": None},
    {"code": "KUR", "description": "kilogram of uranium", "category": "mass", "base_si_unit": "KGM", "conversion_to_si": None},
    {"code": "GFI", "description": "gram of fissile isotopes", "category": "mass", "base_si_unit": "GRM", "conversion_to_si": None},
    {"code": "ASV", "description": "per % volume (alcohol strength by volume)", "category": "alcohol", "base_si_unit": "ASV", "conversion_to_si": None},
    {"code": "DAP", "description": "decitonne of raw product", "category": "mass", "base_si_unit": "KGM", "conversion_to_si": None},
    {"code": "HMT", "description": "hectometre", "category": "length", "base_si_unit": "MTR", "conversion_to_si": Decimal("100")},
    {"code": "ENP", "description": "effective number of primary cells", "category": "count", "base_si_unit": None, "conversion_to_si": None},
    {"code": "CCT", "description": "carrying capacity (tonnes)", "category": "capacity", "base_si_unit": "TNE", "conversion_to_si": None},
    {"code": "CEN", "description": "per hundred items", "category": "count", "base_si_unit": "NAR", "conversion_to_si": Decimal("100")},
    {"code": "LPA", "description": "litre of pure (100%) alcohol", "category": "alcohol", "base_si_unit": "LTR", "conversion_to_si": None},
    {"code": "ENC", "description": "cell equivalent", "category": "count", "base_si_unit": None, "conversion_to_si": None},
    {"code": "MWH", "description": "megawatt-hour", "category": "energy", "base_si_unit": "MWH", "conversion_to_si": None},
    {"code": "TJO", "description": "terajoule", "category": "energy", "base_si_unit": "TJO", "conversion_to_si": None},
    {"code": "CTM", "description": "metric carat", "category": "mass", "base_si_unit": "GRM", "conversion_to_si": Decimal("0.200")},
    {"code": "NPR", "description": "number of pairs", "category": "count", "base_si_unit": "NAR", "conversion_to_si": None},
    {"code": "NCL", "description": "number of cells", "category": "count", "base_si_unit": "NAR", "conversion_to_si": None},
]


async def seed_duty_units(db: AsyncSession) -> dict:
    upserted = 0
    for u in _UNITS:
        stmt = (
            insert(DutyUnit)
            .values(
                code=u["code"],
                description=u["description"],
                category=u.get("category"),
                base_si_unit=u.get("base_si_unit"),
                conversion_to_si=u.get("conversion_to_si"),
                last_updated=datetime.utcnow(),
            )
            .on_conflict_do_update(
                index_elements=[DutyUnit.code],
                set_={
                    "description": u["description"],
                    "category": u.get("category"),
                    "base_si_unit": u.get("base_si_unit"),
                    "conversion_to_si": u.get("conversion_to_si"),
                    "last_updated": datetime.utcnow(),
                },
            )
        )
        await db.execute(stmt)
        upserted += 1
    await db.commit()
    return {"duty_units_upserted": upserted}
