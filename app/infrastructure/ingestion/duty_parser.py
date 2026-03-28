from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from decimal import Decimal, InvalidOperation
from typing import Any

_EA_COMPONENTS = {"EA", "EAR", "ADSZ", "ADSZR", "ADFM", "ADFMR"}
_MEASUREMENT_BASIS_CODES = {"S", "E", "P", "A", "T"}
_DUTY_RATE_FLAGS = {"R", "M"}
_DUTY_BASIS_FLAGS = {"S", "Z"}


@dataclass(frozen=True)
class ParsedDuty:
    duty_rate: Decimal | None = None
    duty_amount: Decimal | None = None
    currency: str | None = None
    duty_unit: str | None = None
    duty_amount_secondary: Decimal | None = None
    duty_unit_secondary: str | None = None
    duty_min_amount: Decimal | None = None
    duty_max_amount: Decimal | None = None
    duty_min_rate: Decimal | None = None
    duty_max_rate: Decimal | None = None
    duty_max_total_rate: Decimal | None = None
    duty_expression_code: str | None = None
    duty_expression_code_suffix: str | None = None
    duty_rate_flag: str | None = None
    duty_measurement_basis: str | None = None
    duty_gross_weight_basis: bool = False
    has_entry_price: bool = False
    entry_price_type: str | None = None
    entry_price_max_rate: Decimal | None = None
    entry_price_max_additional_type: str | None = None
    entry_price_max_specific: Decimal | None = None
    is_nihil: bool = False
    is_alcohol_duty: bool = False
    siv_bands: list[dict[str, Any]] | None = None
    weight_threshold_bands: list[dict[str, Any]] | None = None
    reduction_bands: list[dict[str, Any]] | None = None
    quantity_threshold_bands: list[dict[str, Any]] | None = None
    value_threshold_bands: list[dict[str, Any]] | None = None
    unit_price_threshold_bands: list[dict[str, Any]] | None = None
    count_threshold_bands: list[dict[str, Any]] | None = None
    requires_import_licence: bool = False
    anti_dumping_specific: bool = False
    duty_per_item: bool = False
    duty_per_article: bool = False
    duty_suspended_to: Decimal | None = None
    duty_full_amount: Decimal | None = None
    raw_expression: str = ""
    parse_errors: list[str] = field(default_factory=list)
    human_readable: str | None = None


_RE_PCT_ONLY = re.compile(r"^\s*(?P<num>[\d.,]+)\s*%\s*$")
_RE_PCT = re.compile(r"(?P<num>[\d.,]+)\s*%")
_RE_MONEY_UNIT = re.compile(
    r"(?P<num>[\d.,]+)\s+(?P<ccy>EUR|EUC)\s+(?P<unit>[A-Z0-9]{2,10})(?:\s+(?P<suffix>[A-Z]))?\s*$",
    flags=re.IGNORECASE,
)
_RE_MIN_AMOUNT = re.compile(
    r"\bMIN\s+(?P<num>[\d.,]+)\s+(?P<ccy>EUR|EUC)\s+(?P<unit>[A-Z0-9]{2,10})(?:\s+(?P<suf>[A-Z]))?\b",
    flags=re.IGNORECASE,
)
_RE_MAX_AMOUNT = re.compile(
    r"\bMAX\s+(?P<num>[\d.,]+)\s+(?P<ccy>EUR|EUC)\s+(?P<unit>[A-Z0-9]{2,10})(?:\s+(?P<suf>[A-Z]))?\b",
    flags=re.IGNORECASE,
)
_RE_MAX_RATE = re.compile(r"\bMAX\s+(?P<num>[\d.,]+)\s*%\b", flags=re.IGNORECASE)
_RE_ENTRY_PRICE = re.compile(r"\b(EA|EAR|ADSZ|ADSZR|ADFM|ADFMR)\b", flags=re.IGNORECASE)
_RE_TWO_SPECIFIC = re.compile(
    r"^\s*(?P<a1>[\d.,]+)\s+(?P<c1>EUR|EUC)\s+(?P<u1>[A-Z0-9]{2,10})(?:\s+(?P<s1>[A-Z]))?\s*\+\s*(?P<a2>[\d.,]+)\s+(?P<c2>EUR|EUC)\s+(?P<u2>[A-Z0-9]{2,10})(?:\s+(?P<s2>[A-Z]))?\s*$",
    flags=re.IGNORECASE,
)


