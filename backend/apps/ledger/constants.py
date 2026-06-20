from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

SUPPORTED_CURRENCIES = ["AUD", "CNY", "USD"]


def validate_currency_code(value):
    if value not in SUPPORTED_CURRENCIES:
        raise ValidationError(
            _("%(value)s is not a supported currency."),
            params={"value": value},
        )
