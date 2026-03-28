from __future__ import annotations

from datetime import datetime

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import CertificateCode


_SEED = [
    ("D-008", "GSP certificate of origin (Form A)", "origin"),
    ("D-017", "ATR movement certificate", "origin"),
    ("D-018", "EUR.1 movement certificate", "origin"),
    ("D-019", "EUR-MED movement certificate", "origin"),
    ("D-020", "Import licence (TRQ)", "quota_licence"),
    ("D-023", "Form A (GSP) — variant 23", "origin"),
    ("D-024", "Form A (GSP) — variant 24", "origin"),
    ("D-025", "Battery cell compliance certificate", "compliance"),
    ("D-027", "Battery cell compliance certificate (type 27)", "compliance"),
    ("D-028", "Battery cell compliance certificate (type 28)", "compliance"),
    ("D-029", "Proof of preferential origin (additional)", "origin"),
    ("U-088", "REX (Registered Exporter) declaration", "origin"),
    ("L-139", "UN/EDIFACT — goods outside scope of measure", "exemption"),
    ("L-143", "Documentary proof goods are exempt", "exemption"),
    ("Y-155", "Certificate of authenticity / preferential origin proof", "origin"),
    ("N-990", "Tariff Rate Quota licence", "quota_licence"),
    ("A-001", "Tariff quota allocation licence (type 1)", "quota_licence"),
    ("A-004", "Tariff quota allocation licence (type 4)", "quota_licence"),
    ("A-007", "Tariff quota allocation licence (type 7)", "quota_licence"),
    ("A-019", "Tariff quota allocation licence (type 19)", "quota_licence"),
    ("A-022", "Tariff quota allocation licence (type 22)", "quota_licence"),
    ("Y-019", "Declaration — goods not subject to anti-dumping (type 19)", "anti_dumping"),
    ("Y-020", "Declaration — goods not subject to anti-dumping (type 20)", "anti_dumping"),
    ("Y-022", "Declaration — goods not subject to anti-dumping (type 22)", "anti_dumping"),
    ("Y-036", "Wine analysis document", "control"),
    ("Y-046", "Declaration goods not subject to restriction", "exemption"),
    ("Y-057", "Import authorization for ozone-depleting substances", "licence"),
    ("Y-060", "Plant health certificate", "sanitary"),
    ("Y-062", "Certificate for special purposes (type 62)", "compliance"),
    ("Y-063", "Certificate for special purposes (type 63)", "compliance"),
    ("Y-070", "ODS import licence", "licence"),
    ("Y-072", "Veterinary/sanitary certificate (beef)", "sanitary"),
    ("Y-073", "Veterinary/sanitary certificate (pork)", "sanitary"),
    ("Y-074", "Veterinary/sanitary certificate (poultry)", "sanitary"),
    ("Y-075", "Veterinary/sanitary certificate (sheep/goat)", "sanitary"),
    ("Y-076", "Veterinary/sanitary certificate (game)", "sanitary"),
    ("Y-077", "Veterinary/sanitary certificate (fish)", "sanitary"),
    ("Y-078", "Veterinary/sanitary certificate (dairy)", "sanitary"),
    ("Y-079", "Veterinary/sanitary certificate (eggs)", "sanitary"),
    ("Y-080", "CITES certificate", "cites"),
    ("Y-084", "Timber FLEGT licence", "licence"),
    ("Y-085", "Timber exemption declaration", "exemption"),
    ("Y-086", "REX declaration (individual supplier)", "origin"),
    ("Y-087", "REX declaration — variant 87", "origin"),
    ("Y-088", "REX declaration — variant 88", "origin"),
    ("Y-089", "REX declaration — variant 89", "origin"),
    ("Y-090", "REX declaration — variant 90", "origin"),
    ("Y-091", "REX declaration — variant 91", "origin"),
    ("Y-104", "CITES appendix certificate", "cites"),
    ("Y-105", "CITES re-export certificate", "cites"),
    ("Y-106", "CITES import permit", "cites"),
    ("Y-109", "CITES pre-Convention certificate", "cites"),
    ("Y-110", "CITES Annex IV certificate", "cites"),
    ("Y-111", "CITES Annex V certificate", "cites"),
    ("Y-112", "CITES Annex VI certificate", "cites"),
    ("Y-113", "CITES Annex VII certificate", "cites"),
    ("Y-115", "CITES personal effects exemption", "cites"),
    ("Y-116", "EUR-MED origin declaration", "origin"),
    ("Y-120", "Declaration of conformity (product safety)", "compliance"),
    ("Y-121", "Declaration of end-use", "end_use"),
    ("Y-122", "Declaration of non-preference", "origin"),
    ("Y-123", "Authorisation for end-use procedure", "end_use"),
    ("Y-125", "Specific exemption certificate", "exemption"),
    ("Y-127", "Steel import licence", "licence"),
    ("Y-146", "Dual-use item control document", "control"),
    ("Y-151", "Honey geographic origin declaration", "origin"),
    ("Y-152", "Declaration goods comply with regulation", "compliance"),
    ("Y-154", "End-use simplified procedure declaration", "end_use"),
    ("Y-160", "Annex II declaration — goods not listed", "exemption"),
    ("Y-162", "Entry under simplified procedure", "compliance"),
    ("Y-163", "Oral/email declaration (threshold goods)", "compliance"),
    ("Y-166", "AEO authorisation", "aeo"),
    ("Y-167", "Approved exporter status", "origin"),
    ("Y-169", "Goods not containing controlled items", "exemption"),
    ("Y-170", "Phytosanitary certificate (type 170)", "sanitary"),
    ("Y-024", "Declaration that goods not subject to anti-dumping", "exemption"),
    ("Y-058", "Phytosanitary certificate", "sanitary"),
    ("Y-059", "Veterinary certificate", "sanitary"),
    ("Y-250", "CITES permit", "licence"),
    ("Y-824", "Declaration goods don't fall under this regulation", "exemption"),
    ("Y-878", "End-use exemption declaration", "exemption"),
    ("Y-859", "Declaration goods meet exemption criteria", "exemption"),
    ("N-002", "Import licence", "licence"),
    ("N-851", "Sanitary/phytosanitary certificate", "sanitary"),
    ("C-084", "Authorised use / end-use authorisation", "licence"),
]


async def seed_certificate_codes(db: AsyncSession) -> dict:
    upserted = 0
    for code, desc, category in _SEED:
        stmt = (
            insert(CertificateCode)
            .values(code=code, description=desc, category=category, last_updated=datetime.utcnow())
            .on_conflict_do_update(
                index_elements=[CertificateCode.code],
                set_={"description": desc, "category": category, "last_updated": datetime.utcnow()},
            )
        )
        await db.execute(stmt)
        upserted += 1
    await db.commit()
    return {"certificate_codes_upserted": upserted}
