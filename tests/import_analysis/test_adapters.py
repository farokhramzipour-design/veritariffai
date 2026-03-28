"""
Unit tests for tariff and VAT adapters.

These tests exercise the mock data layer — no external network calls.
"""
from __future__ import annotations

import asyncio

import pytest

from app.adapters.tariff_adapter import get_tariff_data
from app.adapters.vat_adapter import get_vat_data


class TestTariffAdapter:
    def _run(self, coro):
        return asyncio.run(coro)

    def test_cotton_trousers_cn_to_de(self):
        result = self._run(get_tariff_data("620342", "CN", "DE"))
        assert result.duty_rate == 12.0        # EU MFN for Chapter 62
        assert result.anti_dumping is False    # No AD on clothing from CN

    def test_steel_cn_to_de_has_antidumping(self):
        result = self._run(get_tariff_data("720811", "CN", "DE"))
        assert result.duty_rate == 3.0
        assert result.anti_dumping is True
        assert result.anti_dumping_rate == pytest.approx(47.8)

    def test_uk_to_de_same_rate(self):
        result = self._run(get_tariff_data("620342", "GB", "DE"))
        # UK-origin goods: duty rate same as CN under MFN — preference via TCA handled separately
        assert result.duty_rate == 12.0

    def test_machinery_low_duty(self):
        result = self._run(get_tariff_data("847130", "CN", "FR"))
        assert result.duty_rate == pytest.approx(1.7, rel=0.01)

    def test_documents_required_steel(self):
        result = self._run(get_tariff_data("720811", "CN", "DE"))
        assert any("Mill Test" in d for d in result.documents_required)

    def test_ev_cn_countervailing(self):
        result = self._run(get_tariff_data("870380", "CN", "DE"))
        assert result.countervailing is True
        assert result.countervailing_rate == pytest.approx(35.3)


class TestVATAdapter:
    def _run(self, coro):
        return asyncio.run(coro)

    def test_germany_standard_vat(self):
        result = self._run(get_vat_data("DE", "620342"))
        assert result.vat_rate == 19.0
        assert result.vat_category == "STANDARD"

    def test_france_standard_vat(self):
        result = self._run(get_vat_data("FR", "620342"))
        assert result.vat_rate == 20.0

    def test_uk_vat(self):
        result = self._run(get_vat_data("GB", "620342"))
        assert result.vat_rate == 20.0

    def test_unknown_country_returns_none(self):
        result = self._run(get_vat_data("ZZ", "620342"))
        assert result.vat_rate is None

    def test_us_no_vat(self):
        result = self._run(get_vat_data("US", "620342"))
        assert result.vat_rate == 0.0
