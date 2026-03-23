"""
Unit tests for money, HS, and country utilities.
All pure functions — no I/O, no mocks needed.
"""
from __future__ import annotations

import pytest

from app.utils import hs as hs_util
from app.utils import money as money_util
from app.utils import country as country_util


class TestHSUtils:
    def test_strip(self):
        assert hs_util.strip("6203.42") == "620342"
        assert hs_util.strip("6203 42") == "620342"
        assert hs_util.strip("620342") == "620342"

    def test_chapter(self):
        assert hs_util.chapter("620342") == "62"
        assert hs_util.chapter("8471300000") == "84"

    def test_heading(self):
        assert hs_util.heading("620342") == "6203"

    def test_subheading_6(self):
        assert hs_util.subheading_6("620342") == "620342"
        assert hs_util.subheading_6("6203") == "620300"

    def test_is_valid(self):
        assert hs_util.is_valid("620342") is True
        assert hs_util.is_valid("12") is False    # too short
        assert hs_util.is_valid("12345678901") is False  # too long

    def test_format_display(self):
        assert hs_util.format_display("620342") == "6203.42"
        assert hs_util.format_display("8471300000") == "8471.30.00.00"


class TestCountryUtils:
    def test_is_eu(self):
        assert country_util.is_eu("DE") is True
        assert country_util.is_eu("de") is True
        assert country_util.is_eu("CN") is False
        assert country_util.is_eu("GB") is False

    def test_is_eea(self):
        assert country_util.is_eea("NO") is True
        assert country_util.is_eea("DE") is True
        assert country_util.is_eea("CN") is False


class TestMoneyUtils:
    def test_cif_fob_adds_freight_and_insurance(self):
        cif = money_util.calculate_cif(
            customs_value=1000.0,
            freight=100.0,
            insurance=20.0,
            incoterms="FOB",
        )
        assert cif == 1120.0

    def test_cif_incoterms_no_add(self):
        cif = money_util.calculate_cif(
            customs_value=1120.0,
            freight=100.0,
            insurance=20.0,
            incoterms="CIF",
        )
        assert cif == 1120.0  # not added again

    def test_landed_cost_calculation(self):
        bd = money_util.calculate_landed_cost(
            customs_value=1000.0,
            freight=100.0,
            insurance=20.0,
            incoterms="FOB",
            duty_rate_pct=12.0,
            vat_rate_pct=19.0,
            currency="EUR",
        )
        assert bd.cif_value == 1120.0
        assert bd.duty_amount == pytest.approx(134.4, rel=1e-3)   # 1120 * 12%
        # VAT basis = CIF + duty = 1120 + 134.4 = 1254.4
        assert bd.vat_amount == pytest.approx(238.34, rel=1e-2)   # 1254.4 * 19%
        assert bd.total_landed_cost == pytest.approx(1492.74, rel=1e-2)

    def test_zero_duty(self):
        bd = money_util.calculate_landed_cost(
            customs_value=500.0,
            freight=None,
            insurance=None,
            incoterms=None,
            duty_rate_pct=0.0,
            vat_rate_pct=19.0,
        )
        assert bd.duty_amount == 0.0
        assert bd.vat_amount == pytest.approx(95.0)   # 500 * 19%
