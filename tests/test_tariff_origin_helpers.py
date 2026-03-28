from types import SimpleNamespace

from app.api.v1.tariff.router import _measure_duty_rate_pct, _rate_basis_for_measure


def test_rate_basis_mfn() -> None:
    assert _rate_basis_for_measure(measure_type="MFN", origin_code="1011") == "MFN"


def test_rate_basis_bilateral_preference() -> None:
    assert _rate_basis_for_measure(measure_type="PREFERENTIAL", origin_code="GB") == "bilateral_preference"


def test_rate_basis_group_preference() -> None:
    assert _rate_basis_for_measure(measure_type="PREFERENTIAL", origin_code="2005") == "group_preference"


def test_measure_duty_rate_pct_nihil() -> None:
    m = SimpleNamespace(
        rate_ad_valorem=None,
        rate_specific_amount=None,
        measure_condition={"duty": {"is_nihil": True}},
    )
    assert _measure_duty_rate_pct(m) == 0.0

