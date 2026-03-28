from datetime import datetime, timezone
from decimal import Decimal

from app.api.v1.analytics.router import _compact_money, _start_of_month, _start_of_prev_month


def test_start_of_month() -> None:
    dt = datetime(2026, 3, 28, 12, 30, 45, tzinfo=timezone.utc)
    assert _start_of_month(dt) == datetime(2026, 3, 1, 0, 0, 0, tzinfo=timezone.utc)


def test_start_of_prev_month() -> None:
    dt = datetime(2026, 3, 28, 12, 30, 45, tzinfo=timezone.utc)
    assert _start_of_prev_month(dt) == datetime(2026, 2, 1, 0, 0, 0, tzinfo=timezone.utc)


def test_start_of_prev_month_rollover_year() -> None:
    dt = datetime(2026, 1, 15, 0, 0, 0, tzinfo=timezone.utc)
    assert _start_of_prev_month(dt) == datetime(2025, 12, 1, 0, 0, 0, tzinfo=timezone.utc)


def test_compact_money() -> None:
    assert _compact_money(Decimal("2300000"), "GBP") == "£2.3M"
    assert _compact_money(Decimal("999"), "GBP") == "£999.00"

