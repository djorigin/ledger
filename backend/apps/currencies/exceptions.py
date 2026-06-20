class CurrencyError(Exception):
    """Base class for all apps.currencies domain errors."""


class ExchangeRateNotFoundError(CurrencyError):
    pass
