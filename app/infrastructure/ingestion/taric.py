from __future__ import annotations

import asyncio
import gzip
import os
import tempfile
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4
from xml.etree.ElementTree import iterparse

import httpx
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import HSCode, IngestionRun, TariffMeasure
from app.infrastructure.database.session import AsyncSessionMaker


_TARIC_URL = "https://ec.europa.eu/taxation_customs/dds2/taric/xml/taric_download.jsp"

_MEASURE_TYPE_MAP: dict[str, str] = {
    "103": "MFN",
    "142": "PREFERENTIAL",
    "551": "ANTI_DUMPING",
    "552": "COUNTERVAILING",
    "112": "SUSPENSION",
    "115": "END_USE",
}


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


async def _download_taric_xml(*, params: dict[str, str]) -> str:
    backoff_s = 0.5
    last_exc: Exception | None = None
    for _ in range(3):
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                resp = await client.get(_TARIC_URL, params=params, headers={"Accept": "*/*"})
                resp.raise_for_status()
                content = resp.content
            is_gzip = content[:2] == b"\x1f\x8b"
            fd, path = tempfile.mkstemp(prefix="taric_", suffix=".xml")
            os.close(fd)
            if is_gzip:
                xml_bytes = gzip.decompress(content)
                with open(path, "wb") as f:
                    f.write(xml_bytes)
            else:
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
            measure_condition=None,
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
    unit = _first_text(elem, ("MONETARY.UNIT.CODE", "MEASUREMENT.UNIT.CODE", "MEASURE.CONDITION.MONETARY.UNIT.CODE"))
    if not amount_str:
        return None, None, None
    try:
        amount = Decimal(amount_str)
    except Exception:
        return None, None, None
    if expr_id == "01" or unit is None:
        return amount, None, None
    return None, amount, unit


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
        if not mt_id or mt_id not in _MEASURE_TYPE_MAP:
            elem.clear()
            continue
        geo = _first_text(elem, ("GEOGRAPHICAL.AREA.ID",))
        origin = None
        if geo and geo != "1011":
            origin = geo
        valid_from = _parse_date(_first_text(elem, ("VALIDITY.START.DATE",))) or date.today()
        valid_to = _parse_date(_first_text(elem, ("VALIDITY.END.DATE",)))

        rate_ad, rate_specific, unit = _extract_amount_fields(elem)
        measure_type = _MEASURE_TYPE_MAP[mt_id]
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
                "valid_from": valid_from,
                "valid_to": valid_to,
                "source_measure_id": str(sid),
                "raw_json": {
                    "measure_sid": str(sid),
                    "measure_type_id": mt_id,
                    "geographical_area_id": geo,
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

            run.status = "success"
            run.records_processed = len(measures)
            run.completed_at = datetime.utcnow()
            await db.commit()
            return {"source": "TARIC", "status": run.status, "records_processed": len(measures), "hs_codes": len(leaf_codes)}
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
