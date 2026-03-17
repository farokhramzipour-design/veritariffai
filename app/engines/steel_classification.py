"""
Steel Classification Engine – Chapter 72 decision tree.

Implements the full Happy-Path logic from the Veritariff spec:
  Step 1.1  – Material-type gate (scrap/granules/pig-iron/ferro-alloy ...)
  Step 1.2  – Alloy classification (stainless / other-alloy / non-alloy)
  Step 1.2A – Stainless-steel form → headings 7218-7223
  Step 1.2B – Other-alloy-steel form → headings 7224-7228
  Step 1.2C – Non-alloy iron/steel form → headings 7206-7217
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from app.engines.base import AuditStep, EngineError, EngineResult


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class MaterialType(str, Enum):
    WASTE_OR_SCRAP = "waste_or_scrap"
    GRANULES_OR_POWDERS = "granules_or_powders"
    DIRECT_REDUCTION_SPONGE_IRON = "direct_reduction_sponge_iron"
    PIG_IRON = "pig_iron"
    FERRO_ALLOY = "ferro_alloy"
    STEEL = "steel"


class SteelClass(str, Enum):
    STAINLESS_STEEL = "STAINLESS_STEEL"
    OTHER_ALLOY_STEEL = "OTHER_ALLOY_STEEL"
    NON_ALLOY_IRON_STEEL = "NON_ALLOY_IRON_STEEL"


class MetalForm(str, Enum):
    INGOTS = "ingots"
    PRIMARY_FORMS = "primary_forms"
    SEMI_FINISHED = "semi_finished"
    FLAT_ROLLED = "flat_rolled"
    BARS_RODS_HOT_ROLLED_IRREGULAR_COILS = "bars_rods_hot_rolled_irregular_coils"
    BARS_RODS_OTHER = "bars_rods_other"
    ANGLES = "angles"
    SHAPES = "shapes"
    SECTIONS = "sections"
    HOLLOW_DRILL_BARS = "hollow_drill_bars"
    WIRE = "wire"
    ANGLES_SHAPES_L = "angles_shapes"  # L-profiles


# ---------------------------------------------------------------------------
# Input / Output dataclasses
# ---------------------------------------------------------------------------


@dataclass
class SteelClassificationInput:
    """All inputs required by the Chapter-72 decision tree."""

    material_type: MaterialType
    # Chemical composition percentages (required when material_type == STEEL)
    carbon_pct: Optional[float] = None
    chromium_pct: Optional[float] = None
    manganese_pct: Optional[float] = None
    aluminium_pct: Optional[float] = None
    silicon_pct: Optional[float] = None
    nickel_pct: Optional[float] = None
    molybdenum_pct: Optional[float] = None
    # Physical form
    form: Optional[MetalForm] = None
    width_mm: Optional[float] = None  # required for flat-rolled products


@dataclass
class SteelClassificationOutput:
    heading: str                    # 4-digit HS heading, e.g. "7219"
    chapter: str = "72"
    steel_class: Optional[SteelClass] = None
    reasoning: str = ""
    audit_steps: list[AuditStep] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------


def classify_steel(inp: SteelClassificationInput) -> SteelClassificationOutput:
    """
    Apply the Chapter-72 tariff decision tree from the Veritariff Happy Path spec.
    Returns a SteelClassificationOutput or raises EngineError on invalid input.
    """
    steps: list[AuditStep] = []
    warnings: list[str] = []

    # ------------------------------------------------------------------
    # Step 1.1 – Material-type gate
    # ------------------------------------------------------------------
    step1_input = {"material_type": inp.material_type}

    if inp.material_type == MaterialType.WASTE_OR_SCRAP:
        steps.append(_audit("step_1_1_material_gate", step1_input, {"heading": "7204"}))
        return SteelClassificationOutput(
            heading="7204",
            reasoning="Waste or scrap of iron/steel → Heading 7204",
            audit_steps=steps,
            warnings=warnings,
        )

    if inp.material_type == MaterialType.GRANULES_OR_POWDERS:
        steps.append(_audit("step_1_1_material_gate", step1_input, {"heading": "7205"}))
        return SteelClassificationOutput(
            heading="7205",
            reasoning="Granules or powders of pig iron/iron/steel → Heading 7205",
            audit_steps=steps,
            warnings=warnings,
        )

    if inp.material_type == MaterialType.DIRECT_REDUCTION_SPONGE_IRON:
        steps.append(_audit("step_1_1_material_gate", step1_input, {"heading": "7203"}))
        return SteelClassificationOutput(
            heading="7203",
            reasoning="Direct-reduction sponge iron → Heading 7203",
            audit_steps=steps,
            warnings=warnings,
        )

    if inp.material_type == MaterialType.PIG_IRON:
        carbon = inp.carbon_pct or 0.0
        manganese = inp.manganese_pct or 0.0
        out_snap = {"carbon_pct": carbon, "manganese_pct": manganese}

        if carbon > 2.0:
            steps.append(_audit("step_1_1_pig_iron", {**step1_input, **out_snap}, {"heading": "7201", "subtype": "pig_iron"}))
            return SteelClassificationOutput(
                heading="7201",
                reasoning=f"Pig iron (carbon {carbon}% > 2.0%) → Heading 7201",
                audit_steps=steps,
                warnings=warnings,
            )
        if manganese > 6.0:
            steps.append(_audit("step_1_1_pig_iron", {**step1_input, **out_snap}, {"heading": "7201", "subtype": "spiegeleisen"}))
            return SteelClassificationOutput(
                heading="7201",
                reasoning=f"Spiegeleisen (Mn {manganese}% > 6.0%) → Heading 7201",
                audit_steps=steps,
                warnings=warnings,
            )
        # Default pig iron fallback
        steps.append(_audit("step_1_1_pig_iron", {**step1_input, **out_snap}, {"heading": "7201"}))
        warnings.append("Pig iron classified to 7201; verify carbon/manganese percentages")
        return SteelClassificationOutput(
            heading="7201",
            reasoning="Pig iron → Heading 7201",
            audit_steps=steps,
            warnings=warnings,
        )

    if inp.material_type == MaterialType.FERRO_ALLOY:
        steps.append(_audit("step_1_1_material_gate", step1_input, {"heading": "7202"}))
        return SteelClassificationOutput(
            heading="7202",
            reasoning="Ferro-alloy → Heading 7202",
            audit_steps=steps,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Step 1.2 – Steel: determine alloy class
    # ------------------------------------------------------------------
    if inp.carbon_pct is None:
        raise EngineError("MISSING_INPUT", "carbon_pct is required for steel classification")

    carbon = inp.carbon_pct
    chromium = inp.chromium_pct or 0.0
    manganese = inp.manganese_pct or 0.0
    aluminium = inp.aluminium_pct or 0.0
    silicon = inp.silicon_pct or 0.0
    nickel = inp.nickel_pct or 0.0
    molybdenum = inp.molybdenum_pct or 0.0

    composition_snap = {
        "carbon_pct": carbon,
        "chromium_pct": chromium,
        "manganese_pct": manganese,
        "aluminium_pct": aluminium,
    }

    # Stainless: carbon ≤ 1.2 AND chromium ≥ 10.5
    if carbon <= 1.2 and chromium >= 10.5:
        steel_class = SteelClass.STAINLESS_STEEL
        steps.append(_audit("step_1_2_alloy_classification", composition_snap, {"steel_class": steel_class}))
        return _classify_stainless(inp, steel_class, steps, warnings)

    # Other alloy: any of Al≥0.3, Mn≥1.65, Si≥0.6, Cr≥0.3, Ni≥0.3, Mo≥0.08
    _other_alloy = (
        aluminium >= 0.3
        or manganese >= 1.65
        or silicon >= 0.6
        or chromium >= 0.3
        or nickel >= 0.3
        or molybdenum >= 0.08
    )
    if _other_alloy:
        steel_class = SteelClass.OTHER_ALLOY_STEEL
        steps.append(_audit("step_1_2_alloy_classification", composition_snap, {"steel_class": steel_class}))
        return _classify_other_alloy(inp, steel_class, steps, warnings)

    # Non-alloy iron/steel (default)
    steel_class = SteelClass.NON_ALLOY_IRON_STEEL
    steps.append(_audit("step_1_2_alloy_classification", composition_snap, {"steel_class": steel_class}))
    return _classify_non_alloy(inp, steel_class, steps, warnings)


# ---------------------------------------------------------------------------
# Step 1.2A – Stainless steel → 7218-7223
# ---------------------------------------------------------------------------

def _classify_stainless(
    inp: SteelClassificationInput,
    steel_class: SteelClass,
    steps: list[AuditStep],
    warnings: list[str],
) -> SteelClassificationOutput:
    if inp.form is None:
        raise EngineError("MISSING_INPUT", "form is required for stainless steel classification")

    form = inp.form
    width = inp.width_mm or 0.0
    form_snap = {"form": form, "width_mm": width}

    if form in (MetalForm.INGOTS, MetalForm.PRIMARY_FORMS, MetalForm.SEMI_FINISHED):
        heading = "7218"
    elif form == MetalForm.FLAT_ROLLED and width >= 600:
        heading = "7219"
    elif form == MetalForm.FLAT_ROLLED and width < 600:
        if width == 0.0:
            warnings.append("width_mm not provided for flat-rolled product; defaulted to <600 mm path")
        heading = "7220"
    elif form == MetalForm.BARS_RODS_HOT_ROLLED_IRREGULAR_COILS:
        heading = "7221"
    elif form in (MetalForm.BARS_RODS_OTHER, MetalForm.ANGLES, MetalForm.SHAPES, MetalForm.SECTIONS):
        heading = "7222"
    elif form == MetalForm.WIRE:
        heading = "7223"
    else:
        raise EngineError("UNCLASSIFIABLE", f"Form '{form}' not mappable for stainless steel")

    steps.append(_audit("step_1_2A_stainless_form", form_snap, {"heading": heading}))
    return SteelClassificationOutput(
        heading=heading,
        steel_class=steel_class,
        reasoning=f"Stainless steel ({form}, width={width} mm) → Heading {heading}",
        audit_steps=steps,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Step 1.2B – Other alloy steel → 7224-7228
# ---------------------------------------------------------------------------

def _classify_other_alloy(
    inp: SteelClassificationInput,
    steel_class: SteelClass,
    steps: list[AuditStep],
    warnings: list[str],
) -> SteelClassificationOutput:
    if inp.form is None:
        raise EngineError("MISSING_INPUT", "form is required for other alloy steel classification")

    form = inp.form
    width = inp.width_mm or 0.0
    form_snap = {"form": form, "width_mm": width}

    if form in (MetalForm.INGOTS, MetalForm.PRIMARY_FORMS, MetalForm.SEMI_FINISHED):
        heading = "7224"
    elif form == MetalForm.FLAT_ROLLED and width >= 600:
        heading = "7225"
    elif form == MetalForm.FLAT_ROLLED and width < 600:
        if width == 0.0:
            warnings.append("width_mm not provided for flat-rolled product; defaulted to <600 mm path")
        heading = "7226"
    elif form == MetalForm.BARS_RODS_HOT_ROLLED_IRREGULAR_COILS:
        heading = "7227"
    elif form in (
        MetalForm.BARS_RODS_OTHER,
        MetalForm.ANGLES,
        MetalForm.SHAPES,
        MetalForm.SECTIONS,
        MetalForm.HOLLOW_DRILL_BARS,
    ):
        heading = "7228"
    elif form == MetalForm.WIRE:
        heading = "7228"
        warnings.append("Wire of other alloy steel falls under heading 7229; verify subheading")
        heading = "7229"
    else:
        raise EngineError("UNCLASSIFIABLE", f"Form '{form}' not mappable for other alloy steel")

    steps.append(_audit("step_1_2B_other_alloy_form", form_snap, {"heading": heading}))
    return SteelClassificationOutput(
        heading=heading,
        steel_class=steel_class,
        reasoning=f"Other alloy steel ({form}, width={width} mm) → Heading {heading}",
        audit_steps=steps,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Step 1.2C – Non-alloy iron/steel → 7206-7217
# ---------------------------------------------------------------------------

def _classify_non_alloy(
    inp: SteelClassificationInput,
    steel_class: SteelClass,
    steps: list[AuditStep],
    warnings: list[str],
) -> SteelClassificationOutput:
    if inp.form is None:
        raise EngineError("MISSING_INPUT", "form is required for non-alloy steel classification")

    form = inp.form
    width = inp.width_mm or 0.0
    form_snap = {"form": form, "width_mm": width}

    if form == MetalForm.INGOTS:
        heading = "7206"
    elif form in (MetalForm.PRIMARY_FORMS, MetalForm.SEMI_FINISHED):
        heading = "7207"
    elif form == MetalForm.FLAT_ROLLED and width >= 600:
        heading = "7208"
        warnings.append("Hot-rolled, cold-rolled, or coated flat products (≥600 mm) may fall under 7208, 7209, or 7210; verify surface treatment")
    elif form == MetalForm.FLAT_ROLLED and width < 600:
        if width == 0.0:
            warnings.append("width_mm not provided for flat-rolled product; defaulted to <600 mm path")
        heading = "7211"
        warnings.append("Flat-rolled non-alloy steel <600 mm may fall under 7211 or 7212; verify surface treatment")
    elif form == MetalForm.BARS_RODS_HOT_ROLLED_IRREGULAR_COILS:
        heading = "7213"
        warnings.append("Hot-rolled bars/rods may fall under 7213, 7214, or 7215; verify product details")
    elif form in (MetalForm.ANGLES_SHAPES_L, MetalForm.ANGLES, MetalForm.SHAPES, MetalForm.SECTIONS):
        heading = "7216"
    elif form == MetalForm.WIRE:
        heading = "7217"
    elif form in (MetalForm.BARS_RODS_OTHER,):
        heading = "7214"
    else:
        raise EngineError("UNCLASSIFIABLE", f"Form '{form}' not mappable for non-alloy steel")

    steps.append(_audit("step_1_2C_non_alloy_form", form_snap, {"heading": heading}))
    return SteelClassificationOutput(
        heading=heading,
        steel_class=steel_class,
        reasoning=f"Non-alloy iron/steel ({form}, width={width} mm) → Heading {heading}",
        audit_steps=steps,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _audit(step_name: str, inp: dict, out: dict) -> AuditStep:
    return AuditStep(
        step_name=step_name,
        formula_description=f"Chapter-72 decision tree: {step_name}",
        input_snapshot=inp,
        output_snapshot=out,
    )
