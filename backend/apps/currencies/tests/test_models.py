from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.currencies.models import ExchangeRate

pytestmark = pytest.mark.django_db


def test_exchange_rate_unique_constraint_prevents_duplicate_date_pair_source():
    ExchangeRate.objects.create(
        date=date(2026, 1, 2), from_currency="AUD", to_currency="CNY",
        rate=Decimal("4.7482"), source="frankfurter.dev",
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ExchangeRate.objects.create(
                date=date(2026, 1, 2), from_currency="AUD", to_currency="CNY",
                rate=Decimal("9.9999"), source="frankfurter.dev",
            )


def test_exchange_rate_allows_same_pair_different_source():
    ExchangeRate.objects.create(
        date=date(2026, 1, 2), from_currency="AUD", to_currency="CNY",
        rate=Decimal("4.7482"), source="frankfurter.dev",
    )
    ExchangeRate.objects.create(
        date=date(2026, 1, 2), from_currency="AUD", to_currency="CNY",
        rate=Decimal("4.75"), source="other-provider",
    )
    assert ExchangeRate.objects.count() == 2


def test_exchange_rate_rejects_unsupported_currency_code():
    rate = ExchangeRate(
        date=date(2026, 1, 2), from_currency="ZZZ", to_currency="CNY", rate=Decimal("1")
    )
    with pytest.raises(ValidationError):
        rate.full_clean()


def test_exchange_rate_rejects_same_from_and_to_currency():
    rate = ExchangeRate(
        date=date(2026, 1, 2), from_currency="AUD", to_currency="AUD", rate=Decimal("1")
    )
    with pytest.raises(ValidationError):
        rate.full_clean()
