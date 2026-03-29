from __future__ import annotations

import asyncio
import gzip
import os
import re
import tempfile
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import urljoin
from uuid import uuid4
from xml.etree.ElementTree import iterparse

import httpx
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import HSCode, IngestionRun, TariffMeasure
from app.infrastructure.database.session import AsyncSessionMaker


_TARIC_URL = "https://ec.europa.eu/taxation_customs/dds2/taric/xml/taric_download.jsp"

_MFN_MEASURE_TYPE_IDS: set[str] = {
    "103",
    "105",
    "106",
    "112",
    "115",
    "117",
    "119",
    "142",
    "143",
    "145",
}

_PREFERENTIAL_MEASURE_TYPE_IDS: set[str] = {"142", "143", "145"}

_ANTI_DUMPING_MEASURE_TYPE_IDS: set[str] = {"551", "552", "553", "554"}
_COUNTERVAILING_MEASURE_TYPE_IDS: set[str] = {"555", "556"}

_SAFEGUARD_MEASURE_TYPE_IDS: set[str] = {"696"}
_IMPORT_CONTROL_MEASURE_TYPE_IDS: set[str] = {"763", "745", "277"}


def _route_measure(*, measure_type_id: str, measure_type_description: str | None, has_quota_order_number: bool) -> str | None:
    mt = (measure_type_id or "").strip()
    desc = (measure_type_description or "").strip().lower()
    if has_quota_order_number or ("quota" in desc):
        return "TARIFF_QUOTA"
    if mt in _SAFEGUARD_MEASURE_TYPE_IDS or "safeguard" in desc:
        return "SAFEGUARD"
    if mt in _IMPORT_CONTROL_MEASURE_TYPE_IDS or "import control" in desc or "prohibition" in desc or "restriction" in desc:
        return "IMPORT_CONTROL"
    if mt in _ANTI_DUMPING_MEASURE_TYPE_IDS or "anti-dumping" in desc or "anti dumping" in desc:
        return "ANTI_DUMPING"
    if mt in _COUNTERVAILING_MEASURE_TYPE_IDS or "countervailing" in desc:
        return "COUNTERVAILING"
    if mt in _PREFERENTIAL_MEASURE_TYPE_IDS or "preference" in desc or "gsp" in desc:
        return "PREFERENTIAL"
    if mt in _MFN_MEASURE_TYPE_IDS or "third country duty" in desc or "mfn" in desc:
        return "MFN"
    return None


def _local(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _digits(value: str | None) -> str | None:
    if not value:
        return None
    d = "".join(ch for ch in value if ch.isdigit())
    return d or None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value.strip())
    except Exception:
        return None


def _first_text(elem, names: tuple[str, ...]) -> str | None:
    want = set(names)
    for child in elem.iter():
        if _local(child.tag) in want:
            txt = (child.text or "").strip()
            if txt:
                return txt
    return None


def _extract_download_url(html: str, base_url: str) -> str | None:
    hrefs = re.findall(r'href\s*=\s*["\']([^"\']+)["\']', html, flags=re.IGNORECASE)
    candidates: list[str] = []
    for href in hrefs:
        if not href or href.startswith("#"):
            continue
        full = urljoin(base_url, href)
        lower = full.lower()
        if any(ext in lower for ext in (".xml", ".gz", ".zip")):
            candidates.append(full)
        elif "taric" in lower and "download" in lower:
            candidates.append(full)
    return candidates[0] if candidates else None


