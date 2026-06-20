from decimal import Decimal

import requests

from apps.currencies.exceptions import ExchangeRateNotFoundError
from apps.currencies.models import ExchangeRate
from apps.ledger.constants import SUPPORTED_CURRENCIES

FRANKFURTER_BASE_URL = "https://api.frankfurter.dev/v1"
FRANKFURTER_SOURCE = "frankfurter.dev"


def _fetch_rates_from_provider(*, base, symbols):
    """Thin wrapper around the 'latest' HTTP call so tests can mock just this
    function and never touch the network. Returns the parsed JSON response,
    e.g. {"amount": 1.0, "base": "AUD", "date": "2026-06-19",
          "rates": {"CNY": 4.7482, "USD": 0.70143}}."""
    response = requests.get(
        f"{FRANKFURTER_BASE_URL}/latest",
        params={"base": base, "symbols": ",".join(symbols)},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def _fetch_rate_range_from_provider(*, base, symbols, start_date, end_date):
    """Thin wrapper around the date-range HTTP call. Returns the parsed JSON
    response, e.g. {"amount": 1.0, "base": "AUD",
          "start_date": "2025-12-31", "end_date": "2026-01-05",
          "rates": {"2025-12-31": {"CNY": 4.679}, "2026-01-02": {"CNY": 4.682}}}."""
    response = requests.get(
        f"{FRANKFURTER_BASE_URL}/{start_date.isoformat()}..{end_date.isoformat()}",
        params={"base": base, "symbols": ",".join(symbols)},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def fetch_latest_exchange_rates():
    """
    Fetches the most recently published rate for every ordered pair among
    SUPPORTED_CURRENCIES (one API call per base currency) and get_or_creates
    an ExchangeRate row per pair. Idempotent: re-running for a date that's
    already stored creates nothing new and raises nothing.
    """
    created_or_existing = []
    for base in SUPPORTED_CURRENCIES:
        symbols = [c for c in SUPPORTED_CURRENCIES if c != base]
        payload = _fetch_rates_from_provider(base=base, symbols=symbols)
        rate_date = payload["date"]
        for to_currency, rate_value in payload["rates"].items():
            obj, _created = ExchangeRate.objects.get_or_create(
                date=rate_date,
                from_currency=base,
                to_currency=to_currency,
                source=FRANKFURTER_SOURCE,
                defaults={"rate": Decimal(str(rate_value))},
            )
            created_or_existing.append(obj)
    return created_or_existing


def backfill_exchange_rates(*, start_date, end_date):
    """
    Seeds historical ExchangeRate rows for every ordered pair among
    SUPPORTED_CURRENCIES across [start_date, end_date] inclusive, using one
    date-range API call per base currency. Non-trading days (the provider
    simply omits them) are skipped automatically. Idempotent like
    fetch_latest_exchange_rates.
    """
    created_or_existing = []
    for base in SUPPORTED_CURRENCIES:
        symbols = [c for c in SUPPORTED_CURRENCIES if c != base]
        payload = _fetch_rate_range_from_provider(
            base=base, symbols=symbols, start_date=start_date, end_date=end_date
        )
        for rate_date, rates_for_date in payload["rates"].items():
            for to_currency, rate_value in rates_for_date.items():
                obj, _created = ExchangeRate.objects.get_or_create(
                    date=rate_date,
                    from_currency=base,
                    to_currency=to_currency,
                    source=FRANKFURTER_SOURCE,
                    defaults={"rate": Decimal(str(rate_value))},
                )
                created_or_existing.append(obj)
    return created_or_existing


def get_rate(*, from_currency, to_currency, on_date):
    """
    Returns the exchange rate to multiply an amount in from_currency by to
    get the equivalent in to_currency, using the most recent rate on or
    before on_date (the provider doesn't publish on weekends/holidays, so an
    exact match isn't guaranteed). Raises ExchangeRateNotFoundError if no
    rate exists for this pair on or before on_date.
    """
    if from_currency == to_currency:
        return Decimal("1")

    rate_row = (
        ExchangeRate.objects.filter(
            from_currency=from_currency,
            to_currency=to_currency,
            date__lte=on_date,
        )
        .order_by("-date")
        .first()
    )
    if rate_row is None:
        raise ExchangeRateNotFoundError(
            f"No exchange rate found for {from_currency}->{to_currency} on or before {on_date}."
        )
    return rate_row.rate


def convert(*, amount, from_currency, to_currency, on_date):
    """
    Converts amount from from_currency to to_currency using the rate that
    applied on or before on_date. Deliberately not rounded to money
    precision -- that's the caller's job (e.g. the reporting layer), keeping
    this composable and auditable.
    """
    if from_currency == to_currency:
        return amount
    rate = get_rate(from_currency=from_currency, to_currency=to_currency, on_date=on_date)
    return amount * rate
