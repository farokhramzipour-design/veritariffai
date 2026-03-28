import pytest

from app.infrastructure.ingestion.duty_parser import parse_duty_expression


@pytest.mark.parametrize(
    "raw,rate",
    [
        ("8.000 %", 8.0),
        ("0.000 %", 0.0),
        ("12.800 %", 12.8),
    ],
)
def test_pure_ad_valorem(raw: str, rate: float):
    d = parse_duty_expression(raw)
    assert d.duty_rate is not None
    assert float(d.duty_rate) == rate
    assert d.duty_expression_code in ("01", "15")


def test_pure_specific():
    d = parse_duty_expression("30.900 EUR DTN")
    assert d.duty_rate is None
    assert d.duty_amount is not None
    assert float(d.duty_amount) == 30.9
    assert d.currency == "EUR"
    assert d.duty_unit == "DTN"
    assert d.duty_expression_code == "02"


def test_compound_av_plus_specific():
    d = parse_duty_expression("10.200 % + 93.100 EUR DTN")
    assert d.duty_rate is not None and float(d.duty_rate) == 10.2
    assert d.duty_amount is not None and float(d.duty_amount) == 93.1
    assert d.duty_unit == "DTN"
    assert d.duty_expression_code == "03"


def test_thousands_separator():
    d = parse_duty_expression("15.000 % + 1,554.300 EUR TNE")
    assert d.duty_rate is not None and float(d.duty_rate) == 15.0
    assert d.duty_amount is not None and float(d.duty_amount) == 1554.3
    assert d.duty_unit == "TNE"
    assert d.currency == "EUR"


def test_specific_plus_specific_with_basis_p():
    d = parse_duty_expression("0.230 EUR KGM P + 5.500 EUR DTN")
    assert d.duty_amount is not None and float(d.duty_amount) == 0.23
    assert d.duty_unit == "KGM"
    assert d.duty_amount_secondary is not None and float(d.duty_amount_secondary) == 5.5
    assert d.duty_unit_secondary == "DTN"
    assert d.duty_measurement_basis == "P"
    assert d.is_alcohol_duty is True


def test_entry_price_component():
    d = parse_duty_expression("7.600 % + EA")
    assert d.duty_rate is not None and float(d.duty_rate) == 7.6
    assert d.has_entry_price is True
    assert d.entry_price_type == "EA"


def test_min_max_clause_and_g_suffix():
    d = parse_duty_expression("18.400 % MIN 22.000 EUR DTN MAX 24.000 EUR DTN")
    assert d.duty_rate is not None and float(d.duty_rate) == 18.4
    assert d.duty_min_amount is not None and float(d.duty_min_amount) == 22.0
    assert d.duty_max_amount is not None and float(d.duty_max_amount) == 24.0
    assert d.duty_unit == "DTN"

    g = parse_duty_expression("10.400 % MIN 1.300 EUR DTN G")
    assert g.duty_gross_weight_basis is True


def test_asv_x_alcohol_compound():
    d = parse_duty_expression("0.075 EUR ASV X + 0.400 EUR HLT")
    assert d.duty_unit == "ASV"
    assert d.is_alcohol_duty is True
    assert d.duty_amount is not None and float(d.duty_amount) == 0.075
    assert d.duty_amount_secondary is not None and float(d.duty_amount_secondary) == 0.4
    assert d.duty_unit_secondary == "HLT"


def test_nihil_and_zero_shorthand():
    nihil = parse_duty_expression("NIHIL")
    assert nihil.is_nihil is True
    assert nihil.duty_rate is not None and float(nihil.duty_rate) == 0.0
    assert nihil.duty_expression_code == "00"

    zero = parse_duty_expression("0")
    assert zero.duty_rate is not None and float(zero.duty_rate) == 0.0
    assert zero.is_nihil is False


def test_cond_v_siv_bands():
    d = parse_duty_expression(
        "Cond: V 52.600 EUR/DTN(01):12.000 % ; V 51.500 EUR/DTN(01):12.000 % + 1.100 EUR DTN ; V 0.000 EUR/DTN(01):0.000 % + 29.800 EUR DTN"
    )
    assert d.siv_bands is not None
    assert len(d.siv_bands) == 3
    assert d.human_readable is not None and "variable rate" in d.human_readable.lower()


def test_cond_r_thresholds():
    d = parse_duty_expression("Cond: R 80.001/KGM(10):; R 0.000/KGM(28):")
    assert d.weight_threshold_bands is not None
    assert len(d.weight_threshold_bands) == 2


def test_cond_l_reduction_bands():
    d = parse_duty_expression(
        "Cond: L 143.010 EUR/DTN(01):0.000 EUR DTN ; L 95.340 EUR/DTN(01):42.903 EUR DTN - 30.000 % ; L 0.000 EUR/DTN(01):82.628 EUR DTN - 90.000 %"
    )
    assert d.reduction_bands is not None
    assert len(d.reduction_bands) >= 2


def test_cond_f_suspension_amounts():
    d = parse_duty_expression("Cond: F 325.000 EUR/MIL(01):0.000 EUR MIL ; F 0.000 EUR/MIL(11):325.000 EUR MIL")
    assert d.duty_full_amount is not None and float(d.duty_full_amount) == 325.0
    assert d.duty_suspended_to is not None and float(d.duty_suspended_to) == 0.0
    assert d.duty_unit == "MIL"


def test_supplementary_unit_only():
    d = parse_duty_expression("NAR")
    assert d.duty_expression_code == "21"
    assert d.duty_unit == "NAR"
