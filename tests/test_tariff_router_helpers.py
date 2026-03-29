from types import SimpleNamespace

from app.api.v1.tariff.router import _measure_has_any_duty, _normalize_origin_iso2


def test_measure_has_any_duty_true_when_is_nihil() -> None:
    m = SimpleNamespace(
        rate_ad_valorem=None,
        rate_specific_amount=None,
        measure_condition={"duty": {"is_nihil": True}},
    )
    assert _measure_has_any_duty(m) is True


def test_measure_has_any_duty_true_when_raw_expression_present() -> None:
    m = SimpleNamespace(
        rate_ad_valorem=None,
        rate_specific_amount=None,
        measure_condition={"duty": {"raw_expression": "0%"}},
    )
    assert _measure_has_any_duty(m) is True


def test_measure_has_any_duty_false_when_no_signals() -> None:
    m = SimpleNamespace(
        rate_ad_valorem=None,
        rate_specific_amount=None,
        measure_condition=None,
    )
    assert _measure_has_any_duty(m) is False


def test_normalize_origin_iso2_uk_to_gb() -> None:
    assert _normalize_origin_iso2("UK") == "GB"
