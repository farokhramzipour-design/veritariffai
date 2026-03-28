from app.infrastructure.ingestion.origins import classify_origin_code


def test_classify_origin_code_country() -> None:
    assert classify_origin_code("GB") == "country"


def test_classify_origin_code_erga_omnes() -> None:
    assert classify_origin_code("1011") == "erga_omnes"


def test_classify_origin_code_group_numeric() -> None:
    assert classify_origin_code("2005") == "group_numeric"


def test_classify_origin_code_phytosanitary() -> None:
    assert classify_origin_code("4001") == "phytosanitary"


def test_classify_origin_code_safeguard() -> None:
    assert classify_origin_code("5007") == "safeguard"


def test_classify_origin_code_unknown() -> None:
    assert classify_origin_code("XYZ") == "unknown"