def _parse_decimal(s: str | None) -> Decimal | None:
    if s is None:
        return None
    v = str(s).strip()
    if not v:
        return None
    v = v.replace(" ", "")
    if "," in v and "." in v:
        if v.find(",") < v.find("."):
            v = v.replace(",", "")
        else:
            v = v.replace(".", "").replace(",", ".")
    else:
        if v.count(",") == 1 and "." not in v:
            v = v.replace(",", ".")
        elif v.count(",") > 1 and "." not in v:
            v = v.replace(",", "")
    try:
        return Decimal(v)
    except InvalidOperation:
        return None


def _norm_currency(ccy: str) -> str:
    c = ccy.upper().strip()
    if c == "EUC":
        return "EUR"
    return c


def _unit_label(unit: str, unit_desc: dict[str, str] | None) -> str:
    if not unit_desc:
        return unit
    return unit_desc.get(unit, unit)


def _fmt_money(amount: Decimal) -> str:
    q = amount.quantize(Decimal("0.001"))
    s = format(q, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def duty_to_human_readable(d: ParsedDuty, unit_desc: dict[str, str] | None = None) -> str:
    unit_desc = unit_desc or {}
    if d.is_nihil:
        return "Nil (no duty)"
    parts: list[str] = []
    if d.duty_rate is not None:
        parts.append(f"{d.duty_rate.normalize()}%")
    if d.has_entry_price:
        parts.append(f"+ {d.entry_price_type} (entry price component — calculated at border)")
    if d.duty_amount is not None and d.currency and d.duty_unit:
        parts.append(f"{d.currency} {_fmt_money(d.duty_amount)} per {_unit_label(d.duty_unit, unit_desc)}")
    if d.duty_amount_secondary is not None and d.currency and d.duty_unit_secondary:
        parts.append(f"+ {d.currency} {_fmt_money(d.duty_amount_secondary)} per {_unit_label(d.duty_unit_secondary, unit_desc)}")
    if d.duty_min_amount is not None and d.currency and d.duty_unit:
        parts.append(f"(minimum {d.currency} {_fmt_money(d.duty_min_amount)} per {_unit_label(d.duty_unit, unit_desc)})")
    if d.duty_max_amount is not None and d.currency and d.duty_unit:
        parts.append(f"(maximum {d.currency} {_fmt_money(d.duty_max_amount)} per {_unit_label(d.duty_unit, unit_desc)})")
    if d.duty_min_rate is not None:
        parts.append(f"(minimum {d.duty_min_rate.normalize()}%)")
    if d.duty_max_rate is not None:
        parts.append(f"(maximum {d.duty_max_rate.normalize()}%)")
    if d.duty_max_total_rate is not None:
        parts.append(f"(total rate capped at {d.duty_max_total_rate.normalize()}%)")
    if d.anti_dumping_specific:
        parts.append("[anti-dumping specific duty]")
    if d.is_alcohol_duty:
        parts.append("[per % vol alcohol]")
    if d.requires_import_licence:
        parts.append("[import licence required]")
    if d.siv_bands:
        parts.append(f"(variable rate — {len(d.siv_bands)} price bands, calculated at border from declared CIF price)")
    return " ".join(parts) if parts else "See conditions"


def _split_cond_segments(raw: str) -> list[str]:
    s = raw.strip()
    if s.lower().startswith("cond:"):
        s = s.split(":", 1)[1]
    return [p.strip() for p in s.split(";") if p.strip()]


def parse_siv_condition(cond_str: str) -> list[dict[str, Any]] | None:
    s = str(cond_str).strip()
    if not s:
        return None
    if s.lower().startswith("cond:"):
        s = s.split(":", 1)[1].strip()
    if "V " not in s:
        return None
    segments = re.findall(
        r"V\s+(?P<th>[\d.,]+)\s+EUR/(?P<unit>[A-Z0-9]{2,10})\((?P<expr>\d{2})\)\s*:\s*(?P<body>[^;]+)",
        s,
        flags=re.IGNORECASE,
    )
    bands: list[dict[str, Any]] = []
    for th, unit, expr, body in segments:
        duty = parse_duty_expression(body.strip())
        bands.append(
            {
                "threshold": float((_parse_decimal(th) or Decimal("0"))),
                "threshold_unit": unit.upper(),
                "duty_expression_id": expr,
                "duty_rate": float(duty.duty_rate) if duty.duty_rate is not None else None,
                "duty_amount": float(duty.duty_amount) if duty.duty_amount is not None else None,
                "duty_unit": duty.duty_unit,
                "raw": body.strip(),
            }
        )
    return bands or None


def parse_threshold_condition(prefix: str, cond_str: str) -> list[dict[str, Any]] | None:
    p = str(prefix or "").strip().upper()
    if p not in {"R", "J", "M", "U", "X"}:
        return None
    s = str(cond_str).strip()
    if not s:
        return None
    if s.lower().startswith("cond:"):
        s = s.split(":", 1)[1].strip()
    pattern = rf"{p}\s+(?P<th>[\d.,]+)(?:\s+EUR)?/(?P<unit>[A-Z0-9]{{2,10}})\((?P<code>\d{{2}})\)"
    segments = re.findall(pattern, s, flags=re.IGNORECASE)
    if not segments:
        return None
    out: list[dict[str, Any]] = []
    for th, unit, code in segments:
        out.append(
            {
                "threshold": float((_parse_decimal(th) or Decimal("0"))),
                "unit": unit.upper(),
                "measure_expression_code": code,
            }
        )
    return out


def parse_duty_expression(text: str | None) -> ParsedDuty:
    raw = "" if text is None else str(text)
    s = raw.strip()
    d = ParsedDuty(raw_expression=raw)
    if not s:
        return replace(d, parse_errors=["empty duty expression"], human_readable="See conditions")

    try:
        if s.upper() == "NIHIL":
            d = replace(d, is_nihil=True, duty_rate=Decimal("0"), duty_expression_code="00")
            return replace(d, human_readable=duty_to_human_readable(d))
        if s == "0":
            d = replace(d, duty_rate=Decimal("0"), duty_expression_code="01")
            return replace(d, human_readable=duty_to_human_readable(d))

        if s.lower().startswith("cond:"):
            segs = _split_cond_segments(s)
            siv = parse_siv_condition(s)
            weight_bands = parse_threshold_condition("R", s)
            qty_bands = parse_threshold_condition("J", s)
            val_bands = parse_threshold_condition("M", s)
            unit_price_bands = parse_threshold_condition("U", s)
            count_bands = parse_threshold_condition("X", s)

            reduction_bands: list[dict[str, Any]] = []
            for seg in segs:
                m = re.match(
                    r"L\s+(?P<th>[\d.,]+)\s+EUR/(?P<unit>[A-Z0-9]{2,10})\((?P<expr>\d{2})\)\s*:\s*(?P<body>.+)$",
                    seg,
                    flags=re.IGNORECASE,
                )
                if not m:
                    continue
                body = m.group("body").strip()
                m2 = re.match(
                    r"(?P<amt>[\d.,]+)\s+(?P<ccy>EUR|EUC)\s+(?P<u>[A-Z0-9]{2,10})\s*-\s*(?P<red>[\d.,]+)\s*%$",
                    body,
                    flags=re.IGNORECASE,
                )
                if not m2:
                    continue
                reduction_bands.append(
                    {
                        "threshold": float((_parse_decimal(m.group("th")) or Decimal("0"))),
                        "threshold_unit": m.group("unit").upper(),
                        "duty_expression_id": m.group("expr"),
                        "duty_amount": float((_parse_decimal(m2.group("amt")) or Decimal("0"))),
                        "duty_unit": m2.group("u").upper(),
                        "reduction_pct": float((_parse_decimal(m2.group("red")) or Decimal("0"))),
                        "raw": body,
                    }
                )

            duty_full_amount: Decimal | None = None
            duty_suspended_to: Decimal | None = None
            duty_unit: str | None = None
            for seg in segs:
                fm = re.match(
                    r"F\s+(?P<th>[\d.,]+)\s+EUR/(?P<unit>[A-Z0-9]{2,10})\((?P<expr>\d{2})\)\s*:\s*(?P<body>.+)$",
                    seg,
                    flags=re.IGNORECASE,
                )
                if not fm:
                    continue
                th = _parse_decimal(fm.group("th"))
                unit = fm.group("unit").upper()
                body = fm.group("body").strip()
                body_parsed = parse_duty_expression(body)
                if th is not None and th > 0:
                    duty_full_amount = th
                    duty_unit = unit
                if body_parsed.duty_amount is not None and body_parsed.duty_amount == Decimal("0"):
                    duty_suspended_to = Decimal("0")

            fallback_expr: str | None = None
            for seg in segs:
                m = re.match(
                    r"(?P<ctype>[A-Z])(?:\s+cert:\s+(?P<cert>[A-Z]-\d{3}))?\s*\((?P<expr>\d{2})\)\s*:\s*(?P<val>.*)$",
                    seg,
                    flags=re.IGNORECASE,
                )
                if not m or m.group("cert"):
                    continue
                val = m.group("val").strip()
                if val:
                    fallback_expr = val

            base = parse_duty_expression(fallback_expr) if fallback_expr else d
            out = replace(
                base,
                raw_expression=raw,
                siv_bands=siv or base.siv_bands,
                weight_threshold_bands=weight_bands or base.weight_threshold_bands,
                quantity_threshold_bands=qty_bands or base.quantity_threshold_bands,
                value_threshold_bands=val_bands or base.value_threshold_bands,
                unit_price_threshold_bands=unit_price_bands or base.unit_price_threshold_bands,
                count_threshold_bands=count_bands or base.count_threshold_bands,
                reduction_bands=reduction_bands or base.reduction_bands,
                duty_full_amount=duty_full_amount if duty_full_amount is not None else base.duty_full_amount,
                duty_suspended_to=duty_suspended_to if duty_suspended_to is not None else base.duty_suspended_to,
            )
            if duty_unit and not out.duty_unit:
                out = replace(out, duty_unit=duty_unit)
            if out.siv_bands and not out.duty_expression_code:
                out = replace(out, duty_expression_code="V")
            if not out.human_readable:
                out = replace(out, human_readable=duty_to_human_readable(out))
            return out

        tokens = s.split()
        if len(tokens) == 1 and tokens[0].upper() in _EA_COMPONENTS:
            d = replace(d, has_entry_price=True, entry_price_type=tokens[0].upper(), duty_expression_code="06")
            return replace(d, human_readable=duty_to_human_readable(d))

        if re.match(r"^[A-Z0-9]{2,10}$", s) and not re.search(r"\d", s):
            d = replace(d, duty_expression_code="21", duty_unit=s.upper(), currency=None)
            return replace(d, human_readable=duty_to_human_readable(d))
        if re.match(r"^[A-Z0-9]{2,10}\s+[A-Z]$", s) and not re.search(r"\d", s):
            unit, suf = s.split()
            d = replace(d, duty_expression_code="21", duty_unit=unit.upper(), duty_expression_code_suffix=suf.upper(), currency=None)
            return replace(d, human_readable=duty_to_human_readable(d))

        if re.search(r"\bASV\b", s, flags=re.IGNORECASE):
            d = replace(d, is_alcohol_duty=True)

        s_suffix = s
        for suf in ("G", "I", "E"):
            if re.search(rf"\b{suf}\s*$", s_suffix):
                if suf == "G":
                    d = replace(d, duty_gross_weight_basis=True)
                if suf == "I":
                    d = replace(d, requires_import_licence=True, duty_expression_code_suffix="I")
                if suf == "E":
                    d = replace(d, anti_dumping_specific=True, duty_expression_code_suffix="E")
                s_suffix = re.sub(rf"\s+{suf}\s*$", "", s_suffix).strip()

        min_m = _RE_MIN_AMOUNT.search(s_suffix)
        if min_m:
            d = replace(
                d,
                duty_min_amount=_parse_decimal(min_m.group("num")),
                currency=_norm_currency(min_m.group("ccy")),
                duty_unit=min_m.group("unit").upper(),
            )
            s_suffix = (s_suffix[: min_m.start()] + s_suffix[min_m.end() :]).strip()

        max_rate_matches = list(_RE_MAX_RATE.finditer(s_suffix))
        if max_rate_matches:
            last = max_rate_matches[-1]
            max_val = _parse_decimal(last.group("num"))
            if "+" in s_suffix and re.search(r"\b(?:EUR|EUC)\b", s_suffix, flags=re.IGNORECASE):
                d = replace(d, duty_max_total_rate=max_val)
            else:
                d = replace(d, duty_max_rate=max_val)
            s_suffix = (s_suffix[: last.start()] + s_suffix[last.end() :]).strip()

        max_amt_m = _RE_MAX_AMOUNT.search(s_suffix)
        if max_amt_m:
            d = replace(
                d,
                duty_max_amount=_parse_decimal(max_amt_m.group("num")),
                currency=_norm_currency(max_amt_m.group("ccy")),
                duty_unit=max_amt_m.group("unit").upper(),
            )
            s_suffix = (s_suffix[: max_amt_m.start()] + s_suffix[max_amt_m.end() :]).strip()

        ep = _RE_ENTRY_PRICE.search(s_suffix)
        if ep:
            d = replace(d, has_entry_price=True, entry_price_type=ep.group(1).upper())
            s_suffix = _RE_ENTRY_PRICE.sub("", s_suffix, count=1).strip()

        if d.has_entry_price:
            m1 = re.search(
                r"\bMAX\s+(?P<num>[\d.,]+)\s*%\s*\+\s*(?P<type>ADSZ|ADSZR|ADFM|ADFMR)\b",
                raw,
                flags=re.IGNORECASE,
            )
            if m1:
                d = replace(
                    d,
                    entry_price_max_rate=_parse_decimal(m1.group("num")),
                    entry_price_max_additional_type=m1.group("type").upper(),
                )
            m2 = re.search(r"\bMAX\s+(?P<num>[\d.,]+)\s+(?:EUR|EUC)\s+(?P<unit>[A-Z0-9]{2,10})\b", raw, flags=re.IGNORECASE)
            if m2:
                d = replace(d, entry_price_max_specific=_parse_decimal(m2.group("num")))

        triple = re.match(
            r"^\s*(?P<pct>[\d.,]+)\s*%\s*\+\s*(?P<a1>[\d.,]+)\s+(?P<c1>EUR|EUC)\s+(?P<u1>[A-Z0-9]{2,10})(?:\s+(?P<s1>[A-Z]))?\s*\+\s*(?P<a2>[\d.,]+)\s+(?P<c2>EUR|EUC)\s+(?P<u2>[A-Z0-9]{2,10})(?:\s+(?P<s2>[A-Z]))?\s*$",
            s_suffix,
            flags=re.IGNORECASE,
        )
        if triple:
            duty_rate = _parse_decimal(triple.group("pct"))
            duty_amount = _parse_decimal(triple.group("a1"))
            ccy = _norm_currency(triple.group("c1"))
            u1 = triple.group("u1").upper()
            s1 = (triple.group("s1") or "").upper() or None
            a2 = _parse_decimal(triple.group("a2"))
            u2 = triple.group("u2").upper()
            basis = s1 if s1 in _MEASUREMENT_BASIS_CODES else None
            rate_flag = s1 if s1 in _DUTY_RATE_FLAGS else None
            basis_flag = s1 if s1 in _DUTY_BASIS_FLAGS else None
            d = replace(
                d,
                duty_rate=duty_rate,
                duty_amount=duty_amount,
                currency=ccy,
                duty_unit=u1,
                duty_amount_secondary=a2,
                duty_unit_secondary=u2,
                duty_measurement_basis=basis,
                duty_rate_flag=rate_flag,
                duty_expression_code_suffix=basis_flag or d.duty_expression_code_suffix,
                duty_expression_code="04",
            )
            if basis == "P":
                d = replace(d, is_alcohol_duty=True)
            if basis == "T":
                d = replace(d, duty_per_item=True)
            if basis == "A":
                d = replace(d, duty_per_article=True)
            return replace(d, human_readable=duty_to_human_readable(d))

        compound = re.match(
            r"^\s*(?P<pct>[\d.,]+)\s*%\s*\+\s*(?P<a1>[\d.,]+)\s+(?P<c1>EUR|EUC)\s+(?P<u1>[A-Z0-9]{2,10})(?:\s+(?P<s1>[A-Z]))?\s*$",
            s_suffix,
            flags=re.IGNORECASE,
        )
        if compound:
            duty_rate = _parse_decimal(compound.group("pct"))
            duty_amount = _parse_decimal(compound.group("a1"))
            ccy = _norm_currency(compound.group("c1"))
            u1 = compound.group("u1").upper()
            s1 = (compound.group("s1") or "").upper() or None
            basis = s1 if s1 in _MEASUREMENT_BASIS_CODES else None
            rate_flag = s1 if s1 in _DUTY_RATE_FLAGS else None
            basis_flag = s1 if s1 in _DUTY_BASIS_FLAGS else None
            d = replace(
                d,
                duty_rate=duty_rate,
                duty_amount=duty_amount,
                currency=ccy,
                duty_unit=u1,
                duty_measurement_basis=basis,
                duty_rate_flag=rate_flag,
                duty_expression_code_suffix=basis_flag or d.duty_expression_code_suffix,
                duty_expression_code="03",
            )
            if basis == "P":
                d = replace(d, is_alcohol_duty=True)
            if basis == "T":
                d = replace(d, duty_per_item=True)
            if basis == "A":
                d = replace(d, duty_per_article=True)
            return replace(d, human_readable=duty_to_human_readable(d))

        two_specific = _RE_TWO_SPECIFIC.match(s_suffix)
        if two_specific:
            duty_amount = _parse_decimal(two_specific.group("a1"))
            ccy = _norm_currency(two_specific.group("c1"))
            u1 = two_specific.group("u1").upper()
            s1 = (two_specific.group("s1") or "").upper() or None
            a2 = _parse_decimal(two_specific.group("a2"))
            u2 = two_specific.group("u2").upper()
            basis = s1 if s1 in _MEASUREMENT_BASIS_CODES else None
            rate_flag = s1 if s1 in _DUTY_RATE_FLAGS else None
            basis_flag = s1 if s1 in _DUTY_BASIS_FLAGS else None
            d = replace(
                d,
                duty_amount=duty_amount,
                currency=ccy,
                duty_unit=u1,
                duty_amount_secondary=a2,
                duty_unit_secondary=u2,
                duty_measurement_basis=basis,
                duty_rate_flag=rate_flag,
                duty_expression_code_suffix=basis_flag or d.duty_expression_code_suffix,
                duty_expression_code="03",
            )
            if basis == "P":
                d = replace(d, is_alcohol_duty=True)
            if basis == "T":
                d = replace(d, duty_per_item=True)
            if basis == "A":
                d = replace(d, duty_per_article=True)
            return replace(d, human_readable=duty_to_human_readable(d))

        asv = re.match(
            r"^\s*(?P<a1>[\d.,]+)\s+(?P<c1>EUR|EUC)\s+ASV\s+(?P<x>[XP])(?:\s*\+\s*(?P<a2>[\d.,]+)\s+(?P<c2>EUR|EUC)\s+(?P<u2>[A-Z0-9]{2,10}))?\s*$",
            s_suffix,
            flags=re.IGNORECASE,
        )
        if asv:
            d = replace(
                d,
                duty_amount=_parse_decimal(asv.group("a1")),
                currency=_norm_currency(asv.group("c1")),
                duty_unit="ASV",
                is_alcohol_duty=True,
            )
            if asv.group("a2") and asv.group("u2"):
                d = replace(
                    d,
                    duty_amount_secondary=_parse_decimal(asv.group("a2")),
                    duty_unit_secondary=asv.group("u2").upper(),
                    duty_expression_code="03",
                )
            else:
                d = replace(d, duty_expression_code="02")
            return replace(d, human_readable=duty_to_human_readable(d))

        enc = re.match(r"^\s*(?P<num>[\d.,]+)\s+ENC\s+ENP\s*$", s_suffix, flags=re.IGNORECASE)
        if enc:
            d = replace(d, duty_amount=_parse_decimal(enc.group("num")), currency="EUR", duty_unit="ENP", duty_expression_code="02")
            return replace(d, human_readable=duty_to_human_readable(d))

        pct_only = _RE_PCT_ONLY.match(s_suffix)
        if pct_only:
            d = replace(d, duty_rate=_parse_decimal(pct_only.group("num")), duty_expression_code="01")
            if d.duty_min_amount is not None or d.duty_max_amount is not None:
                d = replace(d, duty_expression_code="15")
            return replace(d, human_readable=duty_to_human_readable(d))

        money = _RE_MONEY_UNIT.match(s_suffix)
        if money and "%" not in s_suffix:
            amt = _parse_decimal(money.group("num"))
            ccy = _norm_currency(money.group("ccy"))
            unit = money.group("unit").upper()
            suf = (money.group("suffix") or "").upper() or None
            basis = suf if suf in _MEASUREMENT_BASIS_CODES else None
            rate_flag = suf if suf in _DUTY_RATE_FLAGS else None
            basis_flag = suf if suf in _DUTY_BASIS_FLAGS else None
            d = replace(
                d,
                duty_amount=amt,
                currency=ccy,
                duty_unit=unit,
                duty_measurement_basis=basis,
                duty_rate_flag=rate_flag,
                duty_expression_code_suffix=basis_flag or d.duty_expression_code_suffix,
                duty_expression_code="02",
            )
            if basis == "P":
                d = replace(d, is_alcohol_duty=True)
            if basis == "T":
                d = replace(d, duty_per_item=True)
            if basis == "A":
                d = replace(d, duty_per_article=True)
            return replace(d, human_readable=duty_to_human_readable(d))

        if _RE_PCT.search(s_suffix):
            pct = _RE_PCT.search(s_suffix)
            d = replace(d, duty_rate=_parse_decimal(pct.group("num")) if pct else None, duty_expression_code="01")
            if d.duty_min_amount is not None or d.duty_max_amount is not None:
                d = replace(d, duty_expression_code="15")
            return replace(d, human_readable=duty_to_human_readable(d))

        return replace(d, parse_errors=[f"unhandled duty expression: {raw!r}"], human_readable="See conditions")
    except Exception as exc:
        return replace(d, parse_errors=[str(exc)], human_readable="See conditions")
