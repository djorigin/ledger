from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from apps.currencies.models import ExchangeRate
from apps.currencies.services import backfill_exchange_rates, fetch_latest_exchange_rates

pytestmark = pytest.mark.django_db


def _latest_fixture(base):
    rates_by_base = {
        "AUD": {"CNY": 4.7482, "USD": 0.70143},
        "CNY": {"AUD": 0.21059, "USD": 0.14773},
        "USD": {"AUD": 1.42598, "CNY": 6.7691},
    }
    return {"amount": 1.0, "base": base, "date": "2026-06-19", "rates": rates_by_base[base]}


def test_fetch_latest_exchange_rates_creates_expected_rows():
    with patch(
        "apps.currencies.services._fetch_rates_from_provider",
        side_effect=lambda *, base, symbols: _latest_fixture(base),
    ):
        fetch_latest_exchange_rates()

    assert ExchangeRate.objects.count() == 6
    aud_cny = ExchangeRate.objects.get(from_currency="AUD", to_currency="CNY")
    assert aud_cny.rate == Decimal("4.7482")
    assert aud_cny.date == date(2026, 6, 19)


def test_fetch_latest_exchange_rates_is_idempotent():
    with patch(
        "apps.currencies.services._fetch_rates_from_provider",
        side_effect=lambda *, base, symbols: _latest_fixture(base),
    ):
        fetch_latest_exchange_rates()
        fetch_latest_exchange_rates()

    assert ExchangeRate.objects.count() == 6


def test_backfill_exchange_rates_creates_rows_across_date_range_skipping_gaps():
    def _range_fixture(*, base, symbols, start_date, end_date):
        rates_by_base = {
            "AUD": {"2025-12-31": {"CNY": 4.679}, "2026-01-02": {"CNY": 4.682}},
            "CNY": {"2025-12-31": {"AUD": 0.2137}, "2026-01-02": {"AUD": 0.2136}},
            "USD": {"2025-12-31": {"AUD": 1.4}, "2026-01-02": {"AUD": 1.41}},
        }
        return {
            "amount": 1.0, "base": base,
            "start_date": "2025-12-31", "end_date": "2026-01-02",
            "rates": rates_by_base[base],
        }

    with patch(
        "apps.currencies.services._fetch_rate_range_from_provider", side_effect=_range_fixture
    ):
        backfill_exchange_rates(start_date=date(2025, 12, 31), end_date=date(2026, 1, 2))

    assert not ExchangeRate.objects.filter(date=date(2026, 1, 1)).exists()
    assert ExchangeRate.objects.filter(date=date(2025, 12, 31)).count() == 3
    assert ExchangeRate.objects.filter(date=date(2026, 1, 2)).count() == 3
