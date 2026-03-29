from types import SimpleNamespace

from app.api.v1.tariff.router import _origin_member_countries


def test_origin_member_countries_country() -> None:
    o = SimpleNamespace(is_erga_omnes=False, origin_code="GB", iso2="GB", member_iso2_codes=None)
    assert _origin_member_countries(o) == ["GB"]


def test_origin_member_countries_group() -> None:
    o = SimpleNamespace(is_erga_omnes=False, origin_code="1033", iso2=None, member_iso2_codes=["TT", "JM"])
    assert _origin_member_countries(o) == ["TT", "JM"]


def test_origin_member_countries_erga_omnes() -> None:
    o = SimpleNamespace(is_erga_omnes=True, origin_code="1011", iso2=None, member_iso2_codes=None)
    assert _origin_member_countries(o) is None

