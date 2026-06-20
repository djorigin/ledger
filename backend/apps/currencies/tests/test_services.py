from datetime import date
from decimal import Decimal

import pytest

from apps.currencies.exceptions import ExchangeRateNotFoundError
from apps.currencies.models import ExchangeRate
from apps.currencies.services import convert, get_rate

pytestmark = pytest.mark.django_db


def test_convert_same_currency_short_circuits_without_db_lookup():
    assert ExchangeRate.objects.count() == 0
    result = convert(
        amount=Decimal("100"), from_currency="AUD", to_currency="AUD", on_date=date(2026, 1, 1)
    )
    assert result == Decimal("100")
    assert ExchangeRate.objects.count() == 0


def test_get_rate_finds_exact_date_match():
    ExchangeRate.objects.create(
        date=date(2026, 1, 2), from_currency="AUD", to_currency="CNY", rate=Decimal("4.7482")
    )
    rate = get_rate(from_currency="AUD", to_currency="CNY", on_date=date(2026, 1, 2))
    assert rate == Decimal("4.7482")


def test_get_rate_falls_back_to_most_recent_rate_on_or_before_date():
    # Friday 2026-01-02 has a rate; no weekend rows (matches ECB's real gaps).
    ExchangeRate.objects.create(
        date=date(2026, 1, 2), from_currency="AUD", to_currency="CNY", rate=Decimal("4.7482")
    )
    rate = get_rate(from_currency="AUD", to_currency="CNY", on_date=date(2026, 1, 3))
    assert rate == Decimal("4.7482")


def test_get_rate_picks_most_recent_when_multiple_candidates_exist():
    ExchangeRate.objects.create(
        date=date(2026, 1, 1), from_currency="AUD", to_currency="CNY", rate=Decimal("4.70")
    )
    ExchangeRate.objects.create(
        date=date(2026, 1, 2), from_currency="AUD", to_currency="CNY", rate=Decimal("4.80")
    )
    rate = get_rate(from_currency="AUD", to_currency="CNY", on_date=date(2026, 1, 3))
    assert rate == Decimal("4.80")


def test_get_rate_raises_not_found_when_no_rate_exists_before_date():
    ExchangeRate.objects.create(
        date=date(2026, 1, 5), from_currency="AUD", to_currency="CNY", rate=Decimal("4.80")
    )
    with pytest.raises(ExchangeRateNotFoundError):
        get_rate(from_currency="AUD", to_currency="CNY", on_date=date(2026, 1, 1))


def test_convert_uses_rate_on_transaction_date_not_todays_rate():
    ExchangeRate.objects.create(
        date=date(2026, 1, 1), from_currency="AUD", to_currency="CNY", rate=Decimal("4.50")
    )
    ExchangeRate.objects.create(
        date=date(2026, 6, 1), from_currency="AUD", to_currency="CNY", rate=Decimal("4.90")
    )
    result = convert(
        amount=Decimal("100"), from_currency="AUD", to_currency="CNY", on_date=date(2026, 1, 1)
    )
    assert result == Decimal("450.00")
