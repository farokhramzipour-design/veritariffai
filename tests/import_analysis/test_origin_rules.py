"""
Unit tests for the origin rules service.
"""
from __future__ import annotations

import asyncio

import pytest

from app.services.origin_rules_service import evaluate


def _run(coro):
    return asyncio.run(coro)


class TestOriginRulesService:
    def test_cn_to_de_no_preference(self):
        result = _run(evaluate("CN", "DE", "620342", duty_rate=12.0))
        assert result.preferential_eligible is False
        assert result.preferential_duty_rate is None

    def test_gb_to_de_tca_preference(self):
        result = _run(evaluate("GB", "DE", "620342", duty_rate=12.0))
        assert result.preferential_eligible is True
        assert result.preferential_duty_rate == 0.0
        assert "TCA" in (result.agreement_name or "")
        assert result.proof_of_origin_required is not None

    def test_de_to_fr_internal_eu(self):
        result = _run(evaluate("DE", "FR", "620342", duty_rate=0.0))
        assert result.preferential_eligible is True
        assert result.preferential_duty_rate == 0.0
        assert "Single Market" in (result.agreement_name or "")

    def test_ch_to_de_bilateral(self):
        result = _run(evaluate("CH", "DE", "620342", duty_rate=12.0))
        assert result.preferential_eligible is True
        assert result.preferential_duty_rate == 0.0

    def test_jp_to_de_epa(self):
        result = _run(evaluate("JP", "DE", "620342", duty_rate=12.0))
        assert result.preferential_eligible is True
        assert "Japan" in (result.agreement_name or "") or "EPA" in (result.agreement_name or "")