async def _download_taric_xml(*, params: dict[str, str]) -> str:
    backoff_s = 0.75
    last_exc: Exception | None = None
    for _ in range(5):
        try:
            async with httpx.AsyncClient(timeout=300, follow_redirects=True) as client:
                resp = await client.get(
                    _TARIC_URL,
                    params=params,
                    headers={
                        "Accept": "application/xml,text/xml,*/*",
                        "User-Agent": "veritariffai/1.0",
                    },
                )
                ct = (resp.headers.get("content-type") or "").lower()
                base = str(resp.url)

                content: bytes
                if resp.status_code == 200 and ("xml" in ct or "octet-stream" in ct or "gzip" in ct):
                    content = resp.content
                else:
                    html = resp.text or ""
                    dl = _extract_download_url(html, base)
                    if not dl:
                        snippet = html[:800]
                        raise ValueError(
                            f"TARIC download failed: HTTP {resp.status_code} content-type={ct} url={base} body={snippet}"
                        )
                    dl_resp = await client.get(
                        dl,
                        headers={
                            "Accept": "application/xml,text/xml,*/*",
                            "User-Agent": "veritariffai/1.0",
                        },
                    )
                    dl_ct = (dl_resp.headers.get("content-type") or "").lower()
                    if dl_resp.status_code != 200:
                        snippet = (dl_resp.text or "")[:800]
                        raise ValueError(
                            f"TARIC download link failed: HTTP {dl_resp.status_code} content-type={dl_ct} url={dl_resp.url} body={snippet}"
                        )
                    content = dl_resp.content
            is_gzip = content[:2] == b"\x1f\x8b"
            fd, path = tempfile.mkstemp(prefix="taric_", suffix=".xml")
            os.close(fd)
            if is_gzip:
                xml_bytes = gzip.decompress(content)
                if len(xml_bytes) < 10_000:
                    raise ValueError("TARIC download returned an unexpectedly small response")
                with open(path, "wb") as f:
                    f.write(xml_bytes)
            else:
                if len(content) < 10_000:
                    raise ValueError("TARIC download returned an unexpectedly small response")
                with open(path, "wb") as f:
                    f.write(content)
            return path
        except Exception as exc:
            last_exc = exc
            await asyncio.sleep(backoff_s)
            backoff_s *= 2
    raise last_exc or RuntimeError("TARIC download failed")


async def _upsert_hs_codes(db: AsyncSession, rows: list[dict[str, Any]]) -> None:
    for row in rows:
        stmt = (
            insert(HSCode)
            .values(
                code=row["code"],
                jurisdiction="EU",
                description=row["description"],
                parent_code=None,
                level=len(row["code"]),
                supplementary_unit=None,
                valid_from=row["valid_from"],
                valid_to=None,
            )
            .on_conflict_do_update(
                index_elements=[HSCode.code],
                set_={
                    "jurisdiction": "EU",
                    "description": row["description"],
                    "level": len(row["code"]),
                    "valid_to": None,
                },
            )
        )
        await db.execute(stmt)


async def _upsert_measure(db: AsyncSession, *, row: dict[str, Any]) -> None:
    from app.infrastructure.ingestion.origins import ensure_origin

    origin_code = row.get("country_of_origin")
    if origin_code:
        await ensure_origin(db, origin_code=str(origin_code), origin_name=None)

    stmt = (
        insert(TariffMeasure)
        .values(
            id=uuid4(),
            hs_code=row["hs_code"],
            jurisdiction="EU",
            measure_type=row["measure_type"],
            country_of_origin=row["country_of_origin"],
            preferential_agreement=None,
            rate_ad_valorem=row.get("rate_ad_valorem"),
            rate_specific_amount=row.get("rate_specific_amount"),
            rate_specific_unit=row.get("rate_specific_unit"),
            rate_minimum=None,
            rate_maximum=None,
            agricultural_component=None,
            quota_id=None,
            suspension=row.get("suspension", False),
            measure_condition=row.get("measure_condition"),
            raw_json=row.get("raw_json"),
            valid_from=row["valid_from"],
            valid_to=row.get("valid_to"),
            source_dataset="TARIC",
            source_measure_id=row["source_measure_id"],
            ingested_at=datetime.utcnow(),
        )
        .on_conflict_do_update(
            index_elements=[TariffMeasure.source_dataset, TariffMeasure.source_measure_id],
            index_where=sa.text("source_measure_id IS NOT NULL"),
            set_={
                "hs_code": row["hs_code"],
                "jurisdiction": "EU",
                "measure_type": row["measure_type"],
                "country_of_origin": row["country_of_origin"],
                "rate_ad_valorem": row.get("rate_ad_valorem"),
                "rate_specific_amount": row.get("rate_specific_amount"),
                "rate_specific_unit": row.get("rate_specific_unit"),
                "suspension": row.get("suspension", False),
                "measure_condition": row.get("measure_condition"),
                "raw_json": row.get("raw_json"),
                "valid_from": row["valid_from"],
                "valid_to": row.get("valid_to"),
                "ingested_at": datetime.utcnow(),
            },
        )
    )
    await db.execute(stmt)


