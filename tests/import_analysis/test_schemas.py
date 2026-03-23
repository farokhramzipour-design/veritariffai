"""
Unit tests for Import Analysis schemas.

These tests deliberately do NOT touch the network — they validate schema
validation, field normalisation, and computed properties.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.import_analysis import ImportAnalysisRequest


class TestImportAnalysisRequest:
    def test_valid_minimal(self):
        req = ImportAnalysisRequest(
            product_description="Men's woven cotton trousers",
            origin_country="cn",
            destination_country="de",
        )
        assert req.origin_country == "CN"
        assert req.destination_country == "DE"
        assert req.currency == "EUR"

    def test_iso_uppercasing(self):
        req = ImportAnalysisRequest(
            product_description="Widget",
            origin_country="  gb  ",
            destination_country="us",
            currency="usd",
        )
        assert req.origin_country == "GB"
        assert req.destination_country == "US"
        assert req.currency == "USD"

    def test_full_request(self):
        req = ImportAnalysisRequest(
            product_description="Men's woven cotton trousers",
            origin_country="CN",
            destination_country="DE",
            customs_value=1000.0,
            currency="EUR",
            freight=100.0,
            insurance=20.0,
            incoterms="FOB",
        )
        assert req.customs_value == 1000.0
        assert req.freight == 100.0

    def test_product_description_too_short(self):
        with pytest.raises(ValidationError):
            ImportAnalysisRequest(
                product_description="X",
                origin_country="CN",
                destination_country="DE",
            )

    def test_negative_customs_value_rejected(self):
        with pytest.raises(ValidationError):
            ImportAnalysisRequest(
                product_description="Laptop",
                origin_country="CN",
                destination_country="DE",
                customs_value=-100.0,
            )

    def test_negative_freight_rejected(self):
        with pytest.raises(ValidationError):
            ImportAnalysisRequest(
                product_description="Laptop",
                origin_country="CN",
                destination_country="DE",
                freight=-50.0,
            )