def _parse_goods_nomenclature(xml_path: str) -> dict[str, str]:
    leaf: dict[str, str] = {}
    for event, elem in iterparse(xml_path, events=("end",)):
        if _local(elem.tag) != "GOODS.NOMENCLATURE":
            continue
        hs = _digits(_first_text(elem, ("GOODS.NOMENCLATURE.ITEM.ID",)))
        suffix = _first_text(elem, ("PRODUCTLINE.SUFFIX",))
        if not hs or suffix != "80":
            elem.clear()
            continue
        desc: str | None = None
        for child in elem.iter():
            if _local(child.tag) == "GOODS.NOMENCLATURE.DESCRIPTION.PERIOD":
                lang = _first_text(child, ("LANGUAGE.ID",))
                if lang == "EN":
                    desc = _first_text(child, ("GOODS.NOMENCLATURE.DESCRIPTION",))
                    break
        leaf[hs] = (desc or f"HS {hs}").strip()
        elem.clear()
    return leaf


def _extract_amount_fields(elem) -> tuple[Decimal | None, Decimal | None, str | None]:
    amount_str = _first_text(elem, ("MEASURE.CONDITION.DUTY.AMOUNT", "DUTY.AMOUNT", "MEASURE.COMPONENT.DUTY.AMOUNT"))
    expr_id = _first_text(elem, ("DUTY.EXPRESSION.ID", "MEASURE.CONDITION.DUTY.EXPRESSION.ID"))
    monetary = _first_text(elem, ("MONETARY.UNIT.CODE", "MEASURE.CONDITION.MONETARY.UNIT.CODE"))
    measurement = _first_text(elem, ("MEASUREMENT.UNIT.CODE", "MEASURE.CONDITION.MEASUREMENT.UNIT.CODE"))
    if not amount_str:
        return None, None, None
    try:
        amount = Decimal(amount_str)
    except Exception:
        return None, None, None
    if expr_id == "01":
        return amount, None, None
    unit = None
    if monetary and measurement:
        unit = f"{monetary}/{measurement}"
    elif measurement:
        unit = measurement
    elif monetary:
        unit = monetary
    return None, amount, unit


def _parse_components(elem) -> list[dict[str, Any]]:
    components: list[dict[str, Any]] = []
    for child in elem.iter():
        if _local(child.tag) != "MEASURE.COMPONENT":
            continue
        ad, specific, unit = _extract_amount_fields(child)
        expr_id = _first_text(child, ("DUTY.EXPRESSION.ID",))
        monetary = _first_text(child, ("MONETARY.UNIT.CODE",))
        measurement = _first_text(child, ("MEASUREMENT.UNIT.CODE",))
        amount = ad if ad is not None else specific
        if amount is None and not unit and not expr_id:
            continue
        components.append(
            {
                "duty_expression_id": expr_id,
                "amount": str(amount) if amount is not None else None,
                "monetary_unit": monetary,
                "measurement_unit": measurement,
                "unit": unit,
            }
        )
    return components


def _assemble_raw_expression(*, rate_ad_valorem: Decimal | None, rate_specific_amount: Decimal | None, rate_specific_unit: str | None, components: list[dict[str, Any]]) -> str | None:
    parts: list[str] = []
    if rate_ad_valorem is not None:
        parts.append(f"{rate_ad_valorem} %")
    if rate_specific_amount is not None:
        if rate_specific_unit:
            parts.append(f"{rate_specific_amount} {rate_specific_unit}")
        else:
            parts.append(f"{rate_specific_amount}")
    if not parts and components:
        for c in components:
            a = c.get("amount")
            u = c.get("unit")
            if a and u:
                parts.append(f"{a} {u}")
            elif a:
                parts.append(str(a))
    if not parts:
        return None
    return " + ".join(parts)


def _parse_measure_conditions(elem) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for child in elem.iter():
        if _local(child.tag) != "MEASURE.CONDITION":
            continue
        condition_code = _first_text(child, ("CONDITION.CODE", "MEASURE.CONDITION.CODE"))
        action_code = _first_text(child, ("CONDITION.ACTION.CODE", "MEASURE.CONDITION.ACTION.CODE"))
        cert_type = _first_text(child, ("CERTIFICATE.TYPE.CODE",))
        cert_code = _first_text(child, ("CERTIFICATE.CODE",))
        cert_full = None
        if cert_type and cert_code:
            cert_full = f"{cert_type.strip().upper()}-{cert_code.strip()}"
        duty_amount = _first_text(child, ("MEASURE.CONDITION.DUTY.AMOUNT",))
        duty_expr_id = _first_text(child, ("MEASURE.CONDITION.DUTY.EXPRESSION.ID",))
        measurement_unit = _first_text(child, ("MEASURE.CONDITION.MEASUREMENT.UNIT.CODE",))
        monetary_unit = _first_text(child, ("MEASURE.CONDITION.MONETARY.UNIT.CODE",))
        out.append(
            {
                "condition_code": condition_code,
                "action_code": action_code,
                "certificate_code": cert_full,
                "certificate_type": cert_type,
                "certificate_id": cert_code,
                "duty_amount": duty_amount,
                "duty_expression_id": duty_expr_id,
                "measurement_unit": measurement_unit,
                "monetary_unit": monetary_unit,
            }
        )
    return [c for c in out if any(v for v in c.values())]


def _parse_measures(xml_path: str, leaf_codes: set[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event, elem in iterparse(xml_path, events=("end",)):
        if _local(elem.tag) != "MEASURE":
            continue
        hs = _digits(_first_text(elem, ("GOODS.NOMENCLATURE.ITEM.ID",)))
        if not hs or hs not in leaf_codes:
            elem.clear()
            continue
        sid = _first_text(elem, ("MEASURE.SID",)) or f"TARIC:{hs}:{uuid4()}"
        mt_id = _first_text(elem, ("MEASURE.TYPE.ID",))
        if not mt_id:
            elem.clear()
            continue
        mt_desc = _first_text(elem, ("MEASURE.TYPE.DESCRIPTION",))
        quota_order_number = _first_text(elem, ("ORDER.NUMBER.ID", "MEASURE.ORDER.NUMBER.ID", "QUOTA.ORDER.NUMBER.ID"))
        has_quota = bool(quota_order_number)
        measure_type = _route_measure(measure_type_id=mt_id, measure_type_description=mt_desc, has_quota_order_number=has_quota)
        if not measure_type:
            elem.clear()
            continue
        geo = _first_text(elem, ("GEOGRAPHICAL.AREA.ID",))
        origin = geo or "1011"
        valid_from = _parse_date(_first_text(elem, ("VALIDITY.START.DATE",))) or date.today()
        valid_to = _parse_date(_first_text(elem, ("VALIDITY.END.DATE",)))

        components = _parse_components(elem)
        rate_ad, rate_specific, unit = _extract_amount_fields(elem)
        raw_expression = _assemble_raw_expression(rate_ad_valorem=rate_ad, rate_specific_amount=rate_specific, rate_specific_unit=unit, components=components)
        conditions = _parse_measure_conditions(elem)
        duty_meta: dict[str, Any] = {
            "raw_expression": raw_expression,
            "components": components,
            "is_nihil": False,
        }
        if raw_expression and raw_expression.strip() in {"0", "0.0", "0.00", "0.000", "0.000 %", "0 %"}:
            duty_meta["is_nihil"] = True
        if not raw_expression and not rate_ad and not rate_specific and measure_type in {"TARIFF_QUOTA"}:
            duty_meta["is_nihil"] = True

        suspension = measure_type in {"SUSPENSION", "END_USE"}
        rows.append(
            {
                "hs_code": hs,
                "measure_type": measure_type,
                "country_of_origin": origin,
                "rate_ad_valorem": rate_ad,
                "rate_specific_amount": rate_specific,
                "rate_specific_unit": unit,
                "suspension": suspension,
                "measure_condition": {"duty": duty_meta, "conditions": conditions} if (duty_meta or conditions) else None,
                "valid_from": valid_from,
                "valid_to": valid_to,
                "source_measure_id": str(sid),
                "raw_json": {
                    "measure_sid": str(sid),
                    "measure_type_id": mt_id,
                    "measure_type_description": mt_desc,
                    "geographical_area_id": geo,
                    "quota_order_number": quota_order_number,
                    "duty_expression_id": _first_text(elem, ("DUTY.EXPRESSION.ID", "MEASURE.CONDITION.DUTY.EXPRESSION.ID")),
                },
            }
        )
        elem.clear()
    return rows


async def _run_taric_ingest(*, mode: str, delta_date: date | None) -> dict[str, Any]:
    started = datetime.utcnow()
    async with AsyncSessionMaker() as db:
        run = IngestionRun(source="TARIC", status="running", started_at=started)
        db.add(run)
        await db.commit()
        await db.refresh(run)

        xml_path: str | None = None
        try:
            if mode == "full":
                params = {"Expand": "true", "Lang": "EN"}
            else:
                d = delta_date or date.today()
                params = {
                    "Expand": "true",
                    "Lang": "EN",
                    "Year": str(d.year),
                    "Month": f"{d.month:02d}",
                    "Day": f"{d.day:02d}",
                }
            xml_path = await _download_taric_xml(params=params)
            leaf_map = _parse_goods_nomenclature(xml_path)
            leaf_codes = set(leaf_map.keys())

            hs_rows = [{"code": code, "description": desc, "valid_from": date.today()} for code, desc in leaf_map.items()]
            for i in range(0, len(hs_rows), 500):
                await _upsert_hs_codes(db, hs_rows[i:i + 500])
                await db.commit()

            measures = _parse_measures(xml_path, leaf_codes)
            for i in range(0, len(measures), 500):
                for row in measures[i:i + 500]:
                    await _upsert_measure(db, row=row)
                await db.commit()

            res = await db.execute(
                sa.text(
                    """
                    SELECT COUNT(*) FROM (
                      SELECT DISTINCT tm.hs_code
                      FROM tariff.tariff_measures tm
                      WHERE tm.jurisdiction = 'EU'
                        AND NOT EXISTS (
                          SELECT 1
                          FROM tariff.tariff_measures mfn
                          WHERE mfn.jurisdiction = 'EU'
                            AND mfn.hs_code = tm.hs_code
                            AND mfn.measure_type = 'MFN'
                            AND COALESCE(mfn.country_of_origin, '1011') = '1011'
                        )
                    ) t
                    """
                )
            )
            mfn_missing_count = int(res.scalar_one() or 0)
            sample_res = await db.execute(
                sa.text(
                    """
                    SELECT DISTINCT tm.hs_code
                    FROM tariff.tariff_measures tm
                    WHERE tm.jurisdiction = 'EU'
                      AND NOT EXISTS (
                        SELECT 1
                        FROM tariff.tariff_measures mfn
                        WHERE mfn.jurisdiction = 'EU'
                          AND mfn.hs_code = tm.hs_code
                          AND mfn.measure_type = 'MFN'
                          AND COALESCE(mfn.country_of_origin, '1011') = '1011'
                      )
                    ORDER BY tm.hs_code
                    LIMIT 25
                    """
                )
            )
            missing_mfn_sample = [c for c in sample_res.scalars().all() if isinstance(c, str)]

            run.status = "success"
            run.records_processed = len(measures)
            run.completed_at = datetime.utcnow()
            await db.commit()
            return {
                "source": "TARIC",
                "status": run.status,
                "records_processed": len(measures),
                "hs_codes": len(leaf_codes),
                "mfn_missing_count": mfn_missing_count,
                "mfn_missing_sample": missing_mfn_sample,
            }
        except Exception as exc:
            await db.rollback()
            run.status = "failed"
            run.error_details = str(exc)
            run.completed_at = datetime.utcnow()
            await db.commit()
            return {"source": "TARIC", "status": run.status, "error": str(exc)}
        finally:
            if xml_path:
                try:
                    os.remove(xml_path)
                except Exception:
                    pass


async def ingest_delta() -> dict[str, Any]:
    delta_date_env = os.getenv("TARIC_DELTA_DATE", "").strip()
    d = _parse_date(delta_date_env) if delta_date_env else None
    return await _run_taric_ingest(mode="delta", delta_date=d)


async def ingest_full() -> dict[str, Any]:
    return await _run_taric_ingest(mode="full", delta_date=None)


def ingest_delta_sync() -> dict[str, Any]:
    return asyncio.run(ingest_delta())


def ingest_full_sync() -> dict[str, Any]:
    return asyncio.run(ingest_full())
